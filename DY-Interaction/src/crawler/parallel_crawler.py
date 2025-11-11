"""
并行爬虫 - 支持多服务器并发爬取

使用线程池 + 服务器池实现高效并发爬取
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable, Dict, Any, Optional
from datetime import datetime
import time

from src.database.manager import DatabaseManager
from src.database.models import TargetAccount
from src.crawler.server_pool import ServerPool, APIServer
import logging

logger = logging.getLogger(__name__)


class ParallelCrawler:
    """并行爬虫 - 多服务器并发执行"""

    def __init__(self, server_pool: Optional[ServerPool] = None):
        """
        初始化并行爬虫

        Args:
            server_pool: 服务器池，如果为None则自动创建
        """
        self.db = DatabaseManager()
        self.server_pool = server_pool or ServerPool()

        # 统计信息
        self.total_tasks = 0
        self.successful_tasks = 0
        self.failed_tasks = 0
        self.start_time = None
        self.end_time = None

    def crawl_accounts(
        self,
        accounts: List[TargetAccount],
        crawl_func: Callable[[TargetAccount, APIServer, DatabaseManager], bool],
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        并行爬取多个账号

        Args:
            accounts: 要爬取的账号列表
            crawl_func: 爬取函数，签名: func(account, server, db) -> bool
            show_progress: 是否显示进度

        Returns:
            爬取结果统计
        """
        if not accounts:
            logger.warning("没有要爬取的账号")
            return self._get_stats()

        self.total_tasks = len(accounts)
        self.successful_tasks = 0
        self.failed_tasks = 0
        self.start_time = datetime.now()

        logger.info(f"\n{'=' * 80}")
        logger.info(f"🚀 开始并行爬取 - 共 {len(accounts)} 个账号")
        logger.info(f"📊 服务器池并发容量: {self.server_pool.get_max_workers()}")
        logger.info(f"{'=' * 80}\n")

        # 显示服务器池状态
        if show_progress:
            self.server_pool.print_status()

        # 使用线程池执行
        max_workers = self.server_pool.get_max_workers()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_account = {}
            for account in accounts:
                future = executor.submit(
                    self._crawl_one_account,
                    account,
                    crawl_func
                )
                future_to_account[future] = account

            # 等待完成并收集结果
            completed = 0
            for future in as_completed(future_to_account):
                account = future_to_account[future]
                completed += 1

                try:
                    success = future.result()
                    if success:
                        self.successful_tasks += 1
                    else:
                        self.failed_tasks += 1

                    if show_progress:
                        self._print_progress(completed, account.account_name, success)

                except Exception as e:
                    self.failed_tasks += 1
                    logger.error(f"✗ 账号 {account.account_name} 爬取异常: {e}")

                    if show_progress:
                        self._print_progress(completed, account.account_name, False)

        self.end_time = datetime.now()

        # 打印最终统计
        if show_progress:
            self._print_final_stats()

        return self._get_stats()

    def _crawl_one_account(
        self,
        account: TargetAccount,
        crawl_func: Callable[[TargetAccount, APIServer, DatabaseManager], bool]
    ) -> bool:
        """
        爬取单个账号（内部方法）

        Args:
            account: 目标账号
            crawl_func: 爬取函数

        Returns:
            是否成功
        """
        task_name = f"{account.account_name}({account.id})"
        server = None

        try:
            # 获取可用服务器
            server = self.server_pool.acquire_server(task_name, wait=True)
            if not server:
                logger.error(f"✗ 无法获取服务器用于爬取账号: {account.account_name}")
                return False

            logger.info(f"🔄 [{server.name}] 开始爬取: {account.account_name}")

            # 执行爬取
            success = crawl_func(account, server, self.db)

            # 释放服务器
            self.server_pool.release_server(server, task_name, success=success)

            if success:
                logger.info(f"✓ [{server.name}] 完成爬取: {account.account_name}")
            else:
                logger.warning(f"⚠️  [{server.name}] 爬取失败: {account.account_name}")

            return success

        except Exception as e:
            logger.error(f"✗ 爬取账号 {account.account_name} 时出错: {e}", exc_info=True)
            if server:
                self.server_pool.release_server(server, task_name, success=False)
            return False

    def _print_progress(self, completed: int, account_name: str, success: bool):
        """打印进度"""
        progress_pct = (completed / self.total_tasks) * 100
        status_icon = "✓" if success else "✗"
        print(f"  [{completed}/{self.total_tasks}] ({progress_pct:.0f}%) {status_icon} {account_name}")

    def _print_final_stats(self):
        """打印最终统计"""
        stats = self._get_stats()

        print(f"\n{'=' * 80}")
        print(f"📊 爬取完成统计")
        print(f"{'=' * 80}")
        print(f"  总任务数: {stats['total']}")
        print(f"  ✓ 成功: {stats['successful']} ({stats['success_rate']})")
        print(f"  ✗ 失败: {stats['failed']}")
        print(f"  ⏱️  总耗时: {stats['duration']}")
        print(f"  ⚡ 平均速度: {stats['avg_time_per_task']}")
        print(f"{'=' * 80}\n")

        # 显示服务器池最终状态
        self.server_pool.print_status()

    def _get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        duration = None
        avg_time = None

        if self.start_time and self.end_time:
            duration_seconds = (self.end_time - self.start_time).total_seconds()
            duration = f"{duration_seconds:.1f}秒"
            if self.total_tasks > 0:
                avg_seconds = duration_seconds / self.total_tasks
                avg_time = f"{avg_seconds:.1f}秒/账号"
        else:
            duration = "未完成"
            avg_time = "-"

        success_rate = "0%"
        if self.total_tasks > 0:
            success_rate = f"{(self.successful_tasks / self.total_tasks) * 100:.1f}%"

        return {
            'total': self.total_tasks,
            'successful': self.successful_tasks,
            'failed': self.failed_tasks,
            'success_rate': success_rate,
            'duration': duration,
            'avg_time_per_task': avg_time,
            'start_time': self.start_time,
            'end_time': self.end_time
        }

    def get_server_pool(self) -> ServerPool:
        """获取服务器池对象"""
        return self.server_pool
