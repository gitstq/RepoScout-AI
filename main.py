#!/usr/bin/env python3
"""
main.py - RepoScout-AI CLI 入口

轻量级 AI 驱动 GitHub 仓库智能发现与推荐引擎。

使用方法:
    python main.py search "web framework" --lang python --limit 10
    python main.py trending --lang python --since weekly
    python main.py score owner/repo
    python main.py recommend --limit 10
    python main.py track owner/repo
    python main.py fav list
    python main.py tui
    python main.py export --format json --output report.json
    python main.py config set key value

子命令:
    search      搜索 GitHub 仓库
    trending    查看 GitHub Trending 仓库
    recommend   获取智能推荐
    score       评分指定仓库
    track       趋势追踪
    fav         收藏管理
    tui         启动交互式 TUI 界面
    export      导出报告
    config      配置管理
"""

import argparse
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

# 确保可以导入同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from github_client import GitHubClient, GitHubAPIError
from storage import Storage
from tagger import RepoTagger
from scorer import RepoScorer
from recommender import Recommender, UserProfile
from tracker import TrendTracker
from exporter import ReportExporter
from tui import TUIApp, colored, Colors, supports_color

__version__ = "1.0.0"
__description__ = "轻量级AI驱动GitHub仓库智能发现与推荐引擎"


def setup_logging(verbose: bool = False) -> None:
    """配置日志系统。

    Args:
        verbose: 是否启用详细日志。
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def create_github_client(args: argparse.Namespace) -> GitHubClient:
    """创建 GitHub 客户端实例。

    Args:
        args: 命令行参数。

    Returns:
        GitHubClient 实例。
    """
    token = getattr(args, "token", None) or os.environ.get("GITHUB_TOKEN", "")
    return GitHubClient(token=token if token else None)


def create_storage(args: argparse.Namespace) -> Storage:
    """创建存储实例。

    Args:
        args: 命令行参数。

    Returns:
        Storage 实例。
    """
    db_path = getattr(args, "db", None)
    return Storage(db_path=db_path)


# ==================== 子命令处理函数 ====================

def cmd_search(args: argparse.Namespace) -> int:
    """处理 search 子命令。

    Args:
        args: 命令行参数。

    Returns:
        退出码。
    """
    client = create_github_client(args)
    storage = create_storage(args)

    query = args.query
    language = args.lang or None
    sort = args.sort or "stars"
    order = args.order or "desc"
    limit = args.limit or 30

    print(f"搜索: {query}" + (f" (语言: {language})" if language else ""))
    print(f"排序: {sort} {order}, 数量: {limit}")
    print()

    try:
        result = client.search_repositories(
            query=query,
            sort=sort,
            order=order,
            per_page=limit,
            language=language,
        )

        items = result.get("items", [])
        total = result.get("total_count", 0)
        print(f"找到 {total:,} 个仓库\n")

        for i, repo in enumerate(items, 1):
            name = repo.get("full_name", "")
            desc = (repo.get("description", "") or "")[:80]
            lang = repo.get("language", "") or "-"
            stars = repo.get("stargazers_count", 0) or 0
            forks = repo.get("forks_count", 0) or 0
            updated = (repo.get("updated_at", "") or "")[:10]

            if supports_color():
                print(f"  {colored(f'{i:>3}.', Colors.YELLOW)} "
                      f"{colored(name, Colors.CYAN + Colors.BOLD)}")
                print(f"      {desc}")
                print(f"      {colored(lang, Colors.GREEN)} | "
                      f"{colored(f'★ {stars:,}', Colors.YELLOW)} | "
                      f"⑂ {forks:,} | 更新: {updated}")
            else:
                print(f"  {i:>3}. {name}")
                print(f"      {desc}")
                print(f"      {lang} | Stars: {stars:,} | Forks: {forks:,} | Updated: {updated}")
            print()

            # 记录浏览历史
            storage.add_history(repo, source="search")

        # 导出结果
        if args.output:
            exporter = ReportExporter()
            exporter.export(items, "json", args.output)
            print(f"\n结果已导出到: {args.output}")

    except GitHubAPIError as e:
        print(f"API 错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        logging.exception("搜索失败")
        return 1

    return 0


def cmd_trending(args: argparse.Namespace) -> int:
    """处理 trending 子命令。

    Args:
        args: 命令行参数。

    Returns:
        退出码。
    """
    client = create_github_client(args)
    storage = create_storage(args)

    language = args.lang or None
    since = args.since or "daily"

    print(f"GitHub Trending" + (f" ({language})" if language else "") + f" - {since}\n")

    try:
        repos = client.get_trending(language=language, since=since)

        if not repos:
            print("未获取到 Trending 数据")
            return 0

        print(f"共 {len(repos)} 个仓库\n")

        for i, repo in enumerate(repos, 1):
            name = repo.get("full_name", "")
            desc = repo.get("description", "")[:80]
            lang = repo.get("language", "") or "-"
            stars = repo.get("stars", 0)
            today = repo.get("today_stars", 0)

            if supports_color():
                line = f"  {colored(f'{i:>3}.', Colors.YELLOW)} "
                line += f"{colored(name, Colors.CYAN + Colors.BOLD)} "
                line += f"({lang}) "
                line += f"{colored(f'★{stars:,}', Colors.YELLOW)} "
                if today:
                    line += f"{colored(f'(+{today} today)', Colors.GREEN)} "
                print(line)
            else:
                line = f"  {i:>3}. {name} ({lang}) Stars: {stars:,}"
                if today:
                    line += f" (+{today} today)"
                print(line)

            if desc:
                print(f"       {desc}")
            print()

            # 记录浏览历史
            storage.add_history(repo, source="trending")

        # 导出
        if args.output:
            exporter = ReportExporter()
            exporter.export(repos, "markdown", args.output,
                          title=f"GitHub Trending {language or ''} ({since})")
            print(f"\n结果已导出到: {args.output}")

    except GitHubAPIError as e:
        print(f"API 错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        logging.exception("获取 Trending 失败")
        return 1

    return 0


def cmd_recommend(args: argparse.Namespace) -> int:
    """处理 recommend 子命令。

    Args:
        args: 命令行参数。

    Returns:
        退出码。
    """
    storage = create_storage(args)
    client = create_github_client(args)

    limit = args.limit or 10

    # 构建用户画像
    history = storage.get_history(limit=100)
    favorites = storage.get_favorites(limit=50)

    if not history and not favorites:
        print("暂无浏览历史和收藏数据。")
        print("请先使用 search 或 trending 命令浏览仓库，系统将根据您的兴趣生成推荐。")
        return 0

    print(f"基于浏览历史 ({len(history)}) 和收藏 ({len(favorites)}) 生成推荐...\n")

    recommender = Recommender()
    profile = recommender.build_profile_from_history(history, favorites)

    # 显示用户偏好
    top_langs = profile.get_top_languages(5)
    top_topics = profile.get_top_topics(5)

    if top_langs:
        langs = ", ".join(f"{l} ({s:.0f})" for l, s in top_langs)
        print(f"偏好语言: {langs}")
    if top_topics:
        topics = ", ".join(f"{t} ({s:.0f})" for t, s in top_topics)
        print(f"偏好主题: {topics}")
    print()

    # 获取候选仓库
    candidates = []
    if top_langs and client:
        for lang, _ in top_langs[:3]:
            try:
                result = client.search_repositories(
                    query="stars:>500",
                    language=lang,
                    sort="stars",
                    per_page=20,
                )
                items = result.get("items", [])
                candidates.extend(items)
            except GitHubAPIError:
                continue

    if not candidates:
        print("无法获取候选仓库")
        return 1

    # 生成推荐
    recommendations = recommender.recommend(
        candidates, profile=profile, limit=limit
    )

    print(f"为您推荐 {len(recommendations)} 个仓库:\n")

    for i, rec in enumerate(recommendations, 1):
        name = rec.get("full_name", "")
        desc = rec.get("description", "")[:60]
        score = rec.get("recommend_score", 0)
        lang = rec.get("language", "") or "-"
        stars = rec.get("stars", 0)

        if supports_color():
            print(f"  {colored(f'{i:>3}.', Colors.YELLOW)} "
                  f"{colored(name, Colors.CYAN + Colors.BOLD)} "
                  f"({lang}) "
                  f"{colored(f'★{stars:,}', Colors.YELLOW)} "
                  f"{colored(f'匹配度:{score:.1f}', Colors.GREEN)}")
        else:
            print(f"  {i:>3}. {name} ({lang}) Stars: {stars:,} Score: {score:.1f}")

        if desc:
            print(f"       {desc}")
        print()

    # 导出
    if args.output:
        exporter = ReportExporter()
        exporter.export(recommendations, "json", args.output)
        print(f"\n推荐结果已导出到: {args.output}")

    return 0


def cmd_score(args: argparse.Namespace) -> int:
    """处理 score 子命令。

    Args:
        args: 命令行参数。

    Returns:
        退出码。
    """
    client = create_github_client(args)
    storage = create_storage(args)

    repos_input = args.repos
    if not repos_input:
        print("请指定要评分的仓库（owner/repo 格式）", file=sys.stderr)
        return 1

    repo_names = [r.strip() for r in repos_input.split(",") if r.strip()]
    scorer = RepoScorer()

    results = []
    for repo_name in repo_names:
        if "/" not in repo_name:
            print(f"跳过无效格式: {repo_name}")
            continue

        owner, repo = repo_name.split("/", 1)

        try:
            print(f"评分 {repo_name}...", end=" ", flush=True)
            repo_data = client.get_repository(owner, repo)
            result = scorer.score(repo_data)
            results.append(result)

            grade = result["grade"]
            overall = result["scores"]["overall"]

            if supports_color():
                grade_colors = {
                    "S": Colors.BRIGHT_YELLOW, "A": Colors.GREEN,
                    "B": Colors.CYAN, "C": Colors.YELLOW,
                    "D": Colors.RED, "F": Colors.BRIGHT_RED,
                }
                gc = grade_colors.get(grade, Colors.WHITE)
                print(f"{colored(grade, gc + Colors.BOLD)} ({overall:.1f}/100)")
            else:
                print(f"{grade} ({overall:.1f}/100)")

            # 记录浏览
            storage.add_history(repo_data, source="score")

        except GitHubAPIError as e:
            print(f"失败: {e}")
            continue

    if not results:
        return 1

    # 详细评分信息
    print("\n" + "=" * 60)
    print("评分详情")
    print("=" * 60)

    for result in results:
        name = result["full_name"]
        scores = result["scores"]
        grade = result["grade"]

        print(f"\n  {name} - 等级: {grade}")
        print(f"    活跃度: {scores['activity']:.1f}")
        print(f"    社区:   {scores['community']:.1f}")
        print(f"    健康度: {scores['health']:.1f}")
        print(f"    流行度: {scores['popularity']:.1f}")
        print(f"    综合:   {scores['overall']:.1f}")

    # 导出
    if args.output:
        exporter = ReportExporter()
        fmt = args.format or "json"
        exporter.export(results, fmt, args.output)
        print(f"\n评分报告已导出到: {args.output}")

    return 0


def cmd_track(args: argparse.Namespace) -> int:
    """处理 track 子命令。

    Args:
        args: 命令行参数。

    Returns:
        退出码。
    """
    storage = create_storage(args)
    client = create_github_client(args)

    action = args.action or "view"
    repo_name = args.repo

    tracker = TrendTracker(storage=storage)

    if action == "record":
        if not repo_name or "/" not in repo_name:
            print("请指定仓库（owner/repo 格式）", file=sys.stderr)
            return 1

        owner, repo = repo_name.split("/", 1)
        try:
            repo_data = client.get_repository(owner, repo)
            tracker.track(repo_name, repo_data)
            print(f"已记录快照: {repo_name}")
        except GitHubAPIError as e:
            print(f"获取仓库信息失败: {e}")
            return 1

    elif action == "view":
        if not repo_name:
            print("请指定仓库（owner/repo 格式）", file=sys.stderr)
            return 1

        report = tracker.visualize(repo_name)
        print(report)

    elif action == "compare":
        if not repo_name:
            print("请指定要比较的仓库（逗号分隔）", file=sys.stderr)
            return 1

        names = [n.strip() for n in repo_name.split(",") if n.strip()]
        report = tracker.multi_compare(names)
        print(report)

    elif action == "analyze":
        if not repo_name:
            print("请指定仓库（owner/repo 格式）", file=sys.stderr)
            return 1

        analysis = tracker.analyze(repo_name)
        import json
        print(json.dumps(analysis, indent=2, ensure_ascii=False, default=str))

    else:
        print(f"未知操作: {action}", file=sys.stderr)
        return 1

    return 0


def cmd_fav(args: argparse.Namespace) -> int:
    """处理 fav/favorites 子命令。

    Args:
        args: 命令行参数。

    Returns:
        退出码。
    """
    storage = create_storage(args)
    client = create_github_client(args)

    action = args.action or "list"

    if action == "list":
        favorites = storage.get_favorites(
            sort_by=args.sort or "updated_at",
            order=args.order or "desc",
            limit=args.limit or 50,
        )

        if not favorites:
            print("暂无收藏")
            return 0

        print(f"共 {len(favorites)} 个收藏:\n")

        for i, fav in enumerate(favorites, 1):
            name = fav.get("full_name", "")
            stars = fav.get("stars", 0)
            lang = fav.get("language", "") or "-"
            notes = fav.get("notes", "")
            updated = fav.get("updated_at", "")[:10]

            if supports_color():
                print(f"  {colored(f'{i:>3}.', Colors.YELLOW)} "
                      f"{colored(name, Colors.CYAN + Colors.BOLD)} "
                      f"({lang}) "
                      f"{colored(f'★{stars:,}', Colors.YELLOW)} "
                      f"{colored(updated, Colors.DIM)}")
            else:
                print(f"  {i:>3}. {name} ({lang}) Stars: {stars:,} Updated: {updated}")

            if notes:
                print(f"       备注: {notes}")
            print()

    elif action == "add":
        repo_name = args.repo
        if not repo_name or "/" not in repo_name:
            print("请指定仓库（owner/repo 格式）", file=sys.stderr)
            return 1

        try:
            if client:
                owner, repo = repo_name.split("/", 1)
                repo_data = client.get_repository(owner, repo)
            else:
                repo_data = {
                    "full_name": repo_name,
                    "name": repo_name.split("/")[-1],
                    "owner": repo_name.split("/")[0],
                }

            storage.add_favorite(repo_data, notes=args.notes or "")
            print(f"已收藏: {repo_name}")
        except GitHubAPIError as e:
            print(f"获取仓库信息失败: {e}")
            # 仍然尝试添加基本信息
            storage.add_favorite({
                "full_name": repo_name,
                "name": repo_name.split("/")[-1],
                "owner": repo_name.split("/")[0],
            }, notes=args.notes or "")
            print(f"已收藏（基本信息）: {repo_name}")

    elif action == "remove":
        repo_name = args.repo
        if not repo_name:
            print("请指定要删除的仓库名称", file=sys.stderr)
            return 1

        if storage.remove_favorite(repo_name):
            print(f"已取消收藏: {repo_name}")
        else:
            print(f"未找到: {repo_name}")

    elif action == "check":
        repo_name = args.repo
        if not repo_name:
            print("请指定仓库名称", file=sys.stderr)
            return 1

        if storage.is_favorite(repo_name):
            print(f"{repo_name} 已收藏")
        else:
            print(f"{repo_name} 未收藏")

    elif action == "tags":
        repo_name = args.repo
        if not repo_name:
            print("请指定仓库名称", file=sys.stderr)
            return 1

        if args.tag_action == "list":
            tags = storage.get_tags(repo_name)
            if tags:
                print(f"{repo_name} 的标签: {', '.join(tags)}")
            else:
                print(f"{repo_name} 暂无标签")

        elif args.tag_action == "add" and args.tag:
            storage.add_tag(repo_name, args.tag)
            print(f"已添加标签: {args.tag}")

        elif args.tag_action == "remove" and args.tag:
            storage.remove_tag(repo_name, args.tag)
            print(f"已移除标签: {args.tag}")

    else:
        print(f"未知操作: {action}", file=sys.stderr)
        return 1

    return 0


def cmd_tui(args: argparse.Namespace) -> int:
    """处理 tui 子命令。

    Args:
        args: 命令行参数。

    Returns:
        退出码。
    """
    client = create_github_client(args)
    storage = create_storage(args)

    app = TUIApp(github_client=client, storage=storage)
    app.run()

    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """处理 export 子命令。

    Args:
        args: 命令行参数。

    Returns:
        退出码。
    """
    storage = create_storage(args)
    exporter = ReportExporter()

    source = args.source or "favorites"
    format_type = args.format or "json"
    output = args.output

    if not output:
        print("请指定输出文件路径（--output）", file=sys.stderr)
        return 1

    data = []

    if source == "favorites":
        data = storage.get_favorites(limit=1000)
    elif source == "history":
        data = storage.get_history(limit=1000)
    elif source == "tags":
        all_tags = storage.get_all_tags()
        data = [
            {"full_name": k, "tags": v}
            for k, v in all_tags.items()
        ]
    else:
        print(f"未知数据源: {source}", file=sys.stderr)
        return 1

    if not data:
        print(f"无数据可导出（{source}）")
        return 0

    try:
        filepath = exporter.export(data, format_type, output)
        print(f"已导出 {len(data)} 条记录到: {filepath}")
    except ValueError as e:
        print(f"导出失败: {e}", file=sys.stderr)
        return 1

    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """处理 config 子命令。

    Args:
        args: 命令行参数。

    Returns:
        退出码。
    """
    storage = create_storage(args)

    action = args.action or "list"

    if action == "list":
        prefs = storage.get_all_preferences()
        if prefs:
            print("当前配置:")
            for key, value in prefs.items():
                print(f"  {key} = {value}")
        else:
            print("暂无配置")

    elif action == "set":
        key = args.key
        value = args.value
        if not key or value is None:
            print("请指定配置键和值", file=sys.stderr)
            return 1

        storage.set_preference(key, str(value))
        print(f"已设置: {key} = {value}")

    elif action == "get":
        key = args.key
        if not key:
            print("请指定配置键", file=sys.stderr)
            return 1

        value = storage.get_preference(key)
        print(f"{key} = {value}")

    elif action == "delete":
        key = args.key
        if not key:
            print("请指定配置键", file=sys.stderr)
            return 1

        if storage.delete_preference(key):
            print(f"已删除: {key}")
        else:
            print(f"未找到: {key}")

    elif action == "stats":
        stats = storage.get_stats()
        print("存储统计:")
        for key, value in stats.items():
            if key == "db_size":
                size_kb = value / 1024
                print(f"  {key}: {size_kb:.1f} KB")
            else:
                print(f"  {key}: {value}")

    elif action == "clear-history":
        if storage.clear_history():
            print("浏览历史已清空")
        else:
            print("清空失败")

    else:
        print(f"未知操作: {action}", file=sys.stderr)
        return 1

    return 0


# ==================== CLI 参数解析 ====================

def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。

    Returns:
        配置好的 ArgumentParser 实例。
    """
    parser = argparse.ArgumentParser(
        prog="reposcout",
        description=__description__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s search "machine learning" --lang python --limit 10
  %(prog)s trending --lang javascript --since weekly
  %(prog)s score python/cpython
  %(prog)s recommend --limit 5
  %(prog)s track vuejs/vue --action record
  %(prog)s fav add owner/repo
  %(prog)s tui
  %(prog)s export --source favorites --format html --output report.html
        """,
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="启用详细日志输出",
    )

    # 全局参数
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="GitHub Personal Access Token（也可通过 GITHUB_TOKEN 环境变量设置）",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="SQLite 数据库文件路径",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="子命令",
        description="可用的子命令",
    )

    # ---- search 子命令 ----
    search_parser = subparsers.add_parser(
        "search", help="搜索 GitHub 仓库",
        description="搜索 GitHub 仓库",
    )
    search_parser.add_argument("query", type=str, help="搜索关键词")
    search_parser.add_argument("--lang", type=str, default=None, help="编程语言过滤")
    search_parser.add_argument("--sort", type=str, default="stars",
                               choices=["stars", "forks", "updated"],
                               help="排序字段")
    search_parser.add_argument("--order", type=str, default="desc",
                               choices=["asc", "desc"],
                               help="排序方向")
    search_parser.add_argument("--limit", type=int, default=30, help="返回数量")
    search_parser.add_argument("--output", type=str, default=None, help="导出文件路径")

    # ---- trending 子命令 ----
    trending_parser = subparsers.add_parser(
        "trending", help="查看 GitHub Trending 仓库",
        description="查看 GitHub Trending 仓库",
    )
    trending_parser.add_argument("--lang", type=str, default=None, help="编程语言过滤")
    trending_parser.add_argument("--since", type=str, default="daily",
                                 choices=["daily", "weekly", "monthly"],
                                 help="时间范围")
    trending_parser.add_argument("--output", type=str, default=None, help="导出文件路径")

    # ---- recommend 子命令 ----
    recommend_parser = subparsers.add_parser(
        "recommend", help="获取智能推荐",
        description="基于浏览历史和收藏获取智能推荐",
    )
    recommend_parser.add_argument("--limit", type=int, default=10, help="推荐数量")
    recommend_parser.add_argument("--output", type=str, default=None, help="导出文件路径")

    # ---- score 子命令 ----
    score_parser = subparsers.add_parser(
        "score", help="评分仓库",
        description="对仓库进行多维度综合评分",
    )
    score_parser.add_argument("repos", type=str, help="仓库名称（owner/repo，多个用逗号分隔）")
    score_parser.add_argument("--format", type=str, default="json",
                              choices=["json", "csv", "md", "html"],
                              help="导出格式")
    score_parser.add_argument("--output", type=str, default=None, help="导出文件路径")

    # ---- track 子命令 ----
    track_parser = subparsers.add_parser(
        "track", help="趋势追踪",
        description="追踪仓库增长趋势",
    )
    track_parser.add_argument("repo", type=str, nargs="?", default=None,
                              help="仓库名称（owner/repo，比较时用逗号分隔）")
    track_parser.add_argument("--action", type=str, default="view",
                              choices=["record", "view", "compare", "analyze"],
                              help="操作类型")

    # ---- fav/favorites 子命令 ----
    fav_parser = subparsers.add_parser(
        "fav", help="收藏管理", aliases=["favorites"],
        description="管理收藏的仓库",
    )
    fav_parser.add_argument("action", type=str, nargs="?", default="list",
                            choices=["list", "add", "remove", "check", "tags"],
                            help="操作类型")
    fav_parser.add_argument("repo", type=str, nargs="?", default=None,
                            help="仓库名称")
    fav_parser.add_argument("--notes", type=str, default="", help="收藏备注")
    fav_parser.add_argument("--sort", type=str, default="updated_at",
                            choices=["stars", "forks", "updated_at", "name"],
                            help="排序字段")
    fav_parser.add_argument("--order", type=str, default="desc",
                            choices=["asc", "desc"],
                            help="排序方向")
    fav_parser.add_argument("--limit", type=int, default=50, help="返回数量")
    fav_parser.add_argument("--tag-action", type=str, default="list",
                            choices=["list", "add", "remove"],
                            help="标签操作")
    fav_parser.add_argument("--tag", type=str, default=None, help="标签内容")

    # ---- tui 子命令 ----
    tui_parser = subparsers.add_parser(
        "tui", help="启动交互式 TUI 界面",
        description="启动交互式文本用户界面",
    )

    # ---- export 子命令 ----
    export_parser = subparsers.add_parser(
        "export", help="导出报告",
        description="导出数据为多种格式",
    )
    export_parser.add_argument("--source", type=str, default="favorites",
                               choices=["favorites", "history", "tags"],
                               help="数据源")
    export_parser.add_argument("--format", type=str, default="json",
                               choices=["json", "csv", "md", "markdown", "html"],
                               help="导出格式")
    export_parser.add_argument("--output", type=str, required=True,
                               help="输出文件路径")

    # ---- config 子命令 ----
    config_parser = subparsers.add_parser(
        "config", help="配置管理",
        description="管理用户配置和存储",
    )
    config_parser.add_argument("action", type=str, nargs="?", default="list",
                               choices=["list", "set", "get", "delete", "stats", "clear-history"],
                               help="操作类型")
    config_parser.add_argument("key", type=str, nargs="?", default=None,
                               help="配置键名")
    config_parser.add_argument("value", type=str, nargs="?", default=None,
                               help="配置值")

    return parser


def main() -> int:
    """主入口函数。

    Returns:
        退出码。
    """
    parser = build_parser()
    args = parser.parse_args()

    # 配置日志
    setup_logging(getattr(args, "verbose", False))

    # 如果没有指定子命令，显示帮助
    if not args.command:
        parser.print_help()
        return 0

    # 分发到子命令处理
    command_handlers = {
        "search": cmd_search,
        "trending": cmd_trending,
        "recommend": cmd_recommend,
        "score": cmd_score,
        "track": cmd_track,
        "fav": cmd_fav,
        "favorites": cmd_fav,
        "tui": cmd_tui,
        "export": cmd_export,
        "config": cmd_config,
    }

    handler = command_handlers.get(args.command)
    if handler:
        try:
            return handler(args)
        except KeyboardInterrupt:
            print("\n操作已取消")
            return 130
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            logging.exception("未处理的异常")
            return 1
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
