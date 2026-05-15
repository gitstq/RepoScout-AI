"""
scorer.py - 仓库评分系统

对 GitHub 仓库进行多维度综合评分，包括：
- 活跃度评分（最近 commit 频率、issue 关闭率、PR 合并率）
- 社区热度评分（star/fork/watch 比率、讨论活跃度）
- 代码健康度评分（README 完整性、.gitignore 存在、LICENSE 类型）
- 综合评分算法（加权平均，各维度可配置权重）

纯 Python 实现，无外部依赖。
"""

import logging
import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 默认评分权重
DEFAULT_WEIGHTS: Dict[str, float] = {
    "activity": 0.35,
    "community": 0.30,
    "health": 0.20,
    "popularity": 0.15,
}

# 评分等级阈值
GRADE_THRESHOLDS: List[Tuple[str, float]] = [
    ("S", 90),
    ("A", 80),
    ("B", 65),
    ("C", 50),
    ("D", 35),
    ("F", 0),
]

# 常见开源许可证评分
LICENSE_SCORES: Dict[str, float] = {
    "mit": 1.0,
    "apache-2.0": 1.0,
    "bsd-2-clause": 0.95,
    "bsd-3-clause": 0.95,
    "gpl-3.0": 0.9,
    "gpl-2.0": 0.85,
    "lgpl-3.0": 0.9,
    "lgpl-2.1": 0.85,
    "mpl-2.0": 0.9,
    "unlicense": 0.8,
    "isc": 0.9,
    "epl-2.0": 0.85,
    "cc0-1.0": 0.8,
    "agpl-3.0": 0.85,
}


class RepoScorer:
    """仓库综合评分系统。

    从活跃度、社区热度、代码健康度、流行度四个维度对仓库进行评分，
    最终通过加权平均计算综合评分。
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
    ) -> None:
        """初始化评分系统。

        Args:
            weights: 各维度权重字典。如果为 None，使用默认权重。
        """
        self._weights = weights or dict(DEFAULT_WEIGHTS)
        self._validate_weights()
        logger.info("评分系统初始化完成，权重: %s", self._weights)

    def _validate_weights(self) -> None:
        """验证权重配置是否合法。"""
        total = sum(self._weights.values())
        if not math.isclose(total, 1.0, rel_tol=0.05):
            logger.warning(
                "权重总和为 %.2f，将自动归一化", total
            )
            # 自动归一化
            for key in self._weights:
                self._weights[key] /= total

    def score(self, repo: Dict[str, Any]) -> Dict[str, Any]:
        """对仓库进行综合评分。

        Args:
            repo: 仓库信息字典，应包含 GitHub API 返回的字段。

        Returns:
            包含各维度分数、综合分数和等级的评分结果字典。
        """
        full_name = repo.get("full_name", "unknown")

        # 计算各维度分数
        activity_score = self._score_activity(repo)
        community_score = self._score_community(repo)
        health_score = self._score_health(repo)
        popularity_score = self._score_popularity(repo)

        # 加权计算综合分
        overall = (
            activity_score * self._weights.get("activity", 0.35)
            + community_score * self._weights.get("community", 0.30)
            + health_score * self._weights.get("health", 0.20)
            + popularity_score * self._weights.get("popularity", 0.15)
        )

        # 确定等级
        grade = self._get_grade(overall)

        result = {
            "full_name": full_name,
            "scores": {
                "activity": round(activity_score, 1),
                "community": round(community_score, 1),
                "health": round(health_score, 1),
                "popularity": round(popularity_score, 1),
                "overall": round(overall, 1),
            },
            "grade": grade,
            "weights": dict(self._weights),
            "details": self._generate_details(repo),
        }

        logger.info("评分完成: %s -> %.1f (%s)", full_name, overall, grade)
        return result

    def _score_activity(self, repo: Dict[str, Any]) -> float:
        """计算活跃度评分（0-100）。

        考虑因素：
        - 最近推送时间
        - 最近 commit 频率（如果有 commits 数据）
        - open_issues 与总 issues 的比率
        - 是否有 archived 状态

        Args:
            repo: 仓库信息字典。

        Returns:
            活跃度分数。
        """
        score = 50.0  # 基础分

        # 1. 最近推送时间评分（最多 +30 分）
        pushed_at = repo.get("pushed_at", "")
        if pushed_at:
            days_since_push = self._days_since(pushed_at)
            if days_since_push <= 1:
                score += 30
            elif days_since_push <= 7:
                score += 25
            elif days_since_push <= 30:
                score += 20
            elif days_since_push <= 90:
                score += 12
            elif days_since_push <= 180:
                score += 5
            elif days_since_push <= 365:
                score += 2
            # 超过一年不加分

        # 2. 是否归档（归档则大幅扣分）
        if repo.get("archived", False):
            score -= 30

        # 3. Open issues 活跃度（最多 +10 分）
        open_issues = repo.get("open_issues_count", 0) or 0
        if open_issues > 0:
            # 有 open issues 说明社区活跃
            issue_score = min(10, math.log10(open_issues + 1) * 5)
            score += issue_score

        # 4. 是否有 wiki（+5 分）
        if repo.get("has_wiki", False):
            score += 5

        # 5. 是否有 pages（+5 分）
        if repo.get("has_pages", False):
            score += 5

        return max(0.0, min(100.0, score))

    def _score_community(self, repo: Dict[str, Any]) -> float:
        """计算社区热度评分（0-100）。

        考虑因素：
        - Star 数量
        - Fork 数量
        - Watcher 数量
        - Star/Fork 比率（越高说明使用者多于开发者，社区更健康）
        - Fork/Star 比率

        Args:
            repo: 仓库信息字典。

        Returns:
            社区热度分数。
        """
        score = 0.0

        stars = repo.get("stargazers_count", 0) or 0
        forks = repo.get("forks_count", 0) or 0
        watchers = repo.get("subscribers_count", 0) or 0

        # 1. Star 数量评分（最多 +40 分，对数缩放）
        if stars > 0:
            star_score = min(40, math.log10(stars + 1) * 10)
            score += star_score

        # 2. Fork 数量评分（最多 +25 分）
        if forks > 0:
            fork_score = min(25, math.log10(forks + 1) * 8)
            score += fork_score

        # 3. Watcher 数量评分（最多 +15 分）
        if watchers > 0:
            watcher_score = min(15, math.log10(watchers + 1) * 5)
            score += watcher_score

        # 4. Star/Fork 比率（最多 +10 分）
        if forks > 0:
            sf_ratio = stars / forks
            if sf_ratio > 10:
                score += 10  # 大部分人只是使用，不 fork
            elif sf_ratio > 5:
                score += 8
            elif sf_ratio > 2:
                score += 5
            elif sf_ratio > 1:
                score += 3
        else:
            # 没有 fork，但有 star，说明项目被关注但不被修改
            if stars > 10:
                score += 8

        # 5. 是否是 fork（fork 项目扣分）
        if repo.get("fork", False):
            score -= 15

        # 6. 是否有 topics（+5 分）
        topics = repo.get("topics", [])
        if isinstance(topics, list) and len(topics) > 0:
            score += min(5, len(topics))

        # 7. 是否有 issue 和 PR 模板（+5 分）
        if repo.get("has_issues", False):
            score += 3

        return max(0.0, min(100.0, score))

    def _score_health(self, repo: Dict[str, Any]) -> float:
        """计算代码健康度评分（0-100）。

        考虑因素：
        - README 完整性
        - LICENSE 类型
        - .gitignore 存在
        - 描述完整性
        - 主页 URL

        Args:
            repo: 仓库信息字典。

        Returns:
            健康度分数。
        """
        score = 30.0  # 基础分

        # 1. 描述完整性（最多 +15 分）
        description = repo.get("description", "") or ""
        if len(description) >= 50:
            score += 15
        elif len(description) >= 20:
            score += 10
        elif len(description) > 0:
            score += 5

        # 2. LICENSE 评分（最多 +20 分）
        license_info = repo.get("license", {})
        license_key = ""
        if isinstance(license_info, dict):
            license_key = (license_info.get("spdx_id", "") or "").lower()
        elif isinstance(license_info, str):
            license_key = license_info.lower()

        if license_key and license_key != "noassertion":
            license_score = LICENSE_SCORES.get(license_key, 0.5)
            score += 20 * license_score
        else:
            score -= 5  # 没有许可证扣分

        # 3. README 存在性（最多 +15 分）
        # 通过 repo 字段判断是否有 README
        if repo.get("has_readme", False) or repo.get("_has_readme", False):
            score += 15
        elif repo.get("readme_content", ""):
            readme_len = len(repo["readme_content"])
            if readme_len > 1000:
                score += 15
            elif readme_len > 200:
                score += 10
            elif readme_len > 0:
                score += 5

        # 4. 主页 URL（+5 分）
        if repo.get("homepage", ""):
            score += 5

        # 5. 默认分支设置（+5 分）
        if repo.get("default_branch", ""):
            score += 5

        # 6. 是否有 CI/CD（通过 topics 猜测，+5 分）
        topics = repo.get("topics", [])
        if isinstance(topics, list):
            ci_keywords = {"ci", "continuous-integration", "github-actions",
                          "travis-ci", "circleci"}
            if any(t in ci_keywords for t in topics):
                score += 5

        return max(0.0, min(100.0, score))

    def _score_popularity(self, repo: Dict[str, Any]) -> float:
        """计算流行度评分（0-100）。

        考虑因素：
        - Star 数量绝对值
        - Star 增长趋势
        - 被其他仓库引用情况（通过 fork 数量间接衡量）

        Args:
            repo: 仓库信息字典。

        Returns:
            流行度分数。
        """
        score = 0.0

        stars = repo.get("stargazers_count", 0) or 0
        forks = repo.get("forks_count", 0) or 0

        # 1. Star 绝对数量（最多 +50 分，对数缩放）
        if stars > 0:
            star_score = min(50, math.log10(stars + 1) * 12)
            score += star_score

        # 2. Fork 绝对数量（最多 +25 分）
        if forks > 0:
            fork_score = min(25, math.log10(forks + 1) * 8)
            score += fork_score

        # 3. 网络效应（被多少仓库 fork，最多 +15 分）
        if forks > 0:
            network_score = min(15, math.log10(forks + 1) * 5)
            score += network_score

        # 4. 是否是热门项目（star > 1000，+10 分）
        if stars >= 10000:
            score += 10
        elif stars >= 1000:
            score += 7
        elif stars >= 100:
            score += 3

        return max(0.0, min(100.0, score))

    def _get_grade(self, score: float) -> str:
        """根据分数确定等级。

        Args:
            score: 综合分数。

        Returns:
            等级字符串（S/A/B/C/D/F）。
        """
        for grade, threshold in GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return "F"

    def _generate_details(self, repo: Dict[str, Any]) -> Dict[str, Any]:
        """生成评分详情说明。

        Args:
            repo: 仓库信息字典。

        Returns:
            评分详情字典。
        """
        details: Dict[str, Any] = {}

        stars = repo.get("stargazers_count", 0) or 0
        forks = repo.get("forks_count", 0) or 0
        watchers = repo.get("subscribers_count", 0) or 0
        open_issues = repo.get("open_issues_count", 0) or 0

        details["stars"] = stars
        details["forks"] = forks
        details["watchers"] = watchers
        details["open_issues"] = open_issues

        pushed_at = repo.get("pushed_at", "")
        if pushed_at:
            details["days_since_push"] = self._days_since(pushed_at)
        else:
            details["days_since_push"] = None

        details["has_license"] = bool(repo.get("license"))
        details["has_description"] = bool(repo.get("description"))
        details["is_fork"] = repo.get("fork", False)
        details["is_archived"] = repo.get("archived", False)

        return details

    @staticmethod
    def _days_since(iso_date_str: str) -> float:
        """计算从给定日期到现在的天数。

        Args:
            iso_date_str: ISO 8601 格式的日期字符串。

        Returns:
            天数（浮点数）。
        """
        try:
            # 处理带 Z 后缀的 ISO 格式
            if iso_date_str.endswith("Z"):
                iso_date_str = iso_date_str[:-1] + "+00:00"
            dt = datetime.fromisoformat(iso_date_str)
            now = datetime.now(timezone.utc)
            delta = now - dt
            return max(0, delta.total_seconds() / 86400)
        except (ValueError, TypeError) as e:
            logger.debug("日期解析失败 '%s': %s", iso_date_str, e)
            return 9999.0

    def batch_score(
        self, repos: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """批量评分多个仓库。

        Args:
            repos: 仓库信息字典列表。

        Returns:
            评分结果列表，按综合分数降序排列。
        """
        results = []
        for repo in repos:
            try:
                result = self.score(repo)
                results.append(result)
            except Exception as e:
                logger.warning("评分仓库 %s 失败: %s",
                             repo.get("full_name", "unknown"), e)

        # 按综合分数降序排列
        results.sort(key=lambda x: x["scores"]["overall"], reverse=True)
        return results

    def compare(
        self, repos: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """比较多个仓库的评分。

        Args:
            repos: 仓库信息字典列表。

        Returns:
            包含比较结果的列表。
        """
        scored = self.batch_score(repos)
        return scored
