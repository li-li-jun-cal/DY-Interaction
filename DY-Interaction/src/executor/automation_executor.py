"""
自动化执行器（简化版）- 支持历史和实时两种模式，支持每日配额管理
"""

import logging
import time
import random
from datetime import datetime, date
from src.executor.interaction_executor import InteractionExecutor
from src.executor.element_ids import DouyinElementIds
from src.database.manager import DatabaseManager
from src.database.models import InteractionTask, DeviceDailyStats
from src.config.daily_quota import DailyQuota

logger = logging.getLogger(__name__)


class AutomationExecutor:
    """自动化执行器 - 执行历史或实时任务"""

    def __init__(self, device_id, db_manager, daily_quota: DailyQuota = None):
        """初始化自动化执行器

        Args:
            device_id: 设备ID
            db_manager: 数据库管理器
            daily_quota: 每日配额配置（可选）
        """
        self.device_id = device_id
        self.db = db_manager
        self.daily_quota = daily_quota or DailyQuota()

        # 初始化交互执行器
        try:
            self.executor = InteractionExecutor(device_id, db_manager)
            logger.info(f"✓ 初始化自动化执行器: {device_id}")
            logger.info(f"  配额: {self.daily_quota.get_summary()}")
        except Exception as e:
            logger.error(f"✗ 初始化自动化执行器失败: {e}")
            self.executor = None

    def get_today_stats(self):
        """获取今日统计数据

        Returns:
            dict: {'follow': int, 'like': int, 'collect': int}
        """
        session = self.db.get_session()
        try:
            today = date.today()
            # 修复：使用日期范围查询，而不是直接比较
            today_start = datetime.combine(today, datetime.min.time())
            today_end = datetime.combine(today, datetime.max.time())

            stats = session.query(DeviceDailyStats).filter(
                DeviceDailyStats.device_id == self.device_id,
                DeviceDailyStats.date >= today_start,
                DeviceDailyStats.date <= today_end
            ).first()

            if not stats:
                # 创建今日统计（使用 datetime 对象）
                stats = DeviceDailyStats(
                    device_id=self.device_id,
                    date=today_start,  # 使用 datetime 对象
                    completed_tasks=0,
                    failed_tasks=0,
                    follow_count=0,
                    like_count=0,
                    collect_count=0
                )
                session.add(stats)
                session.commit()

            return {
                'follow': stats.follow_count or 0,
                'like': stats.like_count or 0,
                'collect': stats.collect_count or 0
            }
        finally:
            session.close()

    def update_action_count(self, action_type: str, count: int = 1):
        """更新操作计数

        Args:
            action_type: 'follow', 'like', 'collect'
            count: 增加数量
        """
        session = self.db.get_session()
        try:
            today = date.today()
            # 修复：使用日期范围查询，而不是直接比较
            today_start = datetime.combine(today, datetime.min.time())
            today_end = datetime.combine(today, datetime.max.time())

            stats = session.query(DeviceDailyStats).filter(
                DeviceDailyStats.device_id == self.device_id,
                DeviceDailyStats.date >= today_start,
                DeviceDailyStats.date <= today_end
            ).first()

            if not stats:
                # 创建今日统计（使用 datetime 对象）
                stats = DeviceDailyStats(
                    device_id=self.device_id,
                    date=today_start,  # 使用 datetime 对象
                    completed_tasks=0,
                    failed_tasks=0,
                    follow_count=0,
                    like_count=0,
                    collect_count=0
                )
                session.add(stats)

            # 确保字段不是 None
            if stats.follow_count is None:
                stats.follow_count = 0
            if stats.like_count is None:
                stats.like_count = 0
            if stats.collect_count is None:
                stats.collect_count = 0

            # 更新计数
            if action_type == 'follow':
                stats.follow_count += count
            elif action_type == 'like':
                stats.like_count += count
            elif action_type == 'collect':
                stats.collect_count += count

            session.commit()
        finally:
            session.close()

    def execute_history_task(self, task):
        """执行历史评论自动化（支持动态配额）

        流程:
        1. 搜索评论用户
        2. 进入用户主页
        3. 关注用户（检查配额）
        4. 点赞视频（检查配额）
        5. 收藏视频（检查配额）
        6. 返回主页

        Args:
            task: InteractionTask 对象

        Returns:
            True 成功，False 失败
        """
        session = self.db.get_session()
        try:
            logger.info(f"[{self.device_id}] 执行任务 #{task.id} (历史)")

            # 获取今日统计
            today_stats = self.get_today_stats()
            logger.debug(f"  今日统计: 关注={today_stats['follow']}, 点赞={today_stats['like']}, 收藏={today_stats['collect']}")

            # 标记为进行中
            task.status = 'in_progress'
            task.started_at = datetime.now()
            session.commit()

            # 步骤1: 搜索用户（优先使用抖音号 unique_id）
            search_id = task.comment_unique_id or task.comment_uid or task.comment_user_id
            logger.info(f"  [1/5] 搜索用户 {search_id}")
            if not self.executor.navigate_to_user(search_id):
                raise Exception("无法导航到用户")

            self._random_delay()

            # 步骤2: 关注用户（检查配额）
            should_follow = self.daily_quota.can_follow(today_stats['follow'])
            logger.info(f"  [2/5] 关注用户 ({'执行' if should_follow else '跳过-已达配额'})")

            if should_follow:
                follow_result = self.executor.follow_user()

                # 检查是否已关注
                if follow_result == 'already_followed':
                    logger.info("    用户已关注，直接返回主页进行下一轮")
                    self.executor.go_back_to_home_from_user_page()
                    task.status = 'completed'
                    task.completed_at = datetime.now()
                    session.commit()
                    logger.info(f"✓ 任务 #{task.id} 完成（已关注用户）")
                    return True
                elif follow_result:
                    # 关注成功，更新计数并记录日志
                    self.update_action_count('follow')
                    self.db.log_interaction(task.id, self.device_id, 'follow', 'success')
                    today_stats['follow'] += 1
                    logger.debug(f"    ✓ 关注成功，今日关注: {today_stats['follow']}/{self.daily_quota.max_follow}")
                else:
                    logger.warning("    关注失败，继续")
                    self.db.log_interaction(task.id, self.device_id, 'follow', 'failed', error_msg='follow_failed')
            else:
                logger.info(f"    ⊗ 已达关注配额 ({today_stats['follow']}/{self.daily_quota.max_follow})，跳过关注")

            self._random_delay()

            # 步骤2.5: 检查用户是否有视频
            logger.info(f"  [检测] 检查用户是否有视频")
            if not self.executor.check_user_has_videos():
                logger.warning("    用户无视频（私密账户或无作品），跳过点赞和收藏")
                self.executor.go_back_to_home_from_user_page()
                task.status = 'completed'
                task.completed_at = datetime.now()
                session.commit()
                logger.info(f"✓ 任务 #{task.id} 完成（跳过无视频用户）")
                return True

            # 步骤3: 点赞视频（检查配额）
            should_like = self.daily_quota.can_like(today_stats['like'])
            logger.info(f"  [3/5] 点赞用户视频 ({'执行' if should_like else '跳过-已达配额'})")

            if should_like:
                if self.executor.like_pinned_video():
                    self.update_action_count('like')
                    self.db.log_interaction(task.id, self.device_id, 'like', 'success')
                    today_stats['like'] += 1
                    logger.debug(f"    ✓ 点赞成功，今日点赞: {today_stats['like']}/{self.daily_quota.max_like}")
                else:
                    logger.warning("    点赞失败，继续")
                    self.db.log_interaction(task.id, self.device_id, 'like', 'failed', error_msg='like_failed')
            else:
                logger.info(f"    ⊗ 已达点赞配额 ({today_stats['like']}/{self.daily_quota.max_like})，跳过点赞")

            self._random_delay()

            # 步骤4: 收藏视频（检查配额）
            should_collect = self.daily_quota.can_collect(today_stats['collect'])
            logger.info(f"  [4/5] 收藏另一个视频 ({'执行' if should_collect else '跳过-已达配额'})")

            if should_collect:
                if self.executor.collect_pinned_video():
                    self.update_action_count('collect')
                    self.db.log_interaction(task.id, self.device_id, 'collect', 'success')
                    today_stats['collect'] += 1
                    logger.debug(f"    ✓ 收藏成功，今日收藏: {today_stats['collect']}/{self.daily_quota.max_collect}")
                else:
                    logger.warning("    收藏失败，继续")
                    self.db.log_interaction(task.id, self.device_id, 'collect', 'failed', error_msg='collect_failed')
            else:
                logger.info(f"    ⊗ 已达收藏配额 ({today_stats['collect']}/{self.daily_quota.max_collect})，跳过收藏")

            self._random_delay()

            # 步骤5: 返回主页并刷视频
            logger.info(f"  [5/5] 返回主页并刷视频")
            # 如果跳过了点赞和收藏，从用户主页返回（2次back）
            if not should_like and not should_collect:
                self.executor.go_back_to_home_from_user_page()
            else:
                # 否则从视频页返回（4次back）
                self.executor.go_back_to_home()

            # 标记为完成
            task.status = 'completed'
            task.completed_at = datetime.now()
            session.commit()

            logger.info(f"✓ 任务 #{task.id} 完成")
            return True

        except Exception as e:
            task.status = 'failed'
            task.error_msg = str(e)
            task.retry_count += 1

            if task.retry_count >= task.max_retries:
                logger.error(f"✗ 任务 #{task.id} 失败 (已达最大重试次数)")
            else:
                logger.warning(
                    f"⚠ 任务 #{task.id} 失败，将重试 "
                    f"({task.retry_count}/{task.max_retries}): {e}"
                )

            session.commit()
            return False

        finally:
            session.close()

    def execute_realtime_task(self, task):
        """执行实时评论自动化

        新流程:
        1. 搜索评论用户
        2. 进入用户主页
        3. 关注用户
        4. 随机选择视频进入
        5. 点赞视频
        6. 收藏视频
        7. 评论视频
        8. 返回主页

        Args:
            task: InteractionTask 对象

        Returns:
            True 成功，False 失败
        """
        session = self.db.get_session()
        try:
            logger.info(f"[{self.device_id}] 执行任务 #{task.id} (实时)")

            # 标记为进行中
            task.status = 'in_progress'
            task.started_at = datetime.now()
            session.commit()

            # 步骤1: 搜索用户（优先使用抖音号 unique_id）
            search_id = task.comment_unique_id or task.comment_uid or task.comment_user_id
            logger.info(f"  [1/7] 搜索用户 {search_id}")
            if not self.executor.navigate_to_user(search_id):
                raise Exception("无法导航到用户")

            self._random_delay()

            # 步骤2: 关注用户（在用户主页）
            logger.info(f"  [2/7] 关注用户")
            if self.executor.follow_user():
                self.db.log_interaction(task.id, self.device_id, 'follow', 'success')
                logger.debug("    ✓ 关注成功")
            else:
                logger.warning("    关注失败，继续")
                self.db.log_interaction(task.id, self.device_id, 'follow', 'failed', error_msg='follow_failed')

            self._random_delay()

            # 步骤3: 随机选择视频进入（不评论）
            logger.info(f"  [3/7] 随机选择视频")
            video_element_id = DouyinElementIds.USER_PAGE_VIDEO
            if not self.executor.ops.element_exists(resourceId=video_element_id):
                logger.warning("    未找到视频列表")
                raise Exception("未找到视频列表")

            video_elements = self.executor.ops.auto(resourceId=video_element_id)
            video_count = min(video_elements.count, 6)
            if video_count == 0:
                raise Exception("没有可点击的视频")

            video_index = random.randint(0, video_count - 1)
            logger.debug(f"    随机选择第 {video_index + 1}/{video_count} 个视频")
            video_elements[video_index].click()
            time.sleep(2)

            self._random_delay()

            # 步骤4: 点赞视频
            logger.info(f"  [4/7] 点赞视频")
            like_button_id = self.executor.ops._get_element_id(DouyinElementIds.LIKE_BUTTON)
            if self.executor.ops.element_exists(resourceId=like_button_id):
                self.executor.ops.auto(resourceId=like_button_id).click()
                self.db.log_interaction(task.id, self.device_id, 'like', 'success')
                logger.debug("    ✓ 点赞成功")
                time.sleep(1)
            else:
                logger.warning("    未找到点赞按钮")
                self.db.log_interaction(task.id, self.device_id, 'like', 'failed', error_msg='button_not_found')

            self._random_delay()

            # 步骤5: 收藏视频
            logger.info(f"  [5/7] 收藏视频")
            collect_button_id = self.executor.ops._get_element_id(DouyinElementIds.COLLECT_BUTTON)
            if self.executor.ops.element_exists(resourceId=collect_button_id):
                self.executor.ops.auto(resourceId=collect_button_id).click()
                self.db.log_interaction(task.id, self.device_id, 'collect', 'success')
                logger.debug("    ✓ 收藏成功")
                time.sleep(1)
            else:
                logger.warning("    未找到收藏按钮")
                self.db.log_interaction(task.id, self.device_id, 'collect', 'failed', error_msg='button_not_found')

            self._random_delay()

            # 步骤6: 评论视频
            logger.info(f"  [6/7] 评论视频")
            comment_text = self.generate_comment()
            comment_success = False

            # 点击评论按钮
            comment_button_id = DouyinElementIds.COMMENT_BUTTON
            if self.executor.ops.element_exists(resourceId=comment_button_id):
                self.executor.ops.auto(resourceId=comment_button_id).click()
                time.sleep(1.5)
                logger.debug("    ✓ 已点击评论按钮")

                # 输入评论内容
                comment_input_id = DouyinElementIds.COMMENT_INPUT
                if self.executor.ops.element_exists(resourceId=comment_input_id):
                    input_element = self.executor.ops.auto(resourceId=comment_input_id)
                    input_element.click()
                    time.sleep(0.5)
                    input_element.set_text(comment_text)
                    time.sleep(1)
                    logger.debug(f"    ✓ 已输入评论: {comment_text[:20]}...")

                    # 点击发送按钮
                    send_button_id = DouyinElementIds.SEND_TEXT_COMMENT
                    if self.executor.ops.element_exists(resourceId=send_button_id):
                        self.executor.ops.auto(resourceId=send_button_id).click()
                        time.sleep(2)
                        logger.debug("    ✓ 评论已发送")
                        self.db.log_interaction(task.id, self.device_id, 'comment', 'success')
                        comment_success = True
                    else:
                        logger.warning("    未找到发送按钮")
                        self.db.log_interaction(task.id, self.device_id, 'comment', 'failed', error_msg='send_button_not_found')
                else:
                    logger.warning("    未找到评论输入框")
                    self.db.log_interaction(task.id, self.device_id, 'comment', 'failed', error_msg='input_not_found')
            else:
                logger.warning("    未找到评论按钮")
                self.db.log_interaction(task.id, self.device_id, 'comment', 'failed', error_msg='button_not_found')

            self._random_delay()

            # 步骤7: 返回主页
            logger.info(f"  [7/7] 返回主页")
            self.executor.go_back_to_home()

            # 标记为完成
            task.status = 'completed'
            task.completed_at = datetime.now()
            session.commit()

            logger.info(f"✓ 任务 #{task.id} 完成")
            return True

        except Exception as e:
            task.status = 'failed'
            task.error_msg = str(e)
            task.retry_count += 1

            if task.retry_count >= task.max_retries:
                logger.error(f"✗ 任务 #{task.id} 失败 (已达最大重试次数)")
            else:
                logger.warning(
                    f"⚠ 任务 #{task.id} 失败，将重试 "
                    f"({task.retry_count}/{task.max_retries}): {e}"
                )

            session.commit()
            return False

        finally:
            session.close()

    def simulate_normal_user(self):
        """模拟正常用户行为（用于实时设备的待机状态）

        - 刷视频
        - 随机点赞
        - 可选：随机评论
        """
        try:
            logger.debug(f"[{self.device_id}] 模拟正常用户行为")
            # self.executor.scroll_feed()
            # self.executor.like_random_video()
            # 可选：随机评论某条视频
            time.sleep(5)  # 简单地等待
        except Exception as e:
            logger.warning(f"模拟用户行为失败: {e}")

    def generate_comment(self):
        """生成评论文本"""
        default_comments = [
            "很有意思！😄",
            "赞同！👍",
            "这个很不错！",
            "同意！✨",
            "好内容，关注了！",
            "太棒了！",
            "支持！",
            "一起加油！"
        ]
        return random.choice(default_comments)

    def _random_delay(self):
        """随机延迟（防检测）"""
        delay = random.uniform(2, 5)
        time.sleep(delay)
