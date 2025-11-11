"""
页面导航管理器 - 参考 an13 实现
负责判断当前页面并导航到目标页面
"""
import time
import random
import logging
from typing import Dict, Optional
from .element_ids import DouyinElementIds

logger = logging.getLogger(__name__)


class PageNavigator:
    """页面导航管理器"""

    # 页面类型常量
    PAGE_UNKNOWN = "unknown"
    PAGE_HOME = "home"  # 首页视频页面
    PAGE_USER = "user"  # 用户主页
    PAGE_SEARCH = "search"  # 搜索页面
    PAGE_MESSAGE = "message"  # 消息页面
    PAGE_ME = "me"  # 我的页面
    PAGE_FRIEND = "friend"  # 朋友页面
    PAGE_DESKTOP = "desktop"  # 手机桌面

    def __init__(self, douyin_ops, logger_obj=None):
        """
        初始化页面导航管理器

        Args:
            douyin_ops: DouyinOperations实例
            logger_obj: 日志对象
        """
        self.ops = douyin_ops
        self.logger = logger_obj or logger
        self.element_ids = DouyinElementIds
        # 使用douyin_ops的元素版本管理器
        self.element_version = douyin_ops.element_version

    def _get_element_id(self, element_config):
        """获取元素ID（自动检测版本）"""
        return self.element_version.get_element_id(element_config, self.ops.auto)

    def detect_current_page(self) -> str:
        """
        检测当前所在页面（优化版：快速检测，优先判断常见页面）
        优先使用元素检测，避免使用包名查询（防止被检测）

        Returns:
            页面类型（PAGE_HOME, PAGE_USER, PAGE_SEARCH, PAGE_DESKTOP等）
        """
        try:
            # ========== 优先检测桌面（如果退出了抖音）==========
            desktop_id = self.element_ids.DESKTOP_WORKSPACE
            if self.ops.element_exists(resourceId=desktop_id):
                self.logger.warning("  [页面检测] 当前在手机桌面，需要重启抖音")
                return self.PAGE_DESKTOP

            # ========== 优先检测首页（最常见场景，快速返回）==========
            # 新逻辑：检测3个关键元素 - 底部导航通用按钮 + 底部导航首页 + 首页关注按钮
            bottom_nav_common_id = self._get_element_id(self.element_ids.BOTTOM_NAV_COMMON)
            bottom_nav_home_id = self._get_element_id(self.element_ids.BOTTOM_NAV_HOME)
            homepage_follow_id = self._get_element_id(self.element_ids.HOMEPAGE_FOLLOW_BUTTON)

            has_common = self.ops.element_exists(resourceId=bottom_nav_common_id)
            has_home = self.ops.element_exists(resourceId=bottom_nav_home_id)
            has_follow = self.ops.element_exists(resourceId=homepage_follow_id)

            # 只有3个元素都存在才判定为首页
            if has_common and has_home and has_follow:
                self.logger.debug("  [页面检测] 当前在首页 (检测到3个关键元素)")
                return self.PAGE_HOME

            # ========== 检测搜索页（只检测输入框，减少检测次数）==========
            search_input_id = self._get_element_id(self.element_ids.SEARCH_INPUT)
            if self.ops.element_exists(resourceId=search_input_id):
                self.logger.debug("  [页面检测] 当前在搜索页")
                return self.PAGE_SEARCH

            # ========== 检测用户主页（只检测3个关键元素）==========
            user_avatar_id = self._get_element_id(self.element_ids.USER_PAGE_AVATAR)
            if self.ops.element_exists(resourceId=user_avatar_id):
                user_name_id = self._get_element_id(self.element_ids.USER_PAGE_NAME)
                user_douyin_id = self._get_element_id(self.element_ids.USER_PAGE_DOUYIN_ID)

                has_name = self.ops.element_exists(resourceId=user_name_id)
                has_douyin_id = self.ops.element_exists(resourceId=user_douyin_id)

                if has_name and has_douyin_id:
                    self.logger.debug("  [页面检测] 当前在用户主页")
                    return self.PAGE_USER

            # ========== 其他未知页面 ==========
            self.logger.warning("  [页面检测] 无法确定当前页面")
            return self.PAGE_UNKNOWN

        except Exception as e:
            self.logger.error(f"  [页面检测] 检测失败: {e}")
            return self.PAGE_UNKNOWN

    def ensure_on_homepage(self, max_attempts: int = 5) -> bool:
        """
        确保当前在首页视频页面
        如果不在，尝试导航回首页

        Args:
            max_attempts: 最大尝试次数

        Returns:
            bool: 是否成功到达首页
        """
        self.logger.info("[导航] 确保在首页视频页面...")

        for attempt in range(1, max_attempts + 1):
            # 检测当前页面
            current_page = self.detect_current_page()

            if current_page == self.PAGE_HOME:
                self.logger.info("  ✓ 已在首页")
                return True

            self.logger.info(f"  [尝试 {attempt}/{max_attempts}] 当前页面: {current_page}，尝试返回首页...")

            # 根据当前页面采取不同策略
            if current_page == self.PAGE_DESKTOP:
                # 在桌面，需要重启抖音
                self.logger.warning("    → 检测到在桌面，重新启动抖音...")
                if self.start_douyin_app():
                    time.sleep(3)  # 等待应用启动
                    continue
                else:
                    self.logger.error("    ✗ 启动抖音失败")
                    return False
            elif current_page == self.PAGE_SEARCH:
                # 在搜索页，按返回键1次返回首页
                self.logger.debug("    → 从搜索页返回首页...")
                success = self._try_back_button()
            elif current_page == self.PAGE_USER:
                # 在用户主页，使用底部导航返回
                success = self._navigate_from_user_to_home()
            elif current_page == self.PAGE_UNKNOWN:
                # 未知页面，先尝试按返回键
                success = self._try_back_button()
            else:
                # 其他页面，尝试点击底部导航的首页按钮
                success = self._click_bottom_nav_home()

            if success:
                time.sleep(random.uniform(1.0, 2.0))
                continue
            else:
                # 尝试失败，按返回键
                self._try_back_button()
                time.sleep(random.uniform(1.0, 1.5))

        # 最后再检查一次
        current_page = self.detect_current_page()
        if current_page == self.PAGE_HOME:
            self.logger.info("  ✓ 成功返回首页")
            return True

        self.logger.error(f"  ✗ 无法返回首页，当前页面: {current_page}")
        return False

    def _navigate_from_user_to_home(self) -> bool:
        """
        从用户主页返回首页

        Returns:
            bool: 是否成功
        """
        try:
            self.logger.debug("    → 从用户主页返回首页...")

            # 按返回键
            self.ops.auto.press("back")
            time.sleep(0.5)

            self.logger.debug("    ✓ 按返回键退出用户主页")
            return True

        except Exception as e:
            self.logger.error(f"    ✗ 从用户主页返回失败: {e}")
            return False

    def _click_bottom_nav_home(self) -> bool:
        """
        点击底部导航栏的首页按钮

        Returns:
            bool: 是否成功
        """
        try:
            self.logger.debug("    → 点击底部导航栏首页按钮...")

            # 尝试点击底部导航的首页按钮
            bottom_nav_home_id = self._get_element_id(self.element_ids.BOTTOM_NAV_HOME)
            if self.ops.element_exists(resourceId=bottom_nav_home_id):
                self.ops.auto(resourceId=bottom_nav_home_id).click()
                return True

            return False

        except Exception as e:
            self.logger.error(f"    ✗ 点击底部导航失败: {e}")
            return False

    def _try_back_button(self) -> bool:
        """
        尝试按返回键

        Returns:
            bool: 是否成功
        """
        try:
            self.logger.debug("    → 按返回键...")

            self.ops.auto.press("back")
            time.sleep(random.uniform(0.5, 1.0))

            return True

        except Exception as e:
            self.logger.error(f"    ✗ 按返回键失败: {e}")
            return False

    def go_back_to_home(self) -> bool:
        """
        返回抖音主页

        Returns:
            bool: 是否成功
        """
        return self.ensure_on_homepage()

    def start_douyin_app(self) -> bool:
        """
        通过包名启动抖音应用

        Returns:
            bool: 是否成功启动
        """
        try:
            package_name = self.element_ids.DOUYIN_PACKAGE
            self.logger.info(f"  [应用管理] 启动抖音应用: {package_name}")

            # 使用 app_start 启动应用
            self.ops.auto.app_start(package_name)
            time.sleep(2)  # 等待应用启动

            # 验证是否启动成功
            current_app = self.ops.auto.app_current()
            if current_app.get('package') == package_name:
                self.logger.info("  ✓ 抖音应用启动成功")
                return True
            else:
                self.logger.warning(f"  ⚠ 当前应用: {current_app.get('package')}，不是抖音")
                return False

        except Exception as e:
            self.logger.error(f"  ✗ 启动抖音失败: {e}")
            return False

    def stop_douyin_app(self) -> bool:
        """
        关闭抖音应用

        Returns:
            bool: 是否成功关闭
        """
        try:
            package_name = self.element_ids.DOUYIN_PACKAGE
            self.logger.info(f"  [应用管理] 关闭抖音应用: {package_name}")

            # 使用 app_stop 关闭应用
            self.ops.auto.app_stop(package_name)
            time.sleep(1)  # 等待应用关闭

            # 验证是否关闭成功
            current_app = self.ops.auto.app_current()
            if current_app.get('package') != package_name:
                self.logger.info("  ✓ 抖音应用已关闭")
                return True
            else:
                self.logger.warning("  ⚠ 抖音应用可能未完全关闭")
                return False

        except Exception as e:
            self.logger.error(f"  ✗ 关闭抖音失败: {e}")
            return False
