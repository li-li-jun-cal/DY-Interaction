#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除缺少comment_unique_id的任务

原因：这些任务无法通过抖音搜索找到用户，无法正常执行
解决：删除这912个缺陷任务，保留4245个完整的任务
"""

import sys
from pathlib import Path

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import InteractionTask
from sqlalchemy import func


def analyze_tasks():
    """分析缺少comment_unique_id的任务"""
    db = DatabaseManager()

    with db.get_session() as session:
        print("=" * 70)
        print("分析缺少抖音号的任务")
        print("=" * 70)

        # 统计总任务数
        total_tasks = session.query(func.count(InteractionTask.id)).scalar() or 0
        print(f"\n当前总任务数: {total_tasks}")

        # 统计有comment_unique_id的任务
        with_unique_id = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.comment_unique_id.isnot(None),
            InteractionTask.comment_unique_id != ''
        ).scalar() or 0

        # 统计缺少comment_unique_id的任务
        without_unique_id = session.query(func.count(InteractionTask.id)).filter(
            (InteractionTask.comment_unique_id.is_(None)) |
            (InteractionTask.comment_unique_id == '')
        ).scalar() or 0

        print(f"有comment_unique_id（正常）: {with_unique_id} ({with_unique_id/total_tasks*100:.1f}%)")
        print(f"缺少comment_unique_id（缺陷）: {without_unique_id} ({without_unique_id/total_tasks*100:.1f}%)")

        if without_unique_id > 0:
            print(f"\n⚠️ 将要删除 {without_unique_id} 个缺陷任务")

            # 显示一些缺少unique_id的任务示例
            missing_tasks = session.query(InteractionTask).filter(
                (InteractionTask.comment_unique_id.is_(None)) |
                (InteractionTask.comment_unique_id == '')
            ).limit(10).all()

            print("\n缺陷任务示例:")
            for task in missing_tasks:
                print(f"  任务#{task.id}: {task.comment_user_name}")
                print(f"    comment_user_id: {task.comment_user_id}")
                print(f"    comment_uid: {task.comment_uid}")
                print(f"    status: {task.status}")
                print()

        return without_unique_id, total_tasks


def delete_defective_tasks():
    """删除缺少comment_unique_id的任务"""
    db = DatabaseManager()

    with db.get_session() as session:
        print("\n" + "=" * 70)
        print("删除缺陷任务")
        print("=" * 70)

        # 查找缺少unique_id的任务
        missing_tasks = session.query(InteractionTask).filter(
            (InteractionTask.comment_unique_id.is_(None)) |
            (InteractionTask.comment_unique_id == '')
        ).all()

        delete_count = len(missing_tasks)

        if delete_count == 0:
            print("\n✅ 没有缺陷任务需要删除")
            return 0

        # 按ID进行删除
        for task in missing_tasks:
            session.delete(task)

        session.commit()
        print(f"\n✓ 成功删除 {delete_count} 个缺陷任务")
        return delete_count


def verify_deletion():
    """验证删除结果"""
    from sqlalchemy import distinct
    db = DatabaseManager()

    with db.get_session() as session:
        print("\n" + "=" * 70)
        print("验证删除结果")
        print("=" * 70)

        # 重新统计
        total_tasks = session.query(func.count(InteractionTask.id)).scalar() or 0
        with_unique_id = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.comment_unique_id.isnot(None),
            InteractionTask.comment_unique_id != ''
        ).scalar() or 0
        without_unique_id = total_tasks - with_unique_id

        print(f"\n删除后的统计:")
        print(f"  总任务数: {total_tasks}")
        print(f"  有抖音号: {with_unique_id} ({with_unique_id/total_tasks*100:.1f}% if total_tasks > 0 else 0)%)")
        print(f"  缺少抖音号: {without_unique_id}")

        if without_unique_id == 0:
            print("\n✅ 所有任务都有抖音号了！自动化任务可以正常执行。")

            # 统计用户数
            unique_users = session.query(func.count(distinct(InteractionTask.comment_user_id))).scalar() or 0
            print(f"✅ 任务数 ({total_tasks}) = 用户数 ({unique_users})，数据完整！")
        else:
            print(f"\n⚠️ 还有 {without_unique_id} 个任务缺少抖音号，删除可能失败")


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='删除缺少comment_unique_id的缺陷任务')
    parser.add_argument('--auto', action='store_true', help='自动确认删除')
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("删除缺陷任务 - comment_unique_id为空的任务")
    print("=" * 70)
    print("\n说明：这些任务因为缺少抖音号，无法在自动化中搜索到用户")
    print("      必须删除这些缺陷任务，保留完整的任务")

    # 1. 分析现状
    missing_count, total_tasks = analyze_tasks()

    if missing_count == 0:
        print("\n✅ 所有任务都正常，无需删除")
        return

    # 2. 确认删除
    if args.auto:
        print(f"\n自动模式：准备删除 {missing_count} 个缺陷任务")
        confirm = 'yes'
    else:
        print("\n" + "=" * 70)
        print(f"⚠️ 警告：即将删除 {missing_count} 个任务")
        print(f"    删除后将保留 {total_tasks - missing_count} 个正常任务")
        confirm = input("确认删除? (yes/no): ").strip().lower()

    if confirm != 'yes':
        print("已取消删除")
        return

    # 3. 执行删除
    deleted = delete_defective_tasks()

    # 4. 验证结果
    verify_deletion()

    print("\n" + "=" * 70)
    print("删除完成！")
    print("=" * 70)
    print("\n后续步骤：")
    print("  1. 所有剩余任务都有有效的抖音号")
    print("  2. 自动化任务现在可以正常搜索用户")
    print("  3. 如果需要更多任务，请重新运行爬虫")


if __name__ == '__main__':
    main()
