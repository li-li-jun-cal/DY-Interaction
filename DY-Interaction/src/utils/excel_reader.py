"""
Excel数据读取模块
用于读取抖音ID列表和评论内容
"""
import pandas as pd
import os
from typing import List, Dict, Optional
from datetime import datetime


class ExcelReader:
    """Excel数据读取器"""

    def __init__(self, file_path: str):
        """
        初始化

        Args:
            file_path: Excel文件路径
        """
        self.file_path = file_path
        self.df = None

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Excel文件不存在: {file_path}")

        # 加载Excel
        self._load_excel()

    def _load_excel(self):
        """加载Excel文件"""
        try:
            self.df = pd.read_excel(self.file_path)
            print(f"[OK] 成功加载Excel: {self.file_path}")
            print(f"     总行数: {len(self.df)}")
            print(f"     列名: {list(self.df.columns)}")
        except Exception as e:
            raise Exception(f"加载Excel失败: {e}")

    def get_douyin_ids(self, column_name: str = None, column_index: int = 0,
                       skip_completed: bool = True, status_column: str = '状态') -> List[str]:
        """
        获取抖音ID列表（去除空值）

        Args:
            column_name: 列名（如果指定则使用列名，否则使用索引）
            column_index: 列索引（默认第0列）
            skip_completed: 是否跳过已完成的任务（默认True）
            status_column: 状态列名（默认'状态'）

        Returns:
            抖音ID列表
        """
        if self.df is None:
            raise Exception("Excel未加载")

        try:
            # 使用列名或索引获取数据
            if column_name:
                if column_name not in self.df.columns:
                    raise ValueError(f"列名不存在: {column_name}")
                column_data = self.df[column_name]
            else:
                column_data = self.df.iloc[:, column_index]

            # 去除空值，转换为字符串
            ids = []
            total_rows = 0
            skipped_rows = 0

            for idx, value in enumerate(column_data):
                if pd.notna(value):  # 排除NaN和None
                    total_rows += 1

                    # 检查是否需要跳过已完成的任务
                    if skip_completed and status_column in self.df.columns:
                        status = self.df.iloc[idx][status_column]
                        # 如果状态是"成功"，则跳过
                        if pd.notna(status) and str(status).strip() == '成功':
                            skipped_rows += 1
                            continue

                    ids.append(str(value).strip())

            print(f"[OK] 读取到 {len(ids)} 个待处理抖音ID（总数: {total_rows}, 已完成: {skipped_rows}）")
            return ids

        except Exception as e:
            raise Exception(f"读取抖音ID失败: {e}")

    def get_pending_douyin_ids(self, column_name: str = None, column_index: int = 0,
                               status_column: str = '状态') -> List[tuple]:
        """
        获取未处理的抖音ID列表（返回ID和行索引）

        Args:
            column_name: 列名（如果指定则使用列名，否则使用索引）
            column_index: 列索引（默认第0列）
            status_column: 状态列名（默认'状态'）

        Returns:
            [(row_index, douyin_id), ...] 列表
        """
        if self.df is None:
            raise Exception("Excel未加载")

        try:
            # 使用列名或索引获取数据
            if column_name:
                if column_name not in self.df.columns:
                    raise ValueError(f"列名不存在: {column_name}")
                column_data = self.df[column_name]
            else:
                column_data = self.df.iloc[:, column_index]

            # 获取未处理的ID（带行索引）
            pending_ids = []
            total_rows = 0
            skipped_rows = 0

            for idx, value in enumerate(column_data):
                if pd.notna(value):  # 排除NaN和None
                    total_rows += 1

                    # 检查状态列
                    if status_column in self.df.columns:
                        status = self.df.iloc[idx][status_column]
                        # 如果状态是"成功"，则跳过
                        if pd.notna(status) and str(status).strip() == '成功':
                            skipped_rows += 1
                            continue

                    pending_ids.append((idx, str(value).strip()))

            print(f"[OK] 读取到 {len(pending_ids)} 个待处理抖音ID（总数: {total_rows}, 已完成: {skipped_rows}）")
            return pending_ids

        except Exception as e:
            raise Exception(f"读取待处理抖音ID失败: {e}")

    def get_all_data(self) -> List[Dict]:
        """
        获取所有数据（字典列表格式）

        Returns:
            [{列名: 值}, ...]
        """
        if self.df is None:
            raise Exception("Excel未加载")

        return self.df.to_dict('records')

    def save_excel(self, output_path: str = None):
        """
        保存Excel文件

        Args:
            output_path: 输出路径，如果为None则覆盖原文件
        """
        if self.df is None:
            raise Exception("Excel未加载")

        save_path = output_path or self.file_path

        try:
            self.df.to_excel(save_path, index=False)
            print(f"[OK] Excel已保存: {save_path}")
        except Exception as e:
            raise Exception(f"保存Excel失败: {e}")

    def update_status(self, row_index: int, status_column: str, status_value: str,
                     timestamp_column: str = None, auto_save: bool = True):
        """
        更新指定行的状态

        Args:
            row_index: 行索引（从0开始）
            status_column: 状态列名
            status_value: 状态值
            timestamp_column: 时间戳列名（可选）
            auto_save: 是否自动保存到磁盘（默认True）
        """
        if self.df is None:
            raise Exception("Excel未加载")

        try:
            # 确保列存在
            if status_column not in self.df.columns:
                self.df[status_column] = ''

            # 更新状态
            self.df.at[row_index, status_column] = status_value

            # 更新时间戳（如果指定）
            if timestamp_column:
                if timestamp_column not in self.df.columns:
                    self.df[timestamp_column] = ''
                self.df.at[row_index, timestamp_column] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            print(f"[OK] 更新行 {row_index}: {status_column} = {status_value}")

            # 自动保存（如果启用）
            if auto_save:
                self.save_excel()
                print(f"[OK] 已保存到磁盘: {self.file_path}")

        except Exception as e:
            raise Exception(f"更新状态失败: {e}")

    def get_row_count(self) -> int:
        """获取总行数"""
        if self.df is None:
            return 0
        return len(self.df)

    def print_summary(self):
        """打印数据摘要"""
        if self.df is None:
            print("Excel未加载")
            return

        print("\n" + "=" * 60)
        print("Excel数据摘要")
        print("=" * 60)
        print(f"文件路径: {self.file_path}")
        print(f"总行数: {len(self.df)}")
        print(f"总列数: {len(self.df.columns)}")
        print(f"列名: {list(self.df.columns)}")
        print("\n前5行数据:")
        print(self.df.head())
        print("=" * 60)


# ============ 测试代码 ============

if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    print("Excel读取器测试")
    print("=" * 60)

    # 测试文件路径（使用相对路径）
    excel_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "4.xlsx")

    try:
        # 创建读取器
        reader = ExcelReader(excel_path)

        # 打印摘要
        reader.print_summary()

        # 读取抖音ID（第一列）
        print("\n读取抖音ID列表:")
        ids = reader.get_douyin_ids(column_index=0)
        print(f"前10个ID: {ids[:10]}")

        # 测试更新状态（不保存）
        print("\n测试更新状态:")
        reader.update_status(0, '状态', '已处理', '处理时间')
        print(reader.df.head())

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
