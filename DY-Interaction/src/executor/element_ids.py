"""
抖音APP元素ID配置 - vivo S12 专用版本
简化版：移除 OPPO 设备支持，只保留 vivo S12 (PD2072) 的元素ID
"""

class DouyinElementIds:
    """
    抖音元素ID类 - vivo S12 专用
    """

    # ========== 搜索流程元素 ==========
    # 注意：这些搜索元素适用于多个场景（首页搜索、商城搜索、团购搜索）
    SEARCH_BUTTON = 'com.ss.android.ugc.aweme:id/1r2'           # 搜索按钮
    SEARCH_INPUT = 'com.ss.android.ugc.aweme:id/et_search_kw'   # 搜索输入框（通用）
    SEARCH_CONFIRM = 'com.ss.android.ugc.aweme:id/33a'          # 搜索确认按钮（通用）
    SEARCH_RESULT_TEXT_ELEMENT = 'android:id/text1'             # 搜索结果文本元素

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

    # ========== 顶部Tab导航（共用同一个ID，需通过text区分）==========
    # 注意：这些Tab共用 resourceId: com.ss.android.ugc.aweme:id/4ba
    # 使用方式：d(resourceId=TOP_TAB_COMMON, text=TAB_RECOMMEND).click()
    TOP_TAB_COMMON = 'com.ss.android.ugc.aweme:id/4ba'  # 顶部Tab共用ID

    # Tab名称常量（从右到左顺序：推荐、关注、商城、直播、团购）
    TAB_RECOMMEND = "推荐"      # 首页推荐流
    TAB_FOLLOW = "关注"         # 关注的用户动态
    TAB_MALL = "商城"           # 抖音商城
    TAB_LIVE = "直播"           # 直播间入口
    TAB_GROUP_BUY = "团购"      # 团购活动

    # ========== 首页视频流元素（最重要）==========
    LIKE_BUTTON = 'com.ss.android.ugc.aweme:id/gas'  # 点赞按钮 - 用于检测是否在首页
    COLLECT_BUTTON = 'com.ss.android.ugc.aweme:id/d-z'
    SHARE_BUTTON = 'com.ss.android.ugc.aweme:id/yv+'
    HOMEPAGE_USER_AVATAR = 'com.ss.android.ugc.aweme:id/bi='

    # ========== 直播间元素 ==========
    # 直播间检测和导航
    LIVE_ROOM_INDICATOR = 'com.ss.android.ugc.aweme:id/syx'  # 直播间页面标识
    LIVE_ROOM_ENTRANCE = 'com.ss.android.ugc.aweme:id/rkz'   # 直播间入口（点击进入直播间）
    LIVE_ROOM_EXIT = 'com.ss.android.ugc.aweme:id/close_btn'  # 退出直播间按钮

    # 直播间互动操作
    LIVE_ROOM_COMMENT_BUTTON = 'com.ss.android.ugc.aweme:id/hn4'  # 评论按钮
    LIVE_ROOM_COMMENT_INPUT = 'com.ss.android.ugc.aweme:id/hqk'   # 评论输入框
    LIVE_ROOM_COMMENT_SEND = 'com.ss.android.ugc.aweme:id/34j'    # 评论发送按钮
    LIVE_ROOM_LIKE_AREA = 'com.ss.android.ugc.aweme:id/j_q'       # 点赞区域（点击即点赞）
    LIVE_ROOM_FOLLOW_BUTTON = 'com.ss.android.ugc.aweme:id/jp9'   # 关注按钮（文本："关注"）

    # ========== 商城和团购元素 ==========
    # 注意：商城和团购的商品卡片没有固定ID，需通过滑动(swipe)浏览
    # 搜索功能：复用 SEARCH_INPUT 和 SEARCH_CONFIRM 元素
    # 使用方式：
    #   1. 切换到商城/团购Tab: d(resourceId=TOP_TAB_COMMON, text=TAB_MALL).click()
    #   2. 点击搜索输入框: d(resourceId=SEARCH_INPUT).click()
    #   3. 输入搜索内容: d(resourceId=SEARCH_INPUT).set_text("商品名")
    #   4. 点击搜索: d(resourceId=SEARCH_CONFIRM).click()
    #   5. 浏览商品: d.swipe(start_x, start_y, end_x, end_y, duration)

    # ========== 特殊情况检测元素 ==========
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

    print("\n【顶部Tab导航】")
    print(f"  Tab共用ID: {DouyinElementIds.TOP_TAB_COMMON}")
    print(f"  推荐: {DouyinElementIds.TAB_RECOMMEND}")
    print(f"  关注: {DouyinElementIds.TAB_FOLLOW}")
    print(f"  商城: {DouyinElementIds.TAB_MALL}")
    print(f"  直播: {DouyinElementIds.TAB_LIVE}")
    print(f"  团购: {DouyinElementIds.TAB_GROUP_BUY}")

    print("\n【直播间操作】")
    print(f"  直播间入口: {DouyinElementIds.LIVE_ROOM_ENTRANCE}")
    print(f"  评论按钮: {DouyinElementIds.LIVE_ROOM_COMMENT_BUTTON}")
    print(f"  评论输入框: {DouyinElementIds.LIVE_ROOM_COMMENT_INPUT}")
    print(f"  评论发送: {DouyinElementIds.LIVE_ROOM_COMMENT_SEND}")
    print(f"  点赞区域: {DouyinElementIds.LIVE_ROOM_LIKE_AREA}")
    print(f"  关注按钮: {DouyinElementIds.LIVE_ROOM_FOLLOW_BUTTON}")
    print(f"  退出直播间: {DouyinElementIds.LIVE_ROOM_EXIT}")

    print("=" * 80 + "\n")
