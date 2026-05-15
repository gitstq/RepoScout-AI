"""
tracker.py - 趋势追踪模块

追踪 GitHub 仓库的增长趋势，包括：
- Star 增速计算（日/周/月增速）
- Fork 趋势分析
- 活跃度变化检测
- 趋势可视化（ASCII 图表）

纯 Python 实现，无外部依赖。
"""

import logging
import math
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TrendPoint:
    """单个趋势数据点。"""

    def __init__(
        self,
        timestamp: str,
        stars: int = 0,
        forks: int = 0,
        open_issues: int = 0,
        watchers: int = 0,
    ) -> None:
        """初始化趋势数据点。

        Args:
            timestamp: 时间戳字符串。
            stars: Star 数量。
            forks: Fork 数量。
            open_issues: Open Issue 数量。
            watchers: Watcher 数量。
        """
        self.timestamp = timestamp
        self.stars = stars
        self.forks = forks
        self.open_issues = open_issues
        self.watchers = watchers

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。

        Returns:
            数据点字典。
        """
        return {
            "timestamp": self.timestamp,
            "stars": self.stars,
            "forks": self.forks,
            "open_issues": self.open_issues,
            "watchers": self.watchers,
        }


class TrendAnalyzer:
    """趋势分析器。

    分析仓库的历史数据，计算各种增长指标。
    """

    def __init__(self) -> None:
        """初始化趋势分析器。"""
        pass

    def calculate_growth_rate(
        self, points: List[TrendPoint]
    ) -> Dict[str, Any]:
        """计算增长速率。

        Args:
            points: 趋势数据点列表（按时间升序）。

        Returns:
            包含日/周/月增速的字典。
        """
        if len(points) < 2:
            return {
                "daily_rate": 0.0,
                "weekly_rate": 0.0,
                "monthly_rate": 0.0,
                "total_growth": 0,
                "avg_daily_growth": 0.0,
            }

        first = points[0]
        last = points[-1]

        # 计算时间跨度（天）
        try:
            t_first = datetime.fromisoformat(first.timestamp.replace("Z", "+00:00"))
            t_last = datetime.fromisoformat(last.timestamp.replace("Z", "+00:00"))
            days = max(1, (t_last - t_first).total_seconds() / 86400)
        except (ValueError, AttributeError):
            days = max(1, len(points))

        # Star 增长
        star_growth = last.stars - first.stars
        fork_growth = last.forks - first.forks

        # 日均增长
        avg_daily_stars = star_growth / days
        avg_daily_forks = fork_growth / days

        # 增长率（相对增长）
        star_rate = (
            (star_growth / first.stars * 100) if first.stars > 0 else 0.0
        )
        fork_rate = (
            (fork_growth / first.forks * 100) if first.forks > 0 else 0.0
        )

        result = {
            "daily_rate": round(avg_daily_stars, 2),
            "weekly_rate": round(avg_daily_stars * 7, 2),
            "monthly_rate": round(avg_daily_stars * 30, 2),
            "total_star_growth": star_growth,
            "total_fork_growth": fork_growth,
            "star_growth_rate": round(star_rate, 2),
            "fork_growth_rate": round(fork_rate, 2),
            "avg_daily_stars": round(avg_daily_stars, 2),
            "avg_daily_forks": round(avg_daily_forks, 2),
            "days_tracked": round(days, 1),
            "data_points": len(points),
        }

        logger.debug("增长分析: %s", result)
        return result

    def detect_anomalies(
        self, points: List[TrendPoint], threshold: float = 2.0
    ) -> List[Dict[str, Any]]:
        """检测异常增长点。

        Args:
            points: 趋势数据点列表。
            threshold: 异常阈值（标准差的倍数）。

        Returns:
            异常点列表。
        """
        if len(points) < 3:
            return []

        # 计算每日 star 增量
        deltas = []
        for i in range(1, len(points)):
            delta = points[i].stars - points[i - 1].stars
            deltas.append(delta)

        if not deltas:
            return []

        # 计算统计量
        mean = sum(deltas) / len(deltas)
        variance = sum((d - mean) ** 2 for d in deltas) / len(deltas)
        std = math.sqrt(variance)

        if std == 0:
            return []

        anomalies = []
        for i, delta in enumerate(deltas):
            z_score = abs(delta - mean) / std
            if z_score > threshold:
                anomalies.append({
                    "timestamp": points[i + 1].timestamp,
                    "delta": delta,
                    "z_score": round(z_score, 2),
                    "type": "spike" if delta > mean else "drop",
                })

        logger.debug("检测到 %d 个异常点", len(anomalies))
        return anomalies

    def forecast(
        self, points: List[TrendPoint], days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """简单线性预测未来趋势。

        Args:
            points: 历史数据点。
            days_ahead: 预测天数。

        Returns:
            预测数据点列表。
        """
        if len(points) < 2:
            return []

        # 使用最近的数据点进行线性回归
        recent = points[-min(30, len(points)):]
        n = len(recent)

        # 简单线性回归：y = a + b*x
        x_values = list(range(n))
        y_values = [p.stars for p in recent]

        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)

        if denominator == 0:
            return []

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean

        # 生成预测
        forecast = []
        last_time = datetime.now(timezone.utc)

        for day in range(1, days_ahead + 1):
            predicted_stars = intercept + slope * (n - 1 + day)
            forecast_time = last_time + timedelta(days=day)
            forecast.append({
                "date": forecast_time.strftime("%Y-%m-%d"),
                "predicted_stars": max(0, round(predicted_stars)),
                "predicted_daily_growth": max(0, round(slope, 2)),
            })

        logger.debug("预测未来 %d 天趋势", days_ahead)
        return forecast

    def compare_trends(
        self,
        repo_trends: Dict[str, List[TrendPoint]],
    ) -> Dict[str, Any]:
        """比较多个仓库的趋势。

        Args:
            repo_trends: 仓库名到趋势数据点的映射。

        Returns:
            比较结果字典。
        """
        comparison = {}
        for full_name, points in repo_trends.items():
            growth = self.calculate_growth_rate(points)
            comparison[full_name] = growth

        return comparison


class ASCIIVisualizer:
    """ASCII 趋势图表可视化器。

    在终端中绘制简单的趋势图表。
    """

    # 图表字符
    BLOCK_CHARS = "▁▂▃▄▅▆▇█"
    FALLBACK_CHARS = "_.,-~:;=!*#$@"

    def __init__(self, width: int = 60, height: int = 15) -> None:
        """初始化可视化器。

        Args:
            width: 图表宽度（字符数）。
            height: 图表高度（行数）。
        """
        self._width = width
        self._height = height

    def sparkline(self, values: List[float], char_set: Optional[str] = None) -> str:
        """生成单行迷你趋势图（sparkline）。

        Args:
            values: 数值列表。
            char_set: 自定义字符集。

        Returns:
            Sparkline 字符串。
        """
        if not values:
            return ""

        chars = char_set or self.BLOCK_CHARS
        min_val = min(values)
        max_val = max(values)

        if max_val == min_val:
            return chars[len(chars) // 2] * len(values)

        range_val = max_val - min_val
        result = []
        for v in values:
            idx = int((v - min_val) / range_val * (len(chars) - 1))
            idx = max(0, min(len(chars) - 1, idx))
            result.append(chars[idx])

        return "".join(result)

    def bar_chart(
        self,
        data: List[Tuple[str, float]],
        title: str = "",
        max_bar_width: int = 40,
    ) -> str:
        """生成水平柱状图。

        Args:
            data: (标签, 数值) 列表。
            title: 图表标题。
            max_bar_width: 最大柱宽。

        Returns:
            柱状图字符串。
        """
        if not data:
            return "无数据"

        lines = []
        if title:
            lines.append(f"  {title}")
            lines.append("")

        max_val = max(v for _, v in data)
        label_width = max(len(label) for label, _ in data)

        for label, value in data:
            if max_val > 0:
                bar_len = int(value / max_val * max_bar_width)
            else:
                bar_len = 0
            bar = self.BLOCK_CHARS[-1] * bar_len
            line = f"  {label:>{label_width}}  {bar} {value:.1f}"
            lines.append(line)

        return "\n".join(lines)

    def line_chart(
        self,
        points: List[TrendPoint],
        metric: str = "stars",
        title: str = "",
    ) -> str:
        """生成 ASCII 折线图。

        Args:
            points: 趋势数据点列表。
            metric: 要绘制的指标（stars/forks/open_issues）。
            title: 图表标题。

        Returns:
            折线图字符串。
        """
        if len(points) < 2:
            return "数据点不足，无法绘制图表"

        # 提取数值
        values = []
        labels = []
        for p in points:
            val = getattr(p, metric, 0)
            values.append(val)
            # 缩短时间标签
            try:
                dt = datetime.fromisoformat(p.timestamp.replace("Z", "+00:00"))
                labels.append(dt.strftime("%m-%d"))
            except (ValueError, AttributeError):
                labels.append(p.timestamp[:10] if len(p.timestamp) >= 10 else p.timestamp)

        min_val = min(values)
        max_val = max(values)

        if max_val == min_val:
            max_val = min_val + 1

        width = min(self._width, len(values))
        height = self._height

        lines = []
        if title:
            lines.append(f"  {title}")
            lines.append("")

        # Y 轴标签
        y_labels = []
        for i in range(height):
            val = max_val - (max_val - min_val) * i / (height - 1)
            y_labels.append(val)

        # 绘制图表
        for row in range(height):
            threshold = max_val - (max_val - min_val) * row / (height - 1)
            line_parts = [f"  {threshold:>10.0f} |"]

            for col in range(width):
                # 映射到数据索引
                idx = int(col * (len(values) - 1) / max(1, width - 1))
                val = values[idx]

                # 判断是否应该画点
                next_threshold = max_val - (max_val - min_val) * (row + 1) / (height - 1)
                if next_threshold <= val <= threshold:
                    line_parts.append(self.BLOCK_CHARS[-1])
                elif abs(val - threshold) < (max_val - min_val) / (height - 1) * 0.5:
                    line_parts.append(self.BLOCK_CHARS[-1])
                else:
                    line_parts.append(" ")

            lines.append("".join(line_parts))

        # X 轴
        lines.append(f"  {'':>10} +{'-' * width}")

        # X 轴标签（每隔几个显示一个）
        step = max(1, width // 8)
        x_labels_line = f"  {'':>12}"
        for col in range(0, width, step):
            idx = int(col * (len(labels) - 1) / max(1, width - 1))
            x_labels_line += f"{labels[idx]:>{step}}"
        lines.append(x_labels_line)

        return "\n".join(lines)

    def trend_report(
        self,
        full_name: str,
        points: List[TrendPoint],
        growth: Dict[str, Any],
    ) -> str:
        """生成趋势报告。

        Args:
            full_name: 仓库名称。
            points: 趋势数据点。
            growth: 增长分析结果。

        Returns:
            格式化的趋势报告字符串。
        """
        lines = []
        lines.append("=" * 60)
        lines.append(f"  趋势报告: {full_name}")
        lines.append("=" * 60)
        lines.append("")

        # 基本统计
        lines.append("  [基本统计]")
        lines.append(f"    追踪天数: {growth.get('days_tracked', 0)}")
        lines.append(f"    数据点数: {growth.get('data_points', 0)}")
        lines.append(f"    总 Star 增长: {growth.get('total_star_growth', 0):+d}")
        lines.append(f"    总 Fork 增长: {growth.get('total_fork_growth', 0):+d}")
        lines.append("")

        # 增长速率
        lines.append("  [增长速率]")
        lines.append(f"    日均 Star: {growth.get('avg_daily_stars', 0):.1f}")
        lines.append(f"    周均 Star: {growth.get('weekly_rate', 0):.1f}")
        lines.append(f"    月均 Star: {growth.get('monthly_rate', 0):.1f}")
        lines.append(f"    Star 增长率: {growth.get('star_growth_rate', 0):.1f}%")
        lines.append("")

        # Sparkline
        if points:
            star_values = [p.stars for p in points]
            sparkline = self.sparkline(star_values)
            lines.append(f"  Star 趋势: {sparkline}")

            fork_values = [p.forks for p in points]
            sparkline = self.sparkline(fork_values)
            lines.append(f"  Fork 趋势: {sparkline}")
        lines.append("")

        # ASCII 折线图
        if len(points) >= 2:
            chart = self.line_chart(points, "stars", "Star 增长趋势")
            lines.append(chart)
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)


class TrendTracker:
    """趋势追踪管理器。

    整合数据采集、分析和可视化功能。
    """

    def __init__(self, storage=None) -> None:
        """初始化趋势追踪器。

        Args:
            storage: Storage 实例，用于持久化数据。
        """
        self._storage = storage
        self._analyzer = TrendAnalyzer()
        self._visualizer = ASCIIVisualizer()
        logger.info("趋势追踪器初始化完成")

    def track(self, full_name: str, repo_data: Dict[str, Any]) -> bool:
        """记录仓库当前数据快照。

        Args:
            full_name: 仓库全名。
            repo_data: 仓库数据。

        Returns:
            是否记录成功。
        """
        snapshot = {
            "stars": repo_data.get("stargazers_count", 0) or repo_data.get("stars", 0) or 0,
            "forks": repo_data.get("forks_count", 0) or repo_data.get("forks", 0) or 0,
            "open_issues": repo_data.get("open_issues_count", 0) or 0,
            "watchers": repo_data.get("subscribers_count", 0) or 0,
        }

        if self._storage:
            return self._storage.add_snapshot(full_name, snapshot)

        logger.info("快照已记录: %s (stars=%d)", full_name, snapshot["stars"])
        return True

    def get_trend(
        self, full_name: str, limit: int = 30
    ) -> List[TrendPoint]:
        """获取仓库的趋势数据。

        Args:
            full_name: 仓库全名。
            limit: 数据点数量。

        Returns:
            趋势数据点列表。
        """
        if not self._storage:
            return []

        snapshots = self._storage.get_snapshots(full_name, limit)
        points = []
        for snap in snapshots:
            point = TrendPoint(
                timestamp=snap.get("snapshot_at", ""),
                stars=snap.get("stars", 0),
                forks=snap.get("forks", 0),
                open_issues=snap.get("open_issues", 0),
                watchers=snap.get("watchers", 0),
            )
            points.append(point)

        return points

    def analyze(self, full_name: str) -> Dict[str, Any]:
        """分析仓库趋势。

        Args:
            full_name: 仓库全名。

        Returns:
            分析结果字典。
        """
        points = self.get_trend(full_name)
        growth = self._analyzer.calculate_growth_rate(points)
        anomalies = self._analyzer.detect_anomalies(points)
        forecast = self._analyzer.forecast(points)

        return {
            "full_name": full_name,
            "growth": growth,
            "anomalies": anomalies,
            "forecast": forecast,
            "data_points": len(points),
        }

    def visualize(self, full_name: str) -> str:
        """生成趋势可视化报告。

        Args:
            full_name: 仓库全名。

        Returns:
            可视化报告字符串。
        """
        points = self.get_trend(full_name)
        if not points:
            return f"暂无 {full_name} 的趋势数据，请先使用 track 命令记录数据。"

        growth = self._analyzer.calculate_growth_rate(points)
        return self._visualizer.trend_report(full_name, points, growth)

    def multi_compare(
        self, full_names: List[str]
    ) -> str:
        """比较多仓库趋势。

        Args:
            full_names: 仓库名称列表。

        Returns:
            比较报告字符串。
        """
        repo_trends = {}
        for name in full_names:
            points = self.get_trend(name)
            if points:
                repo_trends[name] = points

        if not repo_trends:
            return "无趋势数据可供比较"

        comparison = self._analyzer.compare_trends(repo_trends)

        lines = []
        lines.append("=" * 60)
        lines.append("  多仓库趋势比较")
        lines.append("=" * 60)
        lines.append("")

        # 表头
        header = f"  {'仓库':<30} {'日均Star':>10} {'周均Star':>10} {'增长率':>10}"
        lines.append(header)
        lines.append("  " + "-" * 58)

        for name, growth in comparison.items():
            line = (
                f"  {name:<30} "
                f"{growth.get('avg_daily_stars', 0):>10.1f} "
                f"{growth.get('weekly_rate', 0):>10.1f} "
                f"{growth.get('star_growth_rate', 0):>9.1f}%"
            )
            lines.append(line)

        lines.append("")

        # Sparkline 比较
        for name, pts in repo_trends.items():
            star_values = [p.stars for p in pts]
            sparkline = self._visualizer.sparkline(star_values)
            lines.append(f"  {name:<30} {sparkline}")

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)
