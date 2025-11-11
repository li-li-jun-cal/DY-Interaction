#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一自动化服务 - DY-Interaction Automation Service

整合所有自动化模式到单一入口，提供统一的CLI接口和服务架构。

用法:
    # 实时模式 - 处理监控发现的新增评论（常驻）
    python programs/run_automation.py realtime --all

    # 近期模式 - 处理3个月内的历史评论（批量）
    python programs/run_automation.py recent --all

    # 长期模式 - 处理3个月前的历史评论（批量）
    python programs/run_automation.py longterm --all

    # 混合模式 - 优先实时，其次近期（常驻）
    python programs/run_automation.py mixed --all

    # 养号模式 - 模拟正常用户行为（常驻）
    python programs/run_automation.py maintenance --devices 1

模式说明:
    realtime:
        - 任务类型: task_type='realtime'
        - 数据来源: 监控爬虫发现的新增评论
        - 工作方式: 常驻运行，无任务时模拟用户行为
        - 响应时间: <1小时
        - 处理流程: 搜索 → 评论 → 关注 → 点赞 → 收藏

    recent:
        - 任务类型: task_type='history_recent'
        - 数据来源: 历史爬虫（3个月内评论）
        - 工作方式: 批量处理，处理完自动结束
        - 响应时间: 数小时到数天
        - 处理流程: 搜索 → 关注 → 点赞 → 收藏

    longterm:
        - 任务类型: task_type='history_old'
        - 数据来源: 历史爬虫（3个月前评论）
        - 工作方式: 批量处理，处理完自动结束
        - 响应时间: 数天到数周
        - 处理流程: 搜索 → 关注 → 点赞 → 收藏

    mixed:
        - 任务类型: 'realtime' + 'history_recent'
        - 优先级: realtime > history_recent
        - 工作方式: 常驻运行，优先处理实时任务
        - 适用场景: 全面覆盖，最大化转化率

    maintenance (养号):
        - 任务类型: 无任务处理
        - 工作方式: 纯粹模拟正常用户行为
        - 适用场景: 维护账号活跃度，防止被检测

设备选项:
    --all                 使用所有在线设备
    --interactive         交互式选择设备
    --devices N           使用指定数量的设备

高级选项:
    --quota-file FILE     使用自定义配额配置文件
    --dry-run             仅显示统计信息，不执行任务
"""

import logging
import sys
import threading
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import InteractionTask
from src.executor.automation_executor import AutomationExecutor
from src.scheduler.task_scheduler import TaskScheduler
from src.utils.device_manager import DeviceManager
from src.config.daily_quota import interactive_quota_config
from sqlalchemy import and_

# 日志配置
LOG_FILES = {
    'realtime': 'logs/automation_realtime.log',
    'recent': 'logs/automation_recent.log',
    'longterm': 'logs/automation_longterm.log',
    'mixed': 'logs/automation_mixed.log',
    'maintenance': 'logs/automation_maintenance.log'
}

logger = logging.getLogger(__name__)


def setup_logging(mode: str):
    """配置日志系统"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILES.get(mode, 'logs/automation.log')),
            logging.StreamHandler()
        ]
    )


class AutomationService:
    """统一自动化服务类"""

    def __init__(self, db: DatabaseManager, scheduler: TaskScheduler):
        """初始化自动化服务

        Args:
            db: 数据库管理器
            scheduler: 任务调度器
        """
        self.db = db
        self.scheduler = scheduler
        self.workers: List[threading.Thread] = []
        self.device_manager = DeviceManager()

    def get_task_statistics(self) -> Dict[str, int]:
        """获取任务统计信息

        Returns:
            包含各类任务数量的字典
        """
        with self.db.session_scope() as session:
            stats = {
                'realtime_pending': session.query(InteractionTask).filter(
                    and_(
                        InteractionTask.task_type == 'realtime',
                        InteractionTask.status == 'pending'
                    )
                ).count(),
                'realtime_completed': session.query(InteractionTask).filter(
                    and_(
                        InteractionTask.task_type == 'realtime',
                        InteractionTask.status == 'completed'
                    )
                ).count(),
                'recent_pending': session.query(InteractionTask).filter(
                    and_(
                        InteractionTask.task_type == 'history_recent',
                        InteractionTask.status == 'pending'
                    )
                ).count(),
                'recent_completed': session.query(InteractionTask).filter(
                    and_(
                        InteractionTask.task_type == 'history_recent',
                        InteractionTask.status == 'completed'
                    )
                ).count(),
                'old_pending': session.query(InteractionTask).filter(
                    and_(
                        InteractionTask.task_type == 'history_old',
                        InteractionTask.status == 'pending'
                    )
                ).count(),
                'old_completed': session.query(InteractionTask).filter(
                    and_(
                        InteractionTask.task_type == 'history_old',
                        InteractionTask.status == 'completed'
                    )
                ).count()
            }
            return stats

    def worker_realtime(self, device_id: str, quota: Optional[dict] = None):
        """实时模式工作线程 - 处理realtime任务"""
        try:
            logger.info(f"✓ 启动实时工作线程: {device_id}")
            executor = AutomationExecutor(device_id, self.db, daily_quota=quota)
        except Exception as e:
            logger.error(f"✗ {device_id} 初始化失败: {e}")
            return

        consecutive_empty = 0
        max_empty_cycles = 6  # 60秒无任务后进入深度待机

        while True:
            try:
                # 获取 realtime 任务
                task = self.scheduler.get_next_task_for_device(device_id, 'realtime')

                if task:
                    consecutive_empty = 0
                    logger.info(f"[{device_id}] 获取实时任务 #{task.id} - {task.comment_user_name}")

                    success = executor.execute_realtime_task(task)

                    if success:
                        self.scheduler.update_daily_stats(device_id, 'completed')
                        logger.info(f"[{device_id}] ✓ 任务完成")
                    else:
                        self.scheduler.update_daily_stats(device_id, 'failed')
                        logger.warning(f"[{device_id}] ⚠ 任务失败")

                    time.sleep(5)
                else:
                    consecutive_empty += 1

                    if consecutive_empty == 1:
                        logger.info(f"[{device_id}] 暂无实时任务，进入待机模式")
                    elif consecutive_empty % 6 == 0:
                        logger.debug(f"[{device_id}] 待机中，监听新任务...")

                    # 待机模式：模拟正常用户
                    executor.simulate_normal_user()
                    time.sleep(10)

                    # 深度睡眠
                    if consecutive_empty > max_empty_cycles:
                        logger.debug(f"[{device_id}] 进入深度睡眠")
                        time.sleep(300)
                        consecutive_empty = 0

            except Exception as e:
                logger.error(f"[{device_id}] 工作线程错误: {e}")
                time.sleep(30)

    def worker_recent(self, device_id: str, quota: Optional[dict] = None):
        """近期模式工作线程 - 处理history_recent任务"""
        try:
            logger.info(f"✓ 启动近期工作线程: {device_id}")
            executor = AutomationExecutor(device_id, self.db, daily_quota=quota)
        except Exception as e:
            logger.error(f"✗ {device_id} 初始化失败: {e}")
            return

        processed_count = 0

        while True:
            try:
                task = self.scheduler.get_next_task_for_device(device_id, 'history_recent')

                if task:
                    processed_count += 1
                    logger.info(f"[{device_id}] 获取近期任务 #{task.id} - {task.comment_user_name} ({processed_count})")

                    success = executor.execute_history_task(task)

                    if success:
                        self.scheduler.update_daily_stats(device_id, 'completed')
                        logger.info(f"[{device_id}] ✓ 任务完成")
                    else:
                        self.scheduler.update_daily_stats(device_id, 'failed')
                        logger.warning(f"[{device_id}] ⚠ 任务失败")

                    time.sleep(5)
                else:
                    logger.info(f"[{device_id}] ✓ 所有近期任务处理完成！共处理 {processed_count} 个任务")
                    break

            except Exception as e:
                logger.error(f"[{device_id}] 工作线程错误: {e}")
                time.sleep(30)

    def worker_longterm(self, device_id: str, quota: Optional[dict] = None):
        """长期模式工作线程 - 处理history_old任务"""
        try:
            logger.info(f"✓ 启动长期工作线程: {device_id}")
            executor = AutomationExecutor(device_id, self.db, daily_quota=quota)
        except Exception as e:
            logger.error(f"✗ {device_id} 初始化失败: {e}")
            return

        consecutive_empty = 0
        max_empty_cycles = 12

        while True:
            try:
                # 检查配额
                quota_status = self.scheduler.check_daily_quota(device_id)
                if quota_status and quota_status['remaining'] <= 0:
                    logger.info(f"[{device_id}] 今日配额已用完，休息中...")
                    time.sleep(3600)
                    continue

                task = self.scheduler.get_next_task_for_device(device_id, 'history_old')

                if task:
                    consecutive_empty = 0
                    logger.info(f"[{device_id}] 获取长期任务 #{task.id} - {task.comment_user_name}")

                    success = executor.execute_history_task(task)

                    if success:
                        self.scheduler.update_daily_stats(device_id, 'completed')
                        logger.info(f"[{device_id}] ✓ 任务完成")
                    else:
                        self.scheduler.update_daily_stats(device_id, 'failed')
                        logger.warning(f"[{device_id}] ⚠ 任务失败")

                    time.sleep(5)
                else:
                    consecutive_empty += 1
                    if consecutive_empty % 6 == 1:
                        logger.debug(f"[{device_id}] 暂无待执行任务，等待中...")
                    time.sleep(10)

                    if consecutive_empty > max_empty_cycles:
                        logger.info(f"[{device_id}] 长时间无任务，进入深度休眠")
                        time.sleep(300)
                        consecutive_empty = 0

            except Exception as e:
                logger.error(f"[{device_id}] 工作线程错误: {e}")
                time.sleep(30)

    def worker_mixed(self, device_id: str, quota: Optional[dict] = None):
        """混合模式工作线程 - 优先realtime，其次history_recent"""
        try:
            logger.info(f"✓ 启动混合工作线程: {device_id}")
            executor = AutomationExecutor(device_id, self.db, daily_quota=quota)
        except Exception as e:
            logger.error(f"✗ {device_id} 初始化失败: {e}")
            return

        consecutive_empty = 0
        max_empty_cycles = 6

        while True:
            try:
                # 优先获取 realtime 任务
                task = self.scheduler.get_next_task_for_device(device_id, 'realtime')
                task_type = 'realtime'

                if task:
                    consecutive_empty = 0
                    logger.info(f"[{device_id}] 获取实时任务 #{task.id} - {task.comment_user_name} [优先]")
                else:
                    # 没有实时任务，获取近期任务
                    task = self.scheduler.get_next_task_for_device(device_id, 'history_recent')
                    task_type = 'history_recent'

                    if task:
                        consecutive_empty = 0
                        logger.info(f"[{device_id}] 获取近期任务 #{task.id} - {task.comment_user_name}")

                if task:
                    # 根据任务类型选择执行方法
                    if task_type == 'realtime':
                        success = executor.execute_realtime_task(task)
                    else:
                        success = executor.execute_history_task(task)

                    if success:
                        self.scheduler.update_daily_stats(device_id, 'completed')
                        logger.info(f"[{device_id}] ✓ 任务完成")
                    else:
                        self.scheduler.update_daily_stats(device_id, 'failed')
                        logger.warning(f"[{device_id}] ⚠ 任务失败")

                    time.sleep(5)
                else:
                    consecutive_empty += 1

                    if consecutive_empty == 1:
                        logger.info(f"[{device_id}] 暂无任务，进入待机模式")
                    elif consecutive_empty % 6 == 0:
                        logger.debug(f"[{device_id}] 待机中...")

                    executor.simulate_normal_user()
                    time.sleep(10)

                    if consecutive_empty > max_empty_cycles:
                        logger.debug(f"[{device_id}] 进入深度睡眠")
                        time.sleep(300)
                        consecutive_empty = 0

            except Exception as e:
                logger.error(f"[{device_id}] 工作线程错误: {e}")
                time.sleep(30)

    def worker_maintenance(self, device_id: str):
        """养号模式工作线程 - 纯粹模拟正常用户行为"""
        try:
            logger.info(f"✓ 启动养号工作线程: {device_id}")
            executor = AutomationExecutor(device_id, self.db)
        except Exception as e:
            logger.error(f"✗ {device_id} 初始化失败: {e}")
            return

        logger.info(f"[{device_id}] 进入养号模式 - 模拟正常用户行为")

        cycle_count = 0

        while True:
            try:
                cycle_count += 1

                # 养号：持续模拟正常用户行为
                if cycle_count % 10 == 1:
                    logger.info(f"[{device_id}] 养号中... (已运行 {cycle_count} 个周期)")

                executor.simulate_normal_user()
                time.sleep(30)  # 每30秒进行一次用户行为模拟

                # 每小时休息一次
                if cycle_count % 120 == 0:  # 30秒 * 120 = 1小时
                    logger.info(f"[{device_id}] 养号休息 5分钟...")
                    time.sleep(300)

            except Exception as e:
                logger.error(f"[{device_id}] 养号线程错误: {e}")
                time.sleep(60)

    def start_automation(self, mode: str, devices: List[str], quota: Optional[dict] = None):
        """启动自动化服务

        Args:
            mode: 工作模式 (realtime/recent/longterm/mixed/maintenance)
            devices: 设备列表
            quota: 配额配置（可选）
        """
        # 选择工作函数
        worker_func_map = {
            'realtime': lambda d: self.worker_realtime(d, quota),
            'recent': lambda d: self.worker_recent(d, quota),
            'longterm': lambda d: self.worker_longterm(d, quota),
            'mixed': lambda d: self.worker_mixed(d, quota),
            'maintenance': self.worker_maintenance
        }

        worker_func = worker_func_map.get(mode)
        if not worker_func:
            raise ValueError(f"Unknown mode: {mode}")

        # 锁定设备
        self.device_manager.lock_devices(devices, f'automation_{mode}')

        # 启动工作线程
        for device_id in devices:
            thread = threading.Thread(
                target=worker_func,
                args=(device_id,),
                daemon=True
            )
            thread.start()
            self.workers.append(thread)
            logger.info(f"  ✓ {device_id} 已启动")

        return self.workers

    def stop_automation(self, mode: str):
        """停止自动化服务"""
        self.device_manager.unlock_devices(f'automation_{mode}')
        logger.info("✓ 设备已解锁")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='DY-Interaction 统一自动化服务',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # 位置参数：模式
    parser.add_argument('mode',
                        choices=['realtime', 'recent', 'longterm', 'mixed', 'maintenance'],
                        help='工作模式')

    # 设备选择
    parser.add_argument('--all', action='store_true',
                        help='使用所有在线设备')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='交互式选择设备')
    parser.add_argument('--devices', type=int,
                        help='使用指定数量的设备')

    # 高级选项
    parser.add_argument('--dry-run', action='store_true',
                        help='仅显示统计，不执行')

    args = parser.parse_args()

    # 设置日志
    setup_logging(args.mode)

    # 模式显示名称
    mode_names = {
        'realtime': '⚡ 实时模式',
        'recent': '📅 近期模式',
        'longterm': '⏳ 长期模式',
        'mixed': '🔀 混合模式',
        'maintenance': '🔧 养号模式'
    }

    logger.info("=" * 70)
    logger.info(f"{mode_names[args.mode]} - 启动")
    logger.info("=" * 70)

    try:
        # 初始化数据库
        logger.info("\n初始化数据库...")
        db = DatabaseManager()
        db.init_db()
        logger.info("✓ 数据库初始化完成")

        # 初始化调度器
        logger.info("\n初始化调度器...")
        scheduler = TaskScheduler(db)
        scheduler.init_device_assignments()
        logger.info("✓ 调度器初始化完成")

        # 创建自动化服务
        service = AutomationService(db, scheduler)

        # 获取任务统计
        logger.info("\n" + "=" * 70)
        logger.info("📊 任务统计")
        logger.info("=" * 70)

        stats = service.get_task_statistics()

        logger.info(f"\n【实时新增评论】(realtime)")
        logger.info(f"  待处理: {stats['realtime_pending']} 个")
        logger.info(f"  已完成: {stats['realtime_completed']} 个")

        logger.info(f"\n【近期历史评论】(history_recent, 3个月内)")
        logger.info(f"  待处理: {stats['recent_pending']} 个")
        logger.info(f"  已完成: {stats['recent_completed']} 个")

        logger.info(f"\n【历史旧评论】(history_old, 3个月前)")
        logger.info(f"  待处理: {stats['old_pending']} 个")
        logger.info(f"  已完成: {stats['old_completed']} 个")

        # Dry-run模式：只显示统计
        if args.dry_run:
            logger.info("\n[Dry Run] 统计信息已显示，退出")
            return 0

        # 检查是否有任务
        total_tasks = stats['realtime_pending'] + stats['recent_pending'] + stats['old_pending']

        # 配额配置
        if args.mode != 'maintenance':
            logger.info("\n" + "=" * 70)
            quota = interactive_quota_config(total_tasks=total_tasks)
            logger.info("=" * 70)
        else:
            quota = None

        # 设备管理
        device_manager = DeviceManager()

        logger.info("\n检测在线设备...")
        online_devices = device_manager.get_online_devices()

        if not online_devices:
            logger.error("❌ 未检测到任何在线设备")
            logger.info("  请确保:")
            logger.info("    1. ADB已正确安装并在PATH中")
            logger.info("    2. 设备已通过USB或网络连接")
            logger.info("    3. 设备已开启USB调试")
            return 1

        logger.info(f"✓ 检测到 {len(online_devices)} 台在线设备")

        # 选择设备
        if args.all:
            selected_devices = online_devices
            logger.info(f"✓ 使用所有 {len(selected_devices)} 台设备")
        elif args.devices:
            selected_devices = online_devices[:args.devices]
            logger.info(f"✓ 使用前 {len(selected_devices)} 台设备")
        elif args.interactive or len(online_devices) > 1:
            selected_devices = device_manager.interactive_select_devices(online_devices)
            if not selected_devices:
                logger.warning("未选择任何设备，退出")
                return 0
        else:
            selected_devices = online_devices
            logger.info(f"✓ 使用唯一在线设备: {selected_devices[0]}")

        # 映射到Device名称
        devices = device_manager.map_to_device_names(selected_devices)

        if not devices:
            logger.warning("⚠ 未配置任何设备，退出")
            return 0

        # 启动自动化服务
        logger.info("\n" + "=" * 70)
        logger.info(f"启动 {len(devices)} 台设备 [{mode_names[args.mode]}]")
        logger.info("=" * 70)

        service.start_automation(args.mode, devices, quota)

        logger.info("\n" + "=" * 70)
        logger.info("📊 系统状态")
        logger.info("=" * 70)
        logger.info(f"  工作设备: {len(devices)} 台 ({', '.join(devices)})")
        logger.info(f"  工作模式: {mode_names[args.mode]}")

        if args.mode == 'realtime':
            logger.info(f"  待处理任务: {stats['realtime_pending']} 个")
        elif args.mode == 'recent':
            logger.info(f"  待处理任务: {stats['recent_pending']} 个")
        elif args.mode == 'longterm':
            logger.info(f"  待处理任务: {stats['old_pending']} 个")
        elif args.mode == 'mixed':
            logger.info(f"  实时任务: {stats['realtime_pending']} 个")
            logger.info(f"  近期任务: {stats['recent_pending']} 个")

        logger.info("=" * 70)

        # 保持主线程运行
        try:
            if args.mode in ['recent', 'longterm']:
                # 批量模式：等待所有线程完成
                for worker in service.workers:
                    worker.join()
                logger.info("\n✓ 所有任务处理完成，程序退出")
            else:
                # 常驻模式：持续运行
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n\n[停止] 收到停止信号，正在关闭...")
            service.stop_automation(args.mode)
            logger.info("✓ 所有工作线程已停止")
            return 0

    except Exception as e:
        logger.error(f"\n❌ 执行出错: {e}")
        import traceback
        traceback.print_exc()

        # 出错时解锁设备
        try:
            service.stop_automation(args.mode)
        except:
            pass

        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
