"""
recommender.py - 智能推荐引擎

基于用户兴趣画像和多维度分析，为用户推荐 GitHub 仓库。包括：
- 基于 TF-IDF 的文本相似度计算（纯 Python 实现）
- 用户兴趣画像构建（基于浏览/收藏历史）
- 技术栈偏好匹配
- 多维度加权推荐评分

纯 Python 实现，无外部依赖。
"""

import logging
import math
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from tagger import TFIDFEngine

logger = logging.getLogger(__name__)


class UserProfile:
    """用户兴趣画像。

    基于用户的浏览历史和收藏记录，构建用户兴趣模型。
    """

    def __init__(self) -> None:
        """初始化用户画像。"""
        self._language_prefs: Counter = Counter()
        self._topic_prefs: Counter = Counter()
        self._scene_prefs: Counter = Counter()
        self._keyword_prefs: Counter = Counter()
        self._viewed_repos: Set[str] = set()
        self._favorite_repos: Set[str] = set()
        self._total_views: int = 0
        self._tfidf: TFIDFEngine = TFIDFEngine()

    @property
    def viewed_count(self) -> int:
        """返回已浏览仓库数。"""
        return self._total_views

    @property
    def favorite_count(self) -> int:
        """返回收藏仓库数。"""
        return len(self._favorite_repos)

    @property
    def has_data(self) -> bool:
        """是否有足够的用户数据来生成推荐。"""
        return self._total_views >= 3 or len(self._favorite_repos) >= 1

    def add_view(self, repo: Dict[str, Any], weight: float = 1.0) -> None:
        """记录一次仓库浏览。

        Args:
            repo: 仓库信息字典。
            weight: 浏览权重（用于区分深度浏览和快速浏览）。
        """
        full_name = repo.get("full_name", "")
        if not full_name:
            return

        self._viewed_repos.add(full_name)
        self._total_views += 1

        # 更新语言偏好
        language = repo.get("language", "") or ""
        if language:
            self._language_prefs[language] += weight

        # 更新 topic 偏好
        topics = repo.get("topics", [])
        if isinstance(topics, str):
            try:
                import json
                topics = json.loads(topics)
            except (json.JSONDecodeError, TypeError):
                topics = []
        for topic in topics:
            self._topic_prefs[topic] += weight

        # 更新关键词偏好
        description = repo.get("description", "") or ""
        if description:
            self._tfidf.add_document(description)
            keywords = self._tfidf.extract_keywords(description, top_n=5)
            for kw, score in keywords:
                self._keyword_prefs[kw] += score * weight

    def add_favorite(self, repo: Dict[str, Any]) -> None:
        """记录一次收藏（权重更高）。

        Args:
            repo: 仓库信息字典。
        """
        full_name = repo.get("full_name", "")
        if not full_name:
            return

        self._favorite_repos.add(full_name)
        # 收藏权重是普通浏览的 3 倍
        self.add_view(repo, weight=3.0)

    def get_top_languages(self, n: int = 10) -> List[Tuple[str, float]]:
        """获取用户偏好的编程语言。

        Args:
            n: 返回前 N 个。

        Returns:
            (语言, 偏好分数) 列表。
        """
        return self._language_prefs.most_common(n)

    def get_top_topics(self, n: int = 10) -> List[Tuple[str, float]]:
        """获取用户偏好的主题。

        Args:
            n: 返回前 N 个。

        Returns:
            (主题, 偏好分数) 列表。
        """
        return self._topic_prefs.most_common(n)

    def get_top_keywords(self, n: int = 10) -> List[Tuple[str, float]]:
        """获取用户偏好的关键词。

        Args:
            n: 返回前 N 个。

        Returns:
            (关键词, 偏好分数) 列表。
        """
        return self._keyword_prefs.most_common(n)

    def get_interest_vector(self) -> Dict[str, float]:
        """获取用户兴趣向量（归一化）。

        Returns:
            特征到权重的映射字典。
        """
        vector: Dict[str, float] = {}

        # 语言偏好
        max_lang = max(self._language_prefs.values()) if self._language_prefs else 1
        for lang, count in self._language_prefs.items():
            vector[f"lang:{lang}"] = count / max_lang

        # 主题偏好
        max_topic = max(self._topic_prefs.values()) if self._topic_prefs else 1
        for topic, count in self._topic_prefs.items():
            vector[f"topic:{topic}"] = count / max_topic

        # 关键词偏好
        max_kw = max(self._keyword_prefs.values()) if self._keyword_prefs else 1
        for kw, score in self._keyword_prefs.items():
            vector[f"kw:{kw}"] = score / max_kw

        return vector


class SimilarityEngine:
    """文本相似度计算引擎。

    基于纯 Python 实现的 TF-IDF 余弦相似度计算。
    """

    @staticmethod
    def cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        """计算两个向量之间的余弦相似度。

        Args:
            vec_a: 向量 A（特征 -> 权重）。
            vec_b: 向量 B（特征 -> 权重）。

        Returns:
            余弦相似度（0 到 1 之间）。
        """
        # 获取所有特征
        all_features = set(vec_a.keys()) | set(vec_b.keys())
        if not all_features:
            return 0.0

        # 计算点积
        dot_product = sum(
            vec_a.get(f, 0.0) * vec_b.get(f, 0.0)
            for f in all_features
        )

        # 计算模
        norm_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
        norm_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    @staticmethod
    def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
        """计算两个集合之间的 Jaccard 相似度。

        Args:
            set_a: 集合 A。
            set_b: 集合 B。

        Returns:
            Jaccard 相似度（0 到 1 之间）。
        """
        if not set_a and not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union) if union else 0.0

    @staticmethod
    def text_similarity(text_a: str, text_b: str) -> float:
        """计算两段文本的相似度（基于词袋模型）。

        Args:
            text_a: 文本 A。
            text_b: 文本 B。

        Returns:
            相似度（0 到 1 之间）。
        """
        # 简单分词
        words_a = set(re.findall(r"[a-z0-9]+", text_a.lower()))
        words_b = set(re.findall(r"[a-z0-9]+", text_b.lower()))

        if not words_a or not words_b:
            return 0.0

        return SimilarityEngine.jaccard_similarity(words_a, words_b)


class Recommender:
    """智能推荐引擎。

    综合用户画像、仓库特征和多维度分析，生成个性化推荐。
    """

    def __init__(
        self,
        content_weight: float = 0.4,
        tech_weight: float = 0.3,
        popularity_weight: float = 0.2,
        diversity_weight: float = 0.1,
    ) -> None:
        """初始化推荐引擎。

        Args:
            content_weight: 内容相似度权重。
            tech_weight: 技术栈匹配权重。
            popularity_weight: 流行度权重。
            diversity_weight: 多样性权重。
        """
        self._content_weight = content_weight
        self._tech_weight = tech_weight
        self._popularity_weight = popularity_weight
        self._diversity_weight = diversity_weight
        self._similarity_engine = SimilarityEngine()
        self._tfidf = TFIDFEngine()
        logger.info("推荐引擎初始化完成")

    def build_profile_from_history(
        self, history: List[Dict[str, Any]], favorites: List[Dict[str, Any]]
    ) -> UserProfile:
        """从浏览历史和收藏记录构建用户画像。

        Args:
            history: 浏览历史列表。
            favorites: 收藏列表。

        Returns:
            用户画像对象。
        """
        profile = UserProfile()

        # 添加浏览历史（权重较低）
        for item in history:
            profile.add_view(item, weight=1.0)

        # 添加收藏（权重较高）
        for item in favorites:
            profile.add_favorite(item)

        logger.info(
            "用户画像构建完成: 浏览 %d, 收藏 %d",
            profile.viewed_count, profile.favorite_count,
        )
        return profile

    def recommend(
        self,
        candidates: List[Dict[str, Any]],
        profile: Optional[UserProfile] = None,
        limit: int = 10,
        exclude_viewed: bool = True,
    ) -> List[Dict[str, Any]]:
        """为用户生成推荐列表。

        Args:
            candidates: 候选仓库列表。
            profile: 用户画像。如果为 None，使用默认推荐策略。
            limit: 返回数量。
            exclude_viewed: 是否排除已浏览的仓库。

        Returns:
            推荐结果列表，包含仓库信息和推荐分数。
        """
        if not candidates:
            return []

        # 如果没有用户画像，使用流行度排序
        if profile is None or not profile.has_data:
            logger.info("无用户画像，使用默认推荐策略")
            return self._default_recommend(candidates, limit)

        # 构建排除集合
        exclude_set: Set[str] = set()
        if exclude_viewed:
            exclude_set = profile._viewed_repos | profile._favorite_repos

        # 获取用户兴趣向量
        interest_vector = profile.get_interest_vector()
        top_languages = set(lang for lang, _ in profile.get_top_languages(10))
        top_topics = set(topic for topic, _ in profile.get_top_topics(20))

        # 计算每个候选仓库的推荐分数
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for repo in candidates:
            full_name = repo.get("full_name", "")

            # 排除已浏览
            if full_name in exclude_set:
                continue

            score = self._compute_recommend_score(
                repo, interest_vector, top_languages, top_topics
            )
            scored.append((score, repo))

        # 按分数降序排列
        scored.sort(key=lambda x: x[0], reverse=True)

        # 构建结果
        results = []
        for score, repo in scored[:limit]:
            results.append({
                "repo": repo,
                "recommend_score": round(score, 2),
                "full_name": repo.get("full_name", ""),
                "name": repo.get("name", ""),
                "description": repo.get("description", ""),
                "stars": repo.get("stargazers_count", repo.get("stars", 0)),
                "language": repo.get("language", ""),
            })

        logger.info("生成 %d 条推荐（从 %d 个候选中）", len(results), len(candidates))
        return results

    def _compute_recommend_score(
        self,
        repo: Dict[str, Any],
        interest_vector: Dict[str, float],
        top_languages: Set[str],
        top_topics: Set[str],
    ) -> float:
        """计算单个仓库的推荐分数。

        Args:
            repo: 仓库信息。
            interest_vector: 用户兴趣向量。
            top_languages: 用户偏好语言集合。
            top_topics: 用户偏好主题集合。

        Returns:
            推荐分数（0-100）。
        """
        score = 0.0

        # 1. 内容相似度评分
        repo_vector = self._build_repo_vector(repo)
        content_sim = self._similarity_engine.cosine_similarity(
            interest_vector, repo_vector
        )
        score += content_sim * 100 * self._content_weight

        # 2. 技术栈匹配评分
        tech_score = self._compute_tech_match(repo, top_languages, top_topics)
        score += tech_score * 100 * self._tech_weight

        # 3. 流行度评分
        stars = repo.get("stargazers_count", 0) or repo.get("stars", 0) or 0
        if stars > 0:
            pop_score = min(1.0, math.log10(stars + 1) / 5)
            score += pop_score * 100 * self._popularity_weight

        # 4. 多样性奖励（基于 topics 数量）
        topics = repo.get("topics", [])
        if isinstance(topics, str):
            try:
                import json
                topics = json.loads(topics)
            except (json.JSONDecodeError, TypeError):
                topics = []
        diversity = min(1.0, len(topics) / 10) if topics else 0
        score += diversity * 100 * self._diversity_weight

        return score

    def _build_repo_vector(self, repo: Dict[str, Any]) -> Dict[str, float]:
        """构建仓库的特征向量。

        Args:
            repo: 仓库信息。

        Returns:
            特征向量字典。
        """
        vector: Dict[str, float] = {}

        # 语言特征
        language = repo.get("language", "") or ""
        if language:
            vector[f"lang:{language.lower()}"] = 1.0

        # 主题特征
        topics = repo.get("topics", [])
        if isinstance(topics, str):
            try:
                import json
                topics = json.loads(topics)
            except (json.JSONDecodeError, TypeError):
                topics = []
        for topic in topics:
            vector[f"topic:{topic.lower()}"] = 1.0

        # 关键词特征
        description = repo.get("description", "") or ""
        if description:
            tfidf = self._tfidf.extract_keywords(description, top_n=5)
            for kw, score in tfidf:
                vector[f"kw:{kw}"] = score

        return vector

    def _compute_tech_match(
        self,
        repo: Dict[str, Any],
        top_languages: Set[str],
        top_topics: Set[str],
    ) -> float:
        """计算技术栈匹配度。

        Args:
            repo: 仓库信息。
            top_languages: 用户偏好语言集合。
            top_topics: 用户偏好主题集合。

        Returns:
            匹配度（0-1）。
        """
        match_count = 0
        total_checks = 0

        # 语言匹配
        language = (repo.get("language", "") or "").lower()
        if language and top_languages:
            total_checks += 1
            if language in top_languages:
                match_count += 1

        # 主题匹配
        topics = repo.get("topics", [])
        if isinstance(topics, str):
            try:
                import json
                topics = json.loads(topics)
            except (json.JSONDecodeError, TypeError):
                topics = []
        if topics and top_topics:
            topic_set = set(t.lower() for t in topics)
            overlap = topic_set & top_topics
            if top_topics:
                total_checks += 1
                match_count += min(1.0, len(overlap) / min(3, len(top_topics)))

        return match_count / total_checks if total_checks > 0 else 0.0

    def _default_recommend(
        self, candidates: List[Dict[str, Any]], limit: int
    ) -> List[Dict[str, Any]]:
        """默认推荐策略（基于流行度和活跃度）。

        Args:
            candidates: 候选仓库列表。
            limit: 返回数量。

        Returns:
            推荐结果列表。
        """
        scored = []
        for repo in candidates:
            stars = repo.get("stargazers_count", 0) or repo.get("stars", 0) or 0
            forks = repo.get("forks_count", 0) or repo.get("forks", 0) or 0
            description = repo.get("description", "") or ""

            # 综合评分：star + fork + 描述完整性
            score = 0.0
            if stars > 0:
                score += math.log10(stars + 1) * 10
            if forks > 0:
                score += math.log10(forks + 1) * 5
            if description:
                score += min(5, len(description) / 20)

            scored.append((score, repo))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, repo in scored[:limit]:
            results.append({
                "repo": repo,
                "recommend_score": round(score, 2),
                "full_name": repo.get("full_name", ""),
                "name": repo.get("name", ""),
                "description": repo.get("description", ""),
                "stars": repo.get("stargazers_count", repo.get("stars", 0)),
                "language": repo.get("language", ""),
            })

        return results

    def find_similar(
        self,
        target_repo: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """查找与目标仓库相似的仓库。

        Args:
            target_repo: 目标仓库。
            candidates: 候选仓库列表。
            limit: 返回数量。

        Returns:
            相似仓库列表。
        """
        target_vector = self._build_repo_vector(target_repo)

        scored = []
        for repo in candidates:
            if repo.get("full_name") == target_repo.get("full_name"):
                continue

            repo_vector = self._build_repo_vector(repo)
            similarity = self._similarity_engine.cosine_similarity(
                target_vector, repo_vector
            )

            # 也考虑描述文本相似度
            target_desc = target_repo.get("description", "") or ""
            repo_desc = repo.get("description", "") or ""
            text_sim = self._similarity_engine.text_similarity(
                target_desc, repo_desc
            )

            combined = similarity * 0.7 + text_sim * 0.3
            scored.append((combined, repo))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for sim, repo in scored[:limit]:
            results.append({
                "repo": repo,
                "similarity": round(sim, 3),
                "full_name": repo.get("full_name", ""),
                "name": repo.get("name", ""),
                "description": repo.get("description", ""),
                "stars": repo.get("stargazers_count", repo.get("stars", 0)),
                "language": repo.get("language", ""),
            })

        return results
