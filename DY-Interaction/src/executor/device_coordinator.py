"""
多设备协调器 - 管理多个设备并行执行任务
"""

import logging
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

from .interaction_executor import InteractionExecutor
from ..database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class MultiDeviceCoordinator:
    """多设备协调器"""

    def __init__(self, db_manager: DatabaseManager, config_file: str = 'config/device_config.json'):
        """初始化多设备协调器

        Args:
            db_manager: 数据库管理器
            config_file: 设备配置文件
        """
        self.db = db_manager
        self.executors = {}  # device_id -> InteractionExecutor
        self.device_info = {}  # device_id -> device_config

        # 加载设备配置
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            for device_config in config.get('devices', []):
                if device_config.get('enabled', True):
                    device_id = device_config['device_id']

                    # 创建执行器
                    executor = InteractionExecutor(
                        device_id=device_id,
                        db_manager=db_manager,
                        device_model=device_config.get('device_model')
                    )

                    self.executors[device_id] = executor
                    self.device_info[device_id] = device_config

                    # 更新数据库中的设备状态
                    device = self.db.get_device(device_id)
                    if not device:
                        self.db.create_device(
                            device_name=device_config['device_name'],
                            device_model=device_config['device_model'],
                            adb_serial=device_config.get('adb_serial', ''),
                            device_id=device_id,
                            account_id=device_config.get('account_id'),
                            account_name=device_config.get('account_name')
                        )

            logger.info(f"✓ 初始化 {len(self.executors)} 个设备执行器")

        except FileNotFoundError:
            logger.error(f"✗ 配置文件不存在: {config_file}")
            logger.info("请复制 config/device_config.example.json 为 config/device_config.json")
            raise
        except Exception as e:
            logger.error(f"✗ 加载设备配置失败: {e}")
            raise

    def get_available_devices(self) -> List[str]:
        """获取所有可用设备ID列表

        Returns:
            设备ID列表
        """
        return list(self.executors.keys())

    def get_device_info(self, device_id: str) -> Optional[Dict]:
        """获取设备信息

        Args:
            device_id: 设备ID

        Returns:
            设备配置信息
        """
        return self.device_info.get(device_id)

    def execute_task_on_device(self, task_id: int, device_id: str) -> bool:
        """在指定设备上执行任务

        Args:
            task_id: InteractionTask ID（使用ID而非对象，避免SQLAlchemy session问题）
            device_id: 设备ID

        Returns:
            是否成功
        """
        executor = self.executors.get(device_id)
        if not executor:
            logger.error(f"设备不存在: {device_id}")
            return False

        try:
            # 从数据库重新获取任务对象（确保在当前线程中有有效的session）
            task = self.db.get_interaction_task(task_id)
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return False

            # 更新设备状态为忙碌
            self.db.update_device_status(device_id, 'busy', task_id)

            # 执行任务
            result = executor.execute_task(task)

            # 更新设备状态为空闲
            self.db.update_device_status(device_id, 'idle')

            return result

        except Exception as e:
            logger.error(f"执行任务 #{task_id} 失败: {e}")
            # 更新设备状态为错误
            self.db.update_device_status(device_id, 'error')
            return False

    def assign_task_to_device(self, task_id: int, strategy: str = 'round_robin') -> Optional[str]:
        """为任务分配设备

        Args:
            task_id: InteractionTask ID
            strategy: 分配策略（round_robin, least_busy, random）

        Returns:
            分配的设备ID
        """
        available_devices = self.get_available_devices()

        if not available_devices:
            logger.error("没有可用的设备")
            return None

        if strategy == 'round_robin':
            # 轮流分配
            device_id = available_devices[task_id % len(available_devices)]

        elif strategy == 'least_busy':
            # 分配给最不忙的设备
            device_stats = {}
            for device_id in available_devices:
                # 查询该设备当前的任务数
                pending_tasks = self.db.get_interaction_tasks(
                    status='in_progress'
                )
                device_task_count = sum(
                    1 for t in pending_tasks if t.assigned_device == device_id
                )
                device_stats[device_id] = device_task_count

            # 选择任务最少的设备
            device_id = min(device_stats, key=device_stats.get)

        elif strategy == 'random':
            # 随机分配
            import random
            device_id = random.choice(available_devices)

        else:
            # 默认使用轮流分配
            device_id = available_devices[0]

        logger.info(f"任务 #{task_id} 分配给设备: {device_id}")
        return device_id

    def execute_task_parallel(self, tasks: List, max_workers: int = None, strategy: str = 'round_robin') -> List:
        """并行执行多个任务

        Args:
            tasks: InteractionTask 列表或任务ID列表
            max_workers: 最多使用的线程数（默认为设备数量）
            strategy: 任务分配策略

        Returns:
            执行结果列表 [(task_id, success), ...]
        """
        if not tasks:
            logger.warning("没有任务需要执行")
            return []

        if max_workers is None:
            max_workers = len(self.executors)

        logger.info(f"并行执行 {len(tasks)} 个任务，使用 {max_workers} 个线程")

        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 为每个任务分配设备并提交
            futures = {}

            for task in tasks:
                # 获取任务ID（支持传入task对象或task_id）
                if isinstance(task, int):
                    task_id = task
                else:
                    task_id = task.id

                # 分配设备
                device_id = self.assign_task_to_device(task_id, strategy)

                if not device_id:
                    logger.error(f"无法为任务 #{task_id} 分配设备")
                    results.append((task_id, False))
                    continue

                # 提交任务（传递task_id而非task对象）
                future = executor.submit(
                    self.execute_task_on_device,
                    task_id,
                    device_id
                )

                futures[future] = (task_id, device_id)

            # 收集结果
            for future in as_completed(futures):
                task_id, device_id = futures[future]

                try:
                    result = future.result()
                    results.append((task_id, result))

                    if result:
                        logger.info(f"✓ 任务 #{task_id} 完成 (设备: {device_id})")
                    else:
                        logger.warning(f"✗ 任务 #{task_id} 失败 (设备: {device_id})")

                except Exception as e:
                    logger.error(f"✗ 任务 #{task_id} 异常: {e}")
                    results.append((task_id, False))

        # 统计
        success_count = sum(1 for _, success in results if success)
        logger.info(f"\n执行完成: {success_count}/{len(tasks)} 个任务成功")

        return results

    def check_devices_health(self) -> Dict[str, str]:
        """检查所有设备的健康状态

        Returns:
            {device_id: status} 字典
        """
        health_status = {}

        for device_id in self.executors.keys():
            try:
                # 检查设备连接（这里可以添加实际的连接检查）
                device = self.db.get_device(device_id)

                if device:
                    health_status[device_id] = device.status
                else:
                    health_status[device_id] = 'unknown'

            except Exception as e:
                logger.error(f"检查设备 {device_id} 失败: {e}")
                health_status[device_id] = 'error'

        return health_status

    def rebalance_tasks(self, failed_device_id: str):
        """任务重新分配（当设备出现问题时）

        Args:
            failed_device_id: 故障设备ID
        """
        logger.warning(f"设备 {failed_device_id} 故障，重新分配任务")

        # 获取该设备上所有未完成的任务
        pending_tasks = self.db.get_interaction_tasks(status='in_progress')
        failed_device_tasks = [
            task.id for task in pending_tasks
            if task.assigned_device == failed_device_id
        ]

        if not failed_device_tasks:
            logger.info("没有需要重新分配的任务")
            return

        logger.info(f"需要重新分配 {len(failed_device_tasks)} 个任务")

        # 将这些任务重置为待执行状态
        for task_id in failed_device_tasks:
            self.db.update_task_status(task_id, 'pending', assigned_device=None)

        # 重新执行这些任务
        self.execute_task_parallel(failed_device_tasks)

    def get_coordinator_stats(self) -> Dict:
        """获取协调器统计信息

        Returns:
            统计信息字典
        """
        device_stats = self.db.get_device_stats()
        task_stats = self.db.get_task_stats()

        return {
            'devices': device_stats,
            'tasks': task_stats,
            'active_executors': len(self.executors)
        }
