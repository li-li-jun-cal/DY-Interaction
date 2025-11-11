"""
测试基于设备的任务去重逻辑

验证：
1. 同一用户可以被多台设备关注（可配置上限）
2. 同一设备不会重复关注同一用户
3. 任务生成器正确统计已完成设备数
4. 任务调度器正确过滤已完成用户
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager
from src.database.models import InteractionTask
from src.scheduler.task_scheduler import TaskScheduler
from src.generator.task_generator import TaskGenerator
from sqlalchemy import func

def test_device_based_deduplication():
    """测试基于设备的去重逻辑"""
    print("\n" + "=" * 80)
    print("测试基于设备的任务去重逻辑")
    print("=" * 80)

    db = DatabaseManager()
    session = db.get_session()
    scheduler = TaskScheduler(db)
    generator = TaskGenerator(db)

    try:
        # 1. 查看配置
        print(f"\n[1] 当前配置:")
        print(f"  允许最多 {generator.max_follow_devices} 台设备关注同一用户")

        # 2. 统计任务状态
        print(f"\n[2] 任务状态统计:")
        status_stats = session.query(
            InteractionTask.status,
            func.count(InteractionTask.id)
        ).group_by(InteractionTask.status).all()

        for status, count in status_stats:
            print(f"  {status:15s}: {count:5d}")

        # 3. 查找被多台设备完成的用户
        print(f"\n[3] 被多台设备关注的用户（Top 10）:")

        multi_device_users = session.query(
            InteractionTask.comment_user_name,
            InteractionTask.comment_unique_id,
            func.count(func.distinct(InteractionTask.assigned_device)).label('device_count')
        ).filter(
            InteractionTask.status == 'completed',
            InteractionTask.assigned_device.isnot(None)
        ).group_by(
            InteractionTask.comment_user_name,
            InteractionTask.comment_unique_id
        ).having(
            func.count(func.distinct(InteractionTask.assigned_device)) > 1
        ).order_by(
            func.count(func.distinct(InteractionTask.assigned_device)).desc()
        ).limit(10).all()

        if multi_device_users:
            print(f"\n  {'用户名':<25s} {'抖音号':<20s} {'设备数':<10s}")
            print("  " + "-" * 55)
            for user_name, unique_id, device_count in multi_device_users:
                print(f"  {user_name:<25s} {unique_id or 'N/A':<20s} {device_count:<10d}")
        else:
            print("  暂无被多台设备关注的用户")

        # 4. 测试任务分配逻辑
        print(f"\n[4] 测试任务分配逻辑:")

        # 选择一个有待处理任务的账号
        pending_task = session.query(InteractionTask)\
            .filter_by(status='pending')\
            .first()

        if pending_task:
            test_user = pending_task.comment_user_name
            test_unique_id = pending_task.comment_unique_id

            print(f"\n  测试用户: {test_user} ({test_unique_id})")

            # 统计该用户有多少台设备完成
            completed_devices = session.query(
                func.count(func.distinct(InteractionTask.assigned_device))
            ).filter(
                InteractionTask.status == 'completed',
                InteractionTask.comment_unique_id == test_unique_id,
                InteractionTask.assigned_device.isnot(None)
            ).scalar() or 0

            print(f"  已有 {completed_devices} 台设备完成")

            # 查看哪些设备完成了
            completed_by = session.query(
                InteractionTask.assigned_device
            ).filter(
                InteractionTask.status == 'completed',
                InteractionTask.comment_unique_id == test_unique_id,
                InteractionTask.assigned_device.isnot(None)
            ).distinct().all()

            if completed_by:
                print(f"  完成设备: {', '.join([d[0] for d in completed_by])}")

            # 检查是否还有待处理任务
            pending_count = session.query(InteractionTask)\
                .filter(
                    InteractionTask.status == 'pending',
                    InteractionTask.comment_unique_id == test_unique_id
                )\
                .count()

            print(f"  待处理任务: {pending_count}")

            if completed_devices < generator.max_follow_devices:
                print(f"  ✓ 未达上限，可以为其他设备生成任务")
            else:
                print(f"  ✗ 已达上限 ({completed_devices}/{generator.max_follow_devices})，不会再生成新任务")

        else:
            print("  暂无待处理任务，无法测试")

        # 5. 测试设备任务分配过滤
        print(f"\n[5] 测试设备任务分配过滤:")

        # 随机选择一台设备
        test_device = "Device-1"

        # 获取该设备已完成的用户数
        device_completed_count = session.query(
            func.count(func.distinct(InteractionTask.comment_unique_id))
        ).filter(
            InteractionTask.assigned_device == test_device,
            InteractionTask.status == 'completed',
            InteractionTask.comment_unique_id.isnot(None)
        ).scalar() or 0

        print(f"\n  测试设备: {test_device}")
        print(f"  已完成用户数: {device_completed_count}")

        # 测试获取任务
        task = scheduler.get_next_task_for_device(test_device, 'history')

        if task:
            print(f"  ✓ 获取到任务 #{task.id}: {task.comment_user_name}")

            # 验证该用户是否被该设备完成过
            is_completed_by_device = session.query(InteractionTask)\
                .filter(
                    InteractionTask.assigned_device == test_device,
                    InteractionTask.status == 'completed',
                    InteractionTask.comment_unique_id == task.comment_unique_id
                )\
                .first()

            if is_completed_by_device:
                print(f"  ✗ 错误: 该用户已被设备完成过！")
            else:
                print(f"  ✓ 验证通过: 该用户未被设备完成过")

            # 回退任务状态
            task.status = 'pending'
            task.assigned_device = None
            session.commit()
            print(f"  (已回退任务状态)")

        else:
            print(f"  ⊗ 无可分配任务")

        # 6. 总结
        print(f"\n" + "=" * 80)
        print("测试总结")
        print("=" * 80)

        total_pending = session.query(InteractionTask)\
            .filter_by(status='pending')\
            .count()

        total_completed = session.query(InteractionTask)\
            .filter_by(status='completed')\
            .count()

        unique_users = session.query(
            func.count(func.distinct(InteractionTask.comment_unique_id))
        ).filter(
            InteractionTask.comment_unique_id.isnot(None)
        ).scalar() or 0

        print(f"\n  待处理任务: {total_pending}")
        print(f"  已完成任务: {total_completed}")
        print(f"  去重用户数: {unique_users}")
        print(f"  配置上限: {generator.max_follow_devices} 台设备/用户")

        if multi_device_users:
            print(f"  ✓ 已有 {len(multi_device_users)} 个用户被多台设备关注")
        else:
            print(f"  ⊗ 暂无用户被多台设备关注")

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        session.close()


if __name__ == "__main__":
    test_device_based_deduplication()
