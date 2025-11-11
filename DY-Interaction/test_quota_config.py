#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试每日配额配置功能
"""

import sys
from pathlib import Path

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config.daily_quota import interactive_quota_config
from src.database.manager import DatabaseManager
from sqlalchemy import func
from src.database.models import InteractionTask

def main():
    """测试配额配置"""
    print("\n" + "=" * 70)
    print("🧪 每日配额配置测试")
    print("=" * 70)

    # 从数据库获取任务数
    try:
        db = DatabaseManager()
        with db.get_session() as session:
            total_tasks = session.query(func.count(InteractionTask.id)).scalar() or 0
        print(f"\n✓ 数据库中有 {total_tasks} 个任务")
    except Exception as e:
        print(f"✗ 获取任务数失败: {e}")
        total_tasks = 4245  # 使用默认值

    # 调用交互式配置
    quota = interactive_quota_config(total_tasks=total_tasks)

    # 显示结果
    print("\n" + "=" * 70)
    print("✅ 配置结果")
    print("=" * 70)
    print(f"✓ {quota.get_summary()}")
    print("=" * 70)

    # 测试各个方法
    print("\n📝 测试配额限制方法:")
    print(f"  can_process_user(100): {quota.can_process_user(100)} (应该为 True)")
    print(f"  can_process_user({quota.max_users}): {quota.can_process_user(quota.max_users)} (应该为 False)")
    print(f"  can_follow(50): {quota.can_follow(50)} (应该为 True)")
    print(f"  can_follow({quota.max_follow}): {quota.can_follow(quota.max_follow)} (应该为 False)")
    print(f"  can_like(200): {quota.can_like(200)} (应该为 True)")
    print(f"  can_like({quota.max_like}): {quota.can_like(quota.max_like)} (应该为 False)")
    print(f"  can_collect(300): {quota.can_collect(300)} (应该为 True)")
    print(f"  can_collect({quota.max_collect}): {quota.can_collect(quota.max_collect)} (应该为 False)")

    print("\n✅ 测试完成！\n")


if __name__ == '__main__':
    main()
