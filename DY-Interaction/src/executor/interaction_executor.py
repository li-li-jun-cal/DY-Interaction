"""
互动执行器 - 基于 an13 的自动化操作
"""

import logging
import time
import random
import json
from typing import Dict, Optional

from .douyin_operations import DouyinOperations
from .page_navigator import PageNavigator
from .element_ids import DouyinElementIds
from ..database.manager import DatabaseManager
from ..utils.comment_text_manager import CommentTextManager

logger = logging.getLogger(__name__)


class InteractionExecutor:
    """互动执行器 - 执行点赞、评论、关注、私信等操作"""

    def _get_actual_device_id(self, device_id: str) -> str:
        """获取真实的设备序列号（支持动态设备映射）

        Args:
            device_id: 逻辑设备ID（如 Device-1）

        Returns:
            真实的设备序列号（如 31014944780020Z）
        """
        # 如果device_id不是Device-X格式，直接返回
        if not device_id.startswith("Device-"):
            return device_id

        try:
            # 1. 尝试从配置文件读取映射
            import json
            from pathlib import Path

            config_file = Path(__file__).parent.parent.parent / 'config' / 'config.json'
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                device_mapping = config.get('devices', {}).get('device_mapping', {})
                if device_id in device_mapping:
                    actual_id = device_mapping[device_id]
                    logger.info(f"✓ 设备映射（配置）: {device_id} -> {actual_id}")
                    return actual_id

            # 2. 如果配置中没有，自动从 adb devices 获取
            import subprocess
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')[1:]  # 跳过第一行 "List of devices attached"

            available_devices = []
            for line in lines:
                if '\t' in line:
                    serial = line.split('\t')[0].strip()
                    available_devices.append(serial)

            if available_devices:
                # 提取设备编号 (Device-1 -> 1, Device-2 -> 2)
                device_num = int(device_id.split('-')[1])

                # 如果设备编号在可用设备范围内，使用对应的设备
                if 1 <= device_num <= len(available_devices):
                    actual_id = available_devices[device_num - 1]
                    logger.info(f"✓ 设备映射（自动）: {device_id} -> {actual_id} (共{len(available_devices)}台)")
                    return actual_id
                else:
                    logger.warning(f"⚠ 设备编号超出范围: {device_id}，可用设备: {len(available_devices)}台")
                    return device_id
            else:
                logger.warning(f"⚠ 未检测到任何 adb 设备")
                return device_id

        except Exception as e:
            logger.warning(f"⚠ 设备映射失败: {e}，使用原始ID")
            return device_id

    def __init__(self, device_id: str, db_manager: DatabaseManager, device_model: str = None):
        """初始化执行器

        Args:
            device_id: 设备ID（如 Device-1 或真实序列号）
            db_manager: 数据库管理器
            device_model: 设备型号（pftm20, PD2072 等）
        """
        self.device_id = device_id
        self.db = db_manager
        self.device_model = device_model

        # 获取真实的设备序列号
        actual_device_id = self._get_actual_device_id(device_id)

        # 初始化自动化操作
        try:
            import uiautomator2 as u2
            # 连接到指定设备（使用真实序列号）
            auto = u2.connect(actual_device_id)
            self.ops = DouyinOperations(
                auto=auto,
                device_model=device_model,
                logger=logger
            )

            # 初始化页面导航器
            self.navigator = PageNavigator(self.ops, logger)

            logger.info(f"✓ 初始化执行器: {device_id} -> {actual_device_id}")
        except Exception as e:
            logger.error(f"✗ 初始化执行器失败: {e}")
            raise

        # 初始化评论文本管理器
        try:
            from pathlib import Path
            # 尝试找评论文件，如果没有则创建一个示例文件
            comments_file = Path(__file__).parent.parent.parent / 'data' / 'comments.xlsx'
            if not comments_file.exists():
                # 如果文件不存在，创建一个包含示例评论的文件
                logger.warning(f"评论文件不存在: {comments_file}，使用内置默认评论")
                self.comment_manager = None  # 暂时不使用评论管理器
            else:
                self.comment_manager = CommentTextManager(comments_file)
        except Exception as e:
            logger.warning(f"初始化评论管理器失败: {e}，使用内置默认评论")
            self.comment_manager = None

        # 操作间隔配置（秒）
        self.delay_range = (3, 8)

    def _random_delay(self):
        """随机延迟（防检测）"""
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)

    def navigate_to_user(self, user_id: str) -> bool:
        """导航到用户主页（完整流程，参考 an13）

        Args:
            user_id: 用户ID或抖音号

        Returns:
            是否成功
        """
        try:
            logger.info(f"  导航到用户: {user_id}")

            # 步骤0: 确保在首页
            if not self.navigator.ensure_on_homepage():
                logger.warning("  无法返回首页，尝试继续")

            # 步骤1: 点击搜索按钮
            logger.debug("  [1/6] 点击搜索按钮")
            result = self.ops.find_and_click_search_button()
            if not result.get('success'):
                logger.warning(f"  无法找到搜索按钮: {result.get('message')}")
                return False

            time.sleep(1)

            # 步骤2: 查找搜索输入框
            logger.debug("  [2/6] 查找搜索输入框")
            input_result = self.ops.find_search_input()
            if not input_result.get('success'):
                logger.warning(f"  无法找到搜索输入框: {input_result.get('message')}")
                return False

            time.sleep(0.5)

            # 步骤3: 输入用户ID
            logger.debug(f"  [3/6] 输入搜索文本: {user_id}")
            result = self.ops.input_search_text(input_result, user_id)
            if not result.get('success'):
                logger.warning(f"  无法输入搜索文本: {result.get('message')}")
                return False

            time.sleep(1)

            # 步骤4: 查找并点击搜索确认按钮
            logger.debug("  [4/6] 查找搜索确认按钮")
            confirm_result = self.ops.find_search_confirm_button()
            if not confirm_result.get('success'):
                logger.warning(f"  无法找到搜索确认按钮: {confirm_result.get('message')}")
                return False

            time.sleep(0.5)

            # 步骤5: 点击搜索确认
            logger.debug("  [5/6] 点击搜索确认")
            result = self.ops.click_search_confirm(confirm_result)
            if not result.get('success'):
                logger.warning(f"  点击确认失败: {result.get('message')}")
                return False

            # 等待搜索结果
            time.sleep(2)

            # 步骤6: 使用找图+偏移点击第一个用户
            logger.debug("  [6/6] 查找并点击用户")
            result = self.ops.find_first_user_result()
            if not result.get('success'):
                logger.warning(f"  无法进入用户主页: {result.get('message')}")
                return False

            # 等待页面加载
            time.sleep(2)

            logger.info("  ✓ 成功导航到用户主页")
            return True

        except Exception as e:
            logger.error(f"  ✗ 导航失败: {e}")
            return False

    def like_comment(self, task) -> bool:
        """给评论点赞

        Args:
            task: InteractionTask 对象

        Returns:
            是否成功
        """
        start_time = time.time()

        try:
            logger.info(f"  执行点赞: {task.comment_user_name}")

            # 进入置顶视频
            pinned_video_result = self.ops.find_pinned_video()
            if not pinned_video_result.get('success'):
                logger.warning("  无法找到置顶视频")
                return False

            if not self.ops.click_pinned_video(pinned_video_result).get('success'):
                logger.warning("  无法点击置顶视频")
                return False

            # 等待视频页面加载
            time.sleep(2)

            # 点赞视频
            if not self.ops.find_and_click_like_button().get('success'):
                logger.warning("  无法找到点赞按钮，但继续执行")

            self.db.log_interaction(
                task.id,
                self.device_id,
                'like',
                'success',
                duration_seconds=time.time() - start_time
            )

            self._random_delay()
            return True

        except Exception as e:
            logger.error(f"  ✗ 点赞失败: {e}")
            self.db.log_interaction(
                task.id,
                self.device_id,
                'like',
                'failed',
                error_msg=str(e),
                duration_seconds=time.time() - start_time
            )
            return False

    def post_comment(self, task_or_text, comment_text: str = None) -> bool:
        """发布评论

        Args:
            task_or_text: InteractionTask 对象 或 评论文本字符串
            comment_text: 评论内容（可选，不提供则自动生成）

        Returns:
            是否成功
        """
        start_time = time.time()

        # 判断第一个参数是 task 还是 comment_text
        if isinstance(task_or_text, str):
            # 第一个参数是评论文本
            comment_text = task_or_text
            task = None
        else:
            # 第一个参数是 task
            task = task_or_text

        try:
            # 如果没有提供评论内容，自动生成
            if not comment_text:
                if self.comment_manager:
                    comment_text = self.comment_manager.get_next_comment()
                if not comment_text:
                    # 使用默认评论列表
                    default_comments = [
                        "很有意思！😄",
                        "赞同！👍",
                        "这个很不错！",
                        "同意！✨",
                        "好内容，关注了！"
                    ]
                    import random
                    comment_text = random.choice(default_comments)

            logger.info(f"  发布评论: {comment_text[:20]}...")

            # 1. 查找并点击评论按钮
            comment_button_result = self.ops.find_comment_button()
            if not comment_button_result.get('success'):
                logger.warning("  无法找到评论按钮")
                return False

            if not self.ops.click_comment_button(comment_button_result).get('success'):
                logger.warning("  无法点击评论按钮")
                return False

            # 等待评论输入框加载
            time.sleep(1)

            # 2. 查找评论输入框
            comment_input_result = self.ops.find_comment_input()
            if not comment_input_result.get('success'):
                logger.warning("  无法找到评论输入框")
                return False

            # 3. 输入评论文本
            if not self.ops.input_comment_text(comment_input_result, comment_text).get('success'):
                logger.warning("  无法输入评论文本")
                return False

            # 等待文本输入完成
            time.sleep(1)

            # 4. 发送评论
            send_button_result = self.ops.find_send_button()
            if not send_button_result.get('success'):
                logger.warning("  无法找到发送按钮，尝试按回车键")
                self.ops.auto.press('enter')
            else:
                if not self.ops.click_send_button(send_button_result).get('success'):
                    logger.warning("  无法点击发送按钮")
                    return False

            # 等待评论发送完成
            time.sleep(2)

            # 记录日志（如果有task）
            if task:
                self.db.log_interaction(
                    task.id,
                    self.device_id,
                    'comment',
                    'success',
                    duration_seconds=time.time() - start_time
                )

            self._random_delay()
            return True

        except Exception as e:
            logger.error(f"  ✗ 评论失败: {e}")
            if task:
                self.db.log_interaction(
                    task.id,
                    self.device_id,
                    'comment',
                    'failed',
                    error_msg=str(e),
                    duration_seconds=time.time() - start_time
                )
            return False

    def follow_user(self, task=None) -> bool:
        """关注用户（在用户主页）

        检测逻辑：
        1. 如果找到关注按钮 (vg0)，点击关注
        2. 如果找到已关注标识 (vg1)，说明已关注，返回特殊状态
        3. 如果都没找到，记录警告

        Args:
            task: InteractionTask 对象（可选）

        Returns:
            True: 关注成功或已关注
            False: 关注失败
            'already_followed': 已关注（用于触发跳过后续操作）
        """
        start_time = time.time()

        try:
            if task:
                logger.info(f"  关注用户: {task.comment_user_name}")
            else:
                logger.info(f"  关注用户")

            # 先检查是否已关注
            already_followed_id = DouyinElementIds.USER_PAGE_ALREADY_FOLLOWED
            if self.ops.element_exists(resourceId=already_followed_id):
                logger.info("    ⚠ 用户已关注，跳过后续操作")
                return 'already_followed'  # 返回特殊标识

            # 查找关注按钮
            follow_button_id = DouyinElementIds.USER_PAGE_FOLLOW_BUTTON
            if self.ops.element_exists(resourceId=follow_button_id):
                element = self.ops.auto(resourceId=follow_button_id)
                element.click()
                logger.debug("    ✓ 关注成功")
                time.sleep(1)
            else:
                logger.warning("    未找到关注按钮")
                return False

            # 记录日志（如果有task）
            if task:
                self.db.log_interaction(
                    task.id,
                    self.device_id,
                    'follow',
                    'success',
                    duration_seconds=time.time() - start_time
                )

            self._random_delay()
            return True

        except Exception as e:
            logger.error(f"  ✗ 关注失败: {e}")
            if task:
                self.db.log_interaction(
                    task.id,
                    self.device_id,
                    'follow',
                    'failed',
                    error_msg=str(e),
                    duration_seconds=time.time() - start_time
                )
            return False

    def check_user_has_videos(self) -> bool:
        """检查用户是否有视频（在用户主页）

        用于检测私密账户或无作品的用户

        Returns:
            True: 有视频，False: 无视频
        """
        try:
            logger.info("  检查用户视频")

            # 使用视频元素ID查找视频
            video_element_id = DouyinElementIds.USER_PAGE_VIDEO

            # 等待一下，确保页面加载完成
            time.sleep(1)

            if not self.ops.element_exists(resourceId=video_element_id):
                logger.warning("    用户无视频（私密账户或无作品）")
                return False

            # 获取视频数量
            video_elements = self.ops.auto(resourceId=video_element_id)
            video_count = video_elements.count

            if video_count == 0:
                logger.warning("    用户无视频（私密账户或无作品）")
                return False

            logger.info(f"    ✓ 用户有 {video_count} 个视频")
            return True

        except Exception as e:
            logger.error(f"  检查视频失败: {e}")
            # 出错时保守处理，假设无视频
            return False

    def send_dm(self, task, message_text: str = None) -> bool:
        """发送私信

        Args:
            task: InteractionTask 对象
            message_text: 私信内容（可选，不提供则自动生成）

        Returns:
            是否成功
        """
        start_time = time.time()

        try:
            # 如果没有提供私信内容，自动生成
            if not message_text:
                message_text = "你好，看到你的评论很有意思！"

            logger.info(f"  发送私信: {message_text[:20]}...")

            # TODO: 根据 an13 的实际接口调整
            # result = self.ops.send_dm(task.comment_user_id, message_text)

            # 暂时模拟成功
            self.db.log_interaction(
                task.id,
                self.device_id,
                'dm',
                'success',
                duration_seconds=time.time() - start_time
            )

            self._random_delay()
            return True

        except Exception as e:
            logger.error(f"  ✗ 私信失败: {e}")
            self.db.log_interaction(
                task.id,
                self.device_id,
                'dm',
                'failed',
                error_msg=str(e),
                duration_seconds=time.time() - start_time
            )
            return False

    def execute_task(self, task, actions: Dict = None) -> bool:
        """执行一个完整的互动任务

        Args:
            task: InteractionTask 对象
            actions: 要执行的操作（dict）
                例如: {'like': True, 'comment': True, 'follow': True, 'dm': False}

        Returns:
            是否执行成功
        """
        logger.info(f"\n执行任务 #{task.id}: {task.comment_user_name}")

        try:
            # 更新任务状态为执行中
            self.db.update_task_status(task.id, 'in_progress', self.device_id)

            # 解析操作配置
            if isinstance(task.actions, str):
                actions_config = json.loads(task.actions)
            else:
                actions_config = task.actions or {}

            # 如果传入了 actions 参数，使用传入的
            if actions:
                actions_config = actions

            # 执行各项操作
            results = {}

            # 1. 导航到用户主页
            # 使用 comment_unique_id（抖音号）进行搜索，这是唯一可以搜索到用户的ID
            user_search_id = task.comment_unique_id or task.comment_user_id
            if not user_search_id:
                logger.warning(f"任务 #{task.id} 缺少 comment_unique_id，无法搜索用户")
                self.db.update_task_status(task.id, 'failed', error_msg='缺少抖音号')
                return False

            if not self.navigate_to_user(user_search_id):
                logger.warning("导航失败，跳过此任务")
                self.db.update_task_status(task.id, 'failed', error_msg='导航失败')
                return False

            # 2. 点赞
            if actions_config.get('like', True):
                results['like'] = self.like_comment(task)

            # 3. 评论
            if actions_config.get('comment', True):
                results['comment'] = self.post_comment(task)

            # 4. 关注
            if actions_config.get('follow', True):
                results['follow'] = self.follow_user(task)

            # 5. 私信
            if actions_config.get('dm', False):
                results['dm'] = self.send_dm(task)

            # 返回首页
            try:
                self.ops.go_back(times=4)
            except Exception as e:
                logger.warning(f"返回首页失败: {e}")

            # 检查是否全部成功
            all_success = all(results.values()) if results else False

            # 更新任务状态
            if all_success:
                self.db.update_task_status(task.id, 'completed')
                logger.info(f"✓ 任务 #{task.id} 完成")
            else:
                self.db.update_task_status(task.id, 'failed', error_msg='部分操作失败')
                logger.warning(f"✗ 任务 #{task.id} 部分失败")

            return all_success

        except Exception as e:
            logger.error(f"✗ 执行任务失败: {e}")
            self.db.update_task_status(task.id, 'failed', error_msg=str(e))
            return False

    def execute_with_retry(self, task, max_retries: int = 3) -> bool:
        """带重试的任务执行

        Args:
            task: InteractionTask 对象
            max_retries: 最大重试次数

        Returns:
            是否成功
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"第 {attempt + 1}/{max_retries} 次尝试")
                result = self.execute_task(task)

                if result:
                    return True

            except Exception as e:
                logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")

                if attempt < max_retries - 1:
                    # 等待后重试
                    wait_time = (attempt + 1) * 5
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)

        logger.error(f"✗ 任务执行失败，已重试 {max_retries} 次")
        return False

    def like_pinned_video(self) -> bool:
        """点赞用户的随机视频（在用户主页）

        Returns:
            是否成功
        """
        try:
            logger.info("  点赞用户视频")

            # 使用视频元素ID查找视频（前6个）
            video_element_id = DouyinElementIds.USER_PAGE_VIDEO
            if not self.ops.element_exists(resourceId=video_element_id):
                logger.warning("    未找到视频元素")
                return False

            # 获取所有视频元素
            video_elements = self.ops.auto(resourceId=video_element_id)
            video_count = min(video_elements.count, 6)  # 最多取前6个

            if video_count == 0:
                logger.warning("    没有可点击的视频")
                return False

            # 随机选择一个视频（0到5之间）
            video_index = random.randint(0, video_count - 1)
            logger.debug(f"    随机选择第 {video_index + 1}/{video_count} 个视频")

            # 点击选中的视频
            video_elements[video_index].click()
            time.sleep(2)

            # 在视频页面点赞
            like_button_id = self.ops._get_element_id(DouyinElementIds.LIKE_BUTTON)
            if self.ops.element_exists(resourceId=like_button_id):
                element = self.ops.auto(resourceId=like_button_id)
                element.click()
                logger.debug("    ✓ 点赞成功")
                time.sleep(1)
                return True
            else:
                logger.warning("    未找到点赞按钮")
                return False

        except Exception as e:
            logger.error(f"  点赞失败: {e}")
            return False

    def collect_pinned_video(self) -> bool:
        """收藏用户的另一个随机视频（从用户主页前6个视频中随机选择）

        Returns:
            是否成功
        """
        try:
            logger.info("  收藏用户视频")

            # 先返回用户主页
            logger.debug("    返回用户主页")
            self.ops.auto.press("back")
            time.sleep(1.5)

            # 使用视频元素ID查找视频（前6个）
            video_element_id = DouyinElementIds.USER_PAGE_VIDEO
            if not self.ops.element_exists(resourceId=video_element_id):
                logger.warning("    未找到视频元素")
                return False

            # 获取所有视频元素
            video_elements = self.ops.auto(resourceId=video_element_id)
            video_count = min(video_elements.count, 6)  # 最多取前6个

            if video_count == 0:
                logger.warning("    没有可点击的视频")
                return False

            # 随机选择一个视频（0到5之间）
            video_index = random.randint(0, video_count - 1)
            logger.debug(f"    随机选择第 {video_index + 1}/{video_count} 个视频")

            # 点击选中的视频
            video_elements[video_index].click()
            time.sleep(2)

            # 在视频页面点击收藏按钮
            collect_button_id = self.ops._get_element_id(DouyinElementIds.COLLECT_BUTTON)
            if self.ops.element_exists(resourceId=collect_button_id):
                element = self.ops.auto(resourceId=collect_button_id)
                element.click()
                logger.debug("    ✓ 收藏成功")
                time.sleep(1)
                return True
            else:
                logger.warning("    未找到收藏按钮")
                return False

        except Exception as e:
            logger.error(f"  收藏失败: {e}")
            return False

    def click_random_user_video_and_comment(self, comment_text: str) -> bool:
        """在用户主页随机选择视频并进入后评论

        流程：
        1. 在用户主页找到视频列表（ID: com.ss.android.ugc.aweme:id/qdf）
        2. 随机选择一个视频
        3. 点击进入视频
        4. 点击评论按钮（ID: com.ss.android.ugc.aweme:id/eex）
        5. 输入评论内容（ID: com.ss.android.ugc.aweme:id/eex）
        6. 点击发送（ID: com.ss.android.ugc.aweme:id/ei9）

        注意：评论后不返回，留在视频页面（让调用者决定后续操作）

        Args:
            comment_text: 评论内容

        Returns:
            是否成功
        """
        try:
            logger.info("  在用户视频中进行评论")

            # 步骤1: 查找用户主页视频列表
            video_element_id = DouyinElementIds.USER_PAGE_VIDEO
            if not self.ops.element_exists(resourceId=video_element_id):
                logger.warning("    未找到视频列表")
                return False

            # 获取所有视频元素
            video_elements = self.ops.auto(resourceId=video_element_id)
            video_count = min(video_elements.count, 6)  # 最多取前6个

            if video_count == 0:
                logger.warning("    没有可点击的视频")
                return False

            # 步骤2: 随机选择一个视频
            video_index = random.randint(0, video_count - 1)
            logger.debug(f"    随机选择第 {video_index + 1}/{video_count} 个视频")

            # 步骤3: 点击视频进入
            video_elements[video_index].click()
            time.sleep(2)  # 等待视频加载

            # 步骤4: 点击评论按钮
            comment_button_id = DouyinElementIds.COMMENT_BUTTON
            if not self.ops.element_exists(resourceId=comment_button_id):
                logger.warning("    未找到评论按钮")
                return False

            self.ops.auto(resourceId=comment_button_id).click()
            time.sleep(1.5)  # 等待评论框出现
            logger.debug("    ✓ 已点击评论按钮")

            # 步骤5: 输入评论内容
            comment_input_id = DouyinElementIds.COMMENT_INPUT
            if not self.ops.element_exists(resourceId=comment_input_id):
                logger.warning("    未找到评论输入框")
                return False

            input_element = self.ops.auto(resourceId=comment_input_id)
            input_element.click()
            time.sleep(0.5)
            input_element.set_text(comment_text)
            time.sleep(1)  # 等待文本输入完成
            logger.debug(f"    ✓ 已输入评论: {comment_text[:20]}...")

            # 步骤6: 点击发送按钮
            send_button_id = DouyinElementIds.SEND_TEXT_COMMENT
            if not self.ops.element_exists(resourceId=send_button_id):
                logger.warning("    未找到发送按钮")
                return False

            self.ops.auto(resourceId=send_button_id).click()
            time.sleep(2)  # 等待评论发送完成
            logger.debug("    ✓ 评论已发送")

            # 评论发送后留在视频页面，不返回
            return True

        except Exception as e:
            logger.error(f"  评论失败: {e}")
            return False

    def go_back_to_home(self) -> bool:
        """返回抖音主页并刷1-3个视频

        从收藏视频后的状态返回首页需要按4次返回键：
        1. 退出当前视频
        2. 返回用户主页
        3. 退出用户主页
        4. 返回抖音首页

        Returns:
            是否成功
        """
        try:
            logger.info("  返回主页")

            # 按4次返回键，从视频页→用户主页→搜索结果→首页
            logger.debug("    按4次返回键")
            for i in range(4):
                self.ops.auto.press("back")
                time.sleep(0.5)

            time.sleep(1.5)

            # 检查是否回到首页，如果没有继续按返回键
            max_extra_backs = 3  # 最多再按3次
            like_button_id = self.ops._get_element_id(DouyinElementIds.LIKE_BUTTON)

            for attempt in range(max_extra_backs):
                if self.ops.element_exists(resourceId=like_button_id):
                    logger.debug("    ✓ 已检测到首页元素")
                    break
                else:
                    logger.debug(f"    未检测到首页元素，继续按返回键 ({attempt + 1}/{max_extra_backs})")
                    self.ops.auto.press("back")
                    time.sleep(0.8)

            # 最后验证
            time.sleep(1)
            if not self.ops.element_exists(resourceId=like_button_id):
                logger.warning("    仍未检测到首页元素，可能在手机桌面或其他界面")

            # 随机刷1-3个视频（模拟正常用户行为）
            num_videos = random.randint(1, 3)
            logger.info(f"  刷 {num_videos} 个视频")

            screen_width, screen_height = self.ops.get_screen_size()
            start_y = int(screen_height * 0.7)
            end_y = int(screen_height * 0.3)
            center_x = screen_width // 2

            for i in range(num_videos):
                # 观看视频几秒
                watch_time = random.uniform(2, 5)
                logger.debug(f"    观看视频 {i+1}/{num_videos} ({watch_time:.1f}秒)")
                time.sleep(watch_time)

                # 向上滑动到下一个视频
                self.ops.auto.swipe(center_x, start_y, center_x, end_y, duration=0.3)
                time.sleep(1)

            logger.info("  ✓ 完成刷视频，准备下一轮")
            return True

        except Exception as e:
            logger.error(f"  返回主页失败: {e}")
            return False

    def go_back_to_home_from_user_page(self) -> bool:
        """从用户主页返回抖音首页并刷1-3个视频

        从用户主页返回首页只需按2次返回键：
        1. 退出用户主页 → 搜索结果页
        2. 退出搜索页 → 抖音首页

        Returns:
            是否成功
        """
        try:
            logger.info("  从用户主页返回首页")

            # 按2次返回键，从用户主页→搜索结果→首页
            logger.debug("    按2次返回键")
            for i in range(2):
                self.ops.auto.press("back")
                time.sleep(0.5)

            time.sleep(1.5)

            # 检查是否回到首页，如果没有继续按返回键
            max_extra_backs = 3  # 最多再按3次
            like_button_id = self.ops._get_element_id(DouyinElementIds.LIKE_BUTTON)

            for attempt in range(max_extra_backs):
                if self.ops.element_exists(resourceId=like_button_id):
                    logger.debug("    ✓ 已检测到首页元素")
                    break
                else:
                    logger.debug(f"    未检测到首页元素，继续按返回键 ({attempt + 1}/{max_extra_backs})")
                    self.ops.auto.press("back")
                    time.sleep(0.8)

            # 最后验证
            time.sleep(1)
            if not self.ops.element_exists(resourceId=like_button_id):
                logger.warning("    仍未检测到首页元素，可能在手机桌面或其他界面")

            # 随机刷1-3个视频（模拟正常用户行为）
            num_videos = random.randint(1, 3)
            logger.info(f"  刷 {num_videos} 个视频")

            screen_width, screen_height = self.ops.get_screen_size()
            start_y = int(screen_height * 0.7)
            end_y = int(screen_height * 0.3)
            center_x = screen_width // 2

            for i in range(num_videos):
                # 观看视频几秒
                watch_time = random.uniform(2, 5)
                logger.debug(f"    观看视频 {i+1}/{num_videos} ({watch_time:.1f}秒)")
                time.sleep(watch_time)

                # 向上滑动到下一个视频
                self.ops.auto.swipe(center_x, start_y, center_x, end_y, duration=0.3)
                time.sleep(1)

            logger.info("  ✓ 完成刷视频，准备下一轮")
            return True

        except Exception as e:
            logger.error(f"  从用户主页返回失败: {e}")
            return False
