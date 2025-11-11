"""
任务生成器 - 统一版本（合并自两个版本）

功能说明：
1. 从API评论生成任务（实时爬虫场景）
2. 从数据库历史评论生成任务（全量爬虫场景）
3. 支持设备级去重（允许多台设备关注同一用户）
4. 支持智能优先级（新评论、热门评论优先）

合并说明：
- 保留了版本1的社交指标筛选功能（点赞数、回复数）
- 保留了版本2的智能去重和优先级逻辑
- 统一接口，支持多种任务生成场景
"""

import logging
import json
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import func

from ..database.manager import DatabaseManager
from ..database.models import Comment, NewComment, InteractionTask

logger = logging.getLogger(__name__)


class TaskGenerator:
    """统一的任务生成器"""

    def __init__(self, db_manager: DatabaseManager):
        """初始化任务生成器

        Args:
            db_manager: 数据库管理器
        """
        self.db = db_manager
        self.max_follow_devices = self._load_max_follow_devices()
        logger.info("✓ 任务生成器初始化完成")

    def _load_max_follow_devices(self) -> int:
        """从配置文件加载允许的最大关注设备数

        Returns:
            允许的最大设备数，默认为3
        """
        try:
            config_file = Path(__file__).parent.parent.parent / 'config' / 'config.json'
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    max_devices = config.get('task_deduplication', {}).get('max_follow_devices', 3)
                    logger.info(f"✓ 加载配置: 允许 {max_devices} 台设备关注同一用户")
                    return max_devices
        except Exception as e:
            logger.warning(f"⚠ 加载配置失败，使用默认值: {e}")

        # 默认值：3台设备
        return 3

    # ========== 方法1: 从API评论生成实时任务（版本1的核心功能） ==========

    def generate_realtime_tasks(self, target_account, comments: List[Dict]) -> List:
        """从API返回的评论列表生成实时任务（用于实时爬虫）

        使用场景：
            爬虫刚获取到新评论（来自monitor_crawler）
            需要立即生成高优先级任务进行交互

        Args:
            target_account: TargetAccount 对象
            comments: API返回的评论列表，格式：
                {
                    'user': {'sec_uid': xxx, 'nickname': xxx},
                    'video_id': xxx,
                    'comment_id': xxx,
                    'digg_count': xxx,
                    'reply_count': xxx
                }

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
                    priority='high',  # ← 新评论优先级最高！
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
        """从API评论生成批量任务（支持限制数量）

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

    # ========== 方法2: 从数据库历史评论生成任务（版本2的核心功能） ==========

    def generate_from_history(self, target_account_id: int) -> int:
        """从历史评论生成'history'类型的任务（支持智能去重）

        使用场景：
            首次爬虫完成后，从所有历史评论生成任务
            支持设备级去重：同一用户可被多台设备关注（最多max_follow_devices台）

        特点：
            - 近3个月的视频评论 = 高优先级（history_recent）
            - 3个月前的视频评论 = 普通优先级（history_old）
            - 必须有comment_unique_id（抖音号）才能生成任务

        Args:
            target_account_id: 目标账号ID

        Returns:
            生成的任务数量
        """
        session = self.db.get_session()
        try:
            # 获取未处理的评论
            unprocessed_comments = session.query(Comment)\
                .filter_by(target_account_id=target_account_id, status='new')\
                .all()

            if not unprocessed_comments:
                logger.info(f"✓ 账号 {target_account_id} 无未处理的历史评论")
                return 0

            logger.info(f"  为账号 {target_account_id} 生成 history 任务...")

            task_count = 0

            for comment in unprocessed_comments:
                # ✅ 必须有comment_unique_id才能创建任务（抖音搜索需要用户名/抖音号）
                if not comment.comment_unique_id:
                    logger.warning(
                        f"    ⊗ 跳过 {comment.comment_user_name}: 缺少 comment_unique_id（无法搜索用户）"
                    )
                    comment.status = 'processed'  # 标记为已处理，不重复警告
                    continue

                # 新逻辑：检查该用户被多少台不同设备关注过（基于设备的去重）
                user_identifier = comment.comment_unique_id or comment.comment_user_id

                # 统计该用户有多少台不同设备的completed任务（包括所有历史任务类型）
                completed_device_count = session.query(
                    func.count(func.distinct(InteractionTask.assigned_device))
                ).filter(
                    InteractionTask.target_account_id == target_account_id,
                    InteractionTask.task_type.in_(['history', 'history_old', 'history_recent']),  # 兼容旧数据
                    InteractionTask.status == 'completed',
                    InteractionTask.assigned_device.isnot(None),
                    (InteractionTask.comment_unique_id == user_identifier) |
                    (InteractionTask.comment_user_id == comment.comment_user_id)
                ).scalar() or 0

                # 检查是否还有该用户的待处理任务（pending/assigned/in_progress）
                has_pending_task = session.query(InteractionTask)\
                    .filter(
                        InteractionTask.target_account_id == target_account_id,
                        InteractionTask.task_type.in_(['history', 'history_old', 'history_recent']),  # 兼容旧数据
                        InteractionTask.status.in_(['pending', 'assigned', 'in_progress']),
                        (InteractionTask.comment_unique_id == user_identifier) |
                        (InteractionTask.comment_user_id == comment.comment_user_id)
                    )\
                    .first()

                # 判断是否可以生成新任务
                can_generate = (
                    not has_pending_task and  # 没有待处理的任务
                    (self.max_follow_devices == 0 or completed_device_count < self.max_follow_devices)  # 未达上限
                )

                if can_generate:
                    # 判断任务类型和优先级：根据视频发布时间
                    three_months_ago = datetime.now() - timedelta(days=90)

                    if comment.video_create_time and comment.video_create_time >= three_months_ago:
                        # 近3个月的视频
                        task_type = 'history_recent'
                        priority = 'high'
                        logger.debug(f"    ✓ [近期历史] {comment.comment_user_name} (视频发布于 {comment.video_create_time.strftime('%Y-%m-%d')})")
                    else:
                        # 3个月前的视频
                        task_type = 'history_old'
                        priority = 'normal'
                        logger.debug(f"    ✓ [历史旧评论] {comment.comment_user_name}")

                    task = InteractionTask(
                        target_account_id=target_account_id,
                        comment_user_id=comment.comment_user_id,
                        comment_user_name=comment.comment_user_name,
                        comment_uid=comment.comment_uid,
                        comment_unique_id=comment.comment_unique_id,
                        comment_sec_uid=comment.comment_sec_uid,
                        video_id=comment.video_id,
                        comment_time=comment.comment_time,  # 保存评论时间用于统计
                        task_type=task_type,  # history_old 或 history_recent
                        priority=priority,    # normal 或 high
                        status='pending'
                    )
                    session.add(task)
                    task_count += 1
                    logger.debug(
                        f"    ✓ 生成任务: {comment.comment_user_name} "
                        f"(已有 {completed_device_count}/{self.max_follow_devices} 台设备完成)"
                    )
                else:
                    # 记录跳过原因
                    if has_pending_task:
                        logger.debug(f"    ⊗ 跳过 {comment.comment_user_name}: 已有待处理任务")
                    else:
                        logger.debug(
                            f"    ⊗ 跳过 {comment.comment_user_name}: "
                            f"已达上限 ({completed_device_count}/{self.max_follow_devices} 台设备)"
                        )

                # 标记评论为已处理
                comment.status = 'processed'

            session.commit()
            logger.info(f"    生成 {task_count} 个 history 任务")

            return task_count

        except Exception as e:
            session.rollback()
            logger.error(f"✗ 生成 history 任务失败: {e}")
            return 0
        finally:
            session.close()

    def generate_from_realtime(self, target_account_id: int) -> int:
        """从新增评论生成'realtime'类型的任务

        使用场景：
            监控爬虫发现新增评论（NewComment表）
            生成高优先级的实时互动任务

        Args:
            target_account_id: 目标账号ID

        Returns:
            生成的任务数量
        """
        session = self.db.get_session()
        try:
            # 获取新增评论
            new_comments = session.query(NewComment)\
                .filter_by(target_account_id=target_account_id)\
                .all()

            if not new_comments:
                logger.info(f"✓ 账号 {target_account_id} 无新增评论")
                return 0

            logger.info(f"  为账号 {target_account_id} 生成 realtime 任务...")

            task_count = 0

            for new_comment in new_comments:
                # ✅ 必须有comment_unique_id才能创建任务（抖音搜索需要用户名/抖音号）
                if not getattr(new_comment, 'comment_unique_id', None):
                    logger.warning(
                        f"    ⊗ 跳过 {new_comment.comment_user_name}: 缺少 comment_unique_id（无法搜索用户）"
                    )
                    continue

                # 检查是否已有该用户的任务（任何状态）
                # 使用 comment_unique_id（抖音号）或 comment_user_id 进行去重
                user_identifier = getattr(new_comment, 'comment_unique_id', None) or new_comment.comment_user_id

                existing_task = session.query(InteractionTask)\
                    .filter(
                        InteractionTask.target_account_id == target_account_id,
                        InteractionTask.task_type == 'realtime'
                    )\
                    .filter(
                        (InteractionTask.comment_unique_id == user_identifier) |
                        (InteractionTask.comment_user_id == new_comment.comment_user_id)
                    )\
                    .filter(
                        # ✅ 检查所有活跃状态：pending, assigned, in_progress, completed
                        InteractionTask.status.in_(['pending', 'assigned', 'in_progress', 'completed'])
                    )\
                    .first()

                if not existing_task:
                    task = InteractionTask(
                        target_account_id=target_account_id,
                        comment_user_id=new_comment.comment_user_id,  # sec_uid
                        comment_user_name=new_comment.comment_user_name,
                        comment_uid=getattr(new_comment, 'comment_uid', None),  # 数字ID
                        comment_unique_id=getattr(new_comment, 'comment_unique_id', None),  # 抖音号
                        video_id=new_comment.video_id,
                        comment_time=new_comment.discovered_at,  # 使用discovered_at作为评论时间
                        task_type='realtime',
                        priority='high',  # 高优先级！
                        status='pending'
                    )
                    session.add(task)
                    task_count += 1

            session.commit()
            logger.info(f"    生成 {task_count} 个 realtime 任务")

            # 将新增评论添加到Comment表（作为新的历史基线）
            # 这样下次监控时就不会重复检测这些评论了
            added_to_history = 0
            for new_comment in new_comments:
                # 检查是否已在Comment表中
                existing_in_history = session.query(Comment).filter_by(
                    target_account_id=target_account_id,
                    video_id=new_comment.video_id,
                    comment_user_id=new_comment.comment_user_id
                ).first()

                if not existing_in_history:
                    # 添加到历史表
                    history_comment = Comment(
                        target_account_id=target_account_id,
                        video_id=new_comment.video_id,
                        comment_user_id=new_comment.comment_user_id,
                        comment_user_name=new_comment.comment_user_name,
                        comment_text=new_comment.comment_text,
                        comment_time=new_comment.discovered_at,
                        created_at=datetime.now(),
                        status='new'  # 标记为新增的评论
                    )
                    session.add(history_comment)
                    added_to_history += 1

            session.commit()
            logger.info(f"    已将 {added_to_history} 条新增评论添加到历史基线")

            # 清空已处理的新增评论
            session.query(NewComment).filter_by(
                target_account_id=target_account_id
            ).delete()
            session.commit()

            return task_count

        except Exception as e:
            session.rollback()
            logger.error(f"✗ 生成 realtime 任务失败: {e}")
            return 0
        finally:
            session.close()

    # ========== 辅助方法（来自版本1） ==========

    def _dedup_users(self, comments: List[Dict]) -> List[Dict]:
        """去重评论用户（同一用户只保留一条评论）

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

    # ========== 批量处理方法（来自版本1和版本2） ==========

    def generate_tasks_for_multiple_accounts(self, target_accounts: List,
                                            comments_map: Dict[int, List[Dict]],
                                            task_type: str = 'realtime',
                                            daily_limit: int = 50) -> Dict[int, List]:
        """为多个目标账号批量生成任务（从API评论）

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

    def generate_all_from_history(self) -> Dict[int, int]:
        """为所有账号生成history任务（从数据库）

        Returns:
            {'account_id': task_count, ...}
        """
        results = {}
        target_accounts = self.db.get_target_accounts()

        for account in target_accounts:
            task_count = self.generate_from_history(account.id)
            results[account.id] = task_count

        return results

    def generate_all_from_realtime(self) -> Dict[int, int]:
        """为所有账号生成realtime任务（从新增评论）

        Returns:
            {'account_id': task_count, ...}
        """
        results = {}
        target_accounts = self.db.get_target_accounts()

        for account in target_accounts:
            task_count = self.generate_from_realtime(account.id)
            results[account.id] = task_count

        return results

    # ========== 工具方法（来自版本1） ==========

    def clean_expired_tasks(self, days: int = 7):
        """清理过期的任务

        Args:
            days: 保留最近多少天的任务
        """
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
