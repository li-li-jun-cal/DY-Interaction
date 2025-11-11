#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DY-Interaction 主菜单 - 命令行交互界面
简单的菜单系统，让您选择要运行的功能
"""

import sys
import subprocess
from pathlib import Path

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import DatabaseManager


def clear_screen():
    """清屏"""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')


def show_header():
    """显示标题"""
    print("=" * 70)
    print("                    DY-Interaction 管理系统")
    print("=" * 70)
    print()


def show_statistics():
    """显示数据统计"""
    db = DatabaseManager()

    # 获取统计数据
    from src.database.models import InteractionTask, TargetAccount, Device, NewComment
    from sqlalchemy import func

    with db.session_scope() as session:
        from datetime import datetime, timedelta

        three_months_ago = datetime.now() - timedelta(days=90)

        # 总用户数
        total_users = session.query(func.count(func.distinct(InteractionTask.comment_user_id))).scalar() or 0

        # 新增用户（最近一次监控发现的新增评论用户）
        # 应该统计 NewComment 表中的唯一用户，这是监控爬虫最近一次发现的新增评论
        new_users = session.query(func.count(func.distinct(NewComment.comment_user_id))).scalar() or 0

        # 3个月内评论用户（按评论时间）
        users_3months = session.query(func.count(func.distinct(InteractionTask.comment_user_id))).filter(
            InteractionTask.comment_time >= three_months_ago,
            InteractionTask.comment_time.isnot(None)
        ).scalar() or 0

        # 3个月前评论用户（按评论时间）
        old_users = session.query(func.count(func.distinct(InteractionTask.comment_user_id))).filter(
            InteractionTask.comment_time < three_months_ago,
            InteractionTask.comment_time.isnot(None)
        ).scalar() or 0

        # 已完成任务 (包括assigned和skipped)
        completed = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.status.in_(['assigned', 'skipped', 'completed'])
        ).scalar() or 0

        # 待完成任务
        pending = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.status == 'pending'
        ).scalar() or 0

        # 总任务数
        total_tasks = session.query(func.count(InteractionTask.id)).scalar() or 0

        # 完成率
        completion_rate = (completed / total_tasks * 100) if total_tasks > 0 else 0

        # 目标账号数
        account_count = session.query(func.count(TargetAccount.id)).scalar() or 0

        # 在线设备数（idle或busy状态）
        online_devices = session.query(func.count(Device.id)).filter(
            Device.status.in_(['idle', 'busy'])
        ).scalar() or 0

    print("📊 数据统计:")
    print(f"  评论用户总量: {total_users} (去重)")
    print(f"  ├─ 新增用户(监控发现): {new_users}")
    print(f"  ├─ 3个月内评论用户: {users_3months}")
    print(f"  └─ 3个月前评论用户: {old_users}")
    print(f"  任务总数: {total_tasks} (每用户1任务)")
    print(f"  ├─ 已处理: {completed} ({completion_rate:.1f}%)")
    print(f"  └─ 待处理: {pending}")

    # 获取操作统计数据
    from src.database.models import DeviceDailyStats, Comment
    total_follow = session.query(func.sum(DeviceDailyStats.follow_count)).scalar() or 0
    total_like = session.query(func.sum(DeviceDailyStats.like_count)).scalar() or 0
    total_collect = session.query(func.sum(DeviceDailyStats.collect_count)).scalar() or 0
    total_comments = session.query(func.count(Comment.id)).scalar() or 0

    print(f"  操作统计:")
    print(f"  ├─ 总关注数: {total_follow}")
    print(f"  ├─ 总点赞数: {total_like}")
    print(f"  ├─ 总收藏数: {total_collect}")
    print(f"  └─ 评论数据: {total_comments}")
    print(f"  目标账号数: {account_count}")
    print(f"  在线设备数: {online_devices}")
    print()


def show_menu():
    """显示主菜单"""
    print("📋 功能菜单:")
    print()
    print("  【爬虫管理】")
    print("    1. 启动全量爬虫 (爬取历史评论)")
    print("    2. 启动监控爬虫 (监控新增评论)")
    print()
    print("  【自动化任务】")
    print("    3. 启动实时自动化 (处理新增评论)")
    print("    4. 启动近期自动化 (处理3个月内评论)")
    print("    5. 启动长期自动化 (处理3个月以上评论)")
    print("    6. 启动混合自动化 (实时+近期)")
    print()
    print("  【系统管理】")
    print("    7. 查看详细统计")
    print("    8. 查看设备列表")
    print("    9. 查看账号列表")
    print("   10. 添加目标账号")
    print("   11. 删除目标账号")
    print("   12. 管理API服务器 (添加/删除/修改)")
    print()
    print("  【数据维护】")
    print("   13. 生成缺失任务 (从评论数据提取新用户)")
    print("   14. 清理重复任务")
    print("   15. 删除缺陷任务 (无comment_unique_id)")
    print("   16. 更新Cookie配置")
    print("   17. 检查设备状态")
    print()
    print("    0. 退出")
    print()


def run_command(cmd, description):
    """运行命令"""
    print(f"\n{'=' * 70}")
    print(f"▶ {description}")
    print(f"{'=' * 70}\n")

    try:
        # 使用subprocess运行命令，保持交互
        result = subprocess.run(cmd, shell=True, cwd=str(PROJECT_ROOT))

        print(f"\n{'=' * 70}")
        if result.returncode == 0:
            print(f"✓ {description} - 执行完成")
        else:
            print(f"✗ {description} - 执行失败 (退出码: {result.returncode})")
        print(f"{'=' * 70}\n")

    except KeyboardInterrupt:
        print("\n\n⚠ 用户中断")
    except Exception as e:
        print(f"\n✗ 执行出错: {e}\n")

    input("\n按回车键返回主菜单...")


def show_devices():
    """显示设备列表"""
    db = DatabaseManager()
    from src.database.models import Device

    with db.session_scope() as session:
        devices = session.query(Device).all()

        print(f"\n{'=' * 70}")
        print("📱 设备列表")
        print(f"{'=' * 70}\n")

        if not devices:
            print("  暂无设备")
        else:
            print(f"{'ID':<5} {'设备名':<20} {'型号':<20} {'状态':<10}")
            print("-" * 70)
            for dev in devices:
                # status: idle, busy, error, offline
                status_icon = "🟢" if dev.status in ['idle', 'busy'] else "🔴"
                print(f"{dev.id:<5} {dev.device_name:<20} {dev.device_model:<20} {status_icon} {dev.status:<10}")

        print(f"\n{'=' * 70}\n")
        input("按回车键返回主菜单...")


def show_accounts():
    """显示账号列表"""
    db = DatabaseManager()
    from src.database.models import TargetAccount

    with db.session_scope() as session:
        accounts = session.query(TargetAccount).all()

        print(f"\n{'=' * 70}")
        print("👤 目标账号列表")
        print(f"{'=' * 70}\n")

        if not accounts:
            print("  暂无目标账号")
        else:
            print(f"{'ID':<5} {'账号名':<25} {'抖音ID':<20}")
            print("-" * 70)
            for acc in accounts:
                print(f"{acc.id:<5} {acc.account_name:<25} {acc.account_id:<20}")

        print(f"\n{'=' * 70}\n")
        input("按回车键返回主菜单...")


def add_account():
    """添加目标账号"""
    db = DatabaseManager()
    from src.database.models import TargetAccount

    print(f"\n{'=' * 70}")
    print("➕ 添加目标账号")
    print(f"{'=' * 70}\n")

    try:
        # 输入账号信息
        print("请输入账号信息（输入空值取消）：\n")

        account_name = input("账号名称: ").strip()
        if not account_name:
            print("\n已取消添加")
            input("\n按回车键返回主菜单...")
            return

        account_id = input("抖音ID (数字): ").strip()
        if not account_id:
            print("\n已取消添加")
            input("\n按回车键返回主菜单...")
            return

        sec_user_id = input("sec_user_id (可选，用于爬虫): ").strip() or None

        # 确认
        print(f"\n{'=' * 70}")
        print("确认添加以下账号：")
        print(f"  账号名称: {account_name}")
        print(f"  抖音ID: {account_id}")
        print(f"  sec_user_id: {sec_user_id or '(未提供)'}")
        print(f"{'=' * 70}\n")

        confirm = input("确认添加? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("\n已取消添加")
            input("\n按回车键返回主菜单...")
            return

        # 添加到数据库
        with db.session_scope() as session:
            # 检查是否已存在
            existing = session.query(TargetAccount).filter(
                TargetAccount.account_id == account_id
            ).first()

            if existing:
                print(f"\n⚠️ 账号已存在: {existing.account_name} ({existing.account_id})")
                input("\n按回车键返回主菜单...")
                return

            # 创建新账号
            new_account = TargetAccount(
                account_name=account_name,
                account_id=account_id,
                sec_user_id=sec_user_id
            )
            session.add(new_account)
            session.commit()

            print(f"\n✓ 成功添加账号: {account_name} ({account_id})")

    except Exception as e:
        print(f"\n✗ 添加失败: {e}")

    input("\n按回车键返回主菜单...")


def delete_account():
    """删除目标账号"""
    db = DatabaseManager()
    from src.database.models import TargetAccount

    with db.session_scope() as session:
        print(f"\n{'=' * 70}")
        print("🗑️ 删除目标账号")
        print(f"{'=' * 70}\n")

        # 显示所有账号
        accounts = session.query(TargetAccount).all()

        if not accounts:
            print("  暂无目标账号")
            input("\n按回车键返回主菜单...")
            return

        print(f"{'ID':<5} {'账号名':<25} {'抖音ID':<20}")
        print("-" * 70)
        for acc in accounts:
            print(f"{acc.id:<5} {acc.account_name:<25} {acc.account_id:<20}")

        print(f"\n{'=' * 70}\n")

        # 选择要删除的账号
        try:
            account_id_input = input("请输入要删除的账号ID (输入0取消): ").strip()

            if account_id_input == '0':
                print("\n已取消删除")
                input("\n按回车键返回主菜单...")
                return

            account_id = int(account_id_input)

            # 查询账号
            account = session.query(TargetAccount).filter(
                TargetAccount.id == account_id
            ).first()

            if not account:
                print(f"\n✗ 未找到ID为 {account_id} 的账号")
                input("\n按回车键返回主菜单...")
                return

            # 确认删除
            print(f"\n确认删除账号: {account.account_name} ({account.account_id})?")
            confirm = input("输入 'DELETE' 确认删除: ").strip()

            if confirm != 'DELETE':
                print("\n已取消删除")
                input("\n按回车键返回主菜单...")
                return

            # 执行删除
            session.delete(account)
            session.commit()

            print(f"\n✓ 成功删除账号: {account.account_name}")

        except ValueError:
            print("\n✗ 请输入有效的数字ID")
        except Exception as e:
            print(f"\n✗ 删除失败: {e}")

    input("\n按回车键返回主菜单...")


def cleanup_duplicate_tasks_menu():
    """清理重复任务（菜单版）"""
    print(f"\n{'=' * 70}")
    print("🧹 清理重复任务")
    print(f"{'=' * 70}\n")

    db = DatabaseManager()
    from src.database.models import InteractionTask
    from sqlalchemy import func

    with db.session_scope() as session:
        total_users = session.query(func.count(func.distinct(InteractionTask.comment_user_id))).scalar() or 0
        total_tasks = session.query(func.count(InteractionTask.id)).scalar() or 0

        print(f"当前状态:")
        print(f"  去重用户数: {total_users}")
        print(f"  总任务数: {total_tasks}")
        print(f"  预期任务数: {total_users} (每用户1任务)")

        if total_tasks == total_users:
            print(f"\n✓ 数据已经是干净的，无需清理")
            input("\n按回车键返回主菜单...")
            return

        print(f"\n⚠️ 发现 {total_tasks - total_users} 个重复任务")
        print(f"\n确认执行清理?")
        confirm = input("输入 'yes' 确认: ").strip().lower()

        if confirm != 'yes':
            print("\n已取消清理")
            input("\n按回车键返回主菜单...")
            return

    # 运行清理脚本
    run_command(
        f"{sys.executable} scripts/cleanup_duplicate_tasks.py --auto",
        "清理重复任务"
    )


def update_cookie_menu():
    """更新Cookie配置（菜单版）"""
    print(f"\n{'=' * 70}")
    print("🍪 更新Cookie配置")
    print(f"{'=' * 70}\n")

    print("请选择更新方式：")
    print("  1. 更新服务器Cookie (update_server_cookie.py)")
    print("  2. 更新Cookie池 (update_cookie_pool.py)")
    print("  0. 返回")

    choice = input("\n请选择 [0-2]: ").strip()

    if choice == '1':
        run_command(
            f"{sys.executable} scripts/update_server_cookie.py",
            "更新服务器Cookie"
        )
    elif choice == '2':
        run_command(
            f"{sys.executable} scripts/update_cookie_pool.py",
            "更新Cookie池"
        )
    else:
        return


def check_devices_menu():
    """检查设备状态（菜单版）"""
    run_command(
        f"{sys.executable} scripts/check_devices.py",
        "检查设备状态"
    )


def show_detailed_stats():
    """显示详细统计"""
    db = DatabaseManager()

    from datetime import datetime, timedelta
    from src.database.models import InteractionTask, TargetAccount, Device, Comment, NewComment
    from sqlalchemy import func, and_

    with db.session_scope() as session:
        print(f"\n{'=' * 70}")
        print("📊 详细数据统计")
        print(f"{'=' * 70}\n")

        # 任务统计
        print("【任务统计】")
        total_tasks = session.query(func.count(InteractionTask.id)).scalar() or 0
        pending = session.query(func.count(InteractionTask.id)).filter(InteractionTask.status == 'pending').scalar() or 0
        assigned = session.query(func.count(InteractionTask.id)).filter(InteractionTask.status == 'assigned').scalar() or 0
        skipped = session.query(func.count(InteractionTask.id)).filter(InteractionTask.status == 'skipped').scalar() or 0
        completed = session.query(func.count(InteractionTask.id)).filter(InteractionTask.status == 'completed').scalar() or 0
        failed = session.query(func.count(InteractionTask.id)).filter(InteractionTask.status == 'failed').scalar() or 0

        print(f"  总任务数: {total_tasks}")
        print(f"  待处理: {pending}")
        print(f"  已分配: {assigned}")
        print(f"  已跳过: {skipped}")
        print(f"  已完成: {completed}")
        print(f"  失败: {failed}")
        print(f"  处理率: {((assigned + skipped + completed) / total_tasks * 100 if total_tasks > 0 else 0):.1f}%")
        print()

        # 任务类型分布（按状态分类）
        print("【任务类型分布】")

        # 实时任务
        realtime_total = session.query(func.count(InteractionTask.id)).filter(InteractionTask.task_type == 'realtime').scalar() or 0
        realtime_pending = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.task_type == 'realtime',
            InteractionTask.status == 'pending'
        ).scalar() or 0
        realtime_processed = realtime_total - realtime_pending

        # 近期历史任务
        recent_total = session.query(func.count(InteractionTask.id)).filter(InteractionTask.task_type == 'history_recent').scalar() or 0
        recent_pending = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.task_type == 'history_recent',
            InteractionTask.status == 'pending'
        ).scalar() or 0
        recent_processed = recent_total - recent_pending

        # 长期历史任务
        old_total = session.query(func.count(InteractionTask.id)).filter(InteractionTask.task_type == 'history_old').scalar() or 0
        old_pending = session.query(func.count(InteractionTask.id)).filter(
            InteractionTask.task_type == 'history_old',
            InteractionTask.status == 'pending'
        ).scalar() or 0
        old_processed = old_total - old_pending

        print(f"  实时任务(realtime): {realtime_total} 总 ({realtime_processed} 已处理 + {realtime_pending} 未处理)")
        print(f"  近期历史(3个月内): {recent_total} 总 ({recent_processed} 已处理 + {recent_pending} 未处理)")
        print(f"  长期历史(3个月前): {old_total} 总 ({old_processed} 已处理 + {old_pending} 未处理)")
        print()

        # 用户统计
        print("【用户统计】")
        total_users = session.query(func.count(func.distinct(InteractionTask.comment_user_id))).scalar() or 0

        # 新增用户（最近24小时内生成的realtime任务）
        yesterday = datetime.now() - timedelta(hours=24)
        three_months_ago = datetime.now() - timedelta(days=90)

        # 新增用户：从NewComment表获取监控发现的新用户
        new_users = session.query(func.count(func.distinct(NewComment.comment_user_id))).scalar() or 0

        users_3months = session.query(func.count(func.distinct(InteractionTask.comment_user_id))).filter(
            InteractionTask.comment_time >= three_months_ago,
            InteractionTask.comment_time.isnot(None)
        ).scalar() or 0

        old_users = session.query(func.count(func.distinct(InteractionTask.comment_user_id))).filter(
            InteractionTask.comment_time < three_months_ago,
            InteractionTask.comment_time.isnot(None)
        ).scalar() or 0

        print(f"  评论用户总量: {total_users}")
        print(f"  ├─ 新增用户(监控发现): {new_users}")
        print(f"  ├─ 3个月内评论用户: {users_3months}")
        print(f"  └─ 3个月前评论用户: {old_users}")
        print()

        # 评论和操作统计
        print("【数据统计】")
        total_comments = session.query(func.count(Comment.id)).scalar() or 0
        print(f"  总评论数: {total_comments}")
        print()

        print("【操作统计】")
        print("说明: 统计数据来自实际完成的互动任务")
        print()

        # 使用新的统计收集器
        from src.stats.interaction_stats import InteractionStatsCollector
        stats_collector = InteractionStatsCollector(session)
        report = stats_collector.get_detailed_report()

        # 总体统计
        print("  💾 历史累计:")
        total = report['total']
        print(f"    关注数: {total.get('follow', 0)}")
        print(f"    点赞数: {total.get('like', 0)}")
        print(f"    评论数: {total.get('comment', 0)}")
        print(f"    收藏数: {total.get('collect', 0)}")
        print()

        # 今日统计
        print("  📅 今日完成:")
        today = report['today']
        print(f"    关注数: {today.get('follow', 0)}")
        print(f"    点赞数: {today.get('like', 0)}")
        print(f"    评论数: {today.get('comment', 0)}")
        print(f"    收藏数: {today.get('collect', 0)}")
        print()

        # 按自动化模式统计
        print("  🤖 按自动化模式:")
        realtime = report['realtime']
        longterm = report['longterm']
        print(f"    实时自动化 (realtime):")
        print(f"      关注: {realtime.get('follow', 0)}, 点赞: {realtime.get('like', 0)}, 评论: {realtime.get('comment', 0)}, 收藏: {realtime.get('collect', 0)}")
        print(f"    长期自动化 (history):")
        print(f"      关注: {longterm.get('follow', 0)}, 点赞: {longterm.get('like', 0)}, 收藏: {longterm.get('collect', 0)}")
        print()

        # 账号和设备
        print("【系统资源】")
        account_count = session.query(func.count(TargetAccount.id)).scalar() or 0
        device_count = session.query(func.count(Device.id)).scalar() or 0
        online_devices = session.query(func.count(Device.id)).filter(Device.status.in_(['idle', 'busy'])).scalar() or 0

        print(f"  目标账号数: {account_count}")
        print(f"  设备总数: {device_count}")
        print(f"  在线设备: {online_devices}")

        print(f"\n{'=' * 70}\n")
        input("按回车键返回主菜单...")


def main():
    """主函数"""
    while True:
        clear_screen()
        show_header()
        show_statistics()
        show_menu()

        choice = input("请选择功能 [0-17]: ").strip()

        if choice == '0':
            print("\n再见！\n")
            break

        elif choice == '1':
            # 全量爬虫 (使用统一爬虫服务)
            run_command(
                f"{sys.executable} programs/run_crawler.py history --all",
                "全量爬虫 - 爬取历史评论"
            )

        elif choice == '2':
            # 监控爬虫 (使用统一爬虫服务)
            run_command(
                f"{sys.executable} programs/run_crawler.py monitor --all",
                "监控爬虫 - 监控新增评论"
            )

        elif choice == '3':
            # 实时自动化 (使用统一自动化服务)
            run_command(
                f"{sys.executable} programs/run_automation.py realtime --all",
                "实时自动化 - 处理新增评论"
            )

        elif choice == '4':
            # 近期自动化 (使用统一自动化服务)
            run_command(
                f"{sys.executable} programs/run_automation.py recent --all",
                "近期自动化 - 处理3个月内评论"
            )

        elif choice == '5':
            # 长期自动化 (使用统一自动化服务)
            run_command(
                f"{sys.executable} programs/run_automation.py longterm --all",
                "长期自动化 - 处理3个月以上评论"
            )

        elif choice == '6':
            # 混合自动化 (使用统一自动化服务)
            run_command(
                f"{sys.executable} programs/run_automation.py mixed --all",
                "混合自动化 - 实时+近期"
            )

        elif choice == '7':
            # 详细统计
            show_detailed_stats()

        elif choice == '8':
            # 设备列表
            show_devices()

        elif choice == '9':
            # 账号列表
            show_accounts()

        elif choice == '10':
            # 添加账号
            add_account()

        elif choice == '11':
            # 删除账号
            delete_account()

        elif choice == '12':
            # 管理API服务器
            run_command(
                f"{sys.executable} scripts/manage_api_servers.py",
                "管理API服务器 (添加/删除/修改)"
            )

        elif choice == '13':
            # 生成缺失任务
            run_command(
                f"{sys.executable} scripts/generate_tasks_from_comments.py --auto",
                "生成缺失任务 (从评论数据提取新用户)"
            )

        elif choice == '14':
            # 清理重复任务
            cleanup_duplicate_tasks_menu()

        elif choice == '15':
            # 删除缺陷任务
            run_command(
                f"{sys.executable} scripts/delete_tasks_without_unique_id.py --auto",
                "删除缺陷任务 (无comment_unique_id)"
            )

        elif choice == '16':
            # 更新Cookie
            update_cookie_menu()

        elif choice == '17':
            # 检查设备
            check_devices_menu()

        else:
            print("\n⚠ 无效的选择，请重新输入\n")
            input("按回车键继续...")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序已退出\n")
    except Exception as e:
        print(f"\n✗ 程序出错: {e}\n")
        import traceback
        traceback.print_exc()
