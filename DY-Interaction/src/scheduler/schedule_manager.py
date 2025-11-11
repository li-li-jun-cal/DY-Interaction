"""
主调度管理器（简化版）
"""

import logging
import time
import threading
import schedule
from datetime import datetime
from src.crawler.history_crawler import HistoryCrawler
from src.crawler.monitor_crawler import MonitorCrawler
from src.generator.task_generator import TaskGenerator
from src.executor.automation_executor import AutomationExecutor
from src.scheduler.task_scheduler import TaskScheduler
from src.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class ScheduleManager:
    """主调度管理器 - 协调所有子系统"""

    def __init__(self, api_client=None):
        """初始化调度管理器

        Args:
            api_client: API 客户端（可选）
        """
        self.db = DatabaseManager()
        self.api = api_client
        self.history_crawler = HistoryCrawler(self.db, self.api) if self.api else None
        self.monitor_crawler = MonitorCrawler(self.db, self.api) if self.api else None
        self.task_generator = TaskGenerator(self.db)
        self.scheduler = TaskScheduler(self.db)
        self.workers = {}

        # 初始化设备分配规则
        self.scheduler.init_device_assignments()

    def start(self):
        """启动调度管理器"""
        logger.info("=" * 70)
        logger.info("🚀 DY-Interaction 简化版系统启动")
        logger.info("=" * 70)

        # 1. 启动长期工作线程（5台设备）
        self._start_long_term_workers()

        # 2. 启动实时工作线程（2台设备）
        self._start_realtime_workers()

        # 3. 如果有API客户端，启动定时爬虫和任务生成
        if self.api:
            # 历史爬虫（初始化一次，或每个月运行一次）
            schedule.every().month.do(self.crawl_history)

            # 监控爬虫（每天凌晨 2 点）
            schedule.every().day.at("02:00").do(self.crawl_monitor)

            # 启动调度线程
            schedule_thread = threading.Thread(target=self._run_schedule, daemon=True)
            schedule_thread.start()
            logger.info("✓ 启动定时任务调度")
        else:
            logger.warning("⚠ 未配置API客户端，跳过爬虫功能")

        # 4. 保持主线程运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n[停止] 收到停止信号，关闭系统...")
            self.stop()

    def crawl_history(self):
        """历史爬虫（一次性或定期）"""
        if not self.api:
            return

        logger.info("\n📝 [历史爬虫] 开始爬取历史评论")
        logger.info("-" * 70)

        target_accounts = self.db.get_target_accounts()

        for account in target_accounts:
            try:
                result = self.history_crawler.crawl_history(account)
                logger.info(f"  └─ 账号 {account.account_id}: {result['status']}")

                # 生成任务
                if result['status'] == 'success' and result.get('total_comments', 0) > 0:
                    task_count = self.task_generator.generate_from_history(account.id)
                    logger.info(f"     生成 {task_count} 个 history 任务")
            except Exception as e:
                logger.error(f"  └─ 账号 {account.account_id} 爬取失败: {e}")

    def crawl_monitor(self):
        """监控爬虫（每天运行一次）"""
        if not self.api:
            return

        logger.info("\n👁️  [监控爬虫] 开始监控新增评论")
        logger.info("-" * 70)

        target_accounts = self.db.get_target_accounts()

        for account in target_accounts:
            try:
                result = self.monitor_crawler.monitor_daily(account)
                logger.info(
                    f"  └─ 账号 {account.account_id}: {result['new_comments_count']} 条新增"
                )

                # 生成任务
                if result['new_comments_count'] > 0:
                    task_count = self.task_generator.generate_from_realtime(account.id)
                    logger.info(f"     生成 {task_count} 个 realtime 任务")
            except Exception as e:
                logger.error(f"  └─ 账号 {account.account_id} 监控失败: {e}")

    def _start_long_term_workers(self):
        """启动长期工作设备（从配置直接读取）"""
        # 从配置文件读取设备数量
        import json
        try:
            with open('config/config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)

            device_config = config.get('devices', {})
            longterm_count = device_config.get('longterm_devices', 4)

            # 生成长期设备列表
            devices = [f'Device-{i+1}' for i in range(longterm_count)]

        except Exception as e:
            logger.warning(f"⚠ 读取设备配置失败，使用默认配置: {e}")
            devices = ['Device-1', 'Device-2', 'Device-3', 'Device-4']

        logger.info(f"✓ 启动 {len(devices)} 台长期工作设备: {', '.join(devices)}")

        for device_id in devices:
            thread = threading.Thread(
                target=self._worker_long_term,
                args=(device_id,),
                daemon=True
            )
            thread.start()
            self.workers[device_id] = thread
            logger.info(f"  ✓ 启动长期工作线程: {device_id}")

    def _start_realtime_workers(self):
        """启动实时工作设备（从配置直接读取）"""
        # 从配置文件读取设备数量
        import json
        try:
            with open('config/config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)

            device_config = config.get('devices', {})
            longterm_count = device_config.get('longterm_devices', 4)
            realtime_count = device_config.get('realtime_devices', 2)

            # 生成实时设备列表
            devices = [f'Device-{longterm_count+i+1}' for i in range(realtime_count)]

        except Exception as e:
            logger.warning(f"⚠ 读取设备配置失败，使用默认配置: {e}")
            devices = ['Device-6', 'Device-7']

        logger.info(f"✓ 启动 {len(devices)} 台实时工作设备: {', '.join(devices)}")

        for device_id in devices:
            thread = threading.Thread(
                target=self._worker_realtime,
                args=(device_id,),
                daemon=True
            )
            thread.start()
            self.workers[device_id] = thread
            logger.info(f"  ✓ 启动实时工作线程: {device_id}")

    def _worker_long_term(self, device_id):
        """长期工作线程"""
        try:
            executor = AutomationExecutor(device_id, self.db)
        except Exception as e:
            logger.error(f"[{device_id}] 初始化失败: {e}")
            return

        consecutive_empty = 0
        max_empty_cycles = 12  # 10秒 × 12 = 120秒（2分钟）无任务后重新检查

        while True:
            try:
                # 检查日配额
                quota = self.scheduler.check_daily_quota(device_id)

                if quota and quota['remaining'] <= 0:
                    logger.info(
                        f"[{device_id}] 今日配额已用完，休息中..."
                    )
                    time.sleep(3600)  # 休息1小时
                    continue

                # 获取下一个 history 任务
                task = self.scheduler.get_next_task_for_device(device_id, 'history')

                if task:
                    consecutive_empty = 0
                    success = executor.execute_history_task(task)

                    if success:
                        self.scheduler.update_daily_stats(device_id, 'completed')
                    else:
                        self.scheduler.update_daily_stats(device_id, 'failed')

                    time.sleep(5)  # 任务间隔
                else:
                    consecutive_empty += 1
                    logger.debug(f"[{device_id}] 暂无待执行任务")
                    time.sleep(10)  # 等待10秒再检查

                    # 连续无任务多次后，长时间睡眠
                    if consecutive_empty > max_empty_cycles:
                        logger.info(f"[{device_id}] 长时间无任务，进入深度休眠")
                        time.sleep(300)  # 5分钟
                        consecutive_empty = 0

            except Exception as e:
                logger.error(f"[{device_id}] 工作线程错误: {e}")
                time.sleep(30)

    def _worker_realtime(self, device_id):
        """实时工作线程"""
        try:
            executor = AutomationExecutor(device_id, self.db)
        except Exception as e:
            logger.error(f"[{device_id}] 初始化失败: {e}")
            return

        consecutive_empty = 0
        max_empty_cycles = 6  # 10秒 × 6 = 60秒（1分钟）无任务后进入待机模式

        while True:
            try:
                # 获取下一个 realtime 任务
                task = self.scheduler.get_next_task_for_device(device_id, 'realtime')

                if task:
                    consecutive_empty = 0
                    success = executor.execute_realtime_task(task)

                    if success:
                        self.scheduler.update_daily_stats(device_id, 'completed')
                    else:
                        self.scheduler.update_daily_stats(device_id, 'failed')

                    time.sleep(5)  # 任务间隔
                else:
                    consecutive_empty += 1
                    logger.debug(f"[{device_id}] 暂无实时任务，进入待机模式")

                    # 待机模式：模拟正常用户
                    executor.simulate_normal_user()
                    time.sleep(10)  # 待机时间

                    # 连续无任务多次后，长时间睡眠
                    if consecutive_empty > max_empty_cycles:
                        logger.info(f"[{device_id}] 待机中，进入深度睡眠")
                        time.sleep(300)  # 5分钟
                        consecutive_empty = 0

            except Exception as e:
                logger.error(f"[{device_id}] 实时工作线程错误: {e}")
                time.sleep(30)

    def _run_schedule(self):
        """运行调度循环"""
        logger.info("✓ 定时任务调度启动")
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"调度错误: {e}")
                time.sleep(5)

    def stop(self):
        """停止调度管理器"""
        logger.info("✓ 系统已停止")
        import sys
        sys.exit(0)
