"""
API 服务器池管理

支持多服务器负载均衡、健康检查、自动故障转移
"""

import json
import threading
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path

import logging

logger = logging.getLogger(__name__)


class APIServer:
    """API 服务器"""

    def __init__(self, name: str, url: str, cookie: str, is_backup: bool = False, concurrency_limit: int = 1):
        """
        初始化API服务器

        Args:
            name: 服务器名称
            url: 服务器URL
            cookie: Cookie
            is_backup: 是否为备用服务器
            concurrency_limit: 单服务器并发容量（同时处理几个任务）
        """
        self.name = name
        self.url = url
        self.cookie = cookie
        self.is_backup = is_backup
        self.concurrency_limit = concurrency_limit  # 单服务器并发容量

        # 状态跟踪
        self.is_healthy = True
        self.current_tasks = []  # 当前正在处理的任务列表
        self.last_check_time = None
        self.consecutive_failures = 0
        self.total_requests = 0
        self.successful_requests = 0

    def can_accept_task(self) -> bool:
        """是否还能接受新任务"""
        return len(self.current_tasks) < self.concurrency_limit and self.is_healthy

    def add_task(self, task_name: str):
        """添加任务"""
        if len(self.current_tasks) < self.concurrency_limit:
            self.current_tasks.append(task_name)
            logger.debug(f"服务器 {self.name} 接受任务: {task_name} ({len(self.current_tasks)}/{self.concurrency_limit})")
        else:
            raise ValueError(f"服务器 {self.name} 已达并发上限: {self.concurrency_limit}")

    def remove_task(self, task_name: str):
        """移除任务"""
        if task_name in self.current_tasks:
            self.current_tasks.remove(task_name)
            logger.debug(f"服务器 {self.name} 完成任务: {task_name} ({len(self.current_tasks)}/{self.concurrency_limit})")

    @property
    def is_busy(self) -> bool:
        """是否忙碌（兼容旧代码）"""
        return len(self.current_tasks) >= self.concurrency_limit

    @property
    def current_task(self) -> Optional[str]:
        """当前任务（兼容旧代码，返回第一个任务）"""
        return self.current_tasks[0] if self.current_tasks else None

    def mark_success(self):
        """记录成功请求"""
        self.total_requests += 1
        self.successful_requests += 1
        self.consecutive_failures = 0
        self.is_healthy = True

    def mark_failure(self):
        """记录失败请求"""
        self.total_requests += 1
        self.consecutive_failures += 1

        # 连续失败3次标记为不健康
        if self.consecutive_failures >= 3:
            self.is_healthy = False
            logger.warning(f"服务器 {self.name} 连续失败{self.consecutive_failures}次，标记为不健康")

    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    def __repr__(self):
        status = "忙碌" if self.is_busy else "空闲"
        health = "健康" if self.is_healthy else "故障"
        return f"<APIServer {self.name} ({health}, {status})>"


class ServerPool:
    """API 服务器池"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化服务器池

        Args:
            config_path: 配置文件路径，默认为 config/api_servers.json
        """
        self.lock = threading.Lock()
        self.primary_servers: List[APIServer] = []
        self.backup_servers: List[APIServer] = []

        # 加载配置
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "api_servers.json"

        self._load_config(config_path)

    def _load_config(self, config_path: Path):
        """加载服务器配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 加载主服务器
            for server_cfg in config.get('primary_servers', []):
                server = APIServer(
                    name=server_cfg['name'],
                    url=server_cfg['url'],
                    cookie=server_cfg['cookie'],
                    is_backup=False,
                    concurrency_limit=server_cfg.get('concurrency_limit', 1)  # 默认1个并发
                )
                self.primary_servers.append(server)

            # 加载备用服务器
            for server_cfg in config.get('backup_servers', []):
                server = APIServer(
                    name=server_cfg['name'],
                    url=server_cfg['url'],
                    cookie=server_cfg['cookie'],
                    is_backup=True,
                    concurrency_limit=server_cfg.get('concurrency_limit', 1)
                )
                self.backup_servers.append(server)

            logger.info(f"✓ 加载服务器配置: {len(self.primary_servers)}主 + {len(self.backup_servers)}备")

        except FileNotFoundError:
            logger.warning(f"⚠️  服务器配置文件不存在: {config_path}")
            logger.info("将使用默认单服务器配置")
            # 创建默认配置
            self._create_default_config(config_path)

        except Exception as e:
            logger.error(f"✗ 加载服务器配置失败: {e}")
            raise

    def _create_default_config(self, config_path: Path):
        """创建默认配置文件"""
        default_config = {
            "primary_servers": [
                {
                    "name": "server1",
                    "url": "http://127.0.0.1:8888",
                    "cookie": "your_cookie_here"
                }
            ],
            "backup_servers": []
        }

        # 确保目录存在
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ 创建默认配置文件: {config_path}")

        # 加载默认配置
        self.primary_servers = [
            APIServer(
                name="server1",
                url="http://127.0.0.1:8888",
                cookie="your_cookie_here"
            )
        ]

    def get_available_server(self, wait: bool = True, timeout: int = 60) -> Optional[APIServer]:
        """
        获取可用的服务器

        Args:
            wait: 如果没有可用服务器，是否等待
            timeout: 等待超时时间（秒）

        Returns:
            可用的服务器，如果没有则返回 None
        """
        start_time = time.time()

        while True:
            with self.lock:
                # 1. 优先从主服务器中选择可接受任务的（未达并发上限且健康）
                for server in self.primary_servers:
                    if server.can_accept_task():
                        return server

                # 2. 如果主服务器都不可用，尝试备用服务器
                for server in self.backup_servers:
                    if server.can_accept_task():
                        logger.warning(f"⚠️  主服务器全忙，使用备用服务器: {server.name}")
                        return server

                # 3. 如果都达到并发上限，尝试选择负载最小的健康服务器
                all_servers = self.primary_servers + self.backup_servers
                healthy_servers = [s for s in all_servers if s.is_healthy]
                if healthy_servers:
                    # 按当前任务数排序，选择负载最小的
                    healthy_servers.sort(key=lambda s: (len(s.current_tasks), s.consecutive_failures))
                    server = healthy_servers[0]
                    if len(server.current_tasks) < server.concurrency_limit:
                        return server

                # 4. 如果都不健康，尝试选择故障次数最少的
                if all_servers:
                    available = [s for s in all_servers if len(s.current_tasks) < s.concurrency_limit]
                    if available:
                        # 按连续失败次数排序，选择最好的
                        available.sort(key=lambda s: s.consecutive_failures)
                        server = available[0]
                        logger.warning(f"⚠️  所有服务器都有故障，使用状态最好的: {server.name}")
                        return server

            # 如果不等待，直接返回
            if not wait:
                return None

            # 检查超时
            if time.time() - start_time > timeout:
                logger.error(f"✗ 等待可用服务器超时（{timeout}秒）")
                return None

            # 等待一段时间再试
            time.sleep(1)

    def acquire_server(self, task_name: str, wait: bool = True) -> Optional[APIServer]:
        """
        获取并分配任务到服务器

        Args:
            task_name: 任务名称
            wait: 是否等待可用服务器

        Returns:
            已分配任务的服务器
        """
        server = self.get_available_server(wait=wait)
        if server:
            with self.lock:
                server.add_task(task_name)
                logger.debug(f"🔒 分配任务到服务器 {server.name}: {task_name}")
        return server

    def release_server(self, server: APIServer, task_name: str, success: bool = True):
        """
        从服务器移除任务

        Args:
            server: 服务器
            task_name: 任务名称
            success: 任务是否成功
        """
        with self.lock:
            if success:
                server.mark_success()
            else:
                server.mark_failure()

            server.remove_task(task_name)
            logger.debug(f"🔓 服务器 {server.name} 完成任务: {task_name} (成功率: {server.get_success_rate():.1%})")

    def get_max_workers(self) -> int:
        """
        获取最大并发数

        Returns:
            所有健康主服务器的并发容量总和
        """
        with self.lock:
            total_capacity = sum(s.concurrency_limit for s in self.primary_servers if s.is_healthy)
            return max(1, total_capacity)  # 至少返回1

    def get_status(self) -> Dict:
        """获取服务器池状态"""
        with self.lock:
            return {
                'primary_servers': [
                    {
                        'name': s.name,
                        'healthy': s.is_healthy,
                        'concurrency_limit': s.concurrency_limit,
                        'current_tasks_count': len(s.current_tasks),
                        'current_tasks': s.current_tasks,
                        'load': f"{len(s.current_tasks)}/{s.concurrency_limit}",
                        'success_rate': f"{s.get_success_rate():.1%}",
                        'total_requests': s.total_requests
                    }
                    for s in self.primary_servers
                ],
                'backup_servers': [
                    {
                        'name': s.name,
                        'healthy': s.is_healthy,
                        'concurrency_limit': s.concurrency_limit,
                        'current_tasks_count': len(s.current_tasks),
                        'current_tasks': s.current_tasks,
                        'load': f"{len(s.current_tasks)}/{s.concurrency_limit}",
                        'success_rate': f"{s.get_success_rate():.1%}",
                        'total_requests': s.total_requests
                    }
                    for s in self.backup_servers
                ],
                'max_workers': self.get_max_workers()
            }

    def print_status(self):
        """打印服务器池状态"""
        status = self.get_status()

        print(f"\n{'=' * 80}")
        print(f"📊 服务器池状态 (总并发容量: {status['max_workers']})")
        print(f"{'=' * 80}\n")

        # 主服务器
        print("主服务器:")
        print(f"{'名称':<12} {'健康':<6} {'负载':<10} {'成功率':<10} {'总请求':<10} {'当前任务':<30}")
        print("-" * 80)
        for s in status['primary_servers']:
            health_text = "✓" if s['healthy'] else "✗"
            load_icon = "🟢" if s['current_tasks_count'] == 0 else "🟡" if s['current_tasks_count'] < s['concurrency_limit'] else "🔴"
            tasks_text = ', '.join(s['current_tasks'][:2]) if s['current_tasks'] else '-'
            if len(s['current_tasks']) > 2:
                tasks_text += f" +{len(s['current_tasks'])-2}..."
            print(f"{s['name']:<12} {health_text:<6} {load_icon} {s['load']:<8} {s['success_rate']:<10} {s['total_requests']:<10} {tasks_text:<30}")

        # 备用服务器
        if status['backup_servers']:
            print("\n备用服务器:")
            print(f"{'名称':<12} {'健康':<6} {'负载':<10} {'成功率':<10} {'总请求':<10} {'当前任务':<30}")
            print("-" * 80)
            for s in status['backup_servers']:
                health_text = "✓" if s['healthy'] else "✗"
                load_icon = "🟢" if s['current_tasks_count'] == 0 else "🟡" if s['current_tasks_count'] < s['concurrency_limit'] else "🔴"
                tasks_text = ', '.join(s['current_tasks'][:2]) if s['current_tasks'] else '-'
                if len(s['current_tasks']) > 2:
                    tasks_text += f" +{len(s['current_tasks'])-2}..."
                print(f"{s['name']:<12} {health_text:<6} {load_icon} {s['load']:<8} {s['success_rate']:<10} {s['total_requests']:<10} {tasks_text:<30}")

        print(f"\n💡 说明: 🟢=空闲 🟡=部分负载 🔴=满载")
        print(f"{'=' * 80}\n")
