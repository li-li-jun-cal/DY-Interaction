"""
抖音APP元素ID配置 - vivo S12 专用版本
简化版：移除 OPPO 设备支持，只保留 vivo S12 (PD2072) 的元素ID
"""

class DouyinElementIds:
    """
    抖音元素ID类 - vivo S12 专用
    """

    # ========== 搜索流程元素 ==========
    SEARCH_BUTTON = 'com.ss.android.ugc.aweme:id/1r2'
    SEARCH_INPUT = 'com.ss.android.ugc.aweme:id/et_search_kw'
    SEARCH_CONFIRM = 'com.ss.android.ugc.aweme:id/33a'
    SEARCH_RESULT_TEXT_ELEMENT = 'android:id/text1'

    # ========== 评论流程元素 ==========
    COMMENT_BUTTON = 'com.ss.android.ugc.aweme:id/eex'
    COMMENT_INPUT = 'com.ss.android.ugc.aweme:id/eex'
    SEND_TEXT_COMMENT = 'com.ss.android.ugc.aweme:id/ei9'
    IMAGE_COMMENT_ICON = 'com.ss.android.ugc.aweme:id/iv_image'
    ALBUM_FIRST_IMAGE = 'com.ss.android.ugc.aweme:id/root_view'
    SEND_IMAGE_COMMENT = 'com.ss.android.ugc.aweme:id/ei9'

    # ========== 用户主页检测元素 ==========
    USER_PAGE_AVATAR = 'com.ss.android.ugc.aweme:id/kz7'
    USER_PAGE_NAME = 'com.ss.android.ugc.aweme:id/sve'
    USER_PAGE_DOUYIN_ID = 'com.ss.android.ugc.aweme:id/4v_'
    USER_PAGE_FOLLOW_BUTTON = 'com.ss.android.ugc.aweme:id/vg0'  # 关注按钮
    USER_PAGE_ALREADY_FOLLOWED = 'com.ss.android.ugc.aweme:id/vg1'  # 已关注标识
    USER_PAGE_MORE_BUTTON = 'com.ss.android.ugc.aweme:id/content_layout'
    USER_PAGE_VIDEO = 'com.ss.android.ugc.aweme:id/qdf'  # 用户主页视频元素（有多个，选前6个）

    # ========== 首页检测元素 ==========
    # 首页检测逻辑：同时具备以下3个元素才判定为首页
    HOMEPAGE_TOP_NAV = 'com.ss.android.ugc.aweme:id/th2'
    HOMEPAGE_FOLLOW_BUTTON = 'com.ss.android.ugc.aweme:id/jm7'  # 首页顶部"关注"按钮
    BOTTOM_NAV_HOME = 'com.ss.android.ugc.aweme:id/0tr'  # 底部导航首页按钮（共5个导航按钮之一）
    BOTTOM_NAV_COMMON = 'com.ss.android.ugc.aweme:id/4ba'  # 底部导航通用容器
    FRAGMENT_CONTAINER = 'com.ss.android.ugc.aweme:id/fragment_container'

    # ========== 首页视频流元素（最重要）==========
    LIKE_BUTTON = 'com.ss.android.ugc.aweme:id/gas'  # 点赞按钮 - 用于检测是否在首页
    COLLECT_BUTTON = 'com.ss.android.ugc.aweme:id/d-z'
    SHARE_BUTTON = 'com.ss.android.ugc.aweme:id/yv+'
    HOMEPAGE_USER_AVATAR = 'com.ss.android.ugc.aweme:id/bi='

    # ========== 特殊情况检测元素 ==========
    LIVE_ROOM_INDICATOR = 'com.ss.android.ugc.aweme:id/syx'
    LIVE_ROOM_EXIT = 'com.ss.android.ugc.aweme:id/close_btn'
    SPECIAL_PAGE_INDICATOR = 'com.ss.android.ugc.aweme:id:special_page'

    # ========== 系统和桌面检测 ==========
    DESKTOP_WORKSPACE = 'com.bbk.launcher2:id/workspace'  # vivo 桌面元素

    # ========== 应用包名 ==========
    DOUYIN_PACKAGE = 'com.ss.android.ugc.aweme'  # 抖音包名
    SPECIAL_PAGE_BACK_BUTTON = 'com.ss.android.ugc.aweme:id/back_btn'
    PRODUCT_RECOMMEND_INDICATOR = 'com.ss.android.ugc.aweme:id/quh'


class DeviceElementVersion:
    """
    设备元素版本管理器 - 简化版
    不再需要检测设备型号，直接返回元素ID
    """

    def __init__(self, device_id, device_model=None, logger=None):
        """
        初始化设备元素版本管理器

        Args:
            device_id: 设备ID
            device_model: 设备型号（不再使用）
            logger: 日志对象
        """
        self.device_id = device_id
        self.device_model = device_model
        self.logger = logger

        if self.logger:
            self.logger.info(f"[设备 {self.device_id}] 使用 vivo S12 元素ID")

    def get_element_id(self, element_config, auto_device=None):
        """
        获取元素ID

        Args:
            element_config: 元素配置（可以是字典或字符串）
            auto_device: uiautomator2 device对象（兼容旧接口，不再使用）

        Returns:
            str: 元素ID
        """
        # 兼容旧的字典格式
        if isinstance(element_config, dict):
            # 优先使用 fallback (vivo)，如果没有则使用 primary
            element_id = element_config.get('fallback') or element_config.get('primary')
            return element_id

        # 新格式：直接返回字符串
        return element_config


if __name__ == "__main__":
    # 测试：打印所有元素配置
    print("\n" + "=" * 80)
    print("抖音APP元素ID配置 - vivo S12 专用版本")
    print("=" * 80)

    print("\n【搜索流程】")
    print(f"  搜索按钮: {DouyinElementIds.SEARCH_BUTTON}")
    print(f"  搜索输入框: {DouyinElementIds.SEARCH_INPUT}")
    print(f"  搜索确认: {DouyinElementIds.SEARCH_CONFIRM}")

    print("\n【首页检测】")
    print(f"  点赞按钮: {DouyinElementIds.LIKE_BUTTON}")
    print(f"  底部导航首页: {DouyinElementIds.BOTTOM_NAV_HOME}")

    print("\n【用户主页检测】")
    print(f"  用户头像: {DouyinElementIds.USER_PAGE_AVATAR}")
    print(f"  用户名字: {DouyinElementIds.USER_PAGE_NAME}")
    print(f"  抖音号: {DouyinElementIds.USER_PAGE_DOUYIN_ID}")

    print("=" * 80 + "\n")
