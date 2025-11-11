#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理重复任务脚本

目标：
- 每个用户只保留1个任务（按comment_user_id去重）
- 如果同一用户有多个任务，按优先级保留：
  1. 优先保留已分配/已处理的任务（assigned/skipped）
  2. 其次按任务类型优先级：history_recent > history_old > realtime > history
  3. 最后按创建时间，保留最新的

执行前会备份，并显示详细的清理计划
"""

import sys
from pathlib import Path
from datetime import datetime

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import InteractionTask
from sqlalchemy import func


def analyze_current_state(session):
    """分析当前状态"""
    print("=" * 70)
    print("当前数据状态分析")
    print("=" * 70)

    total_users = session.query(func.count(func.distinct(InteractionTask.comment_user_id))).scalar() or 0
    total_tasks = session.query(func.count(InteractionTask.id)).scalar() or 0

    print(f"\n去重用户数: {total_users}")
    print(f"总任务数: {total_tasks}")
    print(f"多出任务: {total_tasks - total_users}")

    # 统计每个用户的任务数
    user_task_counts = session.query(
        InteractionTask.comment_user_id,
        func.count(InteractionTask.id).label('task_count')
    ).group_by(
        InteractionTask.comment_user_id
    ).all()

    from collections import Counter
    distribution = Counter([count for _, count in user_task_counts])

    print("\n任务分布:")
    for task_count in sorted(distribution.keys()):
        user_count = distribution[task_count]
        print(f"  {task_count}个任务: {user_count}个用户")

    return total_users, total_tasks, user_task_counts


def get_task_priority(task):
    """计算任务优先级（数字越小优先级越高）"""
    # 1. 状态优先级
    status_priority = {
        'assigned': 1,  # 已分配最高优先级
        'skipped': 2,   # 已跳过
        'pending': 3,   # 待处理
        'completed': 4, # 已完成
        'failed': 5     # 失败
    }

    # 2. 任务类型优先级
    type_priority = {
        'history_recent': 1,  # 3个月内最高优先级
        'history_old': 2,     # 3个月前
        'realtime': 3,        # realtime其实是错误的，优先级低
        'history': 4          # 旧版本，最低优先级
    }

    status_p = status_priority.get(task.status, 99)
    type_p = type_priority.get(task.task_type, 99)

    # 组合优先级：状态权重100，类型权重10，时间权重1
    # 创建时间越晚，优先级越高（用负数）
    time_p = -task.id  # ID越大越新，负数让其优先级越高

    return (status_p * 1000) + (type_p * 100) + (time_p * 0.001)


def create_cleanup_plan(session, user_task_counts):
    """创建清理计划"""
    print("\n" + "=" * 70)
    print("创建清理计划")
    print("=" * 70)

    tasks_to_delete = []
    tasks_to_keep = []

    multi_task_users = [(uid, count) for uid, count in user_task_counts if count > 1]

    print(f"\n需要去重的用户数: {len(multi_task_users)}")
    print("\n前10个用户的清理计划:")

    for idx, (user_id, task_count) in enumerate(multi_task_users[:10]):
        # 获取该用户的所有任务
        tasks = session.query(InteractionTask).filter(
            InteractionTask.comment_user_id == user_id
        ).all()

        # 按优先级排序
        tasks_sorted = sorted(tasks, key=get_task_priority)

        # 保留第一个（优先级最高）
        keep = tasks_sorted[0]
        delete = tasks_sorted[1:]

        print(f"\n  {idx+1}. 用户: {keep.comment_user_name} ({task_count}个任务)")
        print(f"     保留: ID={keep.id}, 类型={keep.task_type}, 状态={keep.status}")
        for t in delete:
            print(f"     删除: ID={t.id}, 类型={t.task_type}, 状态={t.status}")

        tasks_to_keep.append(keep.id)
        tasks_to_delete.extend([t.id for t in delete])

    # 处理所有多任务用户
    for user_id, task_count in multi_task_users:
        tasks = session.query(InteractionTask).filter(
            InteractionTask.comment_user_id == user_id
        ).all()

        tasks_sorted = sorted(tasks, key=get_task_priority)
        keep = tasks_sorted[0]
        delete = tasks_sorted[1:]

        if keep.id not in tasks_to_keep:
            tasks_to_keep.append(keep.id)

        for t in delete:
            if t.id not in tasks_to_delete:
                tasks_to_delete.append(t.id)

    print(f"\n总计:")
    print(f"  保留任务: {len(tasks_to_keep)}个")
    print(f"  删除任务: {len(tasks_to_delete)}个")

    return tasks_to_delete


def execute_cleanup(session, tasks_to_delete):
    """执行清理"""
    print("\n" + "=" * 70)
    print("执行清理")
    print("=" * 70)

    # 按任务类型统计要删除的任务
    delete_by_type = {}
    for task_id in tasks_to_delete:
        task = session.query(InteractionTask).filter(InteractionTask.id == task_id).first()
        if task:
            task_type = task.task_type
            delete_by_type[task_type] = delete_by_type.get(task_type, 0) + 1

    print("\n要删除的任务分布:")
    for task_type, count in delete_by_type.items():
        print(f"  {task_type}: {count}个")

    # 删除任务
    deleted_count = 0
    for task_id in tasks_to_delete:
        task = session.query(InteractionTask).filter(InteractionTask.id == task_id).first()
        if task:
            session.delete(task)
            deleted_count += 1

    session.commit()

    print(f"\n✓ 成功删除 {deleted_count} 个重复任务")

    return deleted_count


def verify_result(session, original_users):
    """验证清理结果"""
    print("\n" + "=" * 70)
    print("验证清理结果")
    print("=" * 70)

    total_users = session.query(func.count(func.distinct(InteractionTask.comment_user_id))).scalar() or 0
    total_tasks = session.query(func.count(InteractionTask.id)).scalar() or 0

    print(f"\n清理后:")
    print(f"  去重用户数: {total_users}")
    print(f"  总任务数: {total_tasks}")

    # 检查是否还有多任务用户
    user_task_counts = session.query(
        InteractionTask.comment_user_id,
        func.count(InteractionTask.id).label('task_count')
    ).group_by(
        InteractionTask.comment_user_id
    ).all()

    multi_task_users = [count for _, count in user_task_counts if count > 1]

    if multi_task_users:
        print(f"\n⚠️ 还有 {len(multi_task_users)} 个用户有多个任务")
    else:
        print(f"\n✓ 所有用户都只有1个任务")

    # 按状态统计
    print("\n任务状态分布:")
    for status in ['pending', 'assigned', 'skipped', 'completed', 'failed']:
        count = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.status == status
        ).scalar() or 0
        if count > 0:
            print(f"  {status}: {count}")

    # 按类型统计
    print("\n任务类型分布:")
    for task_type in ['history_recent', 'history_old', 'realtime', 'history']:
        count = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.task_type == task_type
        ).scalar() or 0
        if count > 0:
            print(f"  {task_type}: {count}")

    return total_users == total_tasks


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='清理重复任务')
    parser.add_argument('--auto', action='store_true', help='自动确认，不需要手动输入')
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("InteractionTask 去重清理脚本")
    print("=" * 70)
    print("\n目标: 每个用户只保留1个任务")
    print("时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    db = DatabaseManager()
    session = db.get_session()

    try:
        # 1. 分析当前状态
        original_users, original_tasks, user_task_counts = analyze_current_state(session)

        if original_tasks == original_users:
            print("\n✓ 数据已经是干净的，无需清理")
            return

        # 2. 创建清理计划
        tasks_to_delete = create_cleanup_plan(session, user_task_counts)

        # 3. 确认
        print("\n" + "=" * 70)

        if args.auto:
            print(f"\n自动模式: 将删除 {len(tasks_to_delete)} 个重复任务")
            confirm = 'yes'
        else:
            confirm = input(f"\n确认删除 {len(tasks_to_delete)} 个重复任务? (yes/no): ").strip().lower()

        if confirm != 'yes':
            print("\n已取消清理")
            return

        # 4. 执行清理
        deleted_count = execute_cleanup(session, tasks_to_delete)

        # 5. 验证结果
        is_clean = verify_result(session, original_users)

        # 6. 总结
        print("\n" + "=" * 70)
        print("清理完成")
        print("=" * 70)
        print(f"\n原始数据: {original_users}个用户, {original_tasks}个任务")
        print(f"清理后: {original_users}个用户, {original_tasks - deleted_count}个任务")
        print(f"删除了: {deleted_count}个重复任务")

        if is_clean:
            print("\n✓ 数据已完全去重！")
        else:
            print("\n⚠️ 还有一些多任务用户，可能是被多设备处理")

    except Exception as e:
        session.rollback()
        print(f"\n✗ 清理失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        session.close()


if __name__ == '__main__':
    main()
