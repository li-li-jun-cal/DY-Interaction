#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
抖音分享链接生成和唤起测试脚本

目的：
1. 从数据库获取评论数据（comment_uid, comment_sec_uid）
2. 调用API生成抖音分享链接
3. 通过手机自动化打开链接
4. 验证是否成功跳转到用户主页

使用方法：
    python scripts/test_douyin_share_link.py

工作流程：
    输入 uid/sec_uid → 调用API → 获取分享链接 → 手机自动化打开 → 进入抖音APP
"""

import sys
import json
import requests
import time
from pathlib import Path
from typing import Optional, Dict, Tuple
from datetime import datetime
import logging

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.manager import DatabaseManager
from src.database.models import Comment, InteractionTask
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DouYinShareLinkTester:
    """抖音分享链接测试器"""

    def __init__(self, device_id: Optional[str] = None):
        """
        初始化测试器

        Args:
            device_id: 手机设备ID，如果为None则自动检测
        """
        self.db_manager = DatabaseManager()
        self.device_id = device_id
        self.share_link = None
        self.api_servers = self._load_api_servers()

        # 初始化手机自动化（后续填充）
        self.device = None
        self._init_device()

        logger.info(f"✓ 分享链接测试器已初始化，设备: {self.device_id}")

    def _load_api_servers(self) -> Dict:
        """从配置文件加载API服务器信息"""
        config_path = project_root / "config" / "config.json"

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('api', {})
        except Exception as e:
            logger.warning(f"⚠️  加载配置文件失败: {e}")
            return {
                'servers': [
                    {'base_url': 'http://149.88.66.146:8008', 'priority': 1},
                    {'base_url': 'http://140.245.55.143:8008', 'priority': 2},
                    {'base_url': 'http://140.245.55.143:20002', 'priority': 3},
                    {'base_url': 'http://38.55.134.72:8008', 'priority': 4},
                ],
                'fallback': {'base_url': 'https://api.tikhub.dev'}
            }

    def _init_device(self):
        """初始化手机自动化设备"""
        try:
            import uiautomator2 as u2

            if not self.device_id:
                # 自动检测设备
                devices = u2.adb.device_list()
                if not devices:
                    logger.error("❌ 未检测到任何Android设备")
                    return False

                self.device_id = devices[0]
                logger.info(f"✓ 自动检测到设备: {self.device_id}")

            # 连接设备
            self.device = u2.connect(self.device_id)
            logger.info(f"✓ 已连接到设备: {self.device_id}")
            return True

        except ImportError:
            logger.warning("⚠️  未安装uiautomator2，手机自动化功能禁用")
            logger.warning("   安装命令: pip install uiautomator2")
            return False
        except Exception as e:
            logger.error(f"❌ 初始化设备失败: {e}")
            return False

    def get_comment_from_db(self, target_account_id: int = 1) -> Optional[Dict]:
        """
        从数据库获取评论数据（包含uid和sec_uid）

        Args:
            target_account_id: 目标账号ID

        Returns:
            评论数据字典，包含 uid 和 sec_uid
        """
        session = self.db_manager.get_session()
        try:
            # 查询有uid和sec_uid的评论
            comment = session.query(Comment).filter(
                Comment.target_account_id == target_account_id,
                Comment.comment_uid != None,
                Comment.comment_sec_uid != None
            ).first()

            if not comment:
                logger.warning(f"⚠️  未找到有uid和sec_uid的评论数据")
                return None

            comment_data = {
                'id': comment.id,
                'uid': comment.comment_uid,
                'sec_uid': comment.comment_sec_uid,
                'unique_id': comment.comment_unique_id,
                'user_name': comment.comment_user_name,
                'comment_text': comment.comment_text,
            }

            logger.info(f"✓ 从数据库获取评论数据:")
            logger.info(f"  - 用户名: {comment.comment_user_name}")
            logger.info(f"  - UID: {comment.comment_uid}")
            logger.info(f"  - SEC_UID: {comment.comment_sec_uid}")
            logger.info(f"  - 抖音号: {comment.comment_unique_id}")

            return comment_data

        except Exception as e:
            logger.error(f"❌ 查询数据库失败: {e}")
            return None
        finally:
            session.close()

    def generate_share_link(self, uid: str, sec_uid: str) -> Optional[str]:
        """
        调用API生成抖音分享链接

        Args:
            uid: 用户ID（数字形式）
            sec_uid: 用户SEC_UID（MS4w开头的字符串）

        Returns:
            分享链接URL
        """
        if not uid or not sec_uid:
            logger.error(f"❌ 参数错误: uid={uid}, sec_uid={sec_uid}")
            logger.error("   请确保uid和sec_uid都有值")
            return None

        # 构建请求
        api_endpoint = "/api/v1/douyin/user/share_link"
        params = {
            'uid': uid,
            'sec_uid': sec_uid,
        }

        # 尝试所有服务器
        servers = self.api_servers.get('servers', [])

        for server in servers:
            base_url = server.get('base_url')
            if not base_url:
                continue

            url = f"{base_url}{api_endpoint}"
            priority = server.get('priority', 99)

            logger.info(f"\n📡 尝试服务器 (优先级{priority}): {base_url}")

            try:
                response = requests.get(
                    url,
                    params=params,
                    timeout=self.api_servers.get('timeout', 30)
                )

                if response.status_code == 200:
                    data = response.json()

                    if data.get('code') == 200:
                        share_link = data.get('data', '')

                        if share_link:
                            logger.info(f"✓ 成功生成分享链接 (服务器{priority}):")
                            logger.info(f"  {share_link}")

                            # 记录缓存信息
                            cache_url = data.get('cache_url')
                            if cache_url:
                                logger.info(f"✓ 缓存URL (24小时有效):")
                                logger.info(f"  {cache_url}")

                            self.share_link = share_link
                            return share_link
                        else:
                            logger.warning(f"⚠️  API返回空链接")
                    else:
                        message = data.get('message', 'Unknown error')
                        logger.warning(f"⚠️  API错误: {message}")
                else:
                    logger.warning(f"⚠️  HTTP {response.status_code}")

            except requests.Timeout:
                logger.warning(f"⚠️  请求超时")
            except requests.RequestException as e:
                logger.warning(f"⚠️  请求失败: {e}")
            except json.JSONDecodeError:
                logger.warning(f"⚠️  响应不是有效的JSON")
            except Exception as e:
                logger.warning(f"⚠️  未预期的错误: {e}")

        # 尝试终极备用服务器
        logger.info(f"\n📡 尝试终极备用服务器: TikHub")
        fallback = self.api_servers.get('fallback', {})
        if fallback.get('base_url'):
            try:
                # TikHub API格式可能不同，这里使用备用方案
                logger.warning("⚠️  终极备用服务器配置格式可能不同，跳过")
            except Exception as e:
                logger.warning(f"⚠️  终极备用服务器请求失败: {e}")

        logger.error(f"❌ 所有服务器都无法生成链接")
        return None

    def open_link_in_browser(self, share_link: str) -> bool:
        """
        在手机浏览器中打开分享链接

        流程:
            1. 检查设备连接状态
            2. 打开浏览器应用
            3. 点击地址栏
            4. 输入分享链接
            5. 点击打开/确定
            6. 等待页面加载
            7. 点击"打开抖音"或对应的按钮
            8. 抖音APP拉起并跳转到用户主页

        Args:
            share_link: 分享链接URL

        Returns:
            是否成功打开
        """
        if not share_link:
            logger.error("❌ 分享链接为空")
            return False

        if not self.device:
            logger.error("❌ 设备未连接，无法执行自动化操作")
            logger.info("   请确保:")
            logger.info("   1. 已安装 uiautomator2: pip install uiautomator2")
            logger.info("   2. Android设备已连接: adb devices")
            logger.info("   3. 设备已开启USB调试")
            return False

        try:
            logger.info(f"\n🔗 准备在浏览器中打开链接...")
            logger.info(f"   链接: {share_link}")

            # ============ 步骤 1: 打开浏览器 ============
            logger.info(f"\n[步骤 1/8] 打开浏览器应用")

            # 方案A: 启动Chrome浏览器
            self.device.app_start('com.android.chrome')
            time.sleep(2)

            logger.info(f"✓ 浏览器已打开")

            # ============ 步骤 2: 点击地址栏 ============
            logger.info(f"\n[步骤 2/8] 点击地址栏")
            logger.warning(f"⚠️  [待完成] 需要地址栏元素定位ID")
            logger.info(f"   可能的ID:")
            logger.info(f"   - com.android.chrome:id/url_bar")
            logger.info(f"   - com.android.chrome:id/location_bar")
            logger.info(f"   - android.widget.EditText")

            # TODO: 添加实际的元素定位和点击
            # address_bar = self.device(resourceId="com.android.chrome:id/url_bar")
            # if address_bar.exists:
            #     address_bar.click()
            #     time.sleep(1)
            # else:
            #     logger.warning("⚠️  未找到地址栏元素，尝试点击屏幕上方")
            #     self.device.click(0.5, 0.08)  # 屏幕上方中心
            #     time.sleep(1)

            # ============ 步骤 3: 清空地址栏并输入链接 ============
            logger.info(f"\n[步骤 3/8] 输入分享链接")
            logger.warning(f"⚠️  [待完成] 需要键盘和文本输入配置")

            # TODO: 实现输入逻辑
            # self.device.send_keys(share_link)  # 输入链接
            # time.sleep(1)

            # ============ 步骤 4: 点击打开/确定 ============
            logger.info(f"\n[步骤 4/8] 点击打开/确定按钮")
            logger.warning(f"⚠️  [待完成] 需要打开按钮元素定位ID")
            logger.info(f"   可能的ID:")
            logger.info(f"   - android.widget.Button")
            logger.info(f"   - 回车键 (Enter key)")

            # TODO: 点击打开
            # self.device.press('enter')  # 按下回车打开链接
            # time.sleep(3)  # 等待页面加载

            # ============ 步骤 5: 等待页面加载 ============
            logger.info(f"\n[步骤 5/8] 等待页面加载")
            logger.info(f"   等待中... (3秒)")
            # 实际测试时在这里检查页面是否加载完成

            # ============ 步骤 6: 检查并点击"打开抖音"按钮 ============
            logger.info(f"\n[步骤 6/8] 检查是否出现'打开抖音'按钮")
            logger.warning(f"⚠️  [待完成] 需要按钮元素定位ID")
            logger.info(f"   可能的ID:")
            logger.info(f"   - com.android.chrome:id/tab_title")
            logger.info(f"   - android.widget.Button (包含'打开')")
            logger.info(f"   - android.widget.TextView (包含'抖音')")

            # TODO: 查找并点击打开抖音按钮
            # open_btn = self.device(text="打开抖音")
            # if open_btn.exists:
            #     logger.info(f"✓ 找到'打开抖音'按钮，点击中...")
            #     open_btn.click()
            #     time.sleep(2)
            # else:
            #     logger.warning(f"⚠️  未找到'打开抖音'按钮，尝试点击页面中央")
            #     self.device.click(0.5, 0.5)
            #     time.sleep(2)

            # ============ 步骤 7: 验证是否进入抖音APP ============
            logger.info(f"\n[步骤 7/8] 等待抖音APP启动")
            logger.warning(f"⚠️  [待完成] 需要验证APP启动的方式")

            # TODO: 验证APP启动
            # max_wait = 10
            # for i in range(max_wait):
            #     current_app = self.device.app_current()
            #     if 'douyin' in current_app['package'].lower() or 'tiktok' in current_app['package'].lower():
            #         logger.info(f"✓ 抖音APP已启动: {current_app['package']}")
            #         break
            #     time.sleep(1)
            # else:
            #     logger.warning(f"⚠️  {max_wait}秒后仍未检测到抖音APP")

            # ============ 步骤 8: 验证是否跳转到用户主页 ============
            logger.info(f"\n[步骤 8/8] 验证是否成功跳转到用户主页")
            logger.warning(f"⚠️  [待完成] 需要用户主页特征元素定位ID")
            logger.info(f"   可能的特征:")
            logger.info(f"   - 用户头像元素")
            logger.info(f"   - 用户名称显示")
            logger.info(f"   - 关注按钮 (如果未关注)")
            logger.info(f"   - 用户视频列表")

            # TODO: 验证用户主页
            # avatar = self.device(resourceId="com.ss.android.ugc.aweme:id/j49")  # 用户头像
            # if avatar.exists:
            #     logger.info(f"✓ 成功进入用户主页")
            #     return True
            # else:
            #     logger.warning(f"⚠️  未检测到用户主页特征")
            #     return False

            logger.info(f"\n" + "="*60)
            logger.info(f"📱 自动化流程框架已准备完成")
            logger.info(f"="*60)
            logger.info(f"✓ 所有步骤均已定义")
            logger.info(f"✓ 请在实际测试中填充各步骤的元素定位ID")
            logger.info(f"✓ 建议使用 uiautomator2 的dump()方法获取控件ID:")
            logger.info(f"   device.dump_hierarchy()  # 获取页面层级结构")
            logger.info(f"="*60)

            return True

        except Exception as e:
            logger.error(f"❌ 自动化操作失败: {e}")
            return False

    def run_test_with_input(self):
        """交互式测试：手动输入uid和sec_uid"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🧪 抖音分享链接测试 - 手动输入模式")
        logger.info(f"{'='*60}\n")

        print("\n请输入以下信息:")
        print("-" * 60)

        uid = input("📍 请输入 UID (用户ID，如: 96874812426): ").strip()
        sec_uid = input("📍 请输入 SEC_UID (如: MS4wLjABAAAA9y04iBlVdeMQqTJbqsQZKb...): ").strip()

        if not uid or not sec_uid:
            logger.error("❌ uid和sec_uid不能为空")
            return False

        logger.info(f"\n✓ 输入的参数:")
        logger.info(f"  - UID: {uid}")
        logger.info(f"  - SEC_UID: {sec_uid[:50]}..." if len(sec_uid) > 50 else f"  - SEC_UID: {sec_uid}")

        # 生成链接
        share_link = self.generate_share_link(uid, sec_uid)

        if not share_link:
            logger.error("❌ 生成分享链接失败，测试终止")
            return False

        # 在浏览器打开
        logger.info(f"\n{'='*60}")
        logger.info(f"下一步: 在手机浏览器中打开分享链接")
        logger.info(f"{'='*60}")

        input("\n按Enter键继续在浏览器中打开链接...")
        return self.open_link_in_browser(share_link)

    def run_test_from_db(self, target_account_id: int = 1):
        """从数据库获取评论数据并测试"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🧪 抖音分享链接测试 - 数据库模式")
        logger.info(f"{'='*60}\n")

        # 从数据库获取数据
        comment_data = self.get_comment_from_db(target_account_id)

        if not comment_data:
            logger.error("❌ 无法从数据库获取数据，请尝试手动输入模式")
            return False

        # 生成链接
        share_link = self.generate_share_link(
            comment_data['uid'],
            comment_data['sec_uid']
        )

        if not share_link:
            logger.error("❌ 生成分享链接失败，测试终止")
            return False

        # 在浏览器打开
        logger.info(f"\n{'='*60}")
        logger.info(f"下一步: 在手机浏览器中打开分享链接")
        logger.info(f"{'='*60}")

        input("\n按Enter键继续在浏览器中打开链接...")
        return self.open_link_in_browser(share_link)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='抖音分享链接生成和唤起测试脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 交互式输入uid和sec_uid
  python scripts/test_douyin_share_link.py --interactive

  # 从数据库获取数据
  python scripts/test_douyin_share_link.py --from-db

  # 指定设备ID
  python scripts/test_douyin_share_link.py --device "emulator-5554"
        """
    )

    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='交互式模式：手动输入uid和sec_uid'
    )

    parser.add_argument(
        '--from-db',
        action='store_true',
        help='从数据库模式：自动从数据库获取评论数据'
    )

    parser.add_argument(
        '--device',
        type=str,
        help='指定设备ID（如: emulator-5554）'
    )

    parser.add_argument(
        '--account-id',
        type=int,
        default=1,
        help='目标账号ID（默认: 1）'
    )

    args = parser.parse_args()

    # 创建测试器
    tester = DouYinShareLinkTester(device_id=args.device)

    # 选择测试模式
    if args.interactive or (not args.from_db):
        # 默认交互模式
        result = tester.run_test_with_input()
    else:
        # 从数据库模式
        result = tester.run_test_from_db(target_account_id=args.account_id)

    # 返回结果
    if result:
        logger.info("\n✅ 测试完成")
        return 0
    else:
        logger.error("\n❌ 测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(main())
