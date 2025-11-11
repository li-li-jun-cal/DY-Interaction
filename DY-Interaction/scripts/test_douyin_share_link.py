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
            import subprocess

            if not self.device_id:
                # 使用adb命令获取设备列表
                logger.info("正在自动检测Android设备...")
                result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
                lines = result.stdout.strip().split('\n')[1:]  # 跳过第一行标题
                devices = [line.split()[0] for line in lines if line.strip() and 'device' in line]

                logger.info(f"检测到 {len(devices)} 个设备: {devices}")

                if not devices:
                    logger.error("❌ 未检测到任何Android设备")
                    logger.error("   请检查:")
                    logger.error("   1. 设备是否通过USB连接")
                    logger.error("   2. 设备是否开启USB调试")
                    logger.error("   3. 运行 'adb devices' 查看设备状态")
                    return False

                self.device_id = devices[0]
                logger.info(f"✓ 自动选择设备: {self.device_id}")

            # 连接设备
            logger.info(f"正在连接设备: {self.device_id}")
            self.device = u2.connect(self.device_id)

            # 验证连接
            device_info = self.device.info
            logger.info(f"✓ 已连接到设备: {self.device_id}")
            logger.info(f"   设备型号: {device_info.get('productName', 'Unknown')}")
            logger.info(f"   Android版本: {device_info.get('version', 'Unknown')}")
            return True

        except ImportError as e:
            logger.error(f"❌ 未安装uiautomator2: {e}")
            logger.error("   安装命令: pip install uiautomator2")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ ADB命令执行失败: {e}")
            logger.error("   请确保已安装Android SDK并配置环境变量")
            return False
        except Exception as e:
            logger.error(f"❌ 初始化设备失败: {e}")
            import traceback
            logger.error(f"   详细错误:\n{traceback.format_exc()}")
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

        # 直接使用备用服务器(TikHub API)
        fallback = self.api_servers.get('fallback', {})
        base_url = fallback.get('base_url')
        api_key = fallback.get('api_key')

        if not base_url:
            logger.error(f"❌ 备用服务器配置缺失")
            return None

        if not api_key:
            logger.error(f"❌ TikHub API密钥缺失")
            return None

        # 构建TikHub API请求
        # 注意: TikHub API的端点是 /api/v1/douyin/app/v3/open_douyin_app_to_user_profile
        api_endpoint = "/api/v1/douyin/app/v3/open_douyin_app_to_user_profile"
        url = f"{base_url}{api_endpoint}"
        params = {
            'uid': uid,
            'sec_uid': sec_uid,
        }
        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {api_key}',  # 使用Bearer Token认证
        }

        logger.info(f"\n📡 使用备用服务器: {base_url}")
        logger.info(f"   API密钥: {api_key[:20]}..." if len(api_key) > 20 else f"   API密钥: {api_key}")

        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,  # 添加认证头
                timeout=self.api_servers.get('timeout', 30)
            )

            if response.status_code == 200:
                data = response.json()

                if data.get('code') == 200:
                    # TikHub API返回格式: data.data.short_url
                    result_data = data.get('data', {})
                    share_link = result_data.get('short_url', '')

                    if share_link:
                        logger.info(f"✓ 成功生成分享链接:")
                        logger.info(f"  {share_link}")

                        # 记录缓存信息
                        cache_url = data.get('cache_url')
                        if cache_url:
                            logger.info(f"✓ 缓存URL (24小时有效):")
                            logger.info(f"  {cache_url}")

                        # 记录请求ID
                        request_id = data.get('request_id')
                        if request_id:
                            logger.info(f"✓ 请求ID: {request_id}")

                        self.share_link = share_link
                        return share_link
                    else:
                        logger.error(f"❌ API返回空链接")
                        logger.error(f"   响应数据: {result_data}")
                        return None
                else:
                    message = data.get('message', 'Unknown error')
                    message_zh = data.get('message_zh', '')
                    logger.error(f"❌ API错误: {message}")
                    if message_zh:
                        logger.error(f"   中文说明: {message_zh}")
                    return None
            else:
                logger.error(f"❌ HTTP {response.status_code}: {response.text}")
                return None

        except requests.Timeout:
            logger.error(f"❌ 请求超时")
            return None
        except requests.RequestException as e:
            logger.error(f"❌ 请求失败: {e}")
            return None
        except json.JSONDecodeError:
            logger.error(f"❌ 响应不是有效的JSON: {response.text}")
            return None
        except Exception as e:
            logger.error(f"❌ 未预期的错误: {e}")
            return None

    def open_link_in_browser(self, share_link: str) -> bool:
        """
        在手机浏览器中打开分享链接 (针对vivo浏览器优化)

        流程:
            1. 返回桌面
            2. 打开浏览器应用
            3. 跳过广告
            4. 点击搜索框
            5. 输入分享链接
            6. 点击进入按钮
            7. 点击"打开"按钮
            8. 验证是否跳转到用户主页

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
            d = self.device  # 简化引用
            logger.info(f"\n🔗 准备在浏览器中打开链接...")
            logger.info(f"   链接: {share_link}")

            # ============ 步骤 1: 返回桌面 ============
            logger.info(f"\n[步骤 1/8] 返回桌面")
            try:
                home_btn = d(resourceId="com.android.systemui:id/home")
                if home_btn.exists(timeout=2):
                    home_btn.click()
                    logger.info(f"✓ 已点击Home按钮返回桌面")
                else:
                    # 备用方案: 使用按键
                    d.press("home")
                    logger.info(f"✓ 已使用按键返回桌面")
                time.sleep(1)
            except Exception as e:
                logger.warning(f"⚠️  返回桌面失败: {e}，继续执行")

            # ============ 步骤 2: 打开浏览器 ============
            logger.info(f"\n[步骤 2/8] 打开浏览器应用")

            # 方案1: 使用包名启动
            try:
                d.app_start('com.vivo.browser')
                logger.info(f"✓ 已通过包名启动浏览器")
            except Exception as e:
                logger.warning(f"⚠️  包名启动失败: {e}")

                # 方案2: 文本定位
                try:
                    browser_icon = d(text="浏览器")
                    if browser_icon.exists(timeout=3):
                        browser_icon.click()
                        logger.info(f"✓ 已通过文本定位启动浏览器")
                    else:
                        # 方案3: 坐标定位
                        logger.warning(f"⚠️  未找到浏览器图标，使用坐标点击")
                        d.click(909, 1757)
                        logger.info(f"✓ 已通过坐标启动浏览器")
                except Exception as e2:
                    logger.error(f"❌ 无法启动浏览器: {e2}")
                    return False

            # ============ 步骤 3: 等待浏览器加载 ============
            logger.info(f"\n[步骤 3/8] 等待浏览器完全加载")
            logger.info(f"   等待6秒...")
            time.sleep(6)

            # ============ 步骤 3.5: 检查是否有缓存页面 ============
            logger.info(f"\n[步骤 3.5/8] 检查浏览器缓存")
            has_cache = False
            try:
                # 检查是否存在关闭按钮(说明有缓存页面)
                close_btn = d(resourceId="com.vivo.browser:id/close_btn")
                if close_btn.exists(timeout=2):
                    has_cache = True
                    logger.info(f"✓ 检测到浏览器缓存页面")
                    close_btn.click()
                    logger.info(f"✓ 已点击关闭按钮清除缓存页面")
                    time.sleep(1)
                else:
                    logger.info(f"✓ 无缓存页面,是首次访问")
            except Exception as e:
                logger.info(f"⚠️  检查缓存失败: {e},继续执行")

            # ============ 步骤 4: 点击搜索框 (仅首次需要) ============
            if not has_cache:
                logger.info(f"\n[步骤 4/8] 点击搜索框 (首次访问)")
                try:
                    search_input = d(resourceId="com.vivo.browser:id/tv_common_search_input")
                    if search_input.exists(timeout=5):
                        search_input.click()
                        logger.info(f"✓ 已点击搜索框")
                        time.sleep(1)
                    else:
                        logger.error(f"❌ 未找到搜索框元素")
                        return False
                except Exception as e:
                    logger.error(f"❌ 点击搜索框失败: {e}")
                    return False
            else:
                logger.info(f"\n[步骤 4/8] 跳过点击搜索框 (已清除缓存)")

            # ============ 步骤 5: 输入分享链接 ============
            logger.info(f"\n[步骤 5/8] 输入分享链接")
            try:
                edit_field = d(resourceId="com.vivo.browser:id/edit")
                if edit_field.exists(timeout=3):
                    # 清空并输入
                    edit_field.clear_text()
                    edit_field.set_text(share_link)
                    logger.info(f"✓ 已输入分享链接")
                    time.sleep(1)
                else:
                    logger.error(f"❌ 未找到输入框元素")
                    return False
            except Exception as e:
                logger.error(f"❌ 输入链接失败: {e}")
                return False

            # ============ 步骤 6: 点击进入按钮 ============
            logger.info(f"\n[步骤 6/8] 点击进入按钮")
            try:
                search_btn = d(resourceId="com.vivo.browser:id/search_btn")
                if search_btn.exists(timeout=3):
                    search_btn.click()
                    logger.info(f"✓ 已点击进入按钮")
                    time.sleep(3)  # 等待页面加载
                else:
                    logger.error(f"❌ 未找到进入按钮")
                    return False
            except Exception as e:
                logger.error(f"❌ 点击进入按钮失败: {e}")
                return False

            # ============ 步骤 7: 点击"打开"按钮 ============
            logger.info(f"\n[步骤 7/8] 等待并点击'打开'按钮")
            try:
                # 等待打开按钮出现(可能需要一些时间加载页面)
                max_wait = 10
                open_btn_found = False

                for i in range(max_wait):
                    # 方案1: 尝试文本定位 (优先,弹窗按钮)
                    open_btn_text = d(text="打开")
                    if open_btn_text.exists():
                        open_btn_text.click()
                        logger.info(f"✓ 已通过文本定位点击'打开'按钮")
                        open_btn_found = True
                        break

                    # 方案2: 尝试Resource ID定位 (备用)
                    open_btn_id = d(resourceId="com.vivo.browser:id/tv_open")
                    if open_btn_id.exists():
                        open_btn_id.click()
                        logger.info(f"✓ 已通过ResourceID定位点击'打开'按钮")
                        open_btn_found = True
                        break

                    logger.info(f"   等待打开按钮出现... ({i+1}/{max_wait}秒)")
                    time.sleep(1)

                # 如果没找到"打开"按钮,尝试刷新页面后用坐标点击
                if not open_btn_found:
                    logger.warning(f"⚠️  未找到'打开'按钮,尝试刷新页面")
                    try:
                        refresh_btn = d(resourceId="com.vivo.browser:id/title_refresh_layout2")
                        if refresh_btn.exists(timeout=3):
                            refresh_btn.click()
                            logger.info(f"✓ 已点击刷新按钮")
                            time.sleep(3)  # 等待页面重新加载

                            # 刷新后直接使用坐标点击
                            logger.info(f"✓ 刷新后使用坐标点击'打开'按钮")
                            d.click(540, 1773)
                            open_btn_found = True
                            time.sleep(1)
                        else:
                            logger.warning(f"⚠️  未找到刷新按钮,直接使用坐标点击")
                            d.click(540, 1773)
                            open_btn_found = True
                            time.sleep(1)
                    except Exception as e:
                        logger.warning(f"⚠️  刷新页面失败: {e},使用坐标点击")
                        d.click(540, 1773)
                        open_btn_found = True
                        time.sleep(1)

                if open_btn_found:
                    logger.info(f"✓ 已点击'打开'按钮,等待抖音APP启动")
                    time.sleep(2)  # 等待抖音APP启动
                else:
                    logger.error(f"❌ 所有方案都无法点击'打开'按钮")
                    return False

            except Exception as e:
                logger.error(f"❌ 点击'打开'按钮失败: {e}")
                return False

            # ============ 步骤 8: 验证是否进入抖音APP ============
            logger.info(f"\n[步骤 8/8] 验证是否成功跳转到抖音APP")
            try:
                # 等待抖音APP启动
                max_wait = 10
                for i in range(max_wait):
                    current_app = d.app_current()
                    package = current_app.get('package', '')

                    if 'douyin' in package.lower() or 'aweme' in package.lower():
                        logger.info(f"✓ 抖音APP已启动: {package}")
                        logger.info(f"   Activity: {current_app.get('activity', 'Unknown')}")

                        # 等待用户主页加载
                        time.sleep(3)
                        logger.info(f"✓ 成功跳转到用户主页")
                        return True

                    logger.info(f"   等待抖音启动... ({i+1}/{max_wait}秒) 当前: {package}")
                    time.sleep(1)

                logger.warning(f"⚠️  {max_wait}秒后仍未检测到抖音APP")
                logger.warning(f"   当前应用: {d.app_current()}")
                return False

            except Exception as e:
                logger.error(f"❌ 验证抖音启动失败: {e}")
                return False

        except Exception as e:
            logger.error(f"❌ 自动化操作失败: {e}")
            import traceback
            logger.error(f"   详细错误:\n{traceback.format_exc()}")
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

    def run_test_from_db(self, target_account_id: int = 1, auto_open: bool = False):
        """从数据库获取评论数据并测试

        Args:
            target_account_id: 目标账号ID
            auto_open: 是否自动打开链接(不等待用户确认)
        """
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

        if not auto_open:
            input("\n按Enter键继续在浏览器中打开链接...")
        else:
            logger.info("\n⚡ 自动模式: 3秒后开始执行...")
            time.sleep(3)

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

    parser.add_argument(
        '--auto',
        action='store_true',
        help='自动模式：不等待用户确认，直接执行'
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
        result = tester.run_test_from_db(
            target_account_id=args.account_id,
            auto_open=args.auto
        )

    # 返回结果
    if result:
        logger.info("\n✅ 测试完成")
        return 0
    else:
        logger.error("\n❌ 测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(main())
