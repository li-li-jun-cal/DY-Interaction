"""
互动统计模块 - 从已完成的互动任务统计

统计数据来源：InteractionLog 表（记录实际执行的操作）
统计内容：
  - 关注数：follow 操作成功数
  - 点赞数：like 操作成功数
  - 评论数：comment 操作成功数
  - 收藏数：collect 操作成功数

统计维度：
  1. 总体统计：所有已完成的操作
  2. 按任务类型统计：realtime vs 长期(history_recent + history_old)
  3. 按时间统计：今日 vs 历史累计
"""

from datetime import datetime, timedelta
from sqlalchemy import func
from src.database.models import InteractionTask, InteractionLog
from typing import Dict, Any


class InteractionStatsCollector:
    """互动统计收集器"""

    def __init__(self, db_session):
        """
        初始化统计收集器

        Args:
            db_session: 数据库会话
        """
        self.session = db_session

    def get_total_stats(self) -> Dict[str, int]:
        """
        获取总体统计（所有时间）

        Returns:
            {
                'follow': int,      # 总关注数
                'like': int,        # 总点赞数
                'comment': int,     # 总评论数
                'collect': int      # 总收藏数
            }
        """
        stats = {}
        actions = ['follow', 'like', 'comment', 'collect']

        for action in actions:
            count = self.session.query(func.count(InteractionLog.id)).filter(
                InteractionLog.action == action,
                InteractionLog.status == 'success'
            ).scalar() or 0
            stats[action] = count

        return stats

    def get_today_stats(self) -> Dict[str, int]:
        """
        获取今日统计

        Returns:
            {
                'follow': int,      # 今日关注数
                'like': int,        # 今日点赞数
                'comment': int,     # 今日评论数
                'collect': int      # 今日收藏数
            }
        """
        today = datetime.now().date()
        stats = {}
        actions = ['follow', 'like', 'comment', 'collect']

        for action in actions:
            count = self.session.query(func.count(InteractionLog.id)).filter(
                InteractionLog.action == action,
                InteractionLog.status == 'success',
                func.date(InteractionLog.created_at) == today
            ).scalar() or 0
            stats[action] = count

        return stats

    def get_stats_by_task_type(self, task_type: str) -> Dict[str, int]:
        """
        获取指定任务类型的统计

        Args:
            task_type: 任务类型 ('realtime' 或其他)

        Returns:
            {
                'follow': int,
                'like': int,
                'comment': int,
                'collect': int
            }
        """
        stats = {}
        actions = ['follow', 'like', 'comment', 'collect']

        for action in actions:
            count = self.session.query(func.count(InteractionLog.id)).filter(
                InteractionLog.action == action,
                InteractionLog.status == 'success',
                InteractionTask.task_type == task_type
            ).join(InteractionTask, InteractionLog.task_id == InteractionTask.id).scalar() or 0
            stats[action] = count

        return stats

    def get_realtime_stats(self) -> Dict[str, int]:
        """
        获取实时自动化统计（realtime任务）
        实时自动化包括：关注、点赞、收藏、评论

        Returns:
            {
                'follow': int,
                'like': int,
                'comment': int,
                'collect': int
            }
        """
        return self.get_stats_by_task_type('realtime')

    def get_longterm_stats(self) -> Dict[str, int]:
        """
        获取长期自动化统计（history_recent + history_old任务）
        长期自动化包括：关注、点赞、收藏（不包括评论）

        Returns:
            {
                'follow': int,
                'like': int,
                'collect': int
            }
        """
        stats = {}
        actions = ['follow', 'like', 'collect']  # 不包括 comment

        for action in actions:
            count = self.session.query(func.count(InteractionLog.id)).filter(
                InteractionLog.action == action,
                InteractionLog.status == 'success',
                InteractionTask.task_type.in_(['history_recent', 'history_old'])
            ).join(InteractionTask, InteractionLog.task_id == InteractionTask.id).scalar() or 0
            stats[action] = count

        return stats

    def get_detailed_report(self) -> Dict[str, Any]:
        """
        获取详细统计报告

        Returns:
            {
                'total': {
                    'follow': int,
                    'like': int,
                    'comment': int,
                    'collect': int
                },
                'today': {
                    'follow': int,
                    'like': int,
                    'comment': int,
                    'collect': int
                },
                'realtime': {
                    'follow': int,
                    'like': int,
                    'comment': int,
                    'collect': int
                },
                'longterm': {
                    'follow': int,
                    'like': int,
                    'collect': int
                }
            }
        """
        return {
            'total': self.get_total_stats(),
            'today': self.get_today_stats(),
            'realtime': self.get_realtime_stats(),
            'longterm': self.get_longterm_stats()
        }

    def print_stats(self):
        """打印统计信息"""
        report = self.get_detailed_report()

        print('='*70)
        print('📊 互动操作统计')
        print('='*70)
        print()

        # 总体统计
        print('【总体统计 (历史累计)】')
        total = report['total']
        print(f'  关注数: {total.get("follow", 0)}')
        print(f'  点赞数: {total.get("like", 0)}')
        print(f'  评论数: {total.get("comment", 0)}')
        print(f'  收藏数: {total.get("collect", 0)}')
        print()

        # 今日统计
        print('【今日统计】')
        today = report['today']
        print(f'  今日关注: {today.get("follow", 0)}')
        print(f'  今日点赞: {today.get("like", 0)}')
        print(f'  今日评论: {today.get("comment", 0)}')
        print(f'  今日收藏: {today.get("collect", 0)}')
        print()

        # 按自动化模式统计
        print('【按自动化模式统计】')
        realtime = report['realtime']
        longterm = report['longterm']
        print(f'  实时自动化(realtime):')
        print(f'    ├─ 关注: {realtime.get("follow", 0)}')
        print(f'    ├─ 点赞: {realtime.get("like", 0)}')
        print(f'    ├─ 收藏: {realtime.get("collect", 0)}')
        print(f'    └─ 评论: {realtime.get("comment", 0)}')
        print(f'  长期自动化(history_recent + history_old):')
        print(f'    ├─ 关注: {longterm.get("follow", 0)}')
        print(f'    ├─ 点赞: {longterm.get("like", 0)}')
        print(f'    └─ 收藏: {longterm.get("collect", 0)}')
        print()
        print('='*70)
