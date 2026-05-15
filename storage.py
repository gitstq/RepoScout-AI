"""
storage.py - 本地存储模块

基于 SQLite 实现本地数据持久化，包括：
- 收藏管理（增删改查）
- 浏览历史记录
- 用户偏好设置
- 自定义标签
- 仓库快照数据（用于趋势追踪）

仅使用标准库 sqlite3，无外部依赖。
"""

import json
import logging
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 默认数据库文件路径
DEFAULT_DB_PATH = os.path.join(
    os.path.expanduser("~"), ".reposcout", "reposcout.db"
)


class Storage:
    """本地 SQLite 存储管理器。

    提供收藏管理、浏览历史、用户偏好、自定义标签等功能的持久化存储。
    自动创建数据库表结构，线程安全（通过连接隔离）。
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """初始化存储管理器。

        Args:
            db_path: 数据库文件路径。如果为 None，使用默认路径。
        """
        self._db_path = db_path or DEFAULT_DB_PATH
        self._ensure_dir()
        self._init_tables()
        logger.info("存储模块初始化完成: %s", self._db_path)

    def _ensure_dir(self) -> None:
        """确保数据库文件所在目录存在。"""
        db_dir = os.path.dirname(self._db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.debug("创建数据库目录: %s", db_dir)

    def _get_conn(self) -> sqlite3.Connection:
        """获取一个新的数据库连接。

        Returns:
            sqlite3 连接对象，启用了 row factory 和 WAL 模式。
        """
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_tables(self) -> None:
        """初始化数据库表结构。"""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            # 收藏表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    html_url TEXT DEFAULT '',
                    language TEXT DEFAULT '',
                    stars INTEGER DEFAULT 0,
                    forks INTEGER DEFAULT 0,
                    topics TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    notes TEXT DEFAULT ''
                )
            """)

            # 浏览历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    name TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    language TEXT DEFAULT '',
                    stars INTEGER DEFAULT 0,
                    visited_at TEXT NOT NULL,
                    source TEXT DEFAULT 'search'
                )
            """)

            # 用户偏好设置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # 自定义标签表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(full_name, tag)
                )
            """)

            # 仓库快照表（用于趋势追踪）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    stars INTEGER DEFAULT 0,
                    forks INTEGER DEFAULT 0,
                    open_issues INTEGER DEFAULT 0,
                    watchers INTEGER DEFAULT 0,
                    snapshot_at TEXT NOT NULL,
                    UNIQUE(full_name, snapshot_at)
                )
            """)

            # 创建索引
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_favorites_full_name "
                "ON favorites(full_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_history_visited_at "
                "ON history(visited_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_history_full_name "
                "ON history(full_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_tags_full_name "
                "ON tags(full_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_snapshots_full_name "
                "ON snapshots(full_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_snapshots_snapshot_at "
                "ON snapshots(snapshot_at)"
            )

            conn.commit()
            logger.debug("数据库表初始化完成")
        finally:
            conn.close()

    # ==================== 收藏管理 ====================

    def add_favorite(self, repo: Dict[str, Any], notes: str = "") -> bool:
        """添加仓库到收藏。

        Args:
            repo: 仓库信息字典，需包含 full_name 等字段。
            notes: 备注信息。

        Returns:
            是否添加成功。
        """
        conn = self._get_conn()
        try:
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            full_name = repo.get("full_name", "")
            if not full_name:
                logger.warning("添加收藏失败: 缺少 full_name")
                return False

            topics = repo.get("topics", [])
            if isinstance(topics, list):
                topics_str = json.dumps(topics)
            else:
                topics_str = str(topics)

            conn.execute("""
                INSERT OR REPLACE INTO favorites
                (full_name, name, owner, description, html_url, language,
                 stars, forks, topics, created_at, updated_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                full_name,
                repo.get("name", full_name.split("/")[-1]),
                repo.get("owner", {}).get("login", full_name.split("/")[0])
                if isinstance(repo.get("owner"), dict)
                else full_name.split("/")[0],
                repo.get("description", "") or "",
                repo.get("html_url", ""),
                repo.get("language", "") or "",
                repo.get("stargazers_count", repo.get("stars", 0)),
                repo.get("forks_count", repo.get("forks", 0)),
                topics_str,
                now,
                now,
                notes,
            ))
            conn.commit()
            logger.info("已收藏: %s", full_name)
            return True
        except sqlite3.Error as e:
            logger.error("添加收藏失败: %s", e)
            return False
        finally:
            conn.close()

    def remove_favorite(self, full_name: str) -> bool:
        """从收藏中移除仓库。

        Args:
            full_name: 仓库全名（owner/repo）。

        Returns:
            是否移除成功。
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "DELETE FROM favorites WHERE full_name = ?", (full_name,)
            )
            conn.commit()
            if cursor.rowcount > 0:
                logger.info("已取消收藏: %s", full_name)
                return True
            logger.warning("收藏不存在: %s", full_name)
            return False
        except sqlite3.Error as e:
            logger.error("移除收藏失败: %s", e)
            return False
        finally:
            conn.close()

    def get_favorites(
        self,
        sort_by: str = "updated_at",
        order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """获取收藏列表。

        Args:
            sort_by: 排序字段（stars/forks/updated_at/name）。
            order: 排序方向（asc/desc）。
            limit: 返回数量。
            offset: 偏移量。

        Returns:
            收藏仓库列表。
        """
        conn = self._get_conn()
        try:
            # 验证排序字段防止 SQL 注入
            allowed_sorts = {"stars", "forks", "updated_at", "name", "language"}
            if sort_by not in allowed_sorts:
                sort_by = "updated_at"
            if order.upper() not in ("ASC", "DESC"):
                order = "DESC"

            cursor = conn.execute(
                f"SELECT * FROM favorites ORDER BY {sort_by} {order} "
                f"LIMIT ? OFFSET ?",
                (limit, offset),
            )
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error("获取收藏列表失败: %s", e)
            return []
        finally:
            conn.close()

    def get_favorite(self, full_name: str) -> Optional[Dict[str, Any]]:
        """获取单个收藏仓库。

        Args:
            full_name: 仓库全名。

        Returns:
            仓库信息字典，如果不存在返回 None。
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM favorites WHERE full_name = ?", (full_name,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None
        except sqlite3.Error as e:
            logger.error("获取收藏失败: %s", e)
            return None
        finally:
            conn.close()

    def is_favorite(self, full_name: str) -> bool:
        """检查仓库是否已收藏。

        Args:
            full_name: 仓库全名。

        Returns:
            是否已收藏。
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT 1 FROM favorites WHERE full_name = ?", (full_name,)
            )
            return cursor.fetchone() is not None
        except sqlite3.Error:
            return False
        finally:
            conn.close()

    def update_favorite_notes(self, full_name: str, notes: str) -> bool:
        """更新收藏仓库的备注。

        Args:
            full_name: 仓库全名。
            notes: 新的备注内容。

        Returns:
            是否更新成功。
        """
        conn = self._get_conn()
        try:
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            cursor = conn.execute("""
                UPDATE favorites SET notes = ?, updated_at = ?
                WHERE full_name = ?
            """, (notes, now, full_name))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error("更新备注失败: %s", e)
            return False
        finally:
            conn.close()

    # ==================== 浏览历史 ====================

    def add_history(
        self,
        repo: Dict[str, Any],
        source: str = "search",
    ) -> bool:
        """添加浏览历史记录。

        Args:
            repo: 仓库信息字典。
            source: 浏览来源（search/trending/recommend/favorites）。

        Returns:
            是否添加成功。
        """
        conn = self._get_conn()
        try:
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            full_name = repo.get("full_name", "")
            if not full_name:
                return False

            conn.execute("""
                INSERT INTO history
                (full_name, name, owner, description, language, stars, visited_at, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                full_name,
                repo.get("name", full_name.split("/")[-1]),
                repo.get("owner", {}).get("login", full_name.split("/")[0])
                if isinstance(repo.get("owner"), dict)
                else full_name.split("/")[0],
                repo.get("description", "") or "",
                repo.get("language", "") or "",
                repo.get("stargazers_count", repo.get("stars", 0)),
                now,
                source,
            ))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error("添加历史记录失败: %s", e)
            return False
        finally:
            conn.close()

    def get_history(
        self,
        limit: int = 50,
        offset: int = 0,
        source: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取浏览历史。

        Args:
            limit: 返回数量。
            offset: 偏移量。
            source: 过滤来源。

        Returns:
            历史记录列表。
        """
        conn = self._get_conn()
        try:
            if source:
                cursor = conn.execute(
                    "SELECT * FROM history WHERE source = ? "
                    "ORDER BY visited_at DESC LIMIT ? OFFSET ?",
                    (source, limit, offset),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM history ORDER BY visited_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                )
            return [self._row_to_dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error("获取历史记录失败: %s", e)
            return []
        finally:
            conn.close()

    def clear_history(self) -> bool:
        """清空浏览历史。

        Returns:
            是否清空成功。
        """
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM history")
            conn.commit()
            logger.info("浏览历史已清空")
            return True
        except sqlite3.Error as e:
            logger.error("清空历史失败: %s", e)
            return False
        finally:
            conn.close()

    def get_history_stats(self) -> Dict[str, Any]:
        """获取浏览历史统计信息。

        Returns:
            包含总数、最常浏览仓库、语言分布等统计的字典。
        """
        conn = self._get_conn()
        try:
            stats: Dict[str, Any] = {}

            # 总浏览次数
            cursor = conn.execute("SELECT COUNT(*) as cnt FROM history")
            stats["total_views"] = cursor.fetchone()["cnt"]

            # 最常浏览的仓库
            cursor = conn.execute("""
                SELECT full_name, COUNT(*) as cnt FROM history
                GROUP BY full_name ORDER BY cnt DESC LIMIT 10
            """)
            stats["most_viewed"] = [
                {"full_name": row["full_name"], "count": row["cnt"]}
                for row in cursor.fetchall()
            ]

            # 语言分布
            cursor = conn.execute("""
                SELECT language, COUNT(*) as cnt FROM history
                WHERE language != ''
                GROUP BY language ORDER BY cnt DESC LIMIT 10
            """)
            stats["language_distribution"] = [
                {"language": row["language"], "count": row["cnt"]}
                for row in cursor.fetchall()
            ]

            # 来源分布
            cursor = conn.execute("""
                SELECT source, COUNT(*) as cnt FROM history
                GROUP BY source ORDER BY cnt DESC
            """)
            stats["source_distribution"] = [
                {"source": row["source"], "count": row["cnt"]}
                for row in cursor.fetchall()
            ]

            return stats
        except sqlite3.Error as e:
            logger.error("获取历史统计失败: %s", e)
            return {}
        finally:
            conn.close()

    # ==================== 用户偏好 ====================

    def set_preference(self, key: str, value: str) -> bool:
        """设置用户偏好。

        Args:
            key: 偏好键名。
            value: 偏好值。

        Returns:
            是否设置成功。
        """
        conn = self._get_conn()
        try:
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""
                INSERT OR REPLACE INTO preferences (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, now))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error("设置偏好失败: %s", e)
            return False
        finally:
            conn.close()

    def get_preference(self, key: str, default: str = "") -> str:
        """获取用户偏好。

        Args:
            key: 偏好键名。
            default: 默认值。

        Returns:
            偏好值。
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT value FROM preferences WHERE key = ?", (key,)
            )
            row = cursor.fetchone()
            return row["value"] if row else default
        except sqlite3.Error:
            return default
        finally:
            conn.close()

    def get_all_preferences(self) -> Dict[str, str]:
        """获取所有用户偏好。

        Returns:
            偏好键值对字典。
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute("SELECT key, value FROM preferences")
            return {row["key"]: row["value"] for row in cursor.fetchall()}
        except sqlite3.Error:
            return {}
        finally:
            conn.close()

    def delete_preference(self, key: str) -> bool:
        """删除用户偏好。

        Args:
            key: 偏好键名。

        Returns:
            是否删除成功。
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "DELETE FROM preferences WHERE key = ?", (key,)
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False
        finally:
            conn.close()

    # ==================== 自定义标签 ====================

    def add_tag(self, full_name: str, tag: str) -> bool:
        """为仓库添加自定义标签。

        Args:
            full_name: 仓库全名。
            tag: 标签文本。

        Returns:
            是否添加成功。
        """
        conn = self._get_conn()
        try:
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""
                INSERT OR IGNORE INTO tags (full_name, tag, created_at)
                VALUES (?, ?, ?)
            """, (full_name, tag, now))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error("添加标签失败: %s", e)
            return False
        finally:
            conn.close()

    def remove_tag(self, full_name: str, tag: str) -> bool:
        """移除仓库的自定义标签。

        Args:
            full_name: 仓库全名。
            tag: 标签文本。

        Returns:
            是否移除成功。
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "DELETE FROM tags WHERE full_name = ? AND tag = ?",
                (full_name, tag),
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False
        finally:
            conn.close()

    def get_tags(self, full_name: str) -> List[str]:
        """获取仓库的所有自定义标签。

        Args:
            full_name: 仓库全名。

        Returns:
            标签列表。
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT tag FROM tags WHERE full_name = ?", (full_name,)
            )
            return [row["tag"] for row in cursor.fetchall()]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def get_all_tags(self) -> Dict[str, List[str]]:
        """获取所有仓库的标签映射。

        Returns:
            仓库全名到标签列表的映射字典。
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT full_name, tag FROM tags ORDER BY full_name, tag"
            )
            result: Dict[str, List[str]] = {}
            for row in cursor.fetchall():
                fn = row["full_name"]
                if fn not in result:
                    result[fn] = []
                result[fn].append(row["tag"])
            return result
        except sqlite3.Error:
            return {}
        finally:
            conn.close()

    # ==================== 仓库快照（趋势追踪） ====================

    def add_snapshot(self, full_name: str, data: Dict[str, Any]) -> bool:
        """保存仓库快照数据。

        Args:
            full_name: 仓库全名。
            data: 快照数据（stars, forks, open_issues, watchers）。

        Returns:
            是否保存成功。
        """
        conn = self._get_conn()
        try:
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""
                INSERT OR IGNORE INTO snapshots
                (full_name, stars, forks, open_issues, watchers, snapshot_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                full_name,
                data.get("stars", 0),
                data.get("forks", 0),
                data.get("open_issues", 0),
                data.get("watchers", 0),
                now,
            ))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error("保存快照失败: %s", e)
            return False
        finally:
            conn.close()

    def get_snapshots(
        self, full_name: str, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """获取仓库的历史快照。

        Args:
            full_name: 仓库全名。
            limit: 返回数量。

        Returns:
            快照列表（按时间升序）。
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                SELECT * FROM snapshots WHERE full_name = ?
                ORDER BY snapshot_at ASC LIMIT ?
            """, (full_name, limit))
            return [self._row_to_dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def get_latest_snapshot(
        self, full_name: str
    ) -> Optional[Dict[str, Any]]:
        """获取仓库的最新快照。

        Args:
            full_name: 仓库全名。

        Returns:
            最新快照字典，如果不存在返回 None。
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                SELECT * FROM snapshots WHERE full_name = ?
                ORDER BY snapshot_at DESC LIMIT 1
            """, (full_name,))
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None
        except sqlite3.Error:
            return None
        finally:
            conn.close()

    def cleanup_old_snapshots(self, days: int = 90) -> int:
        """清理过期的快照数据。

        Args:
            days: 保留最近多少天的数据。

        Returns:
            清理的记录数。
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                DELETE FROM snapshots WHERE snapshot_at < datetime('now', ?)
            """, (f"-{days} days",))
            conn.commit()
            deleted = cursor.rowcount
            if deleted > 0:
                logger.info("清理了 %d 条过期快照", deleted)
            return deleted
        except sqlite3.Error as e:
            logger.error("清理快照失败: %s", e)
            return 0
        finally:
            conn.close()

    # ==================== 辅助方法 ====================

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        """将 sqlite3.Row 转换为普通字典。

        Args:
            row: 数据库行对象。

        Returns:
            字典。
        """
        result = dict(row)
        # 尝试解析 JSON 字段
        for key in ("topics",):
            if key in result and isinstance(result[key], str):
                try:
                    result[key] = json.loads(result[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        return result

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息。

        Returns:
            包含各表记录数的统计字典。
        """
        conn = self._get_conn()
        try:
            stats: Dict[str, Any] = {}
            for table in ("favorites", "history", "preferences", "tags", "snapshots"):
                cursor = conn.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                stats[table] = cursor.fetchone()["cnt"]
            stats["db_path"] = self._db_path
            stats["db_size"] = os.path.getsize(self._db_path) if os.path.exists(self._db_path) else 0
            return stats
        except sqlite3.Error as e:
            logger.error("获取统计信息失败: %s", e)
            return {}
        finally:
            conn.close()
