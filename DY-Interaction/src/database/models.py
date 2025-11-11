"""
DY-Interaction 数据库模型定义

使用 SQLAlchemy ORM 定义所有数据模型
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class TargetAccount(Base):
    """目标账号（要监控的账号）"""
    __tablename__ = 'target_accounts'

    id = Column(Integer, primary_key=True)
    sec_user_id = Column(String(255), unique=True, nullable=True, index=True)  # 可选，允许后续补充
    account_name = Column(String(255), nullable=False)
    account_id = Column(String(255), nullable=False)
    homepage_url = Column(String(500))
    priority = Column(Integer, default=1)  # 优先级，数字越小越优先
    enabled = Column(Boolean, default=True)
    tags = Column(Text)  # JSON format: ["tag1", "tag2"]

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    interaction_tasks = relationship('InteractionTask', back_populates='target_account')
    batch_progress = relationship('BatchProgress', back_populates='target_account')

    def __repr__(self):
        return f"<TargetAccount {self.account_name}>"


class Comment(Base):
    """评论数据（历史评论或新增评论）"""
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True)
    target_account_id = Column(Integer, ForeignKey('target_accounts.id'), nullable=False, index=True)
    video_id = Column(String(255), nullable=False, index=True)
    comment_user_id = Column(String(255), nullable=False, index=True)
    comment_user_name = Column(String(255), nullable=False)

    # 新增：用户ID字段
    comment_uid = Column(String(255), nullable=True)  # 用户数字ID
    comment_sec_uid = Column(String(255), nullable=True, index=True)  # 安全用户ID
    comment_unique_id = Column(String(255), nullable=True, index=True)  # 抖音号（用于搜索）

    comment_text = Column(Text, nullable=False)
    comment_time = Column(DateTime, nullable=True)
    digg_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)

    # 新增：视频信息字段
    video_url = Column(Text, nullable=True)
    video_desc = Column(Text, nullable=True)
    video_digg_count = Column(Integer, default=0)
    video_comment_count = Column(Integer, default=0)
    video_share_count = Column(Integer, default=0)
    video_create_time = Column(DateTime, nullable=True, index=True)  # 视频发布时间（用于优先级判断）

    created_at = Column(DateTime, default=datetime.now)
    status = Column(String(50), default='new')  # 'new', 'processed', 'failed'

    __table_args__ = (
        Index('idx_unique_comment', 'target_account_id', 'video_id', 'comment_user_id'),
    )

    def __repr__(self):
        return f"<Comment {self.comment_user_name}>"


class NewComment(Base):
    """新增评论（每天监控发现）"""
    __tablename__ = 'new_comments'

    id = Column(Integer, primary_key=True)
    target_account_id = Column(Integer, ForeignKey('target_accounts.id'), nullable=False, index=True)
    video_id = Column(String(255), nullable=False, index=True)
    comment_user_id = Column(String(255), nullable=False, index=True)  # sec_uid (MS4w...)
    comment_user_name = Column(String(255), nullable=False)
    comment_uid = Column(String(255), nullable=True, index=True)  # 数字ID
    comment_unique_id = Column(String(255), nullable=True, index=True)  # 抖音号
    comment_text = Column(Text, nullable=False)
    discovered_at = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_unique_new_comment', 'target_account_id', 'video_id', 'comment_user_id'),
    )

    def __repr__(self):
        return f"<NewComment {self.comment_user_name}>"


class InteractionTask(Base):
    """互动任务（简化版）"""
    __tablename__ = 'interaction_tasks'

    id = Column(Integer, primary_key=True)
    target_account_id = Column(Integer, ForeignKey('target_accounts.id'), nullable=False, index=True)
    comment_user_id = Column(String(255), nullable=False)
    comment_user_name = Column(String(255), nullable=False)

    # 新增：用户ID字段
    comment_uid = Column(String(255), nullable=True)  # 用户数字ID
    comment_sec_uid = Column(String(255), nullable=True, index=True)  # 安全用户ID
    comment_unique_id = Column(String(255), nullable=True, index=True)  # 抖音号（用于搜索）

    video_id = Column(String(255), nullable=False)
    comment_id = Column(String(255), nullable=True)

    # 评论创建时间（用于按评论时间分类统计）
    comment_time = Column(DateTime, nullable=True, index=True)

    # 任务类型:
    # - 'history_old': 历史评论（3个月前的评论）
    # - 'history_recent': 近期历史评论（3个月内的评论）
    # - 'realtime': 实时新增评论（监控爬虫发现）
    task_type = Column(String(50), default='history_old', index=True)

    # 任务优先级: 'normal'（正常）或 'high'（高）
    # - history_old: normal
    # - history_recent: high
    # - realtime: high
    priority = Column(String(50), default='normal', index=True)

    # 任务状态: pending, in_progress, completed, failed
    status = Column(String(50), default='pending', index=True)

    # 分配的设备
    assigned_device = Column(String(255), nullable=True)

    # 重试机制
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # 错误信息
    error_msg = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.now, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # 关系
    target_account = relationship('TargetAccount', back_populates='interaction_tasks')
    interaction_logs = relationship('InteractionLog', back_populates='task')

    __table_args__ = (
        Index('idx_status_created', 'status', 'created_at'),
        Index('idx_status_type', 'status', 'task_type'),
        Index('idx_priority_created', 'priority', 'created_at'),
    )

    def __repr__(self):
        return f"<InteractionTask {self.id} - {self.comment_user_name}>"


class InteractionLog(Base):
    """互动日志（记录每次操作）"""
    __tablename__ = 'interaction_logs'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('interaction_tasks.id'), nullable=False, index=True)
    device_id = Column(String(255), nullable=False)

    # 操作类型: like（点赞）, comment（评论）, follow（关注）, dm（私信）, navigate（导航）
    action = Column(String(50), nullable=False)

    # 操作状态: success（成功）, failed（失败）
    status = Column(String(50), nullable=False)

    # 错误信息
    error_msg = Column(Text, nullable=True)

    # 执行时间（秒）
    duration_seconds = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.now, index=True)

    # 关系
    task = relationship('InteractionTask', back_populates='interaction_logs')

    __table_args__ = (
        Index('idx_task_action', 'task_id', 'action'),
    )

    def __repr__(self):
        return f"<InteractionLog {self.action} - {self.status}>"


class BatchProgress(Base):
    """批量处理进度（版本2使用）"""
    __tablename__ = 'batch_progress'

    id = Column(Integer, primary_key=True)
    target_account_id = Column(Integer, ForeignKey('target_accounts.id'), nullable=False, unique=True, index=True)

    # 上次处理的视频ID
    last_video_id = Column(String(255), nullable=True)

    # 上次爬取时间
    last_crawler_time = Column(DateTime, nullable=True)

    # 进度率（百分比）
    progress_rate = Column(Float, default=0.0)

    # 已处理的视频数
    videos_processed = Column(Integer, default=0)

    # 已处理的评论数
    comments_processed = Column(Integer, default=0)

    # 已生成的任务数
    tasks_generated = Column(Integer, default=0)

    # 已完成的任务数
    tasks_completed = Column(Integer, default=0)

    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_at = Column(DateTime, default=datetime.now)

    # 关系
    target_account = relationship('TargetAccount', back_populates='batch_progress')

    def __repr__(self):
        return f"<BatchProgress {self.target_account_id} - {self.progress_rate}%>"


class Device(Base):
    """设备信息"""
    __tablename__ = 'devices'

    id = Column(Integer, primary_key=True)
    device_name = Column(String(255), nullable=False)
    device_model = Column(String(255), nullable=False)
    adb_serial = Column(String(255), unique=True, nullable=False, index=True)
    device_id = Column(String(255), unique=True, nullable=False, index=True)  # 127.0.0.1:5555 format

    # 账号信息
    account_id = Column(String(255), nullable=True)
    account_name = Column(String(255), nullable=True)

    # 设备状态: idle（空闲）, busy（忙碌）, error（错误）, offline（离线）
    status = Column(String(50), default='idle')

    # 最后心跳时间
    last_heartbeat = Column(DateTime, default=datetime.now)

    # 当前任务ID
    current_task_id = Column(Integer, nullable=True)

    # 统计信息
    total_tasks = Column(Integer, default=0)
    successful_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Device {self.device_name} - {self.status}>"


class DeviceAssignment(Base):
    """固定的设备分配规则（简化版）"""
    __tablename__ = 'device_assignment'

    id = Column(Integer, primary_key=True)
    device_id = Column(String(255), unique=True, index=True, nullable=False)
    device_name = Column(String(255), nullable=False)
    assignment_type = Column(String(50), nullable=False)  # 'long_term', 'realtime'
    max_daily_quota = Column(Integer, default=50)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<DeviceAssignment {self.device_id} - {self.assignment_type}>"


class DeviceDailyStats(Base):
    """每日设备统计（包含操作配额）"""
    __tablename__ = 'device_daily_stats'

    id = Column(Integer, primary_key=True)
    device_id = Column(String(255), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)

    # 任务统计
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)

    # 操作统计（新增）
    follow_count = Column(Integer, default=0)  # 关注数量
    like_count = Column(Integer, default=0)    # 点赞数量
    collect_count = Column(Integer, default=0)  # 收藏数量

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_device_date', 'device_id', 'date'),
    )

    def __repr__(self):
        return f"<DeviceDailyStats {self.device_id} - {self.date}>"


class CommentTemplate(Base):
    """评论文案模板（用于自动化评论）"""
    __tablename__ = 'comment_templates'

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)  # 评论内容
    category = Column(String(50), nullable=True, index=True)  # 分类（如：通用、赞美、问询等）
    is_active = Column(Boolean, default=True, index=True)  # 是否启用
    weight = Column(Integer, default=1)  # 权重（越大越容易被选中）
    usage_count = Column(Integer, default=0)  # 使用次数
    last_used_at = Column(DateTime, nullable=True)  # 最后使用时间
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index('idx_active_category', 'is_active', 'category'),
    )

    def __repr__(self):
        return f"<CommentTemplate {self.id} - {self.content[:20]}...>"


class MonitorLog(Base):
    """监控爬虫日志（记录每次监控的结果）"""
    __tablename__ = 'monitor_logs'

    id = Column(Integer, primary_key=True)
    monitor_time = Column(DateTime, nullable=False, index=True)

    # 监控统计
    accounts_count = Column(Integer, default=0)      # 监控账号数
    success_count = Column(Integer, default=0)       # 成功账号数
    failed_count = Column(Integer, default=0)        # 失败账号数
    new_comments_count = Column(Integer, default=0)  # 新增评论数
    tasks_generated = Column(Integer, default=0)     # 生成任务数

    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<MonitorLog {self.monitor_time} - {self.new_comments_count} new comments>"


class VideoCache(Base):
    """视频元数据缓存（用于监控性能优化）"""
    __tablename__ = 'video_cache'

    id = Column(Integer, primary_key=True)
    target_account_id = Column(Integer, ForeignKey('target_accounts.id'), nullable=False, index=True)
    video_id = Column(String(255), nullable=False, unique=True, index=True)  # aweme_id

    # 视频基本信息
    video_title = Column(Text, nullable=True)
    video_desc = Column(Text, nullable=True)
    video_url = Column(Text, nullable=True)
    create_time = Column(DateTime, nullable=True)

    # 统计数据（用于排序）
    comment_count = Column(Integer, default=0)
    digg_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)

    # 监控标记
    is_top_video = Column(Boolean, default=False, index=True)  # 是否Top N视频
    last_monitored = Column(DateTime, nullable=True)  # 最后监控时间

    # 时间戳
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index('idx_account_comment', 'target_account_id', 'comment_count'),
        Index('idx_top_videos', 'target_account_id', 'is_top_video'),
    )

    def __repr__(self):
        return f"<VideoCache {self.video_id} - {self.comment_count} comments>"
