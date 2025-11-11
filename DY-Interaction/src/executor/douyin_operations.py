"""
抖音自动化操作模块 - 函数化设计
每个操作都是独立函数，返回操作是否成功
下一步操作根据上一步结果决定是否执行
"""
import sys
import os
import time

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# 导入需要的模块
try:
    import uiautomator2 as u2
except ImportError:
    u2 = None

from .element_ids import DouyinElementIds, DeviceElementVersion
from .image_recognizer import ImageRecognizer


class DouyinOperations:
    """抖音操作类 - 每个操作都是独立的函数"""

    def __init__(self, auto, template_manager=None, device_model=None, logger=None):
        """
        初始化

        Args:
            auto: 自动化实例（u2.Device对象）
            template_manager: 模板管理器实例(SimpleTemplateManager)
            device_model: 设备型号(用于获取设备专用模板)
            logger: 日志对象
        """
        self.auto = auto
        self.template_manager = template_manager
        self.device_model = device_model
        self.logger = logger

        # 创建设备元素版本管理器（根据设备型号选择元素ID版本）
        device_id = auto.device_id if hasattr(auto, 'device_id') else 'unknown'
        self.element_version = DeviceElementVersion(device_id, device_model, logger)

        # 设置模板目录路径（使用项目根目录）
        self.template_dir = os.path.join(PROJECT_ROOT, "templates")

        # 创建图像识别器
        self.image_recognizer = ImageRecognizer(auto)

    def get_screen_size(self):
        """获取屏幕尺寸 (兼容方法)"""
        info = self.auto.info
        return (info.get('displayWidth', 0), info.get('displayHeight', 0))

    def element_exists(self, **kwargs):
        """检查元素是否存在 (兼容方法)"""
        return self.auto(**kwargs).exists

    def _get_element_id(self, element_config):
        """
        获取元素ID（自动识别版本）

        Args:
            element_config: 元素配置（来自 DouyinElementIds）

        Returns:
            str: 该设备应使用的元素ID
        """
        return self.element_version.get_element_id(element_config, self.auto)

    def _get_template_path(self, template_name: str) -> str:
        """
        获取模板文件路径(优先使用设备专用模板)

        Args:
            template_name: 模板文件名

        Returns:
            模板文件路径(字符串)
        """
        # 如果有模板管理器且指定了设备型号,使用设备专用模板
        if self.template_manager and self.device_model:
            paths = self.template_manager.get_template_paths(template_name, self.device_model)
            if paths:
                template_path = str(paths[0])
                print(f"  [模板路径] 使用设备专用模板: {template_path}")
                return template_path
            else:
                print(f"  [模板路径] 设备 {self.device_model} 没有专用模板 {template_name}, 使用默认路径")
        else:
            if not self.template_manager:
                print(f"  [模板路径] 警告: template_manager 为 None")
            if not self.device_model:
                print(f"  [模板路径] 警告: device_model 为 '{self.device_model}'")

        # fallback: 使用默认路径
        default_path = os.path.join(self.template_dir, template_name)
        print(f"  [模板路径] 使用默认路径: {default_path}")
        return default_path

    # ============ 首页操作 ============

    def find_and_click_search_button(self):
        """
        查找并点击首页搜索按钮（三层查找策略）

        查找策略：
        1. 第一层：元素ID定位（最快最准确）
        2. 第二层：模板匹配找图（支持黑白两种主题）
        3. 第三层：滑动屏幕后继续找图（最多滑动3次）

        Returns:
            dict: {
                'success': bool,
                'position': tuple,
                'method': str,
                'message': str
            }
        """
        print("\n[操作] 查找并点击搜索按钮...")

        # ========== 第一层：元素ID定位 ==========
        try:
            search_button_id = self._get_element_id(DouyinElementIds.SEARCH_BUTTON)

            if self.element_exists(resourceId=search_button_id):
                element = self.auto(resourceId=search_button_id)
                bounds = element.info['bounds']
                x = (bounds['left'] + bounds['right']) // 2
                y = (bounds['top'] + bounds['bottom']) // 2

                print(f"  ✓ [元素定位] 找到搜索按钮 at ({x}, {y})")

                # 点击搜索按钮
                element.click()
                time.sleep(2)

                print(f"  ✓ 成功点击搜索按钮")
                return {
                    'success': True,
                    'position': (x, y),
                    'method': '元素ID定位',
                    'message': '通过元素ID找到并点击搜索按钮'
                }
        except Exception as e:
            print(f"  ⚠ [元素定位] 失败: {e}")

        # ========== 第二层：模板匹配找图 ==========
        print(f"  → [找图] 尝试模板匹配...")

        # 获取设备专用模板路径
        templates = []
        if self.device_model:
            # 尝试黑色主题模板
            black_path = self._get_template_path("HomepageSearchBlack.png")
            if black_path:
                templates.append(("黑色主题", black_path))

            # 尝试白色主题模板
            white_path = self._get_template_path("HomepageSearchWhite.png")
            if white_path:
                templates.append(("白色主题", white_path))

        if templates:
            for theme_name, template_path in templates:
                try:
                    result = self.auto.find_and_tap_template(
                        template_path,
                        threshold=0.8,
                        tap=True
                    )

                    if result['found']:
                        print(f"  ✓ [找图-{theme_name}] 找到搜索按钮 at {result['position']}, 相似度: {result['confidence']:.2%}")
                        time.sleep(2)
                        return {
                            'success': True,
                            'position': result['position'],
                            'method': f'模板匹配({theme_name})',
                            'message': f'通过模板匹配找到并点击搜索按钮'
                        }
                except Exception as e:
                    print(f"  ⚠ [找图-{theme_name}] 失败: {e}")
                    continue

        # ========== 第三层：滑动屏幕后继续找图 ==========
        print(f"  → [滑动+找图] 尝试滑动后继续查找...")

        screen_width, screen_height = self.get_screen_size()
        max_swipes = 3  # 最多滑动3次

        for swipe_count in range(1, max_swipes + 1):
            print(f"  → [滑动 {swipe_count}/{max_swipes}] 向上滑动...")

            # 向上滑动
            start_y = int(screen_height * 0.7)
            end_y = int(screen_height * 0.3)
            center_x = screen_width // 2

            self.auto.swipe(center_x, start_y, center_x, end_y, duration=0.3)
            time.sleep(1)

            # 滑动后再次尝试找图
            if templates:
                for theme_name, template_path in templates:
                    try:
                        result = self.auto.find_and_tap_template(
                            template_path,
                            threshold=0.8,
                            tap=True
                        )

                        if result['found']:
                            print(f"  ✓ [滑动+找图-{theme_name}] 第{swipe_count}次滑动后找到搜索按钮 at {result['position']}, 相似度: {result['confidence']:.2%}")
                            time.sleep(2)
                            return {
                                'success': True,
                                'position': result['position'],
                                'method': f'滑动后模板匹配({theme_name})',
                                'message': f'滑动{swipe_count}次后通过模板匹配找到并点击搜索按钮'
                            }
                    except Exception as e:
                        continue

        # 所有方法都失败
        print(f"  ✗ 所有查找方法都失败")
        return {
            'success': False,
            'position': None,
            'method': None,
            'message': '所有查找方法都失败：元素定位、模板匹配、滑动查找均未找到搜索按钮'
        }

    # ============ 搜索页操作 ============

    def find_search_input(self):
        """
        查找搜索输入框

        通过元素ID: com.ss.android.ugc.aweme:id/et_search_kw

        Returns:
            dict: {
                'success': bool,
                'element': object,
                'position': tuple,
                'method': str,
                'message': str
            }
        """
        print("\n[操作] 查找搜索输入框...")

        try:
            if self.element_exists(resourceId=self._get_element_id(DouyinElementIds.SEARCH_INPUT)):
                element = self.auto(resourceId=self._get_element_id(DouyinElementIds.SEARCH_INPUT))
                bounds = element.info['bounds']
                x = (bounds['left'] + bounds['right']) // 2
                y = (bounds['top'] + bounds['bottom']) // 2

                print(f"  ✓ 找到输入框 at ({x}, {y})")
                return {
                    'success': True,
                    'element': element,
                    'position': (x, y),
                    'method': 'ResourceId(et_search_kw)',
                    'message': '通过ResourceId找到输入框'
                }
            else:
                print("  ✗ 未找到输入框")
                return {
                    'success': False,
                    'element': None,
                    'position': None,
                    'method': None,
                    'message': '未找到输入框'
                }
        except Exception as e:
            print(f"  ✗ 查找失败: {e}")
            return {
                'success': False,
                'element': None,
                'position': None,
                'method': None,
                'message': f'查找失败: {str(e)}'
            }

    def input_search_text(self, input_result, text):
        """
        在搜索框输入文字

        Args:
            input_result: find_search_input的返回结果
            text: 要输入的文字

        Returns:
            dict: {
                'success': bool,
                'message': str
            }
        """
        print(f"\n[操作] 输入文字: {text}")

        if not input_result or not input_result.get('success'):
            print("  ✗ 未提供有效的输入框")
            return {'success': False, 'message': '未找到输入框'}

        try:
            element = input_result['element']
            # 先清空
            element.clear_text()
            time.sleep(0.3)
            # 设置文本
            element.set_text(text)
            time.sleep(0.5)

            print(f"  ✓ 已输入文字: {text}")
            return {
                'success': True,
                'message': f'成功输入文字: {text}'
            }

        except Exception as e:
            print(f"  ✗ 输入失败: {e}")
            return {'success': False, 'message': f'输入失败: {str(e)}'}

    def find_search_confirm_button(self):
        """
        查找搜索确认按钮

        通过元素ID: com.ss.android.ugc.aweme:id/303

        Returns:
            dict: {
                'success': bool,
                'position': tuple,
                'method': str,
                'message': str
            }
        """
        print("\n[操作] 查找搜索确认按钮...")

        try:
            if self.element_exists(resourceId=self._get_element_id(DouyinElementIds.SEARCH_CONFIRM)):
                element = self.auto(resourceId=self._get_element_id(DouyinElementIds.SEARCH_CONFIRM))
                bounds = element.info['bounds']
                x = (bounds['left'] + bounds['right']) // 2
                y = (bounds['top'] + bounds['bottom']) // 2

                print(f"  ✓ 找到搜索按钮 at ({x}, {y})")
                return {
                    'success': True,
                    'position': (x, y),
                    'method': 'ResourceId(303)',
                    'message': '通过ResourceId找到搜索按钮'
                }
            else:
                # 直接使用回车键
                print("  ℹ 未找到按钮，将使用回车键")
                return {
                    'success': True,
                    'position': None,
                    'method': 'Enter',
                    'message': '将使用回车键'
                }
        except Exception as e:
            print(f"  ✗ 查找失败: {e}，将使用回车键")
            return {
                'success': True,
                'position': None,
                'method': 'Enter',
                'message': '查找失败，将使用回车键'
            }

    def click_search_confirm(self, confirm_result):
        """
        点击搜索确认按钮或按回车

        Args:
            confirm_result: find_search_confirm_button的返回结果

        Returns:
            dict: {
                'success': bool,
                'message': str
            }
        """
        print("\n[操作] 确认搜索...")

        if not confirm_result or not confirm_result.get('success'):
            print("  ⚠ 未找到确认按钮，尝试按回车")
            try:
                self.auto.press_enter()
                time.sleep(3)
                return {'success': True, 'message': '已按回车键'}
            except Exception as e:
                return {'success': False, 'message': f'按回车失败: {str(e)}'}

        try:
            if confirm_result['method'] == 'Enter':
                self.auto.press_enter()
                time.sleep(3)
                print(f"  ✓ 已按回车键")
                return {'success': True, 'message': '已按回车键'}
            else:
                x, y = confirm_result['position']
                self.auto.click(x, y)
                time.sleep(3)
                print(f"  ✓ 已点击确认按钮")
                return {'success': True, 'message': '已点击确认按钮'}

        except Exception as e:
            print(f"  ✗ 确认失败: {e}")
            return {'success': False, 'message': f'确认失败: {str(e)}'}

    # ============ 搜索结果页操作 ============

    def switch_to_user_tab(self):
        """
        切换到"用户"标签

        流程：查找user.png模板图片 → 点击切换到用户标签

        Returns:
            dict: {
                'success': bool,
                'message': str
            }
        """
        print("\n[操作] 切换到用户标签...")

        # 使用设备专用模板路径
        user_tab_icon = self._get_template_path("user.png")

        # 检查模板是否存在
        if not os.path.exists(user_tab_icon):
            print(f"  ✗ 模板图片不存在: {user_tab_icon}")
            return {
                'success': False,
                'message': f'模板不存在: {user_tab_icon}'
            }

        print(f"  [查找] 用户标签图标（user.png）...")

        # 使用图像识别器进行模板匹配（阈值0.6）
        result = self.image_recognizer.find_image_template(user_tab_icon, threshold=0.6)

        if result:
            x, y = int(result['result'][0]), int(result['result'][1])
            conf = result.get('confidence', 0)
            print(f"  ✓ 找到用户标签 at ({x}, {y}), 相似度: {conf:.2%}")

            # 点击用户标签
            self.auto.click(x, y)
            time.sleep(2.0)  # 等待切换完成

            print(f"  ✓ 已切换到用户标签")
            return {'success': True, 'message': '已切换到用户标签'}

        # 未找到
        print(f"  ✗ 未找到用户标签图标")
        return {
            'success': False,
            'message': '未找到用户标签图标'
        }

    def find_first_user_result(self):
        """
        查找第一个用户搜索结果并进入用户主页

        流程：
        1. 点击"用户"标签（使用user.png模板）
        2. 定位 android:id/text1 元素（最左边第一个）
        3. 向下偏移50px点击，进入用户主页

        Returns:
            dict: {
                'success': bool,
                'position': tuple,
                'method': str,
                'message': str
            }
        """
        print("\n[操作] 查找第一个用户并进入主页...")

        # 步骤1: 点击"用户"标签
        print("  [步骤1] 点击'用户'标签...")
        tab_result = self.switch_to_user_tab()

        if not tab_result['success']:
            print(f"  ✗ 切换到用户标签失败: {tab_result['message']}")
            return {
                'success': False,
                'position': None,
                'method': None,
                'message': f"切换用户标签失败: {tab_result['message']}"
            }

        print(f"  ✓ 已切换到用户标签，等待加载...")
        time.sleep(2.0)  # 等待用户列表加载

        # 步骤2: 定位 android:id/text1 元素（最左边第一个）+ 向下偏移50px
        print("  [步骤2] 定位 android:id/text1 元素（最左边第一个）...")

        try:
            element_id = "android:id/text1"

            if not self.element_exists(resourceId=element_id):
                print(f"  ✗ 未找到元素 {element_id}")
                return {
                    'success': False,
                    'position': None,
                    'method': None,
                    'message': f'未找到元素 {element_id}'
                }

            elements = self.auto(resourceId=element_id)

            if elements.count == 0:
                print(f"  ✗ 元素数量为0")
                return {
                    'success': False,
                    'position': None,
                    'method': None,
                    'message': f'元素 {element_id} 数量为0'
                }

            print(f"  ✓ 找到 {elements.count} 个 text1 元素")

            # 找到最左边的元素（X坐标最小）
            leftmost_element = None
            min_x = float('inf')

            for i in range(elements.count):
                element = elements[i]
                bounds = element.info['bounds']
                element_x = (bounds['left'] + bounds['right']) // 2

                if element_x < min_x:
                    min_x = element_x
                    leftmost_element = element

            if not leftmost_element:
                print(f"  ✗ 无法确定最左边元素")
                return {
                    'success': False,
                    'position': None,
                    'method': None,
                    'message': '无法确定最左边的text1元素'
                }

            # 获取元素坐标
            bounds = leftmost_element.info['bounds']
            element_x = (bounds['left'] + bounds['right']) // 2
            element_y = (bounds['top'] + bounds['bottom']) // 2

            print(f"  ✓ 最左边的 text1 元素 at ({element_x}, {element_y})")

            # 根据设备型号选择点击方法
            if self.device_model and 'pd2072' in self.device_model.lower():
                # vivo S12: 使用固定坐标
                click_x = 528
                click_y = 487
                device_name = "vivo S12"
                method = "固定坐标"
                print(f"  → [{device_name}] 使用固定坐标: ({click_x}, {click_y})")
            else:
                # OPPO A57: 使用偏移方法
                offset_y = 150
                click_x = int(element_x)
                click_y = int(element_y + offset_y)
                device_name = "OPPO A57"
                method = f"text1偏移{offset_y}px"
                print(f"  → [{device_name}] 向下偏移{offset_y}px，点击位置: ({click_x}, {click_y})")

            # 点击进入用户主页
            self.auto.click(click_x, click_y)
            time.sleep(2.5)  # 等待进入用户主页

            print(f"  ✓ 已进入用户主页")
            return {
                'success': True,
                'position': (click_x, click_y),
                'method': method,
                'message': '成功进入用户主页'
            }

        except Exception as e:
            print(f"  ✗ 查找失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'position': None,
                'method': None,
                'message': f'查找元素失败: {e}'
            }

    # ============ 用户主页操作 ============

    def find_pinned_video(self):
        """
        查找置顶视频（随机选择前3个中的一个）

        通过元素ID自动检测设备版本：
        - OPPO A57: com.ss.android.ugc.aweme:id/qee
        - vivo S12: com.ss.android.ugc.aweme:id/qdf

        Returns:
            dict: {
                'success': bool,
                'position': tuple,
                'element': object,
                'method': str,
                'message': str
            }
        """
        print("\n[操作] 查找置顶视频...")

        try:
            # 使用设备特定的元素ID
            video_element_id = self._get_element_id(DouyinElementIds.USER_PAGE_PINNED_VIDEO)

            if self.element_exists(resourceId=video_element_id):
                elements = self.auto(resourceId=video_element_id)
                element_count = elements.count

                if element_count > 0:
                    print(f"  ✓ 找到 {element_count} 个视频元素")

                    # 随机选择前3个中的一个
                    import random
                    max_index = min(element_count, 3)
                    selected_index = random.randint(0, max_index - 1)

                    selected_element = elements[selected_index]
                    bounds = selected_element.info['bounds']
                    x = (bounds['left'] + bounds['right']) // 2
                    y = (bounds['top'] + bounds['bottom']) // 2

                    print(f"  ✓ 随机选择第{selected_index + 1}个视频 at ({x}, {y})")
                    return {
                        'success': True,
                        'position': (x, y),
                        'element': selected_element,
                        'method': f'ResourceId-随机第{selected_index + 1}个',
                        'message': f'随机选择第{selected_index + 1}个视频'
                    }
                else:
                    print(f"  ✗ 视频元素数量为0")
                    return {
                        'success': False,
                        'position': None,
                        'element': None,
                        'method': None,
                        'message': '未找到视频元素'
                    }
            else:
                print(f"  ✗ 未找到视频元素")
                return {
                    'success': False,
                    'position': None,
                    'element': None,
                    'method': None,
                    'message': '未找到视频元素'
                }
        except Exception as e:
            print(f"  ✗ 查找失败: {e}")
            return {
                'success': False,
                'position': None,
                'element': None,
                'method': None,
                'message': f'查找失败: {str(e)}'
            }

    def click_pinned_video(self, video_result):
        """
        点击置顶视频

        Args:
            video_result: find_pinned_video的返回结果

        Returns:
            dict: {
                'success': bool,
                'message': str
            }
        """
        print("\n[操作] 点击置顶视频...")

        if not video_result or not video_result.get('success'):
            return {'success': False, 'message': '未找到视频'}

        try:
            x, y = video_result['position']
            self.auto.click(x, y)
            time.sleep(3)  # 等待视频加载

            print(f"  ✓ 已点击视频")
            return {'success': True, 'message': '已进入视频页面'}
        except Exception as e:
            return {'success': False, 'message': f'点击失败: {str(e)}'}

    # ============ 视频页操作 ============

    def find_comment_button(self):
        """
        查找评论按钮

        通过元素ID: DouyinElementIds.COMMENT_BUTTON
        自动识别该设备使用的元素版本

        Returns:
            dict: {
                'success': bool,
                'position': tuple,
                'element': object,
                'method': str,
                'message': str
            }
        """
        print("\n[操作] 查找评论按钮...")

        try:
            # 获取该设备的评论按钮元素ID（自动识别版本）
            element_id = self._get_element_id(DouyinElementIds.COMMENT_BUTTON)

            if self.element_exists(resourceId=element_id):
                element = self.auto(resourceId=element_id)
                bounds = element.info['bounds']
                x = (bounds['left'] + bounds['right']) // 2
                y = (bounds['top'] + bounds['bottom']) // 2

                print(f"  ✓ 找到评论按钮 at ({x}, {y}) [元素ID: {element_id}]")
                return {
                    'success': True,
                    'position': (x, y),
                    'element': element,
                    'method': 'ResourceId',
                    'message': f'通过ResourceId找到评论按钮 ({element_id})'
                }
            else:
                print(f"  ✗ 未找到评论按钮 [尝试的元素ID: {element_id}]")
                return {
                    'success': False,
                    'position': None,
                    'element': None,
                    'method': None,
                    'message': f'未找到评论按钮 (元素ID: {element_id})'
                }
        except Exception as e:
            print(f"  ✗ 查找失败: {e}")
            return {
                'success': False,
                'position': None,
                'element': None,
                'method': None,
                'message': f'查找失败: {str(e)}'
            }

    def click_comment_button(self, comment_result):
        """
        点击评论按钮

        Args:
            comment_result: find_comment_button的返回结果

        Returns:
            dict: {
                'success': bool,
                'message': str
            }
        """
        print("\n[操作] 点击评论按钮...")

        if not comment_result or not comment_result.get('success'):
            return {'success': False, 'message': '未找到评论按钮'}

        try:
            x, y = comment_result['position']
            self.auto.click(x, y)
            time.sleep(2)  # 等待评论框出现

            print(f"  ✓ 已点击评论按钮")
            return {'success': True, 'message': '评论框已打开'}
        except Exception as e:
            return {'success': False, 'message': f'点击失败: {str(e)}'}

    def find_comment_input(self):
        """
        查找评论输入框

        通过元素ID: DouyinElementIds.COMMENT_INPUT

        Returns:
            dict: {
                'success': bool,
                'element': object,
                'position': tuple,
                'method': str,
                'message': str
            }
        """
        print("\n[操作] 查找评论输入框...")

        try:
            if self.element_exists(resourceId=self._get_element_id(DouyinElementIds.COMMENT_INPUT)):
                element = self.auto(resourceId=self._get_element_id(DouyinElementIds.COMMENT_INPUT))
                bounds = element.info['bounds']
                x = (bounds['left'] + bounds['right']) // 2
                y = (bounds['top'] + bounds['bottom']) // 2

                print(f"  ✓ 找到评论输入框 at ({x}, {y})")
                return {
                    'success': True,
                    'element': element,
                    'position': (x, y),
                    'method': 'ResourceId',
                    'message': '通过ResourceId找到评论输入框'
                }
            else:
                print(f"  ✗ 未找到评论输入框")
                return {
                    'success': False,
                    'element': None,
                    'position': None,
                    'method': None,
                    'message': '未找到评论输入框'
                }
        except Exception as e:
            print(f"  ✗ 查找失败: {e}")
            return {
                'success': False,
                'element': None,
                'position': None,
                'method': None,
                'message': f'查找失败: {str(e)}'
            }

    def input_comment_text(self, input_result, comment_text):
        """
        输入评论内容

        Args:
            input_result: find_comment_input的返回结果
            comment_text: 评论文字

        Returns:
            dict: {
                'success': bool,
                'message': str
            }
        """
        print(f"\n[操作] 输入评论: {comment_text}")

        if not input_result or not input_result.get('success'):
            return {'success': False, 'message': '未找到评论输入框'}

        try:
            element = input_result['element']
            # 先清空
            element.clear_text()
            time.sleep(0.3)
            # 设置文本
            element.set_text(comment_text)
            time.sleep(0.5)

            print(f"  ✓ 已输入评论: {comment_text}")
            return {'success': True, 'message': '评论已输入'}

        except Exception as e:
            print(f"  ✗ 输入失败: {e}")
            return {'success': False, 'message': f'输入失败: {str(e)}'}

    # ============ 图片评论操作 ============

    def click_image_comment_button(self):
        """
        点击图片评论按钮（打开相册）

        元素ID: DouyinElementIds.IMAGE_COMMENT_ICON

        Returns:
            dict: {
                'success': bool,
                'position': tuple,
                'message': str
            }
        """
        print("\n[操作] 点击图片评论按钮...")

        try:
            if self.element_exists(resourceId=self._get_element_id(DouyinElementIds.IMAGE_COMMENT_ICON)):
                element = self.auto(resourceId=self._get_element_id(DouyinElementIds.IMAGE_COMMENT_ICON))
                bounds = element.info['bounds']
                x = (bounds['left'] + bounds['right']) // 2
                y = (bounds['top'] + bounds['bottom']) // 2

                print(f"  ✓ 找到图片评论按钮 at ({x}, {y})")
                self.auto.click(x, y)
                time.sleep(2)

                print(f"  ✓ 已点击图片评论按钮")
                return {
                    'success': True,
                    'position': (x, y),
                    'message': '已点击图片评论按钮'
                }
        except Exception as e:
            print(f"  ✗ 点击失败: {e}")
            return {
                'success': False,
                'position': None,
                'message': f'点击图片评论按钮失败: {str(e)}'
            }

        print("  ✗ 未找到图片评论按钮")
        return {
            'success': False,
            'position': None,
            'message': '未找到图片评论按钮'
        }

    def select_album_image(self):
        """
        从相册选择图片

        元素ID: DouyinElementIds.ALBUM_FIRST_IMAGE

        Returns:
            dict: {
                'success': bool,
                'position': tuple,
                'message': str
            }
        """
        print("\n[操作] 从相册选择图片...")

        try:
            if self.element_exists(resourceId=self._get_element_id(DouyinElementIds.ALBUM_FIRST_IMAGE)):
                element = self.auto(resourceId=self._get_element_id(DouyinElementIds.ALBUM_FIRST_IMAGE))
                bounds = element.info['bounds']
                x = (bounds['left'] + bounds['right']) // 2
                y = (bounds['top'] + bounds['bottom']) // 2

                print(f"  ✓ 找到相册图片 at ({x}, {y})")
                self.auto.click(x, y)
                time.sleep(1.5)

                print(f"  ✓ 已选择图片")
                return {
                    'success': True,
                    'position': (x, y),
                    'message': '已选择图片'
                }
        except Exception as e:
            print(f"  ✗ 选择失败: {e}")
            return {
                'success': False,
                'position': None,
                'message': f'选择图片失败: {str(e)}'
            }

        print("  ✗ 未找到相册图片")
        return {
            'success': False,
            'position': None,
            'message': '未找到相册图片'
        }

    def input_image_comment_text(self, text):
        """
        在图片评论输入框输入文字

        元素ID: DouyinElementIds.COMMENT_INPUT

        Args:
            text: 要输入的评论文字

        Returns:
            dict: {
                'success': bool,
                'message': str
            }
        """
        print(f"\n[操作] 输入图片评论文字: {text}")

        try:
            if self.element_exists(resourceId=self._get_element_id(DouyinElementIds.COMMENT_INPUT)):
                element = self.auto(resourceId=self._get_element_id(DouyinElementIds.COMMENT_INPUT))
                element.clear_text()
                time.sleep(0.3)
                element.set_text(text)
                time.sleep(0.5)

                print(f"  ✓ 已输入文字: {text}")
                return {
                    'success': True,
                    'message': f'已输入评论文字: {text}'
                }
        except Exception as e:
            print(f"  ✗ 输入失败: {e}")
            return {
                'success': False,
                'message': f'输入失败: {str(e)}'
            }

        print("  ✗ 未找到输入框")
        return {
            'success': False,
            'message': '未找到图片评论输入框'
        }

    def click_image_comment_send(self):
        """
        点击图片评论发送按钮

        元素ID: DouyinElementIds.SEND_IMAGE_COMMENT (eil - 图片评论专用)

        Returns:
            dict: {
                'success': bool,
                'position': tuple,
                'message': str
            }
        """
        print("\n[操作] 点击图片评论发送按钮...")

        try:
            # 图片评论发送按钮使用配置文件中的 SEND_IMAGE_COMMENT
            if self.element_exists(resourceId=self._get_element_id(DouyinElementIds.SEND_IMAGE_COMMENT)):
                element = self.auto(resourceId=self._get_element_id(DouyinElementIds.SEND_IMAGE_COMMENT))
                bounds = element.info['bounds']
                x = (bounds['left'] + bounds['right']) // 2
                y = (bounds['top'] + bounds['bottom']) // 2

                print(f"  ✓ 找到图片评论发送按钮 at ({x}, {y})")
                self.auto.click(x, y)
                time.sleep(2)

                print(f"  ✓ 图片评论已发送")
                return {
                    'success': True,
                    'position': (x, y),
                    'message': '图片评论已发送'
                }
        except Exception as e:
            print(f"  ✗ 点击失败: {e}")
            return {
                'success': False,
                'position': None,
                'message': f'点击发送按钮失败: {str(e)}'
            }

        print("  ✗ 未找到图片评论发送按钮")
        return {
            'success': False,
            'position': None,
            'message': '未找到图片评论发送按钮'
        }

    def find_send_button(self):
        """
        查找发送按钮（文字评论）

        通过元素ID: DouyinElementIds.SEND_TEXT_COMMENT

        Returns:
            dict: {
                'success': bool,
                'position': tuple,
                'element': object,
                'method': str,
                'message': str
            }
        """
        print("\n[操作] 查找发送按钮...")

        try:
            if self.element_exists(resourceId=self._get_element_id(DouyinElementIds.SEND_TEXT_COMMENT)):
                element = self.auto(resourceId=self._get_element_id(DouyinElementIds.SEND_TEXT_COMMENT))
                bounds = element.info['bounds']
                x = (bounds['left'] + bounds['right']) // 2
                y = (bounds['top'] + bounds['bottom']) // 2

                print(f"  ✓ 找到发送按钮 at ({x}, {y})")
                return {
                    'success': True,
                    'position': (x, y),
                    'element': element,
                    'method': 'ResourceId',
                    'message': '通过ResourceId找到发送按钮'
                }
            else:
                # 使用回车键发送
                print("  ℹ 未找到发送按钮，将使用回车键")
                return {
                    'success': True,
                    'position': None,
                    'element': None,
                    'method': 'Enter',
                    'message': '将使用回车键发送'
                }
        except Exception as e:
            print(f"  ✗ 查找失败: {e}，将使用回车键")
            return {
                'success': True,
                'position': None,
                'element': None,
                'method': 'Enter',
                'message': '查找失败，将使用回车键'
            }

    def click_send_button(self, send_result):
        """
        点击发送按钮发送评论

        Args:
            send_result: find_send_button的返回结果

        Returns:
            dict: {
                'success': bool,
                'message': str
            }
        """
        print("\n[操作] 发送评论...")

        if not send_result or not send_result.get('success'):
            try:
                self.auto.press_enter()
                time.sleep(2)
                return {'success': True, 'message': '已按回车发送'}
            except Exception as e:
                return {'success': False, 'message': f'发送失败: {str(e)}'}

        try:
            if send_result['method'] == 'Enter':
                self.auto.press_enter()
                time.sleep(2)
                print(f"  ✓ 已按回车发送")
                return {'success': True, 'message': '评论已发送'}
            else:
                x, y = send_result['position']
                self.auto.click(x, y)
                time.sleep(2)
                print(f"  ✓ 已点击发送")
                return {'success': True, 'message': '评论已发送'}
        except Exception as e:
            return {'success': False, 'message': f'发送失败: {str(e)}'}

    # ============ 导航操作 ============

    def go_back(self, times=1):
        """
        返回上一页（系统返回键）

        Args:
            times: 返回次数

        Returns:
            dict: {
                'success': bool,
                'message': str
            }
        """
        print(f"\n[操作] 返回上一页 (x{times})...")

        try:
            for i in range(times):
                self.auto.press_back()
                time.sleep(1)

            print(f"  ✓ 已返回")
            return {'success': True, 'message': f'已返回{times}次'}
        except Exception as e:
            return {'success': False, 'message': f'返回失败: {str(e)}'}

    def click_user_page_back(self):
        """
        点击用户页面的返回按钮

        元素ID: com.ss.android.ugc.aweme:id/jyz

        Returns:
            dict: {
                'success': bool,
                'position': tuple,
                'message': str
            }
        """
        print("\n[操作] 点击用户页面返回按钮...")

        try:
            if self.element_exists(resourceId="com.ss.android.ugc.aweme:id/jyz"):
                element = self.auto(resourceId="com.ss.android.ugc.aweme:id/jyz")
                bounds = element.info['bounds']
                x = (bounds['left'] + bounds['right']) // 2
                y = (bounds['top'] + bounds['bottom']) // 2

                print(f"  ✓ [ResourceId] 找到返回按钮 at ({x}, {y})")
                self.auto.click(x, y)
                time.sleep(1.5)

                print(f"  ✓ 已点击返回")
                return {
                    'success': True,
                    'position': (x, y),
                    'message': '已点击用户页面返回按钮'
                }
        except Exception as e:
            print(f"  ✗ 点击失败: {e}")
            return {
                'success': False,
                'position': None,
                'message': f'点击返回按钮失败: {str(e)}'
            }

        print("  ✗ 未找到返回按钮")
        return {
            'success': False,
            'position': None,
            'message': '未找到用户页面返回按钮'
        }

    # ============ 断言和检测 ============

    def check_is_homepage(self):
        """
        检测是否在抖音首页（改进版 - 支持多设备型号）

        通过检测多个底部导航栏元素，满足2个即确认在首页：
        1. 首页按钮（底部导航-首页）
        2. 底部导航-通用按钮（团购/直播/同城等，多个按钮共用ID）
        3. 搜索按钮（首页右上角）
        4. 内容容器（推荐feed流）

        Returns:
            dict: {
                'success': bool,  # 检测是否成功执行
                'is_homepage': bool,  # 是否在首页
                'is_phone_desktop': bool,  # 是否在手机桌面
                'matched_count': int,  # 匹配的元素数量
                'message': str
            }
        """
        print("\n[检测] 是否在抖音首页...")

        try:
            matched_elements = []

            # 1. 检测首页按钮（根据设备型号使用对应元素ID）
            bottom_nav_home_id = self._get_element_id(DouyinElementIds.BOTTOM_NAV_HOME)
            if self.element_exists(resourceId=bottom_nav_home_id):
                matched_elements.append("首页按钮")
                print(f"  ✓ 检测到: 首页按钮")

            # 2. 检测底部导航栏按钮（团购/直播/同城/商城/推荐等，共用ID）
            # 通过检测该ID的数量来判断是否有底部导航栏
            try:
                bottom_nav_common_id = self._get_element_id(DouyinElementIds.BOTTOM_NAV_COMMON)
                nav_elements = self.auto(resourceId=bottom_nav_common_id)
                nav_count = nav_elements.count
                if nav_count > 0:
                    matched_elements.append(f"底部导航栏({nav_count}个)")
                    print(f"  ✓ 检测到: 底部导航栏 ({nav_count} 个按钮)")
            except:
                pass

            # 3. 检测搜索按钮（首页右上角）- 使用元素ID
            search_button_id = self._get_element_id(DouyinElementIds.SEARCH_BUTTON)
            if self.element_exists(resourceId=search_button_id):
                matched_elements.append("搜索按钮")
                print(f"  ✓ 检测到: 搜索按钮")

            # 4. 检测推荐feed流容器
            fragment_container_id = self._get_element_id(DouyinElementIds.FRAGMENT_CONTAINER)
            if fragment_container_id and self.element_exists(resourceId=fragment_container_id):
                matched_elements.append("内容容器")
                print(f"  ✓ 检测到: 内容容器")

            matched_count = len(matched_elements)
            print(f"\n  匹配结果: {matched_count} 个首页特征元素")

            # 满足2个或以上即确认在首页
            if matched_count >= 2:
                print(f"  ✓ 满足 {matched_count} 个特征元素，确认在抖音首页")
                return {
                    'success': True,
                    'is_homepage': True,
                    'is_phone_desktop': False,
                    'matched_count': matched_count,
                    'message': f'在抖音首页 (匹配{matched_count}个元素)'
                }
            elif matched_count >= 1:
                print(f"  ⚠ 只匹配 {matched_count} 个元素，不在首页")
                return {
                    'success': True,
                    'is_homepage': False,
                    'is_phone_desktop': False,
                    'matched_count': matched_count,
                    'message': f'不在抖音首页 (仅匹配{matched_count}个元素)'
                }
            else:
                # 没有任何抖音特征元素，可能在手机桌面
                print(f"  ✗ 未检测到任何抖音特征元素，可能在手机桌面")
                return {
                    'success': True,
                    'is_homepage': False,
                    'is_phone_desktop': True,
                    'matched_count': 0,
                    'message': '不在抖音首页（可能在手机桌面）'
                }

        except Exception as e:
            print(f"  ⚠ 检测异常: {e}")
            return {
                'success': True,
                'is_homepage': False,
                'is_phone_desktop': False,
                'matched_count': 0,
                'message': f'检测异常: {str(e)}'
            }

    def check_is_search_page(self):
        """
        检测是否在搜索页面

        通过检测两个元素：
        1. 搜索按钮: com.ss.android.ugc.aweme:id/303
        2. 搜索输入框: com.ss.android.ugc.aweme:id/et_search_kw

        Returns:
            dict: {
                'success': bool,  # 检测是否成功执行
                'is_search_page': bool,  # 是否在搜索页面
                'message': str
            }
        """
        print("\n[检测] 是否在搜索页面...")

        try:
            # 检测搜索按钮
            has_search_btn = self.element_exists(resourceId=self._get_element_id(DouyinElementIds.SEARCH_CONFIRM))
            # 检测搜索输入框
            has_search_input = self.element_exists(resourceId=self._get_element_id(DouyinElementIds.SEARCH_INPUT))

            if has_search_btn and has_search_input:
                print(f"  ✓ 检测到搜索按钮和输入框，确认在搜索页面")
                return {
                    'success': True,
                    'is_search_page': True,
                    'message': '在搜索页面'
                }
            elif has_search_input:
                print(f"  ⚠ 只检测到搜索输入框，未检测到搜索按钮")
                return {
                    'success': True,
                    'is_search_page': False,
                    'message': '不在搜索页面（缺少搜索按钮）'
                }
            elif has_search_btn:
                print(f"  ⚠ 只检测到搜索按钮，未检测到输入框")
                return {
                    'success': True,
                    'is_search_page': False,
                    'message': '不在搜索页面（缺少输入框）'
                }
            else:
                print(f"  ✗ 未检测到搜索页面特征元素")
                return {
                    'success': True,
                    'is_search_page': False,
                    'message': '不在搜索页面'
                }

        except Exception as e:
            print(f"  ⚠ 检测异常: {e}")
            return {
                'success': True,
                'is_search_page': False,  # 异常时假定不在搜索页面
                'message': f'检测异常，假定不在搜索页面: {str(e)}'
            }

    def check_is_user_page(self):
        """
        检测是否在用户页面

        通过检测6个特征元素，满足5个即确认在用户页面：
        1. 头像: com.ss.android.ugc.aweme:id/ky_
        2. 名字: com.ss.android.ugc.aweme:id/st1
        3. 抖音号: com.ss.android.ugc.aweme:id/4t1
        4. 元素4: com.ss.android.ugc.aweme:id/gth
        5. 元素5: com.ss.android.ugc.aweme:id/gth (重复)
        6. 元素6: com.ss.android.ugc.aweme:id/vfd

        Returns:
            dict: {
                'success': bool,  # 检测是否成功执行
                'is_user_page': bool,  # 是否在用户页面
                'matched_count': int,  # 匹配到的元素数量
                'message': str
            }
        """
        print("\n[检测] 是否在用户页面...")

        try:
            # 定义6个特征元素ID（注意：gth重复了，实际只有5个不同的ID）
            element_ids = {
                '头像': 'com.ss.android.ugc.aweme:id/ky_',
                '名字': 'com.ss.android.ugc.aweme:id/st1',
                '抖音号': 'com.ss.android.ugc.aweme:id/4t1',
                '元素4': 'com.ss.android.ugc.aweme:id/gth',
                '元素6': 'com.ss.android.ugc.aweme:id/vfd',
            }

            # 检测每个元素
            matched = []
            not_matched = []

            for name, element_id in element_ids.items():
                if self.element_exists(resourceId=element_id):
                    matched.append(name)
                    print(f"  ✓ 检测到 {name} ({element_id})")
                else:
                    not_matched.append(name)

            matched_count = len(matched)
            total_count = len(element_ids)

            print(f"\n  匹配结果: {matched_count}/{total_count} 个元素")

            # 满足5个或以上即确认在用户页面
            if matched_count >= 5:
                print(f"  ✓ 满足 {matched_count} 个特征元素，确认在用户页面")
                return {
                    'success': True,
                    'is_user_page': True,
                    'matched_count': matched_count,
                    'message': f'在用户页面 (匹配{matched_count}/{total_count})'
                }
            elif matched_count >= 3:
                print(f"  ⚠ 匹配 {matched_count} 个元素，可能在用户页面")
                print(f"  未匹配: {', '.join(not_matched)}")
                return {
                    'success': True,
                    'is_user_page': False,
                    'matched_count': matched_count,
                    'message': f'不在用户页面 (仅匹配{matched_count}/{total_count})'
                }
            else:
                print(f"  ✗ 仅匹配 {matched_count} 个元素，不在用户页面")
                return {
                    'success': True,
                    'is_user_page': False,
                    'matched_count': matched_count,
                    'message': f'不在用户页面 (仅匹配{matched_count}/{total_count})'
                }

        except Exception as e:
            print(f"  ⚠ 检测异常: {e}")
            return {
                'success': True,
                'is_user_page': False,
                'matched_count': 0,
                'message': f'检测异常，假定不在用户页面: {str(e)}'
            }

    def check_for_private_account(self):
        """
        检测是否为私密账户（仅检测，不执行任何操作）

        通过检测私密账户提示元素ID: com.ss.android.ugc.aweme:id/title

        Returns:
            dict: {
                'success': bool,  # 检测是否成功执行
                'is_private': bool,  # 是否为私密账户
                'message': str
            }
        """
        print("\n[检测] 是否为私密账户...")

        try:
            # 检测私密账户标题元素
            if self.element_exists(resourceId="com.ss.android.ugc.aweme:id/title"):
                element = self.auto(resourceId="com.ss.android.ugc.aweme:id/title")
                text = element.info.get('text', '')

                # 检查文本是否包含"私密"关键词
                if "私密" in text:
                    print(f"  ✓ 检测到私密账户: '{text}'")
                    return {
                        'success': True,
                        'is_private': True,
                        'message': f'检测到私密账户: {text}'
                    }

            print("  ✓ 非私密账户")
            return {
                'success': True,
                'is_private': False,
                'message': '非私密账户'
            }

        except Exception as e:
            print(f"  ⚠ 检测异常: {e}")
            return {
                'success': True,
                'is_private': False,  # 异常时假定非私密
                'message': f'检测异常，假定非私密: {str(e)}'
            }

    def check_for_no_content(self):
        """
        检测是否为暂无作品（仅检测，不执行任何操作）

        使用图像识别检测"暂无作品"图标

        Returns:
            dict: {
                'success': bool,  # 检测是否成功执行
                'no_content': bool,  # 是否暂无作品
                'message': str
            }
        """
        print("\n[检测] 是否为暂无作品...")

        # 使用设备专用模板路径
        no_content_icon = self._get_template_path("Noworks.png")

        # 检查模板图片是否存在
        if not os.path.exists(no_content_icon):
            print(f"  ⚠ 模板图片不存在: {no_content_icon}")
            print(f"  假定有作品")
            return {
                'success': True,
                'no_content': False,
                'message': '模板图片不存在，假定有作品'
            }

        try:
            # 方法1: 模板匹配（高阈值）
            print(f"  [图像识别] 查找'暂无作品'图标 from {no_content_icon}...")
            result = self.auto.find_image(no_content_icon, method="template", threshold=0.7)

            if result:
                x, y = int(result['result'][0]), int(result['result'][1])
                conf = result.get('confidence', 0)
                print(f"  ✓ [模板匹配] 检测到暂无作品 at ({x}, {y}), 相似度: {conf:.2%}")
                return {
                    'success': True,
                    'no_content': True,
                    'message': '检测到暂无作品'
                }

            # 方法2: 模板匹配（中阈值）
            print(f"  [模板匹配] 未找到，降低阈值重试...")
            result = self.auto.find_image(no_content_icon, method="template", threshold=0.6)

            if result:
                x, y = int(result['result'][0]), int(result['result'][1])
                conf = result.get('confidence', 0)
                print(f"  ✓ [模板匹配-中阈值] 检测到暂无作品 at ({x}, {y}), 相似度: {conf:.2%}")
                return {
                    'success': True,
                    'no_content': True,
                    'message': '检测到暂无作品'
                }

            # 未找到暂无作品图标
            print("  ✓ 未检测到暂无作品图标（有作品）")
            return {
                'success': True,
                'no_content': False,
                'message': '有作品'
            }

        except Exception as e:
            print(f"  ⚠ 检测异常: {e}")
            # 异常时假定有作品，避免误判
            return {
                'success': True,
                'no_content': False,
                'message': f'检测异常，假定有作品'
            }


# ============ 导出函数 ============

def create_douyin_operations(auto=None, device_id=None, template_manager=None, device_model=None):
    """
    创建抖音操作实例

    Args:
        auto: 自动化实例，如果为None则使用uiautomator2创建
        device_id: 设备ID，如果指定则连接到指定设备
        template_manager: 模板管理器实例(SimpleTemplateManager)
        device_model: 设备型号(用于获取设备专用模板)

    Returns:
        DouyinOperations实例
    """
    if auto is None:
        if u2 is None:
            raise ImportError("uiautomator2 is not installed. Please install it with: pip install uiautomator2")
        auto = u2.connect(device_id) if device_id else u2.connect()

    return DouyinOperations(auto, template_manager=template_manager, device_model=device_model)


if __name__ == "__main__":
    # 测试首页搜索按钮功能
    print("=" * 70)
    print("测试：首页搜索按钮（混合查找方案）")
    print("=" * 70)
    
    # 创建操作实例
    ops = create_douyin_operations()
    
    # 测试查找并点击搜索按钮
    result = ops.find_and_click_search_button()
    
    # 显示结果
    print("\n" + "=" * 70)
    print("测试结果")
    print("=" * 70)
    if result['success']:
        print(f"✓ 成功！")
        print(f"  使用方法: {result['method']}")
        print(f"  点击位置: {result['position']}")
        print(f"  详细信息: {result['message']}")
    else:
        print(f"✗ 失败")
        print(f"  详细信息: {result['message']}")
    print("=" * 70)

