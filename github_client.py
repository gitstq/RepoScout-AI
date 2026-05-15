"""
github_client.py - GitHub API 交互模块

提供与 GitHub REST API v3 的交互能力，包括：
- 搜索仓库
- 获取 Trending 仓库（解析 HTML 页面）
- 获取仓库详情
- 获取仓库 README
- GitHub Token 认证
- 请求限流、错误重试、缓存机制

仅使用标准库 urllib，无外部依赖。
"""

import json
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# GitHub API 基础地址
GITHUB_API_BASE = "https://api.github.com"
GITHUB_WEB_BASE = "https://github.com"
DEFAULT_USER_AGENT = "RepoScout-AI/1.0"

# 请求限流相关
DEFAULT_RATE_LIMIT_WINDOW = 60  # 秒
MIN_REQUEST_INTERVAL = 1.0  # 最小请求间隔（秒）
MAX_RETRIES = 3  # 最大重试次数
RETRY_BACKOFF = 2  # 重试退避因子（秒）


class RateLimiter:
    """简单的请求限流器，确保不超过 GitHub API 速率限制。"""

    def __init__(self, min_interval: float = MIN_REQUEST_INTERVAL) -> None:
        """初始化限流器。

        Args:
            min_interval: 两次请求之间的最小间隔（秒）。
        """
        self._min_interval = min_interval
        self._last_request_time: float = 0.0
        self._remaining: Optional[int] = None
        self._reset_time: Optional[int] = None

    def wait_if_needed(self) -> None:
        """如果距离上次请求时间不足最小间隔，则等待。"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            sleep_time = self._min_interval - elapsed
            logger.debug("限流等待 %.2f 秒", sleep_time)
            time.sleep(sleep_time)

        # 如果已知剩余配额不足，等待到重置时间
        if self._remaining is not None and self._remaining <= 1 and self._reset_time:
            wait = max(0, self._reset_time - time.time()) + 1
            logger.warning("API 配额耗尽，等待 %d 秒后重试", int(wait))
            time.sleep(wait)

    def update_from_headers(self, headers: Dict[str, str]) -> None:
        """根据响应头更新限流信息。

        Args:
            headers: HTTP 响应头字典。
        """
        if "X-RateLimit-Remaining" in headers:
            self._remaining = int(headers["X-RateLimit-Remaining"])
        if "X-RateLimit-Reset" in headers:
            self._reset_time = int(headers["X-RateLimit-Reset"])

    @property
    def remaining(self) -> Optional[int]:
        """返回剩余请求配额。"""
        return self._remaining


class ResponseCache:
    """基于内存的简单响应缓存，支持 TTL 过期。"""

    def __init__(self, default_ttl: int = 300) -> None:
        """初始化缓存。

        Args:
            default_ttl: 默认缓存过期时间（秒）。
        """
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """从缓存中获取数据，如果过期则返回 None。

        Args:
            key: 缓存键。

        Returns:
            缓存的数据，如果不存在或已过期则返回 None。
        """
        if key in self._cache:
            data, expire_at = self._cache[key]
            if time.time() < expire_at:
                logger.debug("缓存命中: %s", key)
                return data
            else:
                del self._cache[key]
                logger.debug("缓存过期: %s", key)
        return None

    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """将数据存入缓存。

        Args:
            key: 缓存键。
            data: 要缓存的数据。
            ttl: 缓存过期时间（秒），None 则使用默认值。
        """
        expire_at = time.time() + (ttl if ttl is not None else self._default_ttl)
        self._cache[key] = (data, expire_at)
        logger.debug("缓存写入: %s (TTL=%ds)", key, ttl or self._default_ttl)

    def clear(self) -> None:
        """清空所有缓存。"""
        self._cache.clear()
        logger.debug("缓存已清空")

    @property
    def size(self) -> int:
        """返回缓存条目数。"""
        return len(self._cache)


class GitHubClient:
    """GitHub API 客户端，封装所有与 GitHub 的交互。

    Features:
        - Token 认证（环境变量 GITHUB_TOKEN 或构造参数）
        - 自动限流与重试
        - 响应缓存
        - 搜索仓库、获取详情、获取 README、解析 Trending 页面
    """

    def __init__(
        self,
        token: Optional[str] = None,
        cache_ttl: int = 300,
        timeout: int = 30,
    ) -> None:
        """初始化 GitHub 客户端。

        Args:
            token: GitHub Personal Access Token。如果为 None，则尝试从环境变量读取。
            cache_ttl: 缓存过期时间（秒）。
            timeout: HTTP 请求超时时间（秒）。
        """
        self._token = token or os.environ.get("GITHUB_TOKEN", "")
        self._timeout = timeout
        self._rate_limiter = RateLimiter()
        self._cache = ResponseCache(default_ttl=cache_ttl)
        logger.info("GitHubClient 初始化完成 (token=%s, cache_ttl=%ds)",
                     "已配置" if self._token else "未配置", cache_ttl)

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头。

        Returns:
            包含认证信息和 User-Agent 的请求头字典。
        """
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/vnd.github.v3+json",
        }
        if self._token:
            headers["Authorization"] = f"token {self._token}"
        return headers

    def _make_request(
        self,
        url: str,
        params: Optional[Dict[str, str]] = None,
        method: str = "GET",
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """发起 HTTP 请求到 GitHub API。

        Args:
            url: 请求的完整 URL。
            params: 查询参数字典。
            method: HTTP 方法（GET/POST 等）。
            use_cache: 是否使用缓存。

        Returns:
            解析后的 JSON 响应字典。

        Raises:
            GitHubAPIError: 当 API 返回错误时。
            urllib.error.URLError: 当网络请求失败时。
        """
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"

        # 检查缓存（仅 GET 请求）
        cache_key = f"{method}:{url}"
        if use_cache and method.upper() == "GET":
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        # 限流
        self._rate_limiter.wait_if_needed()

        headers = self._build_headers()
        req = urllib.request.Request(url, headers=headers, method=method.upper())

        last_error: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                logger.debug("请求 %s (尝试 %d/%d)", url, attempt + 1, MAX_RETRIES)
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
                    resp_headers = {k: v for k, v in resp.headers.items()}
                    self._rate_limiter.update_from_headers(resp_headers)

                    data = json.loads(body)

                    # 缓存成功响应
                    if use_cache and method.upper() == "GET":
                        self._cache.set(cache_key, data)

                    return data

            except urllib.error.HTTPError as e:
                last_error = e
                error_body = ""
                try:
                    error_body = e.read().decode("utf-8", errors="replace")
                except Exception:
                    pass

                if e.code == 403 and "rate limit" in error_body.lower():
                    logger.warning("触发速率限制，等待重试...")
                    self._rate_limiter.update_from_headers(dict(e.headers))
                    self._rate_limiter.wait_if_needed()
                    continue

                if e.code == 404:
                    logger.error("资源不存在: %s", url)
                    raise GitHubAPIError(f"资源不存在: {url}", status_code=404) from e

                if e.code >= 500:
                    logger.warning("服务器错误 %d，重试中...", e.code)
                    time.sleep(RETRY_BACKOFF ** attempt)
                    continue

                logger.error("API 错误 %d: %s", e.code, error_body[:200])
                raise GitHubAPIError(
                    f"API 错误 {e.code}: {error_body[:200]}",
                    status_code=e.code,
                ) from e

            except urllib.error.URLError as e:
                last_error = e
                logger.warning("网络错误 (尝试 %d/%d): %s", attempt + 1, MAX_RETRIES, e)
                time.sleep(RETRY_BACKOFF ** attempt)
                continue

        # 所有重试都失败
        raise GitHubAPIError(
            f"请求失败，已重试 {MAX_RETRIES} 次: {last_error}"
        ) from last_error

    # ==================== 公开 API ====================

    def search_repositories(
        self,
        query: str,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 30,
        page: int = 1,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """搜索 GitHub 仓库。

        Args:
            query: 搜索关键词。
            sort: 排序字段（stars/forks/updated）。
            order: 排序方向（asc/desc）。
            per_page: 每页结果数（最大 100）。
            page: 页码。
            language: 编程语言过滤。

        Returns:
            包含 total_count 和 items 的搜索结果字典。
        """
        params: Dict[str, str] = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": str(min(per_page, 100)),
            "page": str(page),
        }
        if language:
            params["q"] = f"{query} language:{language}"

        logger.info("搜索仓库: query=%s, sort=%s, lang=%s", query, sort, language)
        return self._make_request(
            f"{GITHUB_API_BASE}/search/repositories",
            params=params,
        )

    def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """获取仓库详情。

        Args:
            owner: 仓库所有者。
            repo: 仓库名称。

        Returns:
            仓库详情字典。
        """
        logger.info("获取仓库详情: %s/%s", owner, repo)
        return self._make_request(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        )

    def get_readme(
        self, owner: str, repo: str, decode: bool = True
    ) -> Dict[str, Any]:
        """获取仓库 README 文件内容。

        Args:
            owner: 仓库所有者。
            repo: 仓库名称。
            decode: 是否解码 base64 内容。

        Returns:
            包含 README 信息的字典（含 content、name、path 等字段）。
            如果 decode=True，额外包含 decoded_content 字段。
        """
        logger.info("获取 README: %s/%s", owner, repo)
        data = self._make_request(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/readme"
        )
        if decode and "content" in data:
            import base64
            try:
                raw = data["content"].replace("\n", "")
                data["decoded_content"] = base64.b64decode(raw).decode(
                    "utf-8", errors="replace"
                )
            except Exception as e:
                logger.warning("解码 README 失败: %s", e)
                data["decoded_content"] = ""
        return data

    def get_trending(
        self,
        language: Optional[str] = None,
        since: str = "daily",
    ) -> List[Dict[str, Any]]:
        """获取 GitHub Trending 仓库列表。

        通过解析 github.com/trending 页面 HTML 实现，不依赖 API。

        Args:
            language: 编程语言过滤（如 "python", "javascript"）。
            since: 时间范围（daily/weekly/monthly）。

        Returns:
            Trending 仓库列表，每个元素包含 name, full_name, description,
            stars, forks, language, today_stars 等字段。
        """
        logger.info("获取 Trending: language=%s, since=%s", language, since)

        url = f"{GITHUB_WEB_BASE}/trending"
        if language:
            url = f"{url}/{urllib.parse.quote(language)}"
        if since and since != "daily":
            url = f"{url}?since={since}"

        self._rate_limiter.wait_if_needed()
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        }
        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as e:
            logger.error("获取 Trending 页面失败: %s", e)
            raise GitHubAPIError(f"获取 Trending 页面失败: {e}") from e

        return self._parse_trending_html(html)

    def _parse_trending_html(self, html: str) -> List[Dict[str, Any]]:
        """解析 Trending 页面 HTML，提取仓库信息。

        Args:
            html: Trending 页面的 HTML 内容。

        Returns:
            解析后的仓库列表。
        """
        repos: List[Dict[str, Any]] = []

        # 使用正则表达式解析 HTML（无外部依赖）
        # 匹配仓库条目
        article_pattern = re.compile(
            r'<article\s+class="Box-row"[^>]*>(.*?)</article>',
            re.DOTALL,
        )
        articles = article_pattern.findall(html)

        for article in articles:
            repo_info: Dict[str, Any] = {}

            # 提取仓库名称
            name_match = re.search(
                r'<h2[^>]*>.*?<a[^>]*href="/([^"]+)"[^>]*>(.*?)</a>',
                article,
                re.DOTALL,
            )
            if name_match:
                repo_info["full_name"] = name_match.group(1).strip()
                repo_info["name"] = repo_info["full_name"].split("/")[-1]
            else:
                continue

            # 提取描述
            desc_match = re.search(
                r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>',
                article,
                re.DOTALL,
            )
            if desc_match:
                desc = re.sub(r"<[^>]+>", "", desc_match.group(1)).strip()
                repo_info["description"] = desc
            else:
                repo_info["description"] = ""

            # 提取编程语言
            lang_match = re.search(
                r'<span[^>]*itemprop="programmingLanguage"[^>]*>(.*?)</span>',
                article,
                re.DOTALL,
            )
            if lang_match:
                repo_info["language"] = lang_match.group(1).strip()
            else:
                repo_info["language"] = ""

            # 提取总 Star 数
            stars_match = re.search(
                r'<a[^>]*href="/[^"]+/stargazers"[^>]*>\s*<svg[^>]*>.*?</svg>\s*([\d,]+)\s*</a>',
                article,
                re.DOTALL,
            )
            if stars_match:
                repo_info["stars"] = int(stars_match.group(1).replace(",", ""))
            else:
                repo_info["stars"] = 0

            # 提取总 Fork 数
            forks_match = re.search(
                r'<a[^>]*href="/[^"]+/forks"[^>]*>\s*<svg[^>]*>.*?</svg>\s*([\d,]+)\s*</a>',
                article,
                re.DOTALL,
            )
            if forks_match:
                repo_info["forks"] = int(forks_match.group(1).replace(",", ""))
            else:
                repo_info["forks"] = 0

            # 提取今日新增 Star 数
            today_match = re.search(
                r'([\d,]+)\s*stars\s*(today|this\s+week|this\s+month)',
                article,
                re.DOTALL | re.IGNORECASE,
            )
            if today_match:
                repo_info["today_stars"] = int(today_match.group(1).replace(",", ""))
            else:
                repo_info["today_stars"] = 0

            # 提取贡献者
            contributors_match = re.search(
                r'Built by.*?<img[^>]*alt="@([^"]+)"',
                article,
                re.DOTALL,
            )
            if contributors_match:
                repo_info["top_contributor"] = contributors_match.group(1)
            else:
                repo_info["top_contributor"] = ""

            repos.append(repo_info)

        logger.info("解析到 %d 个 Trending 仓库", len(repos))
        return repos

    def get_contributors(
        self, owner: str, repo: str, per_page: int = 10
    ) -> List[Dict[str, Any]]:
        """获取仓库贡献者列表。

        Args:
            owner: 仓库所有者。
            repo: 仓库名称。
            per_page: 返回数量。

        Returns:
            贡献者列表。
        """
        logger.info("获取贡献者: %s/%s", owner, repo)
        return self._make_request(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contributors",
            params={"per_page": str(per_page)},
        )

    def get_languages(self, owner: str, repo: str) -> Dict[str, int]:
        """获取仓库使用的编程语言及字节数。

        Args:
            owner: 仓库所有者。
            repo: 仓库名称。

        Returns:
            语言到字节数的映射字典。
        """
        logger.info("获取语言: %s/%s", owner, repo)
        return self._make_request(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/languages"
        )

    def get_commits(
        self, owner: str, repo: str, per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """获取仓库最近的提交记录。

        Args:
            owner: 仓库所有者。
            repo: 仓库名称。
            per_page: 返回数量。

        Returns:
            提交记录列表。
        """
        logger.info("获取提交: %s/%s", owner, repo)
        return self._make_request(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits",
            params={"per_page": str(per_page)},
        )

    @property
    def rate_limit_remaining(self) -> Optional[int]:
        """返回剩余 API 配额。"""
        return self._rate_limiter.remaining

    @property
    def cache_size(self) -> int:
        """返回当前缓存条目数。"""
        return self._cache.size

    def clear_cache(self) -> None:
        """清空请求缓存。"""
        self._cache.clear()


class GitHubAPIError(Exception):
    """GitHub API 错误异常。"""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        """初始化异常。

        Args:
            message: 错误描述。
            status_code: HTTP 状态码（如果有）。
        """
        super().__init__(message)
        self.status_code = status_code
        self.message = message

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message
