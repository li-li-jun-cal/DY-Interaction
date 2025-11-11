"""
测试首页检测逻辑
验证3个关键元素的检测：
1. com.ss.android.ugc.aweme:id/4ba (BOTTOM_NAV_COMMON)
2. com.ss.android.ugc.aweme:id/0tr (BOTTOM_NAV_HOME)
3. com.ss.android.ugc.aweme:id/jm7 (HOMEPAGE_FOLLOW_BUTTON)
"""
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.executor.douyin_operations import DouyinOperations
from src.executor.page_navigator import PageNavigator
from src.executor.element_ids import DouyinElementIds
from src.utils.logger import setup_logger

def test_homepage_detection():
    """测试首页检测"""
    logger = setup_logger("test_homepage")

    # 获取第一个连接的设备
    import subprocess
    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
    lines = [line for line in result.stdout.strip().split('\n')[1:] if line.strip() and 'offline' not in line]

    if not lines:
        logger.error("❌ 没有找到连接的设备")
        return False

    device_id = lines[0].split()[0]
    logger.info(f"使用设备: {device_id}")

    # 初始化
    ops = DouyinOperations(device_id, logger)
    navigator = PageNavigator(ops, logger)
    element_ids = DouyinElementIds

    logger.info("=" * 80)
    logger.info("测试首页检测逻辑（3元素检测法）")
    logger.info("=" * 80)

    # 1. 检测3个关键元素
    logger.info("\n[步骤1] 检测3个关键元素...")

    bottom_nav_common_id = element_ids.BOTTOM_NAV_COMMON
    bottom_nav_home_id = element_ids.BOTTOM_NAV_HOME
    homepage_follow_id = element_ids.HOMEPAGE_FOLLOW_BUTTON

    logger.info(f"  检查元素1: {bottom_nav_common_id}")
    has_common = ops.element_exists(resourceId=bottom_nav_common_id)
    logger.info(f"    → 结果: {'✓ 存在' if has_common else '✗ 不存在'}")

    logger.info(f"  检查元素2: {bottom_nav_home_id}")
    has_home = ops.element_exists(resourceId=bottom_nav_home_id)
    logger.info(f"    → 结果: {'✓ 存在' if has_home else '✗ 不存在'}")

    logger.info(f"  检查元素3: {homepage_follow_id}")
    has_follow = ops.element_exists(resourceId=homepage_follow_id)
    logger.info(f"    → 结果: {'✓ 存在' if has_follow else '✗ 不存在'}")

    # 2. 判断是否在首页
    logger.info("\n[步骤2] 判断是否在首页...")
    is_homepage = has_common and has_home and has_follow

    if is_homepage:
        logger.info("  ✓ 3个元素都存在，确认在首页！")
    else:
        missing = []
        if not has_common:
            missing.append(f"BOTTOM_NAV_COMMON ({bottom_nav_common_id})")
        if not has_home:
            missing.append(f"BOTTOM_NAV_HOME ({bottom_nav_home_id})")
        if not has_follow:
            missing.append(f"HOMEPAGE_FOLLOW_BUTTON ({homepage_follow_id})")

        logger.warning(f"  ✗ 不在首页，缺少以下元素: {', '.join(missing)}")

    # 3. 使用PageNavigator检测
    logger.info("\n[步骤3] 使用PageNavigator检测当前页面...")
    current_page = navigator.detect_current_page()
    logger.info(f"  检测结果: {current_page}")

    if current_page == navigator.PAGE_HOME:
        logger.info("  ✓ PageNavigator确认在首页")
    else:
        logger.warning(f"  ✗ PageNavigator检测为: {current_page}")

    # 4. 测试导航到首页
    logger.info("\n[步骤4] 测试确保在首页功能...")
    success = navigator.ensure_on_homepage()

    if success:
        logger.info("  ✓ 成功确保在首页")
    else:
        logger.error("  ✗ 无法导航到首页")

    # 5. 再次验证
    logger.info("\n[步骤5] 最终验证...")
    final_page = navigator.detect_current_page()
    logger.info(f"  最终页面: {final_page}")

    logger.info("\n" + "=" * 80)
    if final_page == navigator.PAGE_HOME:
        logger.info("✅ 测试通过：首页检测逻辑正常工作")
        return True
    else:
        logger.error("❌ 测试失败：无法正确检测或导航到首页")
        return False

if __name__ == "__main__":
    print("\n")
    print("=" * 80)
    print("首页检测逻辑测试")
    print("=" * 80)
    print("\n请确保：")
    print("1. 设备已连接并解锁")
    print("2. 抖音应用已安装")
    print("3. 设备当前在抖音首页或其他页面")
    print("\n按 Enter 继续...")
    input()

    success = test_homepage_detection()

    print("\n" + "=" * 80)
    if success:
        print("✅ 所有测试通过")
    else:
        print("❌ 测试失败")
    print("=" * 80)
