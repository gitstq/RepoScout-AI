"""
tagger.py - 智能标签系统

为 GitHub 仓库自动生成分类标签，包括：
- 项目类型自动识别（library/tool/framework/application/demo 等）
- 技术栈自动提取（从 topics、languages、description 中提取）
- 应用场景分类（web/mobile/ai/devops/security 等）
- 关键词提取（基于 TF-IDF）

纯 Python 实现，无外部依赖。
"""

import logging
import math
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ==================== 项目类型关键词映射 ====================

PROJECT_TYPE_PATTERNS: Dict[str, List[str]] = {
    "library": [
        "library", "lib", "sdk", "api", "module", "package",
        "工具库", "类库", "开发包",
    ],
    "tool": [
        "tool", "cli", "utility", "util", "cmd", "command-line",
        "工具", "命令行",
    ],
    "framework": [
        "framework", "框架", "mvc", "mvvm",
    ],
    "application": [
        "application", "app", "webapp", "web app", "service",
        "应用", "服务",
    ],
    "demo": [
        "demo", "example", "sample", "boilerplate", "starter",
        "template", "scaffold", "脚手架", "示例",
    ],
    "documentation": [
        "docs", "documentation", "wiki", "guide", "tutorial",
        "文档", "教程",
    ],
    "benchmark": [
        "benchmark", "performance", "perf", "基准测试",
    ],
    "game": [
        "game", "游戏",
    ],
    "plugin": [
        "plugin", "extension", "addon", "插件", "扩展",
    ],
}

# ==================== 应用场景关键词映射 ====================

SCENE_PATTERNS: Dict[str, List[str]] = {
    "web": [
        "web", "http", "rest", "graphql", "frontend", "backend",
        "server", "website", "spa", "ssr", "html", "css", "javascript",
        "react", "vue", "angular", "svelte", "next", "nuxt",
        "django", "flask", "fastapi", "express", "koa", "gin",
        "网站", "前端", "后端",
    ],
    "mobile": [
        "mobile", "ios", "android", "react-native", "flutter",
        "swift", "kotlin", "app", "移动端", "手机",
    ],
    "ai": [
        "ai", "ml", "machine-learning", "deep-learning", "neural",
        "nlp", "cv", "computer-vision", "gpt", "llm", "transformer",
        "pytorch", "tensorflow", "keras", "model", "训练",
        "人工智能", "机器学习", "深度学习",
    ],
    "devops": [
        "devops", "ci", "cd", "docker", "kubernetes", "k8s",
        "terraform", "ansible", "jenkins", "deploy", "container",
        "orchestration", "运维", "部署", "容器",
    ],
    "security": [
        "security", "crypto", "encryption", "authentication",
        "authorization", "firewall", "vulnerability", "pentest",
        "安全", "加密", "认证",
    ],
    "data": [
        "data", "database", "sql", "nosql", "mongodb", "postgres",
        "redis", "elasticsearch", "big-data", "etl", "data-pipeline",
        "数据分析", "数据库",
    ],
    "desktop": [
        "desktop", "gui", "electron", "qt", "gtk", "wx",
        "桌面", "图形界面",
    ],
    "iot": [
        "iot", "embedded", "raspberry", "arduino", "sensor",
        "物联网", "嵌入式",
    ],
    "blockchain": [
        "blockchain", "smart-contract", "solidity", "web3", "defi",
        "nft", "token", "区块链",
    ],
    "testing": [
        "test", "testing", "tdd", "bdd", "mock", "stub",
        "selenium", "pytest", "jest", "mocha", "测试",
    ],
}

# ==================== 常见编程语言别名映射 ====================

LANGUAGE_ALIASES: Dict[str, Set[str]] = {
    "javascript": {"javascript", "js", "nodejs", "node.js", "node"},
    "typescript": {"typescript", "ts"},
    "python": {"python", "py"},
    "java": {"java"},
    "go": {"go", "golang"},
    "rust": {"rust", "rs"},
    "c++": {"c++", "cpp", "cplusplus"},
    "c": {"c"},
    "c#": {"c#", "csharp", "cs"},
    "ruby": {"ruby", "rb"},
    "php": {"php"},
    "swift": {"swift"},
    "kotlin": {"kotlin", "kt"},
    "dart": {"dart"},
    "shell": {"shell", "bash", "sh", "zsh"},
    "sql": {"sql"},
    "html": {"html", "html5"},
    "css": {"css", "css3", "scss", "sass", "less"},
}

# ==================== 停用词 ====================

STOP_WORDS: Set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off", "over",
    "under", "again", "further", "then", "once", "and", "but", "or",
    "nor", "not", "so", "yet", "both", "either", "neither", "each",
    "every", "all", "any", "few", "more", "most", "other", "some",
    "such", "no", "only", "own", "same", "than", "too", "very",
    "just", "because", "if", "when", "where", "how", "what", "which",
    "who", "whom", "this", "that", "these", "those", "it", "its",
    "my", "your", "his", "her", "our", "their", "we", "you", "he",
    "she", "they", "me", "him", "us", "them",
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
    "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
    "你", "会", "着", "没有", "看", "好", "自己", "这",
}


class TFIDFEngine:
    """纯 Python 实现的 TF-IDF 计算引擎。

    用于从仓库描述、README 等文本中提取关键词。
    """

    def __init__(self) -> None:
        """初始化 TF-IDF 引擎。"""
        self._documents: List[List[str]] = []
        self._idf_cache: Dict[str, float] = {}
        self._vocabulary: Set[str] = set()

    def add_document(self, text: str) -> List[str]:
        """添加一个文档到语料库。

        Args:
            text: 文档文本。

        Returns:
            分词后的词列表。
        """
        tokens = self._tokenize(text)
        self._documents.append(tokens)
        self._vocabulary.update(tokens)
        # 重新计算 IDF
        self._compute_idf()
        return tokens

    def add_documents(self, texts: List[str]) -> None:
        """批量添加文档。

        Args:
            texts: 文档文本列表。
        """
        for text in texts:
            tokens = self._tokenize(text)
            self._documents.append(tokens)
            self._vocabulary.update(tokens)
        self._compute_idf()

    def _tokenize(self, text: str) -> List[str]:
        """对文本进行分词处理。

        Args:
            text: 原始文本。

        Returns:
            小写化的词元列表。
        """
        # 转小写
        text = text.lower()
        # 提取单词（含连字符的技术术语）
        tokens = re.findall(r"[a-z][a-z0-9_-]+|[a-z]", text)
        # 过滤停用词和过短的词
        tokens = [t for t in tokens if t not in STOP_WORDS and len(t) > 1]
        return tokens

    def _compute_idf(self) -> None:
        """计算逆文档频率（IDF）。"""
        n = len(self._documents)
        if n == 0:
            return

        # 统计每个词出现在多少个文档中
        df: Counter = Counter()
        for doc_tokens in self._documents:
            unique_tokens = set(doc_tokens)
            for token in unique_tokens:
                df[token] += 1

        # 计算 IDF
        self._idf_cache = {}
        for word in self._vocabulary:
            self._idf_cache[word] = math.log((n + 1) / (df[word] + 1)) + 1

    def compute_tfidf(self, text: str) -> Dict[str, float]:
        """计算单个文本的 TF-IDF 值。

        Args:
            text: 文本内容。

        Returns:
            词到 TF-IDF 值的映射字典。
        """
        tokens = self._tokenize(text)
        if not tokens:
            return {}

        # 计算 TF
        tf_counts = Counter(tokens)
        max_tf = max(tf_counts.values())
        n = len(tokens)

        tfidf: Dict[str, float] = {}
        for word, count in tf_counts.items():
            # 归一化 TF
            tf = count / n
            # 获取 IDF（如果词不在缓存中，使用默认值）
            idf = self._idf_cache.get(word, 1.0)
            tfidf[word] = tf * idf

        return tfidf

    def extract_keywords(
        self, text: str, top_n: int = 10
    ) -> List[Tuple[str, float]]:
        """从文本中提取关键词。

        Args:
            text: 文本内容。
            top_n: 返回前 N 个关键词。

        Returns:
            (关键词, TF-IDF 分数) 的列表，按分数降序排列。
        """
        tfidf = self.compute_tfidf(text)
        sorted_words = sorted(tfidf.items(), key=lambda x: x[1], reverse=True)
        return sorted_words[:top_n]


class RepoTagger:
    """仓库智能标签系统。

    根据仓库的名称、描述、topics、语言等信息，自动生成分类标签。
    """

    def __init__(self) -> None:
        """初始化标签系统。"""
        self._tfidf = TFIDFEngine()

    def analyze(self, repo: Dict[str, Any]) -> Dict[str, Any]:
        """对仓库进行全面标签分析。

        Args:
            repo: 仓库信息字典。

        Returns:
            包含 project_type, scenes, tech_stack, keywords 的分析结果字典。
        """
        name = repo.get("name", "")
        full_name = repo.get("full_name", "")
        description = repo.get("description", "") or ""
        topics = repo.get("topics", [])
        if isinstance(topics, str):
            try:
                import json
                topics = json.loads(topics)
            except (json.JSONDecodeError, TypeError):
                topics = []
        language = repo.get("language", "") or ""
        readme = repo.get("readme", "") or ""

        # 合并所有文本用于分析
        combined_text = f"{name} {description} {' '.join(topics)} {readme}"

        # 1. 项目类型识别
        project_type = self._identify_project_type(
            name, description, topics
        )

        # 2. 应用场景分类
        scenes = self._classify_scenes(
            name, description, topics, language
        )

        # 3. 技术栈提取
        tech_stack = self._extract_tech_stack(
            topics, language, description, readme
        )

        # 4. 关键词提取
        self._tfidf.add_document(combined_text)
        keywords = self._tfidf.extract_keywords(combined_text, top_n=10)

        result = {
            "full_name": full_name,
            "project_type": project_type,
            "scenes": scenes,
            "tech_stack": tech_stack,
            "keywords": [kw for kw, _ in keywords],
            "keyword_scores": keywords,
        }

        logger.debug("标签分析完成: %s -> type=%s, scenes=%s",
                     full_name, project_type, scenes)
        return result

    def _identify_project_type(
        self,
        name: str,
        description: str,
        topics: List[str],
    ) -> str:
        """识别项目类型。

        Args:
            name: 仓库名称。
            description: 仓库描述。
            topics: 主题标签列表。

        Returns:
            项目类型字符串。
        """
        # 合并所有文本
        text = f"{name} {description} {' '.join(topics)}".lower()

        scores: Dict[str, float] = {}
        for ptype, patterns in PROJECT_TYPE_PATTERNS.items():
            score = 0.0
            for pattern in patterns:
                if pattern.lower() in text:
                    score += 1.0
            scores[ptype] = score

        if not scores or max(scores.values()) == 0:
            return "other"

        return max(scores, key=scores.get)  # type: ignore[arg-type]

    def _classify_scenes(
        self,
        name: str,
        description: str,
        topics: List[str],
        language: str,
    ) -> List[str]:
        """分类应用场景。

        Args:
            name: 仓库名称。
            description: 仓库描述。
            topics: 主题标签列表。
            language: 主要编程语言。

        Returns:
            应用场景标签列表。
        """
        text = f"{name} {description} {' '.join(topics)} {language}".lower()

        matched: List[Tuple[str, float]] = []
        for scene, patterns in SCENE_PATTERNS.items():
            score = 0.0
            for pattern in patterns:
                if pattern.lower() in text:
                    score += 1.0
            if score > 0:
                matched.append((scene, score))

        # 按匹配分数降序排列
        matched.sort(key=lambda x: x[1], reverse=True)
        return [scene for scene, _ in matched]

    def _extract_tech_stack(
        self,
        topics: List[str],
        language: str,
        description: str,
        readme: str,
    ) -> List[str]:
        """提取技术栈信息。

        Args:
            topics: 主题标签列表。
            language: 主要编程语言。
            description: 仓库描述。
            readme: README 内容。

        Returns:
            技术栈标签列表。
        """
        tech: Set[str] = set()

        # 从语言提取
        if language:
            tech.add(language.lower())

        # 从 topics 提取（topics 通常是技术栈标签）
        tech_topic_patterns = {
            "react", "vue", "angular", "svelte", "nextjs", "nuxt",
            "django", "flask", "fastapi", "spring", "rails",
            "express", "koa", "gin", "echo", "fiber",
            "docker", "kubernetes", "terraform",
            "postgresql", "mysql", "mongodb", "redis",
            "elasticsearch", "kafka", "rabbitmq",
            "webpack", "vite", "rollup", "esbuild",
            "tailwindcss", "bootstrap", "material-ui",
            "jest", "pytest", "cypress", "playwright",
            "grpc", "websocket", "graphql",
            "opencv", "pandas", "numpy", "scipy",
        }

        for topic in topics:
            topic_lower = topic.lower()
            if topic_lower in tech_topic_patterns:
                tech.add(topic_lower)
            # 检查是否是已知语言别名
            for lang, aliases in LANGUAGE_ALIASES.items():
                if topic_lower in aliases:
                    tech.add(lang)

        # 从描述和 README 中提取已知技术栈
        combined = f"{description} {readme}".lower()
        for tech_name in tech_topic_patterns:
            if tech_name in combined and tech_name not in tech:
                tech.add(tech_name)

        return sorted(tech)

    def batch_analyze(
        self, repos: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """批量分析多个仓库。

        Args:
            repos: 仓库信息字典列表。

        Returns:
            分析结果列表。
        """
        results = []
        for repo in repos:
            try:
                result = self.analyze(repo)
                results.append(result)
            except Exception as e:
                logger.warning("分析仓库 %s 失败: %s",
                             repo.get("full_name", "unknown"), e)
        return results
