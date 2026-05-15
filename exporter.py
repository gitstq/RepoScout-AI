"""
exporter.py - 报告导出模块

将仓库数据和分析结果导出为多种格式：
- JSON 格式导出
- CSV 格式导出
- Markdown 格式导出（含表格、徽章）
- HTML 格式导出（带样式的报告页面）

纯 Python 实现，无外部依赖。
"""

import csv
import io
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseExporter:
    """导出器基类。"""

    def __init__(self) -> None:
        """初始化导出器。"""
        self._generated_at = datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )

    def _format_number(self, num: int) -> str:
        """格式化数字（添加千位分隔符）。

        Args:
            num: 数字。

        Returns:
            格式化后的字符串。
        """
        return f"{num:,}"

    def _get_grade_color(self, grade: str) -> str:
        """获取等级对应的颜色标签（用于 Markdown）。

        Args:
            grade: 等级字符串。

        Returns:
            带颜色的 Markdown 文本。
        """
        colors = {
            "S": "#FFD700",  # 金色
            "A": "#28a745",  # 绿色
            "B": "#17a2b8",  # 蓝色
            "C": "#ffc107",  # 黄色
            "D": "#fd7e14",  # 橙色
            "F": "#dc3545",  # 红色
        }
        color = colors.get(grade, "#6c757d")
        return f"![](https://img.shields.io/badge/Grade-{grade}-{color.replace('#', '')})"


class JSONExporter(BaseExporter):
    """JSON 格式导出器。"""

    def export(
        self,
        data: Any,
        filepath: str,
        pretty: bool = True,
    ) -> str:
        """导出数据为 JSON 文件。

        Args:
            data: 要导出的数据。
            filepath: 输出文件路径。
            pretty: 是否格式化输出。

        Returns:
            输出文件路径。
        """
        indent = 2 if pretty else None
        content = json.dumps(data, indent=indent, ensure_ascii=False, default=str)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("JSON 导出完成: %s", filepath)
        return filepath


class CSVExporter(BaseExporter):
    """CSV 格式导出器。"""

    def export_repos(
        self,
        repos: List[Dict[str, Any]],
        filepath: str,
        fields: Optional[List[str]] = None,
    ) -> str:
        """导出仓库列表为 CSV 文件。

        Args:
            repos: 仓库信息列表。
            filepath: 输出文件路径。
            fields: 要导出的字段列表。如果为 None，使用默认字段。

        Returns:
            输出文件路径。
        """
        default_fields = [
            "full_name", "name", "description", "language",
            "stars", "forks", "html_url",
        ]

        export_fields = fields or default_fields

        # 确保所有仓库都有这些字段
        rows = []
        for repo in repos:
            row = {}
            for field in export_fields:
                value = repo.get(field, "")
                if isinstance(value, (list, dict)):
                    value = json.dumps(value, ensure_ascii=False)
                row[field] = str(value) if value is not None else ""
            rows.append(row)

        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=export_fields)
            writer.writeheader()
            writer.writerows(rows)

        logger.info("CSV 导出完成: %s (%d 条记录)", filepath, len(rows))
        return filepath

    def export_scores(
        self,
        scores: List[Dict[str, Any]],
        filepath: str,
    ) -> str:
        """导出评分为 CSV 文件。

        Args:
            scores: 评分结果列表。
            filepath: 输出文件路径。

        Returns:
            输出文件路径。
        """
        fields = [
            "full_name", "grade", "activity", "community",
            "health", "popularity", "overall",
        ]

        rows = []
        for item in scores:
            score_data = item.get("scores", {})
            row = {
                "full_name": item.get("full_name", ""),
                "grade": item.get("grade", ""),
                "activity": score_data.get("activity", 0),
                "community": score_data.get("community", 0),
                "health": score_data.get("health", 0),
                "popularity": score_data.get("popularity", 0),
                "overall": score_data.get("overall", 0),
            }
            rows.append(row)

        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

        logger.info("评分 CSV 导出完成: %s", filepath)
        return filepath


class MarkdownExporter(BaseExporter):
    """Markdown 格式导出器。"""

    def export_repos(
        self,
        repos: List[Dict[str, Any]],
        filepath: str,
        title: str = "GitHub 仓库报告",
    ) -> str:
        """导出仓库列表为 Markdown 文件。

        Args:
            repos: 仓库信息列表。
            filepath: 输出文件路径。
            title: 报告标题。

        Returns:
            输出文件路径。
        """
        lines = []
        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"> 生成时间: {self._generated_at}")
        lines.append(f"> 仓库数量: {len(repos)}")
        lines.append("")

        # 汇总表格
        lines.append("## 仓库列表")
        lines.append("")
        lines.append("| # | 仓库 | 描述 | 语言 | Stars | Forks |")
        lines.append("|---|------|------|------|-------|-------|")

        for i, repo in enumerate(repos, 1):
            name = repo.get("full_name", "")
            desc = (repo.get("description", "") or "")[:60]
            lang = repo.get("language", "") or "-"
            stars = self._format_number(repo.get("stargazers_count", repo.get("stars", 0)) or 0)
            forks = self._format_number(repo.get("forks_count", repo.get("forks", 0)) or 0)
            lines.append(f"| {i} | **{name}** | {desc} | {lang} | {stars} | {forks} |")

        lines.append("")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info("Markdown 导出完成: %s", filepath)
        return filepath

    def export_scores(
        self,
        scores: List[Dict[str, Any]],
        filepath: str,
        title: str = "仓库评分报告",
    ) -> str:
        """导出评分为 Markdown 文件。

        Args:
            scores: 评分结果列表。
            filepath: 输出文件路径。
            title: 报告标题。

        Returns:
            输出文件路径。
        """
        lines = []
        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"> 生成时间: {self._generated_at}")
        lines.append(f"> 评估仓库数: {len(scores)}")
        lines.append("")

        # 评分汇总表
        lines.append("## 评分概览")
        lines.append("")
        lines.append("| 排名 | 仓库 | 等级 | 活跃度 | 社区 | 健康 | 流行 | 综合 |")
        lines.append("|------|------|------|--------|------|------|------|------|")

        for i, item in enumerate(scores, 1):
            name = item.get("full_name", "")
            grade = item.get("grade", "-")
            s = item.get("scores", {})
            lines.append(
                f"| {i} | **{name}** | {grade} "
                f"| {s.get('activity', 0)} "
                f"| {s.get('community', 0)} "
                f"| {s.get('health', 0)} "
                f"| {s.get('popularity', 0)} "
                f"| **{s.get('overall', 0)}** |"
            )

        lines.append("")

        # 等级分布
        grade_dist: Dict[str, int] = {}
        for item in scores:
            g = item.get("grade", "F")
            grade_dist[g] = grade_dist.get(g, 0) + 1

        if grade_dist:
            lines.append("## 等级分布")
            lines.append("")
            for g in ["S", "A", "B", "C", "D", "F"]:
                count = grade_dist.get(g, 0)
                if count > 0:
                    bar = "#" * count
                    lines.append(f"- **{g}**: {bar} ({count})")
            lines.append("")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info("评分 Markdown 导出完成: %s", filepath)
        return filepath

    def export_trending(
        self,
        repos: List[Dict[str, Any]],
        filepath: str,
        language: str = "",
        since: str = "daily",
    ) -> str:
        """导出 Trending 仓库为 Markdown。

        Args:
            repos: Trending 仓库列表。
            filepath: 输出文件路径。
            language: 编程语言。
            since: 时间范围。

        Returns:
            输出文件路径。
        """
        title = f"GitHub Trending"
        if language:
            title += f" - {language}"
        if since:
            title += f" ({since})"

        return self.export_repos(repos, filepath, title)


class HTMLExporter(BaseExporter):
    """HTML 格式导出器。"""

    def export_repos(
        self,
        repos: List[Dict[str, Any]],
        filepath: str,
        title: str = "GitHub 仓库报告",
    ) -> str:
        """导出仓库列表为 HTML 文件。

        Args:
            repos: 仓库信息列表。
            filepath: 输出文件路径。
            title: 报告标题。

        Returns:
            输出文件路径。
        """
        rows_html = ""
        for i, repo in enumerate(repos, 1):
            name = repo.get("full_name", "")
            desc = (repo.get("description", "") or "")[:100]
            lang = repo.get("language", "") or "-"
            stars = self._format_number(repo.get("stargazers_count", repo.get("stars", 0)) or 0)
            forks = self._format_number(repo.get("forks_count", repo.get("forks", 0)) or 0)
            html_url = f"https://github.com/{name}"

            rows_html += f"""
            <tr>
                <td>{i}</td>
                <td><a href="{html_url}" target="_blank">{name}</a></td>
                <td class="desc">{self._escape_html(desc)}</td>
                <td><span class="lang-badge">{self._escape_html(lang)}</span></td>
                <td class="stars">&#9733; {stars}</td>
                <td>{forks}</td>
            </tr>"""

        html = self._wrap_html(title, f"""
        <div class="header">
            <h1>{self._escape_html(title)}</h1>
            <p class="meta">生成时间: {self._generated_at} | 仓库数量: {len(repos)}</p>
        </div>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>仓库</th>
                    <th>描述</th>
                    <th>语言</th>
                    <th>Stars</th>
                    <th>Forks</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info("HTML 导出完成: %s", filepath)
        return filepath

    def export_scores(
        self,
        scores: List[Dict[str, Any]],
        filepath: str,
        title: str = "仓库评分报告",
    ) -> str:
        """导出评分为 HTML 文件。

        Args:
            scores: 评分结果列表。
            filepath: 输出文件路径。
            title: 报告标题。

        Returns:
            输出文件路径。
        """
        rows_html = ""
        for i, item in enumerate(scores, 1):
            name = item.get("full_name", "")
            grade = item.get("grade", "-")
            s = item.get("scores", {})
            grade_class = f"grade-{grade.lower()}"
            html_url = f"https://github.com/{name}"

            rows_html += f"""
            <tr>
                <td>{i}</td>
                <td><a href="{html_url}" target="_blank">{name}</a></td>
                <td><span class="grade-badge {grade_class}">{grade}</span></td>
                <td>{s.get('activity', 0)}</td>
                <td>{s.get('community', 0)}</td>
                <td>{s.get('health', 0)}</td>
                <td>{s.get('popularity', 0)}</td>
                <td class="overall">{s.get('overall', 0)}</td>
            </tr>"""

        # 等级分布
        grade_dist: Dict[str, int] = {}
        for item in scores:
            g = item.get("grade", "F")
            grade_dist[g] = grade_dist.get(g, 0) + 1

        dist_html = ""
        for g in ["S", "A", "B", "C", "D", "F"]:
            count = grade_dist.get(g, 0)
            if count > 0:
                pct = count / len(scores) * 100 if scores else 0
                dist_html += f"""
                <div class="grade-bar">
                    <span class="grade-label">{g}</span>
                    <div class="bar" style="width: {pct}%"></div>
                    <span class="grade-count">{count}</span>
                </div>"""

        html = self._wrap_html(title, f"""
        <div class="header">
            <h1>{self._escape_html(title)}</h1>
            <p class="meta">生成时间: {self._generated_at} | 评估仓库数: {len(scores)}</p>
        </div>

        <div class="grade-distribution">
            <h2>等级分布</h2>
            {dist_html}
        </div>

        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>仓库</th>
                    <th>等级</th>
                    <th>活跃度</th>
                    <th>社区</th>
                    <th>健康</th>
                    <th>流行</th>
                    <th>综合</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info("评分 HTML 导出完成: %s", filepath)
        return filepath

    def _wrap_html(self, title: str, body: str) -> str:
        """生成完整的 HTML 页面。

        Args:
            title: 页面标题。
            body: 页面内容。

        Returns:
            完整的 HTML 字符串。
        """
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._escape_html(title)} - RepoScout-AI</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f6f8fa;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
            padding: 30px;
        }}
        .header {{
            border-bottom: 2px solid #e1e4e8;
            padding-bottom: 16px;
            margin-bottom: 24px;
        }}
        .header h1 {{
            font-size: 24px;
            color: #24292e;
        }}
        .meta {{
            color: #586069;
            font-size: 14px;
            margin-top: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
        }}
        th, td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #e1e4e8;
        }}
        th {{
            background: #f6f8fa;
            font-weight: 600;
            font-size: 13px;
            color: #24292e;
        }}
        td a {{
            color: #0366d6;
            text-decoration: none;
            font-weight: 500;
        }}
        td a:hover {{
            text-decoration: underline;
        }}
        .desc {{
            color: #586069;
            font-size: 13px;
            max-width: 400px;
        }}
        .stars {{
            color: #e3b341;
            font-weight: 500;
        }}
        .lang-badge {{
            display: inline-block;
            padding: 2px 8px;
            background: #f1f8ff;
            color: #0366d6;
            border-radius: 12px;
            font-size: 12px;
        }}
        .overall {{
            font-weight: 700;
            color: #24292e;
        }}
        .grade-badge {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 14px;
            color: #fff;
        }}
        .grade-s {{ background: #FFD700; color: #333; }}
        .grade-a {{ background: #28a745; }}
        .grade-b {{ background: #17a2b8; }}
        .grade-c {{ background: #ffc107; color: #333; }}
        .grade-d {{ background: #fd7e14; }}
        .grade-f {{ background: #dc3545; }}
        .grade-distribution {{
            margin-bottom: 24px;
        }}
        .grade-distribution h2 {{
            font-size: 18px;
            margin-bottom: 12px;
        }}
        .grade-bar {{
            display: flex;
            align-items: center;
            margin-bottom: 6px;
        }}
        .grade-label {{
            width: 20px;
            font-weight: 700;
            text-align: center;
        }}
        .bar {{
            height: 20px;
            background: #28a745;
            border-radius: 3px;
            margin: 0 8px;
            min-width: 4px;
        }}
        .grade-count {{
            font-size: 13px;
            color: #586069;
        }}
        .footer {{
            margin-top: 24px;
            padding-top: 16px;
            border-top: 1px solid #e1e4e8;
            text-align: center;
            color: #586069;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        {body}
        <div class="footer">
            Generated by <strong>RepoScout-AI</strong> | {self._generated_at}
        </div>
    </div>
</body>
</html>"""

    @staticmethod
    def _escape_html(text: str) -> str:
        """转义 HTML 特殊字符。

        Args:
            text: 原始文本。

        Returns:
            转义后的文本。
        """
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )


class ReportExporter:
    """统一报告导出管理器。

    根据指定的格式自动选择合适的导出器。
    """

    def __init__(self) -> None:
        """初始化导出管理器。"""
        self._json_exporter = JSONExporter()
        self._csv_exporter = CSVExporter()
        self._md_exporter = MarkdownExporter()
        self._html_exporter = HTMLExporter()

    def export(
        self,
        data: Any,
        format_type: str,
        filepath: str,
        **kwargs: Any,
    ) -> str:
        """导出数据到指定格式。

        Args:
            data: 要导出的数据。
            format_type: 导出格式（json/csv/md/markdown/html）。
            filepath: 输出文件路径。
            **kwargs: 额外参数。

        Returns:
            输出文件路径。

        Raises:
            ValueError: 不支持的导出格式。
        """
        # 确保输出目录存在
        dir_path = os.path.dirname(filepath)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        fmt = format_type.lower()

        if fmt == "json":
            return self._json_exporter.export(data, filepath, **kwargs)

        elif fmt in ("csv",):
            if isinstance(data, list) and data and "scores" in data[0]:
                return self._csv_exporter.export_scores(data, filepath)
            return self._csv_exporter.export_repos(data, filepath, **kwargs)

        elif fmt in ("md", "markdown"):
            if isinstance(data, list) and data and "scores" in data[0]:
                return self._md_exporter.export_scores(
                    data, filepath, **kwargs
                )
            return self._md_exporter.export_repos(data, filepath, **kwargs)

        elif fmt == "html":
            if isinstance(data, list) and data and "scores" in data[0]:
                return self._html_exporter.export_scores(
                    data, filepath, **kwargs
                )
            return self._html_exporter.export_repos(data, filepath, **kwargs)

        else:
            raise ValueError(
                f"不支持的导出格式: {format_type}。"
                f"支持的格式: json, csv, md, markdown, html"
            )

    def auto_export(
        self,
        data: Any,
        filepath: str,
        **kwargs: Any,
    ) -> str:
        """根据文件扩展名自动选择导出格式。

        Args:
            data: 要导出的数据。
            filepath: 输出文件路径。

        Returns:
            输出文件路径。
        """
        ext = os.path.splitext(filepath)[1].lower().lstrip(".")
        format_map = {
            "json": "json",
            "csv": "csv",
            "md": "md",
            "markdown": "md",
            "html": "html",
            "htm": "html",
        }
        fmt = format_map.get(ext, "json")
        return self.export(data, fmt, filepath, **kwargs)
