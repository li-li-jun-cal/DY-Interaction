#!/usr/bin/env python3
"""
测试桌面检测和应用管理功能
"""

import sys
from pathlib import Path

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import time
from src.executor.douyin_operations import DouyinOperations
from src.database.manager import DatabaseManager

def test_desktop_detection_and_app_management():
    """测试桌面检测和应用管理功能"""
    print("=" * 70)
    print("🧪 测试桌面检测和应用管理功能")
    print("=" * 70)

    # 选择设备
    device_id = "Device-1"
    print(f"\n使用设备: {device_id}")

    try:
        # 初始化
        db = DatabaseManager()
        ops = DouyinOperations(device_id, db)

        print("\n测试1: 检测当前页面")
        print("-" * 70)
        current_page = ops.navigator.detect_current_page()
        print(f"  当前页面: {current_page}")

        print("\n测试2: 关闭抖音应用")
        print("-" * 70)
        ops.navigator.stop_douyin_app()
        time.sleep(2)

        print("\n测试3: 再次检测页面（应该在桌面）")
        print("-" * 70)
        current_page = ops.navigator.detect_current_page()
        print(f"  当前页面: {current_page}")

        if current_page == "desktop":
            print("  ✓ 桌面检测成功！")
        else:
            print("  ⚠ 未检测到桌面")

        print("\n测试4: 重新启动抖音")
        print("-" * 70)
        ops.navigator.start_douyin_app()
        time.sleep(3)

        print("\n测试5: 确保回到首页")
        print("-" * 70)
        success = ops.navigator.ensure_on_homepage()
        if success:
            print("  ✓ 成功返回首页！")
        else:
            print("  ✗ 返回首页失败")

        print("\n测试6: 最终页面检测")
        print("-" * 70)
        current_page = ops.navigator.detect_current_page()
        print(f"  当前页面: {current_page}")

        print("\n" + "=" * 70)
        print("✓ 测试完成")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_desktop_detection_and_app_management()
