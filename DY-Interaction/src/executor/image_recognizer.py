"""
增强版图像识别工具 - 支持多种匹配算法提高准确度
从 an13 项目移植
"""
import cv2
import numpy as np
import aircv as ac
from typing import Optional, Tuple


class ImageRecognizer:
    """图像识别器 - 支持多种匹配算法"""

    def __init__(self, device, threshold: float = 0.8):
        self.device = device
        self.threshold = threshold

    def _imread_chinese(self, file_path: str):
        """
        读取包含中文路径的图片

        Args:
            file_path: 图片路径（可以包含中文）

        Returns:
            OpenCV 图片对象或 None
        """
        import os
        if not os.path.exists(file_path):
            return None

        # 使用 numpy 读取，绕过 OpenCV 的中文路径问题
        import numpy as np
        with open(file_path, 'rb') as f:
            image_data = f.read()

        # 将二进制数据转换为 numpy 数组
        image_array = np.frombuffer(image_data, dtype=np.uint8)

        # 解码图片
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        return image

    def find_image_template(self, template_path: str, threshold: float = 0.6,
                           bgremove: bool = True, rgb: bool = False) -> Optional[dict]:
        """
        使用模板匹配（支持背景移除和RGB模式）

        Args:
            template_path: 模板图片路径
            threshold: 匹配阈值
            bgremove: 是否移除背景（提高准确度）
            rgb: 是否使用RGB模式（默认False使用灰度）

        Returns:
            匹配结果字典或None
        """
        screen_pil = self.device.screenshot()
        screen = cv2.cvtColor(np.array(screen_pil), cv2.COLOR_RGB2BGR)

        # 支持中文路径
        template = self._imread_chinese(template_path)
        if template is None:
            print(f"[ERROR] 无法加载模板图片: {template_path}")
            return None

        # 使用aircv的find_template，支持背景移除
        result = ac.find_template(screen, template, threshold=threshold,
                                 rgb=rgb, bgremove=bgremove)

        if result:
            print(f"[模板匹配] 找到图片，相似度: {result['confidence']:.2%}, "
                  f"坐标: ({int(result['result'][0])}, {int(result['result'][1])})")
        return result

    def find_image_sift(self, template_path: str, min_match_count: int = 10) -> Optional[dict]:
        """
        使用SIFT特征点匹配（对缩放、旋转、光照变化鲁棒）

        Args:
            template_path: 模板图片路径
            min_match_count: 最小匹配特征点数量

        Returns:
            匹配结果字典或None
        """
        screen_pil = self.device.screenshot()
        screen = cv2.cvtColor(np.array(screen_pil), cv2.COLOR_RGB2BGR)

        # 支持中文路径
        template = self._imread_chinese(template_path)
        if template is None:
            print(f"[ERROR] 无法加载模板图片: {template_path}")
            print(f"请检查: 1) 文件是否存在  2) 路径是否正确")
            return None

        # 转换为灰度图
        screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        # 创建SIFT检测器
        sift = cv2.SIFT_create()

        # 检测关键点和描述符
        kp1, des1 = sift.detectAndCompute(template_gray, None)
        kp2, des2 = sift.detectAndCompute(screen_gray, None)

        if des1 is None or des2 is None:
            print("[SIFT匹配] 未检测到特征点")
            return None

        # 使用FLANN匹配器
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)

        matches = flann.knnMatch(des1, des2, k=2)

        # 应用比值测试
        good_matches = []
        for m_n in matches:
            if len(m_n) == 2:
                m, n = m_n
                if m.distance < 0.7 * n.distance:
                    good_matches.append(m)

        if len(good_matches) >= min_match_count:
            # 计算中心点
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches])
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches])

            # 计算模板在屏幕上的位置
            center_x = int(np.mean(dst_pts[:, 0]))
            center_y = int(np.mean(dst_pts[:, 1]))

            confidence = len(good_matches) / len(kp1) if len(kp1) > 0 else 0

            print(f"[SIFT匹配] 找到图片，匹配点数: {len(good_matches)}, "
                  f"相似度: {confidence:.2%}, 坐标: ({center_x}, {center_y})")

            return {
                'result': (center_x, center_y),
                'confidence': confidence,
                'matches': len(good_matches)
            }
        else:
            print(f"[SIFT匹配] 匹配点不足: {len(good_matches)}/{min_match_count}")
            return None

    def find_image_orb(self, template_path: str, min_match_count: int = 10) -> Optional[dict]:
        """
        使用ORB特征点匹配（速度更快，效果略差于SIFT）

        Args:
            template_path: 模板图片路径
            min_match_count: 最小匹配特征点数量

        Returns:
            匹配结果字典或None
        """
        screen_pil = self.device.screenshot()
        screen = cv2.cvtColor(np.array(screen_pil), cv2.COLOR_RGB2BGR)

        # 支持中文路径
        template = self._imread_chinese(template_path)
        if template is None:
            print(f"[ERROR] 无法加载模板图片: {template_path}")
            return None

        # 转换为灰度图
        screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        # 创建ORB检测器
        orb = cv2.ORB_create(nfeatures=1000)

        # 检测关键点和描述符
        kp1, des1 = orb.detectAndCompute(template_gray, None)
        kp2, des2 = orb.detectAndCompute(screen_gray, None)

        if des1 is None or des2 is None:
            print("[ORB匹配] 未检测到特征点")
            return None

        # 使用BFMatcher
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)

        # 按距离排序
        matches = sorted(matches, key=lambda x: x.distance)
        good_matches = matches[:min_match_count * 2]

        if len(good_matches) >= min_match_count:
            # 计算中心点
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches])

            center_x = int(np.mean(dst_pts[:, 0]))
            center_y = int(np.mean(dst_pts[:, 1]))

            confidence = len(good_matches) / len(kp1) if len(kp1) > 0 else 0

            print(f"[ORB匹配] 找到图片，匹配点数: {len(good_matches)}, "
                  f"相似度: {confidence:.2%}, 坐标: ({center_x}, {center_y})")

            return {
                'result': (center_x, center_y),
                'confidence': confidence,
                'matches': len(good_matches)
            }
        else:
            print(f"[ORB匹配] 匹配点不足: {len(good_matches)}/{min_match_count}")
            return None

    def find_image_auto(self, template_path: str) -> Optional[dict]:
        """
        自动尝试多种方法，返回最佳结果

        依次尝试：
        1. 模板匹配 + 背景移除
        2. SIFT特征匹配
        3. ORB特征匹配
        4. 降低阈值的模板匹配

        Returns:
            最佳匹配结果或None
        """
        print("\n[自动匹配] 开始尝试多种算法...")

        # 方法1: 模板匹配 + 背景移除
        print("\n尝试方法1: 模板匹配 + 背景移除")
        result = self.find_image_template(template_path, threshold=0.7, bgremove=True)
        if result and result['confidence'] > 0.7:
            return result

        # 方法2: SIFT特征匹配
        print("\n尝试方法2: SIFT特征匹配")
        result = self.find_image_sift(template_path, min_match_count=8)
        if result and result['confidence'] > 0.3:
            return result

        # 方法3: ORB特征匹配
        print("\n尝试方法3: ORB特征匹配")
        result = self.find_image_orb(template_path, min_match_count=8)
        if result and result['confidence'] > 0.3:
            return result

        # 方法4: 降低阈值的模板匹配
        print("\n尝试方法4: 降低阈值的模板匹配")
        result = self.find_image_template(template_path, threshold=0.5, bgremove=True)
        if result:
            return result

        print("\n所有方法都未能找到图片")
        return None

    def click_image(self, template_path: str, method: str = "auto", **kwargs) -> bool:
        """
        查找并点击图片

        Args:
            template_path: 模板图片路径
            method: 匹配方法 ("auto", "template", "sift", "orb")
            **kwargs: 传递给查找方法的额外参数

        Returns:
            是否成功点击
        """
        if method == "auto":
            result = self.find_image_auto(template_path)
        elif method == "template":
            result = self.find_image_template(template_path, **kwargs)
        elif method == "sift":
            result = self.find_image_sift(template_path, **kwargs)
        elif method == "orb":
            result = self.find_image_orb(template_path, **kwargs)
        else:
            print(f"未知方法: {method}")
            return False

        if result:
            x, y = result['result']
            self.device.click(int(x), int(y))
            print(f"\n[OK] 已点击坐标: ({int(x)}, {int(y)})")
            return True
        else:
            print("\n[ERROR] 未找到图片，无法点击")
            return False
