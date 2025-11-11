#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化执行统计模块

功能: 记录每次自动化执行的成果
  - 处理的任务数
  - 关注数
  - 点赞数
  - 收藏数
  - 评论数
  - 执行时间
  - 成功率

使用场景:
  自动化启动时记录开始时间和任务数
  自动化结束时统计完成的操作
  生成执行报告
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import InteractionTask, InteractionLog
from sqlalchemy import func


class AutomationExecutionStats:
    """自动化执行统计类"""

    def __init__(self, automation_mode: str, device_ids: list = None):
        """
        初始化统计

        Args:
            automation_mode: 自动化模式 ('realtime', 'recent', 'long_term', 'mixed')
            device_ids: 设备 ID 列表 (可选)
        """
        self.db = DatabaseManager()
        self.automation_mode = automation_mode
        self.device_ids = device_ids or []

        # 记录统计时间戳
        self.start_time = datetime.now()
        self.end_time = None

        # 记录执行前的状态
        self.start_stats = self._get_current_stats()

    def _get_current_stats(self) -> Dict[str, int]:
        """获取当前的操作统计"""
        with self.db.session_scope() as session:
            stats = {}

            # 统计各种操作
            for action in ['follow', 'like', 'comment', 'collect']:
                count = session.query(func.count(InteractionLog.id)).filter(
                    InteractionLog.action == action,
                    InteractionLog.status == 'success'
                ).scalar() or 0
                stats[f'total_{action}'] = count

            # 按自动化模式统计
            if self.automation_mode == 'realtime':
                task_types = ['realtime']
            elif self.automation_mode == 'recent':
                task_types = ['history_recent']
            elif self.automation_mode == 'long_term':
                task_types = ['history_old']
            elif self.automation_mode == 'mixed':
                task_types = ['realtime', 'history_recent']
            else:
                task_types = []

            # 统计各模式的任务完成数
            for action in ['follow', 'like', 'comment', 'collect']:
                count = session.query(func.count(InteractionLog.id)).filter(
                    InteractionLog.action == action,
                    InteractionLog.status == 'success',
                    InteractionTask.task_type.in_(task_types)
                ).join(
                    InteractionTask,
                    InteractionLog.task_id == InteractionTask.id
                ).scalar() or 0
                stats[f'mode_{action}'] = count

            return stats

    def finish_execution(self):
        """完成执行，生成报告"""
        self.end_time = datetime.now()
        self._generate_report()

    def _generate_report(self) -> Dict[str, Any]:
        """生成执行报告"""
        end_stats = self._get_current_stats()

        # 计算增量
        delta_stats = {}
        for key in self.start_stats:
            delta_stats[key] = end_stats[key] - self.start_stats[key]

        # 计算耗时
        duration = (self.end_time - self.start_time).total_seconds()

        # 统计任务完成情况
        with self.db.session_scope() as session:
            # 确定任务类型
            if self.automation_mode == 'realtime':
                task_types = ['realtime']
            elif self.automation_mode == 'recent':
                task_types = ['history_recent']
            elif self.automation_mode == 'long_term':
                task_types = ['history_old']
            elif self.automation_mode == 'mixed':
                task_types = ['realtime', 'history_recent']
            else:
                task_types = []

            # 统计完成的任务
            completed_tasks = session.query(func.count(InteractionTask.id)).filter(
                InteractionTask.task_type.in_(task_types),
                InteractionTask.status.in_(['completed', 'assigned', 'skipped'])
            ).scalar() or 0

        # 构建报告
        report = {
            'automation_mode': self.automation_mode,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S'),
            'duration_seconds': duration,
            'duration_display': self._format_duration(duration),
            'completed_tasks': completed_tasks,
            'operations': {
                'follow': delta_stats.get('mode_follow', 0),
                'like': delta_stats.get('mode_like', 0),
                'collect': delta_stats.get('mode_collect', 0),
                'comment': delta_stats.get('mode_comment', 0),
            },
            'totals': {
                'follow': end_stats.get('mode_follow', 0),
                'like': end_stats.get('mode_like', 0),
                'collect': end_stats.get('mode_collect', 0),
                'comment': end_stats.get('mode_comment', 0),
            }
        }

        return report

    def _format_duration(self, seconds: float) -> str:
        """格式化耗时"""
        if seconds < 60:
            return f"{int(seconds)}秒"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}分{secs}秒"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}小时{minutes}分"

    def print_report(self):
        """打印执行报告"""
        report = self._generate_report()

        print('\n' + '='*70)
        print('📊 自动化执行统计报告')
        print('='*70)

        print(f'\n【执行信息】')
        print(f'  自动化模式: {self._mode_display(report["automation_mode"])}')
        print(f'  开始时间: {report["start_time"]}')
        print(f'  结束时间: {report["end_time"]}')
        print(f'  耗时: {report["duration_display"]}')

        print(f'\n【任务统计】')
        print(f'  本次处理任务: {report["completed_tasks"]} 个')

        print(f'\n【操作统计】')
        print(f'  本次关注数: {report["operations"]["follow"]}')
        print(f'  本次点赞数: {report["operations"]["like"]}')
        print(f'  本次收藏数: {report["operations"]["collect"]}')
        if self.automation_mode in ['realtime', 'mixed']:
            print(f'  本次评论数: {report["operations"]["comment"]}')

        print(f'\n【累计统计】')
        print(f'  总关注数: {report["totals"]["follow"]}')
        print(f'  总点赞数: {report["totals"]["like"]}')
        print(f'  总收藏数: {report["totals"]["collect"]}')
        if self.automation_mode in ['realtime', 'mixed']:
            print(f'  总评论数: {report["totals"]["comment"]}')

        print(f'\n{"="*70}\n')

    @staticmethod
    def _mode_display(mode: str) -> str:
        """获取模式的显示名称"""
        modes = {
            'realtime': '实时自动化 (realtime)',
            'recent': '近期自动化 (3个月内)',
            'long_term': '长期自动化 (3个月前)',
            'mixed': '混合自动化 (实时+近期)',
        }
        return modes.get(mode, mode)


def create_execution_log(automation_mode: str, result: Dict[str, Any]):
    """
    创建执行日志记录

    Args:
        automation_mode: 自动化模式
        result: 执行结果字典
    """
    db = DatabaseManager()

    # 可以在此处添加日志表的记录
    # 暂时打印到控制台
    pass


if __name__ == '__main__':
    # 测试示例
    stats = AutomationExecutionStats('realtime')

    # 模拟执行（实际使用时由自动化脚本调用）
    import time
    time.sleep(2)

    stats.finish_execution()
    stats.print_report()
