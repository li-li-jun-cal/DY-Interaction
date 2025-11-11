"""
评论文本管理器 - 从Excel文件循环选择评论文本
支持从指定列读取评论，用于多设备分列管理
"""
import random
from pathlib import Path
from typing import Optional, List, Union
from .excel_reader import ExcelReader


class CommentTextManager:
    """评论文本管理器 - 负责从Excel中循环选择评论"""

    def __init__(self, comments_file: Path, logger=None, column: Union[str, int] = None):
        """
        初始化评论文本管理器

        Args:
            comments_file: 评论文本Excel文件路径
            logger: 日志对象
            column: 列名或列索引（用于多设备分列管理）
                   - str: 列名（如 "A列评论", "B列评论"）
                   - int: 列索引（如 0, 1, 2）
                   - None: 自动检测（默认）

        Example:
            # 设备A使用第0列
            manager_A = CommentTextManager(file, column=0)

            # 设备B使用第1列
            manager_B = CommentTextManager(file, column=1)

            # 或使用列名
            manager_A = CommentTextManager(file, column="A设备评论")
            manager_B = CommentTextManager(file, column="B设备评论")
        """
        self.comments_file = comments_file
        self.logger = logger
        self.column = column  # 新增：指定列
        self.comments = []
        self.current_index = 0  # 当前循环索引

        # 加载评论文本
        self._load_comments()

    def _load_comments(self):
        """从Excel加载评论文本"""
        try:
            if not self.comments_file.exists():
                if self.logger:
                    self.logger.warning(f"评论文件不存在: {self.comments_file}")
                return

            # 使用ExcelReader读取评论
            excel_reader = ExcelReader(str(self.comments_file))

            # 如果指定了列
            if self.column is not None:
                if isinstance(self.column, int):
                    # 使用列索引
                    if self.column < len(excel_reader.df.columns):
                        self.comments = excel_reader.df.iloc[:, self.column].dropna().astype(str).tolist()
                        self.comments = [c.strip() for c in self.comments if c.strip()]
                        if self.logger:
                            col_name = excel_reader.df.columns[self.column]
                            self.logger.info(f"✓ 加载了 {len(self.comments)} 条评论文本 from 列[{self.column}]({col_name})")
                    else:
                        if self.logger:
                            self.logger.error(f"列索引 {self.column} 超出范围（共 {len(excel_reader.df.columns)} 列）")

                elif isinstance(self.column, str):
                    # 使用列名
                    if self.column in excel_reader.df.columns:
                        self.comments = excel_reader.df[self.column].dropna().astype(str).tolist()
                        self.comments = [c.strip() for c in self.comments if c.strip()]
                        if self.logger:
                            self.logger.info(f"✓ 加载了 {len(self.comments)} 条评论文本 from 列[{self.column}]")
                    else:
                        if self.logger:
                            self.logger.error(f"列名 '{self.column}' 不存在，可用列: {list(excel_reader.df.columns)}")

                return

            # 如果没有指定列，自动检测（向后兼容）
            # 尝试多个可能的列名
            possible_columns = ['评论内容', 'comment', 'text', '内容', 'Comment', 'Text']

            for col_name in possible_columns:
                if col_name in excel_reader.df.columns:
                    # 读取该列的所有非空值
                    self.comments = excel_reader.df[col_name].dropna().astype(str).tolist()
                    # 去除空字符串
                    self.comments = [c.strip() for c in self.comments if c.strip()]
                    break

            if not self.comments:
                # 如果没有找到指定列名,尝试读取第一列
                self.comments = excel_reader.df.iloc[:, 0].dropna().astype(str).tolist()
                self.comments = [c.strip() for c in self.comments if c.strip()]

            if self.logger:
                self.logger.info(f"✓ 加载了 {len(self.comments)} 条评论文本 from {self.comments_file.name}")

        except Exception as e:
            if self.logger:
                self.logger.error(f"加载评论文本失败: {e}")
            self.comments = []

    def get_next_comment(self) -> Optional[str]:
        """
        循环获取下一条评论文本（按顺序遍历列表）

        Returns:
            评论文本,如果没有可用评论则返回None
        """
        if not self.comments:
            if self.logger:
                self.logger.warning("没有可用的评论文本")
            return None

        # 获取当前索引的评论
        comment = self.comments[self.current_index]

        # 移动到下一个索引，循环回到开头
        self.current_index = (self.current_index + 1) % len(self.comments)

        return comment

    def get_random_comment(self) -> Optional[str]:
        """
        循环获取下一条评论文本（保持向后兼容）

        注意：此方法已改为循环遍历，不再随机选择

        Returns:
            评论文本,如果没有可用评论则返回None
        """
        return self.get_next_comment()

    def get_multiple_comments(self, count: int) -> List[str]:
        """
        循环获取多条评论文本（按顺序遍历）

        Args:
            count: 需要的评论数量

        Returns:
            评论文本列表
        """
        if not self.comments:
            if self.logger:
                self.logger.warning("没有可用的评论文本")
            return []

        return [self.get_next_comment() for _ in range(count)]

    def has_comments(self) -> bool:
        """
        检查是否有可用的评论文本

        Returns:
            True if 有评论, False otherwise
        """
        return len(self.comments) > 0

    def get_comment_count(self) -> int:
        """
        获取评论文本数量

        Returns:
            评论数量
        """
        return len(self.comments)


# ============ 测试代码 ============

if __name__ == "__main__":
    from utils.logger import get_logger

    logger = get_logger(name="CommentTextManagerTest")

    # 测试评论文本管理器
    comments_file = Path("devices/default/comments.xlsx")

    if comments_file.exists():
        manager = CommentTextManager(comments_file, logger=logger)

        print(f"\n总评论数: {manager.get_comment_count()}")

        if manager.has_comments():
            print("\n循环选择10条评论（测试循环效果）:")
            for i in range(10):
                comment = manager.get_next_comment()
                print(f"  {i+1}. {comment}")

            print(f"\n当前索引: {manager.current_index}")
    else:
        print(f"测试文件不存在: {comments_file}")
