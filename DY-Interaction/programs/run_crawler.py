#!/usr/bin/env python3
"""
统一爬虫服务 - DY-Interaction Crawler Service

功能：
    - 历史爬虫：爬取所有视频的历史评论
    - 监控爬虫：定期监控新增评论
    - 支持多种运行模式和调度策略
    - 智能去重：历史爬虫自动跳过已爬取账号
    - 交互选择：支持单选、多选、全选账号

用法：
    # 历史爬虫 - 交互式选择（推荐）
    python programs/run_crawler.py history --interactive

    # 历史爬虫 - 自动爬取新账号（默认）
    python programs/run_crawler.py history

    # 历史爬虫 - 强制爬取所有账号
    python programs/run_crawler.py history --all

    # 历史爬虫 - 指定账号
    python programs/run_crawler.py history --accounts 1,3

    # 监控爬虫 - 交互式选择
    python programs/run_crawler.py monitor --interactive

    # 监控爬虫 - 所有账号
    python programs/run_crawler.py monitor --all

    # 混合模式 - 先历史后监控
    python programs/run_crawler.py hybrid --interactive

智能特性：
    - 历史爬虫默认只爬取新账号（未爬取过的）
    - 交互模式显示每个账号的爬取状态（✓已爬取 / ⭐新账号）
    - 重新爬取已爬账号时会二次确认
    - 支持选择 "n" 快速选择所有新账号

设计理念：
    - 单一入口：所有爬虫功能统一管理
    - 智能去重：避免重复爬取浪费资源
    - 用户友好：交互式选择，清晰的状态提示
    - 可配置：支持命令行参数和配置文件
    - 易扩展：便于添加新的爬虫策略
"""

import sys
import logging
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 确保日志目录存在
log_dir = PROJECT_ROOT / 'logs'
log_dir.mkdir(exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'crawler_service.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

from src.database.manager import DatabaseManager
from src.crawler.history_crawler import HistoryCrawler
from src.crawler.monitor_crawler import MonitorCrawler
from src.generator.task_generator import TaskGenerator
from src.crawler.api_client import DouyinAPIClient
from src.crawler.server_pool import ServerPool
from src.crawler.parallel_crawler import ParallelCrawler


class CrawlerService:
    """统一的爬虫服务类"""

    def __init__(self, enable_parallel: bool = False):
        """初始化爬虫服务

        Args:
            enable_parallel: 是否启用并行爬取（需要配置多服务器）
        """
        self.db = None
        self.api_client = None
        self.task_generator = None
        self.config = {}
        self.enable_parallel = enable_parallel
        self.server_pool = None
        self.parallel_crawler = None

    def initialize(self) -> bool:
        """初始化所有组件

        Returns:
            bool: 初始化是否成功
        """
        try:
            # 加载配置
            logger.info("加载配置...")
            self.config = self._load_config()

            # 初始化数据库
            logger.info("初始化数据库...")
            self.db = DatabaseManager()
            self.db.init_db()
            logger.info("✓ 数据库初始化完成")

            # 初始化API客户端
            logger.info("初始化API客户端...")
            self.api_client = DouyinAPIClient()
            logger.info("✓ API客户端初始化完成")

            # 初始化任务生成器
            self.task_generator = TaskGenerator(self.db)
            logger.info("✓ 任务生成器初始化完成")

            # 初始化服务器池和并行爬虫（如果启用）
            if self.enable_parallel:
                logger.info("初始化服务器池...")
                self.server_pool = ServerPool()
                self.parallel_crawler = ParallelCrawler(self.server_pool)
                max_workers = self.server_pool.get_max_workers()
                logger.info(f"✓ 并行爬取已启用 (最大并发: {max_workers})")

            return True

        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}")
            logger.error("""
可能的原因:
  1. 配置文件不存在: config/config.json
  2. API服务器无法连接
  3. 数据库初始化失败

解决方案:
  1. 检查 config/config.json 配置文件
  2. 验证API服务器地址和密钥
  3. 确保数据库文件可访问
            """)
            return False

    def _load_config(self) -> dict:
        """加载配置文件

        Returns:
            dict: 配置字典
        """
        try:
            config_file = PROJECT_ROOT / 'config' / 'config.json'
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning("⚠ 配置文件不存在，使用默认配置")
                return {}
        except Exception as e:
            logger.warning(f"⚠ 读取配置文件失败: {e}，使用默认配置")
            return {}

    def get_target_accounts(self, account_filter: Optional[str] = None, interactive: bool = False, mode: str = 'history') -> List:
        """获取目标账号列表

        Args:
            account_filter: 账号过滤器（如 "1,3" 或 "all"）
            interactive: 是否使用交互式选择
            mode: 爬虫模式 (history/monitor)，用于智能过滤

        Returns:
            List: 目标账号列表
        """
        all_accounts = self.db.get_target_accounts()

        if not all_accounts:
            logger.error("❌ 未配置任何目标账号")
            logger.info("请在 config/target_accounts.json 中配置目标账号")
            return []

        logger.info(f"✓ 找到 {len(all_accounts)} 个目标账号")

        # 对于历史爬虫，检查哪些账号已经爬取过
        crawled_accounts = set()
        if mode == 'history':
            crawled_accounts = self._get_crawled_accounts()

        # 交互式选择
        if interactive:
            return self._interactive_select_accounts(all_accounts, crawled_accounts, mode)

        # 如果没有过滤器
        if not account_filter:
            # 历史爬虫默认只爬取新账号
            if mode == 'history' and crawled_accounts:
                new_accounts = [acc for acc in all_accounts if acc.id not in crawled_accounts]
                if new_accounts:
                    logger.info(f"✓ 发现 {len(new_accounts)} 个新账号（未爬取过）")
                    logger.info(f"   已跳过 {len(crawled_accounts)} 个已爬取账号")
                    logger.info("   提示：使用 --interactive 可以选择重新爬取")
                    return new_accounts
                else:
                    logger.warning("⚠ 所有账号都已爬取过")
                    logger.info("   使用 --interactive 可以选择重新爬取")
                    return []
            # 监控爬虫默认全部
            return all_accounts

        # 解析 'all' 过滤器
        if account_filter == 'all':
            return all_accounts

        # 解析账号编号过滤
        try:
            indices = [int(x.strip()) for x in account_filter.split(',')]
            if any(i < 1 or i > len(all_accounts) for i in indices):
                logger.error(f"❌ 编号超出范围！请输入 1-{len(all_accounts)} 之间的数字")
                return []

            selected = [all_accounts[i-1] for i in sorted(set(indices))]
            logger.info(f"✓ 已选择 {len(selected)} 个账号")
            return selected

        except ValueError:
            logger.error("❌ 账号编号格式错误！示例：1,3")
            return []

    def _get_crawled_accounts(self) -> set:
        """获取已经爬取过的账号ID集合

        Returns:
            set: 已爬取账号的ID集合
        """
        from src.database.models import Comment
        with self.db.session_scope() as session:
            # 查询有评论数据的账号
            result = session.query(Comment.target_account_id).distinct().all()
            return {row[0] for row in result if row[0]}

    def _interactive_select_accounts(self, all_accounts: List, crawled_accounts: set, mode: str) -> List:
        """交互式选择账号

        Args:
            all_accounts: 所有账号列表
            crawled_accounts: 已爬取账号ID集合
            mode: 爬虫模式

        Returns:
            List: 选择的账号列表
        """
        print("\n" + "=" * 70)
        print(f"📋 账号列表（共 {len(all_accounts)} 个）")
        print("=" * 70)

        # 显示账号列表
        print(f"\n{'编号':<6} {'账号名':<25} {'抖音ID':<20} {'状态':<10}")
        print("-" * 70)

        for idx, acc in enumerate(all_accounts, 1):
            status = ""
            if mode == 'history':
                if acc.id in crawled_accounts:
                    status = "✓ 已爬取"
                else:
                    status = "⭐ 新账号"

            print(f"{idx:<6} {acc.account_name:<25} {acc.account_id:<20} {status:<10}")

        print("\n" + "=" * 70)
        print("选择方式:")
        print("  0 - 全部账号")
        if mode == 'history' and crawled_accounts:
            new_count = len([a for a in all_accounts if a.id not in crawled_accounts])
            print(f"  n - 仅新账号（{new_count}个未爬取）")
        print("  1-{} - 单个账号".format(len(all_accounts)))
        print("  1,3,5 - 多个账号（逗号分隔）")
        print("=" * 70)

        choice = input("\n请输入选择: ").strip()

        # 处理选择
        if choice == '0':
            logger.info(f"✓ 已选择全部 {len(all_accounts)} 个账号")
            return all_accounts

        if mode == 'history' and choice.lower() == 'n':
            new_accounts = [acc for acc in all_accounts if acc.id not in crawled_accounts]
            if new_accounts:
                logger.info(f"✓ 已选择 {len(new_accounts)} 个新账号")
                return new_accounts
            else:
                logger.warning("⚠ 没有新账号")
                return []

        # 解析编号
        try:
            indices = [int(x.strip()) for x in choice.split(',')]
            if any(i < 1 or i > len(all_accounts) for i in indices):
                logger.error(f"❌ 编号超出范围！")
                return []

            selected = [all_accounts[i-1] for i in sorted(set(indices))]
            logger.info(f"✓ 已选择 {len(selected)} 个账号:")
            for acc in selected:
                status_mark = "✓" if acc.id in crawled_accounts else "⭐"
                logger.info(f"   {status_mark} {acc.account_name}")

            # 如果选择了已爬取的账号，提示确认
            if mode == 'history':
                selected_crawled = [acc for acc in selected if acc.id in crawled_accounts]
                if selected_crawled:
                    print(f"\n⚠️  注意：选择中包含 {len(selected_crawled)} 个已爬取账号，将重新爬取")
                    confirm = input("确认继续？(y/n): ").strip().lower()
                    if confirm != 'y':
                        logger.info("已取消")
                        return []

            return selected

        except ValueError:
            logger.error("❌ 输入格式错误")
            return []

    def run_history_crawler(self, accounts: List, days: int = 90) -> dict:
        """运行历史爬虫

        Args:
            accounts: 目标账号列表
            days: 爬取最近N天的数据

        Returns:
            dict: 爬虫结果统计
        """
        logger.info("=" * 70)
        logger.info("📝 历史爬虫模式 - 启动")
        logger.info(f"   账号数量: {len(accounts)}")
        logger.info(f"   时间范围: 最近 {days} 天")
        if self.enable_parallel:
            logger.info(f"   并行模式: ✓ 已启用 (最大并发: {self.server_pool.get_max_workers()})")
        logger.info("=" * 70)

        # 使用并行模式
        if self.enable_parallel and self.parallel_crawler:
            return self._run_history_parallel(accounts, days)

        # 使用串行模式（原有逻辑）
        return self._run_history_serial(accounts, days)

    def _run_history_serial(self, accounts: List, days: int = 90) -> dict:
        """串行模式：逐个账号爬取（原有逻辑）"""
        crawler = HistoryCrawler(self.db, self.api_client)

        total_comments = 0
        total_videos = 0
        total_tasks = 0
        success_count = 0
        failed_count = 0

        for idx, account in enumerate(accounts, 1):
            logger.info(f"\n[账号 {idx}/{len(accounts)}] {account.account_name}")
            logger.info("-" * 70)

            try:
                # 爬取历史评论
                result = crawler.crawl_history(account, days=days)

                if result['status'] == 'success':
                    videos = result.get('total_videos', 0)
                    comments = result.get('total_comments', 0)

                    logger.info(f"  ✓ 爬虫完成")
                    logger.info(f"    - 视频数: {videos}")
                    logger.info(f"    - 评论数: {comments}")

                    total_videos += videos
                    total_comments += comments
                    success_count += 1

                    # 生成任务
                    task_count = self.task_generator.generate_from_history(account.id)
                    total_tasks += task_count
                    logger.info(f"  ✓ 任务生成: {task_count} 个")

                else:
                    logger.error(f"  ✗ 爬虫失败: {result.get('error', '未知错误')}")
                    failed_count += 1

            except Exception as e:
                logger.error(f"  ✗ 处理失败: {e}")
                failed_count += 1

        # 返回统计结果
        stats = {
            'mode': 'history',
            'accounts_total': len(accounts),
            'accounts_success': success_count,
            'accounts_failed': failed_count,
            'total_videos': total_videos,
            'total_comments': total_comments,
            'total_tasks': total_tasks
        }

        self._print_summary(stats)
        return stats

    def _run_history_parallel(self, accounts: List, days: int = 90) -> dict:
        """并行模式：多服务器并发爬取"""
        def crawl_one_account(account, server, db):
            """并行爬取单个账号的包装函数"""
            try:
                # 创建爬虫实例（使用服务器的cookie）
                from src.crawler.api_client import DouyinAPIClient
                api_client = DouyinAPIClient(cookie=server.cookie, api_url=server.url)
                crawler = HistoryCrawler(db, api_client)

                # 爬取历史
                result = crawler.crawl_history(account, days=days)

                if result['status'] == 'success':
                    # 生成任务
                    task_gen = TaskGenerator(db)
                    task_count = task_gen.generate_from_history(account.id)
                    logger.info(f"  [{server.name}] ✓ 任务生成: {task_count} 个")
                    return True
                else:
                    logger.error(f"  [{server.name}] ✗ 爬取失败: {result.get('error', '未知错误')}")
                    return False

            except Exception as e:
                logger.error(f"  [{server.name}] ✗ 异常: {e}")
                return False

        # 使用并行爬虫执行
        result_stats = self.parallel_crawler.crawl_accounts(
            accounts=accounts,
            crawl_func=crawl_one_account,
            show_progress=True
        )

        # 转换统计格式（兼容原有格式）
        stats = {
            'mode': 'history_parallel',
            'accounts_total': result_stats['total'],
            'accounts_success': result_stats['successful'],
            'accounts_failed': result_stats['failed'],
            'total_videos': 0,  # 并行模式暂不统计
            'total_comments': 0,  # 并行模式暂不统计
            'total_tasks': 0,  # 并行模式暂不统计
            'duration': result_stats['duration'],
            'avg_time': result_stats['avg_time_per_task']
        }

        return stats

    def run_monitor_crawler(self, accounts: List, top_n: int = 5) -> dict:
        """运行监控爬虫

        Args:
            accounts: 目标账号列表
            top_n: 监控前N个视频

        Returns:
            dict: 监控结果统计
        """
        logger.info("=" * 70)
        logger.info("👁️  监控爬虫模式 - 启动")
        logger.info(f"   账号数量: {len(accounts)}")
        logger.info(f"   监控策略: 每账号前 {top_n} 个视频")
        logger.info(f"   运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if self.enable_parallel:
            logger.info(f"   并行模式: ✓ 已启用 (最大并发: {self.server_pool.get_max_workers()})")
        logger.info("=" * 70)

        # 使用并行模式
        if self.enable_parallel and self.parallel_crawler:
            return self._run_monitor_parallel(accounts, top_n)

        # 使用串行模式（原有逻辑）
        return self._run_monitor_serial(accounts, top_n)

    def _run_monitor_serial(self, accounts: List, top_n: int = 5) -> dict:
        """串行模式：逐个账号监控（原有逻辑）"""
        crawler = MonitorCrawler(self.db, self.api_client)

        total_new_comments = 0
        total_tasks = 0
        success_count = 0
        failed_count = 0

        for idx, account in enumerate(accounts, 1):
            logger.info(f"\n[账号 {idx}/{len(accounts)}] {account.account_name}")
            logger.info("-" * 70)

            try:
                # 监控新增评论
                result = crawler.monitor_daily(account, top_n=top_n)

                if result['status'] == 'success':
                    new_count = result.get('new_comments_count', 0)
                    logger.info(f"  ✓ 监控完成")
                    logger.info(f"    - 新增评论: {new_count} 条")

                    total_new_comments += new_count
                    success_count += 1

                    # 生成高优先级任务
                    if new_count > 0:
                        task_count = self.task_generator.generate_from_realtime(account.id)
                        total_tasks += task_count
                        logger.info(f"  ✓ 生成任务: {task_count} 个（高优先级）")
                    else:
                        logger.info(f"  ℹ️  暂无新增")

                else:
                    logger.error(f"  ✗ 监控失败: {result.get('error', '未知错误')}")
                    failed_count += 1

            except Exception as e:
                logger.error(f"  ✗ 处理失败: {e}")
                failed_count += 1

        # 返回统计结果
        stats = {
            'mode': 'monitor',
            'accounts_total': len(accounts),
            'accounts_success': success_count,
            'accounts_failed': failed_count,
            'new_comments': total_new_comments,
            'total_tasks': total_tasks
        }

        self._print_summary(stats)
        return stats

    def _run_monitor_parallel(self, accounts: List, top_n: int = 5) -> dict:
        """并行模式：多服务器并发监控"""
        def monitor_one_account(account, server, db):
            """并行监控单个账号的包装函数"""
            try:
                # 创建监控爬虫实例（使用服务器的cookie）
                from src.crawler.api_client import DouyinAPIClient
                api_client = DouyinAPIClient(cookie=server.cookie, api_url=server.url)
                crawler = MonitorCrawler(db, api_client)

                # 监控
                result = crawler.monitor_daily(account, top_n=top_n)

                if result['status'] == 'success':
                    new_count = result.get('new_comments_count', 0)

                    # 生成高优先级任务
                    if new_count > 0:
                        task_gen = TaskGenerator(db)
                        task_count = task_gen.generate_from_realtime(account.id)
                        logger.info(f"  [{server.name}] ✓ 新增 {new_count} 条评论，生成 {task_count} 个任务")
                    else:
                        logger.info(f"  [{server.name}] ✓ 暂无新增评论")

                    return True
                else:
                    logger.error(f"  [{server.name}] ✗ 监控失败: {result.get('error', '未知错误')}")
                    return False

            except Exception as e:
                logger.error(f"  [{server.name}] ✗ 异常: {e}")
                return False

        # 使用并行爬虫执行
        result_stats = self.parallel_crawler.crawl_accounts(
            accounts=accounts,
            crawl_func=monitor_one_account,
            show_progress=True
        )

        # 转换统计格式（兼容原有格式）
        stats = {
            'mode': 'monitor_parallel',
            'accounts_total': result_stats['total'],
            'accounts_success': result_stats['successful'],
            'accounts_failed': result_stats['failed'],
            'new_comments': 0,  # 并行模式暂不统计
            'total_tasks': 0,  # 并行模式暂不统计
            'duration': result_stats['duration'],
            'avg_time': result_stats['avg_time_per_task']
        }

        return stats

    def run_hybrid_crawler(self, accounts: List, days: int = 90, top_n: int = 5) -> dict:
        """运行混合模式（先历史后监控）

        Args:
            accounts: 目标账号列表
            days: 历史爬虫天数
            top_n: 监控前N个视频

        Returns:
            dict: 混合结果统计
        """
        logger.info("=" * 70)
        logger.info("🔄 混合爬虫模式 - 启动")
        logger.info("   执行顺序: 历史爬虫 → 监控爬虫")
        logger.info("=" * 70)

        # 先运行历史爬虫
        logger.info("\n【第1阶段】历史爬虫")
        history_stats = self.run_history_crawler(accounts, days)

        # 再运行监控爬虫
        logger.info("\n【第2阶段】监控爬虫")
        monitor_stats = self.run_monitor_crawler(accounts, top_n)

        # 合并统计
        stats = {
            'mode': 'hybrid',
            'history': history_stats,
            'monitor': monitor_stats
        }

        logger.info("\n" + "=" * 70)
        logger.info("📊 混合模式 - 总体统计")
        logger.info("=" * 70)
        logger.info(f"  历史评论数: {history_stats['total_comments']}")
        logger.info(f"  新增评论数: {monitor_stats['new_comments']}")
        logger.info(f"  总任务数: {history_stats['total_tasks'] + monitor_stats['total_tasks']}")
        logger.info("=" * 70)

        return stats

    def _print_summary(self, stats: dict):
        """打印统计摘要

        Args:
            stats: 统计数据字典
        """
        logger.info("\n" + "=" * 70)
        logger.info(f"📊 {stats['mode'].upper()} 模式 - 统计结果")
        logger.info("=" * 70)
        logger.info(f"  账号总数: {stats['accounts_total']}")
        logger.info(f"    - 成功: {stats['accounts_success']}")
        logger.info(f"    - 失败: {stats['accounts_failed']}")

        if stats['mode'] == 'history':
            logger.info(f"  总视频数: {stats['total_videos']}")
            logger.info(f"  总评论数: {stats['total_comments']}")
            logger.info(f"  生成任务: {stats['total_tasks']}")
        elif stats['mode'] == 'monitor':
            logger.info(f"  新增评论: {stats['new_comments']}")
            logger.info(f"  生成任务: {stats['total_tasks']}")

        logger.info("=" * 70)


def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='DY-Interaction 统一爬虫服务',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 历史爬虫 - 交互式选择账号（推荐）
  python programs/run_crawler.py history --interactive

  # 历史爬虫 - 自动爬取新账号（默认）
  python programs/run_crawler.py history

  # 历史爬虫 - 爬取所有账号（包括已爬取）
  python programs/run_crawler.py history --all

  # 历史爬虫 - 爬取指定账号
  python programs/run_crawler.py history --accounts 1,3

  # 历史爬虫 - 并行模式（多服务器并发）🚀
  python programs/run_crawler.py history --all --parallel

  # 历史爬虫 - 交互选择 + 并行模式
  python programs/run_crawler.py history --interactive --parallel

  # 监控爬虫 - 交互式选择账号
  python programs/run_crawler.py monitor --interactive

  # 监控爬虫 - 监控所有账号
  python programs/run_crawler.py monitor --all

  # 监控爬虫 - 并行模式
  python programs/run_crawler.py monitor --all --parallel

  # 混合模式 - 先历史后监控
  python programs/run_crawler.py hybrid --interactive

  # 混合模式 - 并行爬取
  python programs/run_crawler.py hybrid --all --parallel
        """
    )

    # 子命令
    subparsers = parser.add_subparsers(dest='mode', help='爬虫模式', required=True)

    # 历史爬虫模式
    history_parser = subparsers.add_parser('history', help='历史爬虫模式')
    history_parser.add_argument('--all', action='store_true', help='爬取所有账号')
    history_parser.add_argument('--accounts', type=str, help='指定账号编号（如：1,3）')
    history_parser.add_argument('--interactive', '-i', action='store_true', help='交互式选择账号')
    history_parser.add_argument('--days', type=int, default=90, help='爬取最近N天（默认90）')
    history_parser.add_argument('--parallel', '-p', action='store_true', help='启用并行爬取（需配置多服务器）')

    # 监控爬虫模式
    monitor_parser = subparsers.add_parser('monitor', help='监控爬虫模式')
    monitor_parser.add_argument('--all', action='store_true', help='监控所有账号（默认）')
    monitor_parser.add_argument('--accounts', type=str, help='指定账号编号（如：1,3）')
    monitor_parser.add_argument('--interactive', '-i', action='store_true', help='交互式选择账号')
    monitor_parser.add_argument('--top-n', type=int, default=5, help='监控前N个视频（默认5）')
    monitor_parser.add_argument('--parallel', '-p', action='store_true', help='启用并行爬取（需配置多服务器）')

    # 混合模式
    hybrid_parser = subparsers.add_parser('hybrid', help='混合模式（历史+监控）')
    hybrid_parser.add_argument('--all', action='store_true', help='处理所有账号')
    hybrid_parser.add_argument('--accounts', type=str, help='指定账号编号（如：1,3）')
    hybrid_parser.add_argument('--interactive', '-i', action='store_true', help='交互式选择账号')
    hybrid_parser.add_argument('--days', type=int, default=90, help='历史爬虫天数（默认90）')
    hybrid_parser.add_argument('--top-n', type=int, default=5, help='监控视频数（默认5）')
    hybrid_parser.add_argument('--parallel', '-p', action='store_true', help='启用并行爬取（需配置多服务器）')

    return parser


def main():
    """主函数"""
    # 解析命令行参数
    parser = create_parser()
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("🚀 DY-Interaction 统一爬虫服务")
    logger.info(f"   模式: {args.mode.upper()}")
    logger.info(f"   启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    try:
        # 初始化服务
        enable_parallel = hasattr(args, 'parallel') and args.parallel
        service = CrawlerService(enable_parallel=enable_parallel)
        if not service.initialize():
            return 1

        # 获取目标账号
        account_filter = 'all' if args.all else args.accounts
        interactive = getattr(args, 'interactive', False)
        accounts = service.get_target_accounts(account_filter, interactive, args.mode)

        if not accounts:
            logger.error("❌ 没有可处理的账号")
            return 1

        # 根据模式执行爬虫
        if args.mode == 'history':
            service.run_history_crawler(accounts, args.days)

        elif args.mode == 'monitor':
            service.run_monitor_crawler(accounts, args.top_n)

        elif args.mode == 'hybrid':
            service.run_hybrid_crawler(accounts, args.days, args.top_n)

        logger.info("\n✅ 爬虫服务执行完成")
        return 0

    except KeyboardInterrupt:
        logger.info("\n\n⏸️  收到停止信号，正在退出...")
        return 0

    except Exception as e:
        logger.error(f"\n❌ 执行出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
