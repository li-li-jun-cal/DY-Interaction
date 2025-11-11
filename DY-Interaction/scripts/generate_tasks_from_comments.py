#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评论用户去重并生成任务

功能:
  1. 从 Comment 表中提取所有评论用户
  2. 按 comment_user_id 去重
  3. 为每个新用户生成 InteractionTask
  4. 支持按评论时间分类（3个月作为分界线）
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import Comment, InteractionTask, TargetAccount
from sqlalchemy import func, distinct


def extract_unique_comment_users():
    """
    从 Comment 表提取所有唯一的评论用户

    Returns:
        List of dicts with user info
    """
    db = DatabaseManager()

    with db.get_session() as session:
        print('\n' + '='*70)
        print('📊 从评论数据提取唯一用户')
        print('='*70)

        # 获取已有任务的用户
        existing_users = session.query(func.distinct(InteractionTask.comment_user_id)).all()
        existing_user_ids = set(user[0] for user in existing_users)
        print(f'\n已有任务的用户数: {len(existing_user_ids)}')

        # 从 Comment 表获取所有唯一用户
        # 获取用户评论过的视频（选择最后评论的视频作为代表）
        unique_users = session.query(
            Comment.comment_user_id,
            Comment.comment_user_name,
            Comment.comment_uid,
            Comment.comment_sec_uid,
            Comment.comment_unique_id,
            func.count(Comment.id).label('comment_count'),
            func.min(Comment.comment_time).label('first_comment_time'),
            func.max(Comment.comment_time).label('last_comment_time'),
            func.min(Comment.target_account_id).label('target_account_id'),
            # 获取最后评论的视频ID（用于任务）
            func.max(Comment.video_id).label('last_video_id')
        ).group_by(
            Comment.comment_user_id
        ).all()

        print(f'Comment 表中的唯一用户数: {len(unique_users)}')

        # 筛选出未转换为任务的用户
        new_users = [u for u in unique_users if u[0] not in existing_user_ids]
        print(f'新用户（未转换为任务）: {len(new_users)}')

        print(f'\n提取用户详情:')
        # 取前10个示例
        for i, user in enumerate(new_users[:10], 1):
            print(f'  {i}. {user[1]} (评论数: {user[5]})')
        if len(new_users) > 10:
            print(f'  ... 还有 {len(new_users) - 10} 个用户')

        return new_users


def generate_tasks_from_comments(new_users=None):
    """
    为提取的用户生成 InteractionTask

    Args:
        new_users: 用户列表（如果为 None 则重新提取）
    """
    db = DatabaseManager()

    if new_users is None:
        # 重新提取用户
        new_users = extract_unique_comment_users()

    if not new_users:
        print('\n没有新用户可转换')
        return 0

    with db.get_session() as session:
        print('\n' + '='*70)
        print('🔄 为新用户生成任务')
        print('='*70)

        three_months_ago = datetime.now() - timedelta(days=90)
        created_count = 0
        skipped_count = 0

        for idx, user in enumerate(new_users, 1):
            if idx % 1000 == 0:
                print(f'\n进度: {idx}/{len(new_users)}')

            comment_user_id = user[0]
            comment_user_name = user[1]
            comment_uid = user[2]
            comment_sec_uid = user[3]
            comment_unique_id = user[4]
            comment_count = user[5]
            first_comment_time = user[6]
            last_comment_time = user[7]
            target_account_id = user[8]
            last_video_id = user[9]

            # 验证必要字段
            if not comment_unique_id:
                skipped_count += 1
                if idx <= 10:
                    print(f'  ⊗ 跳过用户 {comment_user_name}: 缺少 comment_unique_id')
                continue

            if not last_video_id:
                skipped_count += 1
                if idx <= 10:
                    print(f'  ⊗ 跳过用户 {comment_user_name}: 缺少 video_id')
                continue

            # 根据评论时间判断任务类型
            if last_comment_time and last_comment_time >= three_months_ago:
                # 最后评论时间在3个月内 -> history_recent
                task_type = 'history_recent'
            elif first_comment_time and first_comment_time < three_months_ago:
                # 第一条评论在3个月前 -> history_old
                task_type = 'history_old'
            else:
                # 无法判断，默认 history_recent
                task_type = 'history_recent'

            # 创建任务
            try:
                task = InteractionTask(
                    target_account_id=target_account_id,
                    comment_user_id=comment_user_id,
                    comment_user_name=comment_user_name,
                    comment_uid=comment_uid,
                    comment_sec_uid=comment_sec_uid,
                    comment_unique_id=comment_unique_id,
                    video_id=last_video_id,  # 使用最后评论的视频ID
                    comment_time=last_comment_time,
                    task_type=task_type,
                    priority='normal' if task_type == 'history_old' else 'high',
                    status='pending'
                )
                session.add(task)
                created_count += 1

                if idx <= 5:
                    print(f'  ✅ 创建任务: {comment_user_name} -> {task_type}')

            except Exception as e:
                skipped_count += 1
                if idx <= 10:
                    print(f'  ⊗ 创建失败 {comment_user_name}: {str(e)}')

        # 提交所有任务
        try:
            session.commit()
            print(f'\n✅ 任务生成完成！')
            print(f'  创建任务: {created_count} 个')
            print(f'  跳过用户: {skipped_count} 个')
            print(f'  总计: {created_count + skipped_count} 个')
        except Exception as e:
            session.rollback()
            print(f'\n❌ 提交失败: {str(e)}')
            return 0

        return created_count


def verify_results():
    """验证生成结果"""
    db = DatabaseManager()

    with db.get_session() as session:
        print('\n' + '='*70)
        print('✅ 验证结果')
        print('='*70)

        # 统计新的任务数据
        total_tasks = session.query(func.count(InteractionTask.id)).scalar() or 0
        unique_task_users = session.query(func.count(func.distinct(InteractionTask.comment_user_id))).scalar() or 0

        # 统计新的评论数据
        total_comments = session.query(func.count(Comment.id)).scalar() or 0
        unique_comment_users = session.query(func.count(func.distinct(Comment.comment_user_id))).scalar() or 0

        print(f'\n【Comment 表】')
        print(f'  总评论数: {total_comments}')
        print(f'  唯一用户数: {unique_comment_users}')

        print(f'\n【InteractionTask 表】')
        print(f'  总任务数: {total_tasks}')
        print(f'  唯一用户数: {unique_task_users}')

        print(f'\n【覆盖率】')
        coverage = (unique_task_users / unique_comment_users * 100) if unique_comment_users > 0 else 0
        print(f'  用户覆盖率: {coverage:.1f}%')

        # 按任务类型统计
        print(f'\n【任务分布】')
        realtime = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.task_type == 'realtime'
        ).scalar() or 0
        recent = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.task_type == 'history_recent'
        ).scalar() or 0
        old = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.task_type == 'history_old'
        ).scalar() or 0

        print(f'  realtime: {realtime}')
        print(f'  history_recent: {recent}')
        print(f'  history_old: {old}')

        print()


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='从评论数据生成任务')
    parser.add_argument('--auto', action='store_true', help='自动确认并执行')
    parser.add_argument('--verify-only', action='store_true', help='仅验证数据，不生成任务')
    args = parser.parse_args()

    print('\n' + '='*70)
    print('🔄 评论用户去重并生成任务')
    print('='*70)

    # 第1步: 提取唯一用户
    new_users = extract_unique_comment_users()

    # 第2步: 仅验证或生成任务
    if args.verify_only:
        print('\n仅验证模式，跳过任务生成')
    else:
        if args.auto or len(new_users) == 0:
            print('\n开始生成任务...')
            created = generate_tasks_from_comments(new_users)
        else:
            confirm = input(f'\n确认为 {len(new_users)} 个新用户生成任务? (yes/no): ').strip().lower()
            if confirm == 'yes':
                created = generate_tasks_from_comments(new_users)
            else:
                print('\n已取消')
                return

    # 第3步: 验证结果
    verify_results()

    print('='*70)
    print('\n✅ 完成！')
    print()


if __name__ == '__main__':
    main()
