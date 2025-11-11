"""
任务调度器（简化版 - 固定设备分配）
"""

import logging
from datetime import datetime, timedelta
from src.database.models import InteractionTask, DeviceAssignment, DeviceDailyStats
from src.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class TaskScheduler:
    """任务分配调度器"""

    def __init__(self, db_manager):
        """初始化任务调度器

        Args:
            db_manager: 数据库管理器
        """
        self.db = db_manager

    def get_next_task_for_device(self, device_id, task_type):
        """为指定设备获取下一个任务（基于设备的去重）

        该方法会自动过滤掉设备已经完成过的用户，确保：
        1. 设备不会重复关注同一用户
        2. 不同设备可以关注同一用户

        Args:
            device_id: 设备ID
            task_type: 任务类型 ('history' 或 'realtime')

        Returns:
            InteractionTask 对象，或 None
        """
        session = self.db.get_session()
        try:
            # 获取该设备已经完成的用户ID列表（使用 unique_id 和 user_id）
            completed_users = session.query(InteractionTask)\
                .filter(
                    InteractionTask.assigned_device == device_id,
                    InteractionTask.task_type == task_type,
                    InteractionTask.status == 'completed'
                )\
                .all()

            # 提取已完成用户的标识（unique_id 或 user_id）
            completed_unique_ids = set()
            completed_user_ids = set()

            for task in completed_users:
                if task.comment_unique_id:
                    completed_unique_ids.add(task.comment_unique_id)
                if task.comment_user_id:
                    completed_user_ids.add(task.comment_user_id)

            # 查询待处理任务
            query = session.query(InteractionTask)\
                .filter(
                    InteractionTask.status == 'pending',
                    InteractionTask.task_type == task_type,
                    InteractionTask.assigned_device.is_(None)
                )

            # 过滤掉已完成的用户
            if completed_unique_ids or completed_user_ids:
                # 排除已完成的用户
                if completed_unique_ids:
                    query = query.filter(
                        ~InteractionTask.comment_unique_id.in_(completed_unique_ids)
                    )
                if completed_user_ids:
                    query = query.filter(
                        ~InteractionTask.comment_user_id.in_(completed_user_ids)
                    )

            # 按优先级和时间排序
            if task_type == 'realtime':
                task = query.order_by(
                    InteractionTask.priority.desc(),
                    InteractionTask.created_at.asc()
                ).first()
            else:
                task = query.order_by(InteractionTask.created_at.asc()).first()

            # 分配给该设备
            if task:
                task.assigned_device = device_id
                task.status = 'assigned'
                session.commit()
                logger.debug(f"[{device_id}] 分配任务 #{task.id} - {task.comment_user_name}")
            else:
                # 检查是否因为所有任务都被该设备完成过
                total_pending = session.query(InteractionTask)\
                    .filter(
                        InteractionTask.status == 'pending',
                        InteractionTask.task_type == task_type,
                        InteractionTask.assigned_device.is_(None)
                    )\
                    .count()

                if total_pending > 0:
                    logger.debug(
                        f"[{device_id}] 无可分配任务：{total_pending} 个待处理任务已被该设备完成过"
                    )

            return task

        finally:
            session.close()

    def check_daily_quota(self, device_id):
        """检查设备的每日配额

        Args:
            device_id: 设备ID

        Returns:
            {'used': int, 'limit': int, 'remaining': int} 或 None
        """
        session = self.db.get_session()
        try:
            # 获取设备的配额限制
            assignment = session.query(DeviceAssignment)\
                .filter_by(device_id=device_id)\
                .first()

            if not assignment:
                logger.warning(f"设备 {device_id} 未在 DeviceAssignment 中配置")
                return None

            # 获取今天的统计
            today = datetime.now().date()
            stats = session.query(DeviceDailyStats)\
                .filter(
                    DeviceDailyStats.device_id == device_id,
                    DeviceDailyStats.date == today
                )\
                .first()

            used = stats.completed_tasks if stats else 0
            limit = assignment.max_daily_quota
            remaining = max(0, limit - used)

            return {
                'used': used,
                'limit': limit,
                'remaining': remaining
            }

        finally:
            session.close()

    def update_daily_stats(self, device_id, task_status):
        """更新设备的每日统计

        Args:
            device_id: 设备ID
            task_status: 任务状态 ('completed' 或 'failed')
        """
        session = self.db.get_session()
        try:
            today = datetime.now().date()
            stats = session.query(DeviceDailyStats)\
                .filter(
                    DeviceDailyStats.device_id == device_id,
                    DeviceDailyStats.date == today
                )\
                .first()

            if not stats:
                stats = DeviceDailyStats(
                    device_id=device_id,
                    date=today,
                    completed_tasks=0,
                    failed_tasks=0
                )
                session.add(stats)

            # 确保字段不是 None
            if stats.completed_tasks is None:
                stats.completed_tasks = 0
            if stats.failed_tasks is None:
                stats.failed_tasks = 0

            if task_status == 'completed':
                stats.completed_tasks += 1
            elif task_status == 'failed':
                stats.failed_tasks += 1

            session.commit()

        finally:
            session.close()

    def init_device_assignments(self):
        """初始化设备分配规则（支持自动检测设备）"""
        session = self.db.get_session()
        try:
            # 从配置文件读取设备数量
            import json
            import subprocess
            try:
                with open('config/config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)

                device_config = config.get('devices', {})

                # 如果配置为自动检测
                if device_config.get('auto_detect', False):
                    # 从 adb devices 获取设备列表
                    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
                    lines = result.stdout.strip().split('\n')[1:]  # 跳过第一行

                    available_devices = []
                    for line in lines:
                        if '\t' in line:
                            serial = line.split('\t')[0].strip()
                            available_devices.append(serial)

                    longterm_count = len(available_devices)
                    realtime_count = 0  # 默认全部用于长期
                    logger.info(f"✓ 自动检测到 {longterm_count} 台设备")

                # 否则从配置读取
                elif 'longterm_devices' in device_config:
                    longterm_count = device_config.get('longterm_devices', 4)
                    realtime_count = device_config.get('realtime_devices', 0)
                    logger.info(f"✓ 从配置读取: {longterm_count} 台长期 + {realtime_count} 台实时")

                else:
                    # 默认值：尝试自动检测
                    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
                    lines = result.stdout.strip().split('\n')[1:]

                    available_devices = []
                    for line in lines:
                        if '\t' in line:
                            serial = line.split('\t')[0].strip()
                            available_devices.append(serial)

                    longterm_count = len(available_devices) if available_devices else 4
                    realtime_count = 0
                    logger.info(f"✓ 自动检测到 {longterm_count} 台设备")

            except Exception as e:
                logger.warning(f"⚠ 读取设备配置失败，使用默认配置: {e}")
                longterm_count = 4
                realtime_count = 0

            # 生成设备分配列表
            devices = []

            # 长期工作设备
            for i in range(1, longterm_count + 1):
                devices.append((f'Device-{i}', f'设备{i}-长期', 'long_term', 50))

            # 实时工作设备
            for i in range(realtime_count):
                devices.append((f'Device-{longterm_count+i+1}', f'设备{longterm_count+i+1}-实时', 'realtime', 999))

            logger.info(f"✓ 设备配置：{longterm_count} 台长期 + {realtime_count} 台实时 = {longterm_count + realtime_count} 台总计")

            for device_id, device_name, assignment_type, quota in devices:
                # 检查是否已存在
                existing = session.query(DeviceAssignment).filter_by(device_id=device_id).first()
                if not existing:
                    assignment = DeviceAssignment(
                        device_id=device_id,
                        device_name=device_name,
                        assignment_type=assignment_type,
                        max_daily_quota=quota
                    )
                    session.add(assignment)

            session.commit()
            logger.info("✓ 设备分配规则初始化成功")

        except Exception as e:
            session.rollback()
            logger.error(f"✗ 初始化设备分配规则失败: {e}")
        finally:
            session.close()
