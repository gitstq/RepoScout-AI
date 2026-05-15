"""
tui.py - TUI 界面模块

基于终端控制码实现的交互式文本用户界面（TUI），包括：
- 主菜单界面
- 仓库列表浏览（支持排序、过滤、分页）
- 仓库详情查看
- 搜索界面
- 收藏管理界面
- 趋势图表展示
- 颜色主题支持

纯 Python 实现，使用终端 ANSI 转义序列，无外部依赖。
"""

import logging
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ==================== 终端颜色控制 ====================

class Colors:
    """终端 ANSI 颜色代码。"""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"

    # 前景色
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"

    # 亮色
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # 背景色
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


def colored(text: str, color: str) -> str:
    """为文本添加颜色。

    Args:
        text: 原始文本。
        color: ANSI 颜色代码。

    Returns:
        带颜色代码的文本。
    """
    return f"{color}{text}{Colors.RESET}"


def supports_color() -> bool:
    """检测终端是否支持颜色。

    Returns:
        是否支持颜色输出。
    """
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") in ("dumb", ""):
        return False
    if not sys.stdout.isatty():
        return False
    return True


# ==================== 终端控制 ====================

class Terminal:
    """终端控制工具类。"""

    @staticmethod
    def clear_screen() -> None:
        """清空终端屏幕。"""
        print("\033[2J\033[H", end="", flush=True)

    @staticmethod
    def move_cursor(row: int, col: int) -> None:
        """移动光标到指定位置。

        Args:
            row: 行号（从 0 开始）。
            col: 列号（从 0 开始）。
        """
        print(f"\033[{row + 1};{col + 1}H", end="", flush=True)

    @staticmethod
    def hide_cursor() -> None:
        """隐藏光标。"""
        print("\033[?25l", end="", flush=True)

    @staticmethod
    def show_cursor() -> None:
        """显示光标。"""
        print("\033[?25h", end="", flush=True)

    @staticmethod
    def get_terminal_size() -> Tuple[int, int]:
        """获取终端大小。

        Returns:
            (宽度, 高度) 元组。
        """
        try:
            size = os.get_terminal_size()
            return size.columns, size.lines
        except OSError:
            return 80, 24

    @staticmethod
    def print_line(text: str = "", fill_char: str = " ") -> None:
        """打印一行并填充到终端宽度。

        Args:
            text: 文本内容。
            fill_char: 填充字符。
        """
        width = Terminal.get_terminal_size()[0]
        cleaned = text.replace("\033", "").replace("[", "").replace("m", "")
        # 粗略计算可见字符宽度
        visible_len = len(cleaned)
        padding = max(0, width - visible_len)
        print(f"{text}{fill_char * padding}")


# ==================== UI 组件 ====================

class ProgressBar:
    """简单的文本进度条。"""

    def __init__(
        self,
        total: int = 100,
        width: int = 40,
        fill_char: str = "#",
        empty_char: str = "-",
    ) -> None:
        """初始化进度条。

        Args:
            total: 总量。
            width: 进度条宽度。
            fill_char: 填充字符。
            empty_char: 空白字符。
        """
        self._total = total
        self._width = width
        self._fill_char = fill_char
        self._empty_char = empty_char
        self._current = 0

    def update(self, current: int) -> str:
        """更新进度条。

        Args:
            current: 当前进度。

        Returns:
            进度条字符串。
        """
        self._current = min(current, self._total)
        pct = self._current / self._total if self._total > 0 else 0
        filled = int(pct * self._width)
        bar = self._fill_char * filled + self._empty_char * (self._width - filled)
        return f"[{bar}] {pct * 100:.1f}%"


class Table:
    """文本表格渲染器。"""

    def __init__(self, headers: List[str], col_widths: Optional[List[int]] = None) -> None:
        """初始化表格。

        Args:
            headers: 表头列表。
            col_widths: 列宽列表。如果为 None，自动计算。
        """
        self._headers = headers
        self._rows: List[List[str]] = []
        self._col_widths = col_widths or [len(h) for h in headers]

    def add_row(self, row: List[str]) -> None:
        """添加一行数据。

        Args:
            row: 行数据列表。
        """
        # 自动调整列宽
        for i, cell in enumerate(row):
            cell_len = len(str(cell))
            if i < len(self._col_widths) and cell_len > self._col_widths[i]:
                self._col_widths[i] = cell_len
        self._rows.append([str(cell) for cell in row])

    def render(self, use_color: bool = True) -> str:
        """渲染表格。

        Args:
            use_color: 是否使用颜色。

        Returns:
            表格字符串。
        """
        lines = []

        # 表头
        header_parts = []
        for i, h in enumerate(self._headers):
            w = self._col_widths[i] if i < len(self._col_widths) else len(h)
            if use_color:
                header_parts.append(colored(h.ljust(w), Colors.BOLD + Colors.CYAN))
            else:
                header_parts.append(h.ljust(w))
        lines.append(" | ".join(header_parts))

        # 分隔线
        sep_parts = []
        for i in range(len(self._headers)):
            w = self._col_widths[i] if i < len(self._col_widths) else 10
            sep_parts.append("-" * w)
        lines.append("-+-".join(sep_parts))

        # 数据行
        for row in self._rows:
            row_parts = []
            for i, cell in enumerate(row):
                w = self._col_widths[i] if i < len(self._col_widths) else len(cell)
                row_parts.append(cell.ljust(w)[:w])
            lines.append(" | ".join(row_parts))

        return "\n".join(lines)


# ==================== 主 TUI 应用 ====================

class TUIApp:
    """交互式 TUI 应用主类。

    提供完整的终端交互界面，包括菜单导航、仓库浏览、搜索等功能。
    """

    def __init__(
        self,
        github_client=None,
        storage=None,
    ) -> None:
        """初始化 TUI 应用。

        Args:
            github_client: GitHubClient 实例。
            storage: Storage 实例。
        """
        self._client = github_client
        self._storage = storage
        self._running = True
        self._use_color = supports_color()
        self._current_page = 0
        self._page_size = 10
        self._current_repos: List[Dict[str, Any]] = []
        self._search_query = ""
        self._sort_field = "stars"
        self._sort_order = "desc"
        self._filter_language = ""

        logger.info("TUI 初始化完成 (color=%s)", self._use_color)

    def _c(self, text: str, color: str) -> str:
        """条件着色辅助方法。

        Args:
            text: 文本。
            color: 颜色代码。

        Returns:
            着色后的文本（如果不支持颜色则返回原文）。
        """
        if self._use_color:
            return colored(text, color)
        return text

    def run(self) -> None:
        """启动 TUI 主循环。"""
        Terminal.clear_screen()
        while self._running:
            self._show_main_menu()
            choice = self._get_input("请选择操作")
            self._handle_main_menu(choice)

    def _show_main_menu(self) -> None:
        """显示主菜单。"""
        Terminal.clear_screen()
        print()
        print(self._c("  ╔══════════════════════════════════════════╗", Colors.CYAN))
        print(self._c("  ║       RepoScout-AI  智能仓库发现       ║", Colors.CYAN + Colors.BOLD))
        print(self._c("  ╚══════════════════════════════════════════╝", Colors.CYAN))
        print()
        print(f"  {self._c('1.', Colors.YELLOW)} 搜索仓库")
        print(f"  {self._c('2.', Colors.YELLOW)} 查看 Trending")
        print(f"  {self._c('3.', Colors.YELLOW)} 智能推荐")
        print(f"  {self._c('4.', Colors.YELLOW)} 仓库评分")
        print(f"  {self._c('5.', Colors.YELLOW)} 趋势追踪")
        print(f"  {self._c('6.', Colors.YELLOW)} 收藏管理")
        print(f"  {self._c('7.', Colors.YELLOW)} 浏览历史")
        print(f"  {self._c('8.', Colors.YELLOW)} 配置管理")
        print()
        print(f"  {self._c('0.', Colors.RED)} 退出")
        print()

        # 显示统计信息
        if self._storage:
            stats = self._storage.get_stats()
            fav_count = stats.get("favorites", 0)
            hist_count = stats.get("history", 0)
            print(self._c(f"  收藏: {fav_count} | 浏览: {hist_count}", Colors.DIM))
        print()

    def _handle_main_menu(self, choice: str) -> None:
        """处理主菜单选择。

        Args:
            choice: 用户输入。
        """
        choice = choice.strip()

        if choice == "0" or choice.lower() == "q":
            self._running = False
            print(self._c("\n  再见！", Colors.GREEN))
            time.sleep(0.5)

        elif choice == "1":
            self._search_screen()

        elif choice == "2":
            self._trending_screen()

        elif choice == "3":
            self._recommend_screen()

        elif choice == "4":
            self._score_screen()

        elif choice == "5":
            self._track_screen()

        elif choice == "6":
            self._favorites_screen()

        elif choice == "7":
            self._history_screen()

        elif choice == "8":
            self._config_screen()

        else:
            print(self._c("  无效选择，请重试", Colors.RED))
            time.sleep(1)

    def _get_input(self, prompt: str = "") -> str:
        """获取用户输入。

        Args:
            prompt: 提示文本。

        Returns:
            用户输入的字符串。
        """
        try:
            return input(f"  {self._c(prompt + ': ', Colors.GREEN)}").strip()
        except (EOFError, KeyboardInterrupt):
            return ""

    def _wait_for_continue(self) -> None:
        """等待用户按回车继续。"""
        try:
            input(self._c("\n  按回车键继续...", Colors.DIM))
        except (EOFError, KeyboardInterrupt):
            pass

    # ==================== 搜索界面 ====================

    def _search_screen(self) -> None:
        """搜索界面。"""
        Terminal.clear_screen()
        print(self._c("\n  === 搜索仓库 ===\n", Colors.BOLD))

        query = self._get_input("输入搜索关键词")
        if not query:
            return

        lang = self._get_input("编程语言（可选，回车跳过）")

        print(self._c("\n  搜索中...", Colors.DIM))

        if self._client:
            try:
                result = self._client.search_repositories(
                    query=query,
                    language=lang if lang else None,
                    per_page=self._page_size,
                )
                items = result.get("items", [])
                total = result.get("total_count", 0)
                self._current_repos = items

                print(f"\n  找到 {total} 个仓库，显示前 {len(items)} 个：\n")
                self._show_repo_list(items)

            except Exception as e:
                print(self._c(f"  搜索失败: {e}", Colors.RED))
        else:
            print(self._c("  未配置 GitHub 客户端", Colors.RED))

        self._wait_for_continue()

    # ==================== Trending 界面 ====================

    def _trending_screen(self) -> None:
        """Trending 仓库界面。"""
        Terminal.clear_screen()
        print(self._c("\n  === GitHub Trending ===\n", Colors.BOLD))

        lang = self._get_input("编程语言（可选，回车跳过）")
        since_options = "daily / weekly / monthly"
        since = self._get_input(f"时间范围 ({since_options})")
        if since not in ("daily", "weekly", "monthly"):
            since = "daily"

        print(self._c("\n  获取中...", Colors.DIM))

        if self._client:
            try:
                repos = self._client.get_trending(
                    language=lang if lang else None,
                    since=since,
                )
                self._current_repos = repos

                title = f"  Trending"
                if lang:
                    title += f" ({lang})"
                title += f" - {since}"
                print(f"\n{self._c(title, Colors.BOLD)}\n")

                self._show_repo_list(repos, show_today_stars=True)

            except Exception as e:
                print(self._c(f"  获取失败: {e}", Colors.RED))
        else:
            print(self._c("  未配置 GitHub 客户端", Colors.RED))

        self._wait_for_continue()

    # ==================== 推荐界面 ====================

    def _recommend_screen(self) -> None:
        """智能推荐界面。"""
        Terminal.clear_screen()
        print(self._c("\n  === 智能推荐 ===\n", Colors.BOLD))

        if not self._storage:
            print(self._c("  未配置存储模块", Colors.RED))
            self._wait_for_continue()
            return

        history = self._storage.get_history(limit=50)
        favorites = self._storage.get_favorites(limit=50)

        if not history and not favorites:
            print(self._c("  暂无浏览历史和收藏数据", Colors.YELLOW))
            print(self._c("  请先搜索和浏览一些仓库，系统将根据您的兴趣生成推荐", Colors.DIM))
            self._wait_for_continue()
            return

        print(f"  基于您的浏览历史 ({len(history)}) 和收藏 ({len(favorites)}) 生成推荐...\n")

        # 使用简单的推荐逻辑
        from recommender import Recommender, UserProfile

        recommender = Recommender()
        profile = recommender.build_profile_from_history(history, favorites)

        # 显示用户偏好
        top_langs = profile.get_top_languages(5)
        top_topics = profile.get_top_topics(5)

        if top_langs:
            langs = ", ".join(f"{l}({s:.0f})" for l, s in top_langs)
            print(f"  偏好语言: {self._c(langs, Colors.CYAN)}")
        if top_topics:
            topics = ", ".join(f"{t}({s:.0f})" for t, s in top_topics)
            print(f"  偏好主题: {self._c(topics, Colors.CYAN)}")
        print()

        # 基于偏好语言搜索推荐
        if top_langs and self._client:
            top_lang = top_langs[0][0]
            try:
                result = self._client.search_repositories(
                    query=f"stars:>1000",
                    language=top_lang,
                    sort="stars",
                    per_page=self._page_size,
                )
                items = result.get("items", [])
                print(f"  为您推荐 ({top_lang}):\n")
                self._show_repo_list(items)
            except Exception as e:
                print(self._c(f"  获取推荐失败: {e}", Colors.RED))
        else:
            print(self._c("  数据不足，无法生成推荐", Colors.YELLOW))

        self._wait_for_continue()

    # ==================== 评分界面 ====================

    def _score_screen(self) -> None:
        """仓库评分界面。"""
        Terminal.clear_screen()
        print(self._c("\n  === 仓库评分 ===\n", Colors.BOLD))

        repo_input = self._get_input("输入仓库名称 (owner/repo)")
        if not repo_input:
            return

        if "/" not in repo_input:
            print(self._c("  格式错误，请使用 owner/repo 格式", Colors.RED))
            self._wait_for_continue()
            return

        owner, repo = repo_input.split("/", 1)

        if self._client:
            try:
                print(self._c("  获取仓库信息...", Colors.DIM))
                repo_data = self._client.get_repository(owner, repo)

                from scorer import RepoScorer
                scorer = RepoScorer()
                result = scorer.score(repo_data)

                self._show_score_detail(result)

                # 记录浏览历史
                if self._storage:
                    self._storage.add_history(repo_data, source="score")

            except Exception as e:
                print(self._c(f"  评分失败: {e}", Colors.RED))
        else:
            print(self._c("  未配置 GitHub 客户端", Colors.RED))

        self._wait_for_continue()

    def _show_score_detail(self, score_result: Dict[str, Any]) -> None:
        """显示评分详情。

        Args:
            score_result: 评分结果字典。
        """
        name = score_result.get("full_name", "")
        scores = score_result.get("scores", {})
        grade = score_result.get("grade", "-")
        details = score_result.get("details", {})

        # 等级颜色
        grade_colors = {
            "S": Colors.BRIGHT_YELLOW,
            "A": Colors.GREEN,
            "B": Colors.CYAN,
            "C": Colors.YELLOW,
            "D": Colors.RED,
            "F": Colors.BRIGHT_RED,
        }
        grade_color = grade_colors.get(grade, Colors.WHITE)

        print()
        print(f"  仓库: {self._c(name, Colors.BOLD)}")
        print(f"  等级: {self._c(grade, grade_color + Colors.BOLD)}")
        overall_val = f'{scores.get("overall", 0):.1f}'
        print(f"  综合: {self._c(overall_val, Colors.BOLD)} / 100")
        print()

        # 各维度分数
        dimensions = [
            ("活跃度", "activity", Colors.GREEN),
            ("社区", "community", Colors.CYAN),
            ("健康度", "health", Colors.YELLOW),
            ("流行度", "popularity", Colors.MAGENTA),
        ]

        for label, key, color in dimensions:
            value = scores.get(key, 0)
            bar_width = 30
            filled = int(value / 100 * bar_width)
            bar = self._c("#" * filled, color) + "-" * (bar_width - filled)
            print(f"  {label:6s} |{bar}| {value:.1f}")

        print()

        # 详情
        stars = details.get("stars", 0)
        forks = details.get("forks", 0)
        days = details.get("days_since_push")
        has_license = details.get("has_license", False)
        is_fork = details.get("is_fork", False)

        print(f"  Stars: {stars:,} | Forks: {forks:,}")
        if days is not None:
            print(f"  最近推送: {int(days)} 天前")
        print(f"  许可证: {'有' if has_license else '无'}")
        if is_fork:
            print(self._c("  注意: 这是一个 Fork 仓库", Colors.YELLOW))

    # ==================== 趋势追踪界面 ====================

    def _track_screen(self) -> None:
        """趋势追踪界面。"""
        Terminal.clear_screen()
        print(self._c("\n  === 趋势追踪 ===\n", Colors.BOLD))

        if not self._storage:
            print(self._c("  未配置存储模块", Colors.RED))
            self._wait_for_continue()
            return

        print(f"  {self._c('1.', Colors.YELLOW)} 记录仓库快照")
        print(f"  {self._c('2.', Colors.YELLOW)} 查看趋势报告")
        print(f"  {self._c('3.', Colors.YELLOW)} 比较多仓库")
        print()

        choice = self._get_input("请选择")

        if choice == "1":
            self._track_record()
        elif choice == "2":
            self._track_view()
        elif choice == "3":
            self._track_compare()
        else:
            print(self._c("  无效选择", Colors.RED))

        self._wait_for_continue()

    def _track_record(self) -> None:
        """记录仓库快照。"""
        repo_input = self._get_input("输入仓库名称 (owner/repo)")
        if not repo_input or "/" not in repo_input:
            return

        if self._client:
            try:
                owner, repo = repo_input.split("/", 1)
                repo_data = self._client.get_repository(owner, repo)

                from tracker import TrendTracker
                tracker = TrendTracker(storage=self._storage)
                tracker.track(repo_input, repo_data)

                print(self._c(f"  已记录快照: {repo_input}", Colors.GREEN))
            except Exception as e:
                print(self._c(f"  记录失败: {e}", Colors.RED))
        else:
            print(self._c("  未配置 GitHub 客户端", Colors.RED))

    def _track_view(self) -> None:
        """查看趋势报告。"""
        repo_input = self._get_input("输入仓库名称 (owner/repo)")
        if not repo_input:
            return

        from tracker import TrendTracker
        tracker = TrendTracker(storage=self._storage)
        report = tracker.visualize(repo_input)
        print()
        print(report)

    def _track_compare(self) -> None:
        """比较多仓库趋势。"""
        repos_input = self._get_input("输入仓库名称，用逗号分隔")
        if not repos_input:
            return

        names = [n.strip() for n in repos_input.split(",") if n.strip()]

        from tracker import TrendTracker
        tracker = TrendTracker(storage=self._storage)
        report = tracker.multi_compare(names)
        print()
        print(report)

    # ==================== 收藏管理界面 ====================

    def _favorites_screen(self) -> None:
        """收藏管理界面。"""
        while True:
            Terminal.clear_screen()
            print(self._c("\n  === 收藏管理 ===\n", Colors.BOLD))

            if self._storage:
                favorites = self._storage.get_favorites(limit=20)
                if favorites:
                    print(f"  共 {len(favorites)} 个收藏:\n")
                    for i, fav in enumerate(favorites, 1):
                        name = fav.get("full_name", "")
                        stars = fav.get("stars", 0)
                        lang = fav.get("language", "") or "-"
                        print(f"  {self._c(f'{i:>3}.', Colors.YELLOW)} "
                              f"{self._c(name, Colors.CYAN)} "
                              f"({lang}) "
                              f"{self._c(f'★{stars}', Colors.YELLOW)}")
                else:
                    print(self._c("  暂无收藏", Colors.DIM))
            else:
                print(self._c("  未配置存储模块", Colors.RED))

            print()
            print(f"  {self._c('a.', Colors.YELLOW)} 添加收藏")
            print(f"  {self._c('d.', Colors.YELLOW)} 删除收藏")
            print(f"  {self._c('b.', Colors.RED)} 返回")
            print()

            choice = self._get_input("请选择")
            if choice == "b" or not choice:
                break
            elif choice == "a":
                repo_input = self._get_input("输入仓库名称 (owner/repo)")
                if repo_input and "/" in repo_input:
                    if self._client:
                        try:
                            owner, repo = repo_input.split("/", 1)
                            repo_data = self._client.get_repository(owner, repo)
                            self._storage.add_favorite(repo_data)
                            print(self._c(f"  已收藏: {repo_input}", Colors.GREEN))
                        except Exception as e:
                            print(self._c(f"  获取仓库信息失败: {e}", Colors.RED))
                    else:
                        self._storage.add_favorite({
                            "full_name": repo_input,
                            "name": repo_input.split("/")[-1],
                            "owner": repo_input.split("/")[0],
                        })
                        print(self._c(f"  已收藏: {repo_input}", Colors.GREEN))
                    time.sleep(1)
            elif choice == "d":
                repo_input = self._get_input("输入要删除的仓库名称")
                if repo_input and self._storage:
                    if self._storage.remove_favorite(repo_input):
                        print(self._c(f"  已取消收藏: {repo_input}", Colors.GREEN))
                    else:
                        print(self._c(f"  未找到: {repo_input}", Colors.YELLOW))
                    time.sleep(1)

    # ==================== 浏览历史界面 ====================

    def _history_screen(self) -> None:
        """浏览历史界面。"""
        Terminal.clear_screen()
        print(self._c("\n  === 浏览历史 ===\n", Colors.BOLD))

        if self._storage:
            history = self._storage.get_history(limit=20)
            stats = self._storage.get_history_stats()

            print(f"  总浏览次数: {stats.get('total_views', 0)}\n")

            if history:
                for i, item in enumerate(history, 1):
                    name = item.get("full_name", "")
                    source = item.get("source", "")
                    visited = item.get("visited_at", "")[:16]
                    print(f"  {self._c(f'{i:>3}.', Colors.YELLOW)} "
                          f"{self._c(name, Colors.CYAN)} "
                          f"{self._c(f'[{source}]', Colors.DIM)} "
                          f"{self._c(visited, Colors.DIM)}")
            else:
                print(self._c("  暂无浏览历史", Colors.DIM))

            # 语言分布
            lang_dist = stats.get("language_distribution", [])
            if lang_dist:
                print()
                print(self._c("  语言分布:", Colors.BOLD))
                for item in lang_dist[:5]:
                    lang = item.get("language", "")
                    count = item.get("count", 0)
                    bar = "#" * min(20, count)
                    print(f"    {lang:<12} {self._c(bar, Colors.GREEN)} {count}")
        else:
            print(self._c("  未配置存储模块", Colors.RED))

        self._wait_for_continue()

    # ==================== 配置界面 ====================

    def _config_screen(self) -> None:
        """配置管理界面。"""
        Terminal.clear_screen()
        print(self._c("\n  === 配置管理 ===\n", Colors.BOLD))

        if self._storage:
            prefs = self._storage.get_all_preferences()
            if prefs:
                print("  当前配置:")
                for key, value in prefs.items():
                    print(f"    {self._c(key, Colors.CYAN)} = {value}")
            else:
                print(self._c("  暂无配置", Colors.DIM))
        else:
            print(self._c("  未配置存储模块", Colors.RED))

        print()
        print(f"  {self._c('s.', Colors.YELLOW)} 设置配置项")
        print(f"  {self._c('i.', Colors.YELLOW)} 查看存储统计")
        print(f"  {self._c('b.', Colors.RED)} 返回")
        print()

        choice = self._get_input("请选择")
        if choice == "s" and self._storage:
            key = self._get_input("配置键名")
            value = self._get_input("配置值")
            if key and value:
                self._storage.set_preference(key, value)
                print(self._c(f"  已设置: {key} = {value}", Colors.GREEN))
                time.sleep(1)
        elif choice == "i" and self._storage:
            stats = self._storage.get_stats()
            print()
            print("  存储统计:")
            for key, value in stats.items():
                if key == "db_size":
                    size_kb = value / 1024
                    print(f"    {key}: {size_kb:.1f} KB")
                else:
                    print(f"    {key}: {value}")
            self._wait_for_continue()

    # ==================== 仓库列表显示 ====================

    def _show_repo_list(
        self,
        repos: List[Dict[str, Any]],
        show_today_stars: bool = False,
    ) -> None:
        """显示仓库列表。

        Args:
            repos: 仓库列表。
            show_today_stars: 是否显示今日新增 Star。
        """
        if not repos:
            print(self._c("  无结果", Colors.DIM))
            return

        for i, repo in enumerate(repos, 1):
            name = repo.get("full_name", "")
            desc = (repo.get("description", "") or "")[:50]
            lang = repo.get("language", "") or "-"
            stars = repo.get("stargazers_count", repo.get("stars", 0)) or 0
            forks = repo.get("forks_count", repo.get("forks", 0)) or 0

            line = f"  {self._c(f'{i:>3}.', Colors.YELLOW)} "
            line += f"{self._c(name, Colors.CYAN + Colors.BOLD)} "
            line += f"({lang}) "
            line += f"{self._c(f'★{stars:,}', Colors.YELLOW)} "
            line += f"{self._c(f'⑂{forks:,}', Colors.DIM)} "

            if show_today_stars:
                today = repo.get("today_stars", 0)
                if today:
                    line += f"{self._c(f'(+{today} today)', Colors.GREEN)} "

            print(line)
            if desc:
                print(f"       {self._c(desc, Colors.DIM)}")

        # 记录浏览历史
        if self._storage:
            for repo in repos[:5]:
                try:
                    self._storage.add_history(repo, source="tui")
                except Exception:
                    pass
