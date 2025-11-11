"""
任务生成器 - 根据爬取的评论生成互动任务
"""

import logging
import json
from typing import List, Dict
from datetime import datetime

from ..database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class TaskGenerator:
    """任务生成器"""

    def __init__(self, db_manager: DatabaseManager):
        """初始化任务生成器

        Args:
            db_manager: 数据库管理器
        """
        self.db = db_manager
        logger.info("✓ 任务生成器初始化完成")

    def generate_realtime_tasks(self, target_account, comments: List[Dict]) -> List:
        """为版本1（实时监控）生成任务

        Args:
            target_account: TargetAccount 对象
            comments: 评论列表

        Returns:
            生成的任务列表
        """
        if not comments:
            logger.info("没有评论需要生成任务")
            return []

        logger.info(f"为 {target_account.account_name} 生成实时任务")

        # 去重：同一个用户只保留一条评论
        unique_users = self._dedup_users(comments)
        logger.info(f"去重后剩余 {len(unique_users)} 个用户")

        # 生成任务
        tasks = []

        for comment in unique_users:
            try:
                # 检查是否已经存在该用户的任务
                existing_tasks = self.db.get_interaction_tasks(status=None, limit=1000)
                user_exists = any(
                    t.comment_user_id == comment['user']['sec_uid']
                    for t in existing_tasks
                )

                if user_exists:
                    logger.debug(f"用户 {comment['user']['nickname']} 已存在任务，跳过")
                    continue

                # 创建任务
                task = self.db.create_task(
                    target_account_id=target_account.id,
                    comment_user_id=comment['user']['sec_uid'],
                    comment_user_name=comment['user']['nickname'],
                    video_id=comment.get('video_id', ''),
                    comment_id=comment.get('comment_id', ''),
                    task_type='realtime',
                    actions={
                        'like': True,
                        'comment': True,
                        'follow': True,
                        'dm': False
                    }
                )

                tasks.append(task)
                logger.debug(f"✓ 生成任务: {comment['user']['nickname']}")

            except Exception as e:
                logger.error(f"生成任务失败: {e}")
                continue

        logger.info(f"✓ 共生成 {len(tasks)} 个任务")
        return tasks

    def generate_batch_tasks(self, target_account, comments: List[Dict], daily_limit: int = 50) -> List:
        """为版本2（批量处理）生成任务

        Args:
            target_account: TargetAccount 对象
            comments: 评论列表
            daily_limit: 每天处理的用户数

        Returns:
            生成的任务列表
        """
        if not comments:
            logger.info("没有评论需要生成任务")
            return []

        logger.info(f"为 {target_account.account_name} 生成批量任务（限制 {daily_limit} 个）")

        # 去重：同一个用户只保留一条评论
        unique_users = self._dedup_users(comments)
        logger.info(f"去重后剩余 {len(unique_users)} 个用户")

        # 优先级排序
        prioritized = self._prioritize_comments(unique_users)

        # 只取前 daily_limit 个
        selected = prioritized[:daily_limit]
        logger.info(f"根据优先级选择 {len(selected)} 个用户")

        # 生成任务
        tasks = []

        for comment in selected:
            try:
                # 检查是否已经存在该用户的任务
                existing_tasks = self.db.get_interaction_tasks(status=None, limit=10000)
                user_exists = any(
                    t.comment_user_id == comment['user']['sec_uid']
                    for t in existing_tasks
                )

                if user_exists:
                    logger.debug(f"用户 {comment['user']['nickname']} 已存在任务，跳过")
                    continue

                # 创建任务
                task = self.db.create_task(
                    target_account_id=target_account.id,
                    comment_user_id=comment['user']['sec_uid'],
                    comment_user_name=comment['user']['nickname'],
                    video_id=comment.get('video_id', ''),
                    comment_id=comment.get('comment_id', ''),
                    task_type='batch',
                    actions={
                        'like': True,
                        'comment': True,
                        'follow': True,
                        'dm': False
                    }
                )

                tasks.append(task)
                logger.debug(f"✓ 生成任务: {comment['user']['nickname']}")

            except Exception as e:
                logger.error(f"生成任务失败: {e}")
                continue

        logger.info(f"✓ 共生成 {len(tasks)} 个任务")

        # 更新批量处理进度
        if tasks:
            last_video_id = comments[0].get('video_id', '') if comments else ''
            self.db.update_batch_progress(
                target_account.id,
                last_video_id,
                videos_count=0,
                comments_count=len(comments),
                tasks_count=len(tasks)
            )

        return tasks

    def _dedup_users(self, comments: List[Dict]) -> List[Dict]:
        """去重评论用户

        Args:
            comments: 评论列表

        Returns:
            去重后的评论列表
        """
        seen_users = set()
        unique_comments = []

        for comment in comments:
            user_id = comment.get('user', {}).get('sec_uid', '')

            if user_id and user_id not in seen_users:
                seen_users.add(user_id)
                unique_comments.append(comment)

        return unique_comments

    def _prioritize_comments(self, comments: List[Dict]) -> List[Dict]:
        """评论优先级排序

        按以下优先级排序：
        1. 点赞数（降序）
        2. 回复数（降序）
        3. 发布时间（升序，前面的评论优先）

        Args:
            comments: 评论列表

        Returns:
            排序后的评论列表
        """
        def sort_key(comment):
            # 点赞数（越多越优先，所以取负数）
            digg_count = -comment.get('digg_count', 0)

            # 回复数（越多越优先，所以取负数）
            reply_count = -comment.get('reply_count', 0)

            # 发布时间（越早越优先，所以不取负数）
            create_time = comment.get('create_time', 0)

            return (digg_count, reply_count, create_time)

        sorted_comments = sorted(comments, key=sort_key)
        return sorted_comments

    def filter_by_criteria(self, comments: List[Dict], min_digg_count: int = 0,
                          min_reply_count: int = 0) -> List[Dict]:
        """根据条件筛选评论

        Args:
            comments: 评论列表
            min_digg_count: 最小点赞数
            min_reply_count: 最小回复数

        Returns:
            筛选后的评论列表
        """
        filtered = []

        for comment in comments:
            digg_count = comment.get('digg_count', 0)
            reply_count = comment.get('reply_count', 0)

            if digg_count >= min_digg_count and reply_count >= min_reply_count:
                filtered.append(comment)

        logger.info(f"筛选条件: 点赞≥{min_digg_count}, 回复≥{min_reply_count}")
        logger.info(f"筛选结果: {len(filtered)}/{len(comments)} 条评论符合条件")

        return filtered

    def generate_tasks_for_multiple_accounts(self, target_accounts: List,
                                            comments_map: Dict[int, List[Dict]],
                                            task_type: str = 'realtime',
                                            daily_limit: int = 50) -> Dict[int, List]:
        """为多个目标账号批量生成任务

        Args:
            target_accounts: 目标账号列表
            comments_map: {account_id: [comments]} 字典
            task_type: 任务类型（realtime 或 batch）
            daily_limit: 每天处理的用户数（仅批量模式）

        Returns:
            {account_id: [tasks]} 字典
        """
        result = {}

        for account in target_accounts:
            comments = comments_map.get(account.id, [])

            if not comments:
                logger.info(f"账号 {account.account_name} 没有评论")
                continue

            if task_type == 'realtime':
                tasks = self.generate_realtime_tasks(account, comments)
            else:  # batch
                tasks = self.generate_batch_tasks(account, comments, daily_limit)

            result[account.id] = tasks

        total_tasks = sum(len(tasks) for tasks in result.values())
        logger.info(f"\n总计为 {len(target_accounts)} 个账号生成 {total_tasks} 个任务")

        return result

    def clean_expired_tasks(self, days: int = 7):
        """清理过期的任务

        Args:
            days: 保留最近多少天的任务
        """
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=days)
        logger.info(f"清理 {cutoff_date.strftime('%Y-%m-%d')} 之前的任务")

        # 这里需要在 DatabaseManager 中添加相应的方法
        # self.db.delete_tasks_before(cutoff_date)

        logger.info("✓ 任务清理完成")

    def get_task_statistics(self) -> Dict:
        """获取任务统计信息

        Returns:
            统计信息字典
        """
        stats = self.db.get_task_stats()

        return {
            'total': stats['total'],
            'pending': stats['pending'],
            'in_progress': stats['in_progress'],
            'completed': stats['completed'],
            'failed': stats['failed'],
            'success_rate': f"{stats['completed'] / stats['total'] * 100:.1f}%" if stats['total'] > 0 else "0%"
        }
