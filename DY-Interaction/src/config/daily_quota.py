"""
每日操作配额配置
支持启动时动态配置
"""

class DailyQuota:
    """每日操作配额配置"""

    # 默认配额
    DEFAULT_MAX_USERS = 500  # 每日处理用户数（默认500个）
    DEFAULT_MAX_FOLLOW = 100   # 每日关注数
    DEFAULT_MAX_LIKE = 500    # 每日点赞数
    DEFAULT_MAX_COLLECT = 500 # 每日收藏数

    def __init__(self,
                 max_users: int = None,
                 max_follow: int = None,
                 max_like: int = None,
                 max_collect: int = None,
                 total_tasks: int = None):
        """
        初始化配额配置

        Args:
            max_users: 每日最大处理用户数
            max_follow: 每日最大关注数
            max_like: 每日最大点赞数
            max_collect: 每日最大收藏数
            total_tasks: 数据库中的总任务数（用于自动计算默认值）
        """
        # 如果指定了总任务数，使用其作为max_users的默认值
        if total_tasks is not None and total_tasks > 0:
            default_max_users = total_tasks
        else:
            default_max_users = self.DEFAULT_MAX_USERS

        self.max_users = max_users or default_max_users
        self.max_follow = max_follow or self.DEFAULT_MAX_FOLLOW
        self.max_like = max_like or self.DEFAULT_MAX_LIKE
        self.max_collect = max_collect or self.DEFAULT_MAX_COLLECT

    def can_follow(self, current_count: int) -> bool:
        """是否可以继续关注"""
        return current_count < self.max_follow

    def can_like(self, current_count: int) -> bool:
        """是否可以继续点赞"""
        return current_count < self.max_like

    def can_collect(self, current_count: int) -> bool:
        """是否可以继续收藏"""
        return current_count < self.max_collect

    def can_process_user(self, current_count: int) -> bool:
        """是否可以继续处理用户"""
        return current_count < self.max_users

    def get_summary(self) -> str:
        """获取配额摘要"""
        return (
            f"每日配额: "
            f"用户={self.max_users}, "
            f"关注={self.max_follow}, "
            f"点赞={self.max_like}, "
            f"收藏={self.max_collect}"
        )

    def __repr__(self):
        return self.get_summary()


def interactive_quota_config(total_tasks: int = None) -> DailyQuota:
    """
    交互式配额配置（在自动化启动前调用）

    Args:
        total_tasks: 数据库中的总任务数（可选）

    Returns:
        配置好的DailyQuota对象

    示例:
        quota = interactive_quota_config(total_tasks=4245)
    """
    print("\n" + "=" * 70)
    print("⚙️ 每日操作配额配置")
    print("=" * 70)

    # 计算默认值
    if total_tasks and total_tasks > 0:
        default_max_users = total_tasks
        print(f"\n📊 检测到数据库中有 {total_tasks} 个任务")
        print(f"   建议配额: 每日处理用户数 = {total_tasks}")
    else:
        default_max_users = DailyQuota.DEFAULT_MAX_USERS
        print(f"\n📊 使用默认配额")

    print(f"\n📋 当前配额设置:")
    print(f"   1️⃣  每日处理用户数 [默认: {default_max_users}]")
    print(f"   2️⃣  每日关注数     [默认: {DailyQuota.DEFAULT_MAX_FOLLOW}]")
    print(f"   3️⃣  每日点赞数     [默认: {DailyQuota.DEFAULT_MAX_LIKE}]")
    print(f"   4️⃣  每日收藏数     [默认: {DailyQuota.DEFAULT_MAX_COLLECT}]")
    print()

    # 询问用户是否要修改配额
    user_choice = input("是否需要修改配额? (y/n，默认n): ").strip().lower()

    if user_choice == 'y':
        # 让用户逐一修改
        print("\n📝 开始配置（直接按回车使用默认值）:")

        # 配置 max_users
        while True:
            max_users_input = input(f"  每日处理用户数 [默认: {default_max_users}]: ").strip()
            if not max_users_input:
                max_users = default_max_users
                break
            try:
                max_users = int(max_users_input)
                if max_users > 0:
                    break
                else:
                    print("  ⚠️ 请输入正数")
            except ValueError:
                print("  ⚠️ 请输入有效的数字")

        # 配置 max_follow
        while True:
            max_follow_input = input(f"  每日关注数 [默认: {DailyQuota.DEFAULT_MAX_FOLLOW}]: ").strip()
            if not max_follow_input:
                max_follow = DailyQuota.DEFAULT_MAX_FOLLOW
                break
            try:
                max_follow = int(max_follow_input)
                if max_follow > 0:
                    break
                else:
                    print("  ⚠️ 请输入正数")
            except ValueError:
                print("  ⚠️ 请输入有效的数字")

        # 配置 max_like
        while True:
            max_like_input = input(f"  每日点赞数 [默认: {DailyQuota.DEFAULT_MAX_LIKE}]: ").strip()
            if not max_like_input:
                max_like = DailyQuota.DEFAULT_MAX_LIKE
                break
            try:
                max_like = int(max_like_input)
                if max_like > 0:
                    break
                else:
                    print("  ⚠️ 请输入正数")
            except ValueError:
                print("  ⚠️ 请输入有效的数字")

        # 配置 max_collect
        while True:
            max_collect_input = input(f"  每日收藏数 [默认: {DailyQuota.DEFAULT_MAX_COLLECT}]: ").strip()
            if not max_collect_input:
                max_collect = DailyQuota.DEFAULT_MAX_COLLECT
                break
            try:
                max_collect = int(max_collect_input)
                if max_collect > 0:
                    break
                else:
                    print("  ⚠️ 请输入正数")
            except ValueError:
                print("  ⚠️ 请输入有效的数字")

        quota = DailyQuota(
            max_users=max_users,
            max_follow=max_follow,
            max_like=max_like,
            max_collect=max_collect
        )
    else:
        # 使用默认配额
        quota = DailyQuota(total_tasks=total_tasks)

    # 显示最终配置
    print("\n" + "=" * 70)
    print("✅ 配额配置完成")
    print("=" * 70)
    print(f"✓ {quota.get_summary()}")
    print("=" * 70 + "\n")

    return quota
