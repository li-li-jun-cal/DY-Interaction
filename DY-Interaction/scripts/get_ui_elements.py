#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
UI元素定位助手

用途：帮助快速获取Android UI控件的ID、文本、坐标等信息，
      用于填充test_douyin_share_link.py中各个步骤的元素定位。

使用方法：
    1. 连接设备: adb devices
    2. 打开要查询的应用界面
    3. 运行本脚本: python scripts/get_ui_elements.py
    4. 根据提示选择要查询的内容
"""

import sys
from pathlib import Path
from typing import Optional, Dict, List
import json
import time

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import get_logger

logger = get_logger(__name__)


class UIElementFinder:
    """UI元素查询工具"""

    def __init__(self, device_id: Optional[str] = None):
        """
        初始化工具

        Args:
            device_id: 设备ID，如果为None则自动检测
        """
        self.device_id = device_id
        self.device = None
        self._init_device()

    def _init_device(self) -> bool:
        """初始化设备连接"""
        try:
            import uiautomator2 as u2

            if not self.device_id:
                devices = u2.adb.device_list()
                if not devices:
                    logger.error("❌ 未检测到任何Android设备")
                    return False
                self.device_id = devices[0]
                logger.info(f"✓ 自动检测到设备: {self.device_id}")

            self.device = u2.connect(self.device_id)
            logger.info(f"✓ 已连接到设备: {self.device_id}")
            return True

        except ImportError:
            logger.error("❌ 未安装uiautomator2")
            logger.info("   安装命令: pip install uiautomator2")
            return False
        except Exception as e:
            logger.error(f"❌ 初始化设备失败: {e}")
            return False

    def dump_hierarchy(self, save_file: bool = True) -> Optional[Dict]:
        """
        导出页面层级结构（UI树）

        Args:
            save_file: 是否保存到文件

        Returns:
            页面层级字典
        """
        if not self.device:
            logger.error("❌ 设备未连接")
            return None

        try:
            logger.info("\n📸 正在导出页面层级结构...")
            hierarchy = self.device.dump_hierarchy()

            if save_file:
                output_file = Path.cwd() / "ui_hierarchy.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(hierarchy, f, indent=2, ensure_ascii=False)
                logger.info(f"✓ 层级结构已保存到: {output_file}")
                logger.info(f"✓ 可以用文本编辑器打开查看UI树结构")

            return hierarchy

        except Exception as e:
            logger.error(f"❌ 导出失败: {e}")
            return None

    def find_element_by_text(self, text: str) -> Optional[List[Dict]]:
        """
        根据文本查找元素

        Args:
            text: 要查找的文本（支持模糊匹配）

        Returns:
            匹配的元素列表
        """
        if not self.device:
            logger.error("❌ 设备未连接")
            return None

        try:
            logger.info(f"\n🔍 查找包含 '{text}' 的元素...")

            elements = self.device(text__contains=text)
            if elements.exists:
                logger.info(f"✓ 找到 {len(elements)} 个匹配元素:")

                result = []
                for elem in elements:
                    info = {
                        'text': elem.get_text(),
                        'className': elem.info.get('className'),
                        'resourceId': elem.info.get('resourceId'),
                        'contentDescription': elem.info.get('contentDescription'),
                        'bounds': elem.info.get('bounds'),
                        'center': elem.center(),
                    }
                    result.append(info)

                    logger.info(f"\n  ├─ 文本: {info['text']}")
                    logger.info(f"  ├─ 类型: {info['className']}")
                    logger.info(f"  ├─ ID: {info['resourceId']}")
                    logger.info(f"  ├─ 描述: {info['contentDescription']}")
                    logger.info(f"  ├─ 位置: {info['center']}")
                    logger.info(f"  └─ 边界: {info['bounds']}")

                return result
            else:
                logger.warning(f"⚠️  未找到包含 '{text}' 的元素")
                return None

        except Exception as e:
            logger.error(f"❌ 查找失败: {e}")
            return None

    def find_element_by_id(self, resource_id: str) -> Optional[Dict]:
        """
        根据Resource ID查找元素

        Args:
            resource_id: 资源ID（如: com.android.chrome:id/url_bar）

        Returns:
            元素信息
        """
        if not self.device:
            logger.error("❌ 设备未连接")
            return None

        try:
            logger.info(f"\n🔍 查找ID为 '{resource_id}' 的元素...")

            element = self.device(resourceId=resource_id)
            if element.exists:
                logger.info(f"✓ 找到元素:")

                info = {
                    'text': element.get_text(),
                    'className': element.info.get('className'),
                    'resourceId': resource_id,
                    'contentDescription': element.info.get('contentDescription'),
                    'bounds': element.info.get('bounds'),
                    'center': element.center(),
                    'clickable': element.info.get('clickable'),
                    'enabled': element.info.get('enabled'),
                }

                logger.info(f"  ├─ 文本: {info['text']}")
                logger.info(f"  ├─ 类型: {info['className']}")
                logger.info(f"  ├─ 描述: {info['contentDescription']}")
                logger.info(f"  ├─ 可点击: {info['clickable']}")
                logger.info(f"  ├─ 已启用: {info['enabled']}")
                logger.info(f"  ├─ 位置: {info['center']}")
                logger.info(f"  └─ 边界: {info['bounds']}")

                return info
            else:
                logger.warning(f"⚠️  未找到ID为 '{resource_id}' 的元素")
                return None

        except Exception as e:
            logger.error(f"❌ 查找失败: {e}")
            return None

    def find_element_by_class(self, class_name: str) -> Optional[List[Dict]]:
        """
        根据类名查找元素

        Args:
            class_name: 类名（如: android.widget.EditText）

        Returns:
            匹配的元素列表
        """
        if not self.device:
            logger.error("❌ 设备未连接")
            return None

        try:
            logger.info(f"\n🔍 查找类型为 '{class_name}' 的元素...")

            elements = self.device(className=class_name)
            if elements.exists:
                logger.info(f"✓ 找到 {len(elements)} 个 {class_name} 元素:")

                result = []
                for i, elem in enumerate(elements, 1):
                    info = {
                        'index': i,
                        'text': elem.get_text(),
                        'className': class_name,
                        'resourceId': elem.info.get('resourceId'),
                        'contentDescription': elem.info.get('contentDescription'),
                        'bounds': elem.info.get('bounds'),
                        'center': elem.center(),
                    }
                    result.append(info)

                    logger.info(f"\n  [{i}] 文本: {info['text']}")
                    logger.info(f"      ID: {info['resourceId']}")
                    logger.info(f"      中心坐标: {info['center']}")

                return result
            else:
                logger.warning(f"⚠️  未找到 {class_name} 元素")
                return None

        except Exception as e:
            logger.error(f"❌ 查找失败: {e}")
            return None

    def screenshot(self, filename: str = "screenshot.png") -> bool:
        """
        截图

        Args:
            filename: 保存文件名

        Returns:
            是否成功
        """
        if not self.device:
            logger.error("❌ 设备未连接")
            return False

        try:
            self.device.screenshot(filename)
            logger.info(f"✓ 截图已保存: {filename}")
            return True
        except Exception as e:
            logger.error(f"❌ 截图失败: {e}")
            return False

    def list_all_clickable_elements(self) -> Optional[List[Dict]]:
        """
        列出所有可点击的元素

        Returns:
            可点击元素列表
        """
        if not self.device:
            logger.error("❌ 设备未连接")
            return None

        try:
            logger.info("\n🔍 搜索所有可点击的元素...")

            elements = self.device(clickable=True)
            if elements.exists:
                logger.info(f"✓ 找到 {len(elements)} 个可点击元素:")

                result = []
                for i, elem in enumerate(elements, 1):
                    if i > 20:  # 限制输出数量
                        logger.info(f"\n  ... 还有 {len(elements) - 20} 个元素")
                        break

                    info = {
                        'index': i,
                        'text': elem.get_text() or '(无文本)',
                        'className': elem.info.get('className', '')[-30:],  # 截断显示
                        'resourceId': elem.info.get('resourceId'),
                        'center': elem.center(),
                    }
                    result.append(info)

                    logger.info(f"\n  [{i:2d}] {info['text'][:30]}")
                    logger.info(f"       ID: {info['resourceId']}")
                    logger.info(f"       类型: {info['className']}")
                    logger.info(f"       中心: {info['center']}")

                return result
            else:
                logger.warning(f"⚠️  未找到可点击的元素")
                return None

        except Exception as e:
            logger.error(f"❌ 查找失败: {e}")
            return None

    def interactive_search(self):
        """交互式搜索UI元素"""
        while True:
            print("\n" + "="*60)
            print("🔍 UI元素查询工具")
            print("="*60)
            print("\n请选择查询方式:")
            print("  1. 导出完整页面层级 (保存为JSON)")
            print("  2. 根据文本查找元素 (如: '打开')")
            print("  3. 根据ID查找元素")
            print("  4. 根据类型查找元素 (如: android.widget.Button)")
            print("  5. 列出所有可点击的元素")
            print("  6. 截图")
            print("  0. 退出")
            print("-"*60)

            choice = input("\n请选择 (0-6): ").strip()

            if choice == '0':
                logger.info("👋 再见!")
                break
            elif choice == '1':
                self.dump_hierarchy()
            elif choice == '2':
                text = input("请输入要查找的文本: ").strip()
                if text:
                    self.find_element_by_text(text)
            elif choice == '3':
                res_id = input("请输入Resource ID (如: com.android.chrome:id/url_bar): ").strip()
                if res_id:
                    self.find_element_by_id(res_id)
            elif choice == '4':
                class_name = input("请输入类名 (如: android.widget.Button): ").strip()
                if class_name:
                    self.find_element_by_class(class_name)
            elif choice == '5':
                self.list_all_clickable_elements()
            elif choice == '6':
                filename = input("请输入截图文件名 (默认: screenshot.png): ").strip()
                if not filename:
                    filename = "screenshot.png"
                self.screenshot(filename)
            else:
                logger.warning("❌ 无效选择，请重试")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Android UI元素定位助手',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 交互模式
  python scripts/get_ui_elements.py

  # 导出页面层级
  python scripts/get_ui_elements.py --dump

  # 根据文本查找
  python scripts/get_ui_elements.py --find-text "打开"

  # 查找所有可点击元素
  python scripts/get_ui_elements.py --clickable

  # 指定设备
  python scripts/get_ui_elements.py --device "emulator-5554"
        """
    )

    parser.add_argument(
        '--dump',
        action='store_true',
        help='导出完整页面层级'
    )

    parser.add_argument(
        '--find-text',
        type=str,
        help='根据文本查找元素'
    )

    parser.add_argument(
        '--find-id',
        type=str,
        help='根据ID查找元素'
    )

    parser.add_argument(
        '--find-class',
        type=str,
        help='根据类名查找元素'
    )

    parser.add_argument(
        '--clickable',
        action='store_true',
        help='列出所有可点击的元素'
    )

    parser.add_argument(
        '--screenshot',
        type=str,
        nargs='?',
        const='screenshot.png',
        help='截图（可指定文件名）'
    )

    parser.add_argument(
        '--device',
        type=str,
        help='指定设备ID'
    )

    args = parser.parse_args()

    # 创建工具
    finder = UIElementFinder(device_id=args.device)

    if not finder.device:
        logger.error("❌ 无法连接到设备，退出")
        return 1

    # 执行相应命令
    if args.dump:
        finder.dump_hierarchy()
    elif args.find_text:
        finder.find_element_by_text(args.find_text)
    elif args.find_id:
        finder.find_element_by_id(args.find_id)
    elif args.find_class:
        finder.find_element_by_class(args.find_class)
    elif args.clickable:
        finder.list_all_clickable_elements()
    elif args.screenshot:
        finder.screenshot(args.screenshot)
    else:
        # 默认交互模式
        finder.interactive_search()

    return 0


if __name__ == '__main__':
    sys.exit(main())
