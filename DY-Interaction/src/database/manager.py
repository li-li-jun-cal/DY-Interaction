"""
DY-Interaction 数据库管理器

处理所有数据库操作
"""

import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from .models import Base, TargetAccount, InteractionTask, InteractionLog, BatchProgress, Device, DeviceAssignment

logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_url='sqlite:///data/dy_interaction.db', auto_sync=True):
        """初始化数据库管理器

        Args:
            db_url: 数据库连接字符串
            auto_sync: 是否自动同步配置文件（目标账号和设备）
        """
        self.db_url = db_url
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.auto_sync = auto_sync
        logger.info(f"数据库连接: {db_url}")

    def init_db(self):
        """初始化数据库（创建所有表）"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("✓ 数据库表创建成功")

            # 自动同步配置
            if self.auto_sync:
                self.sync_target_accounts()
                self.sync_devices()

        except SQLAlchemyError as e:
            logger.error(f"✗ 数据库初始化失败: {e}")
            raise

    def sync_target_accounts(self):
        """从配置文件同步目标账号到数据库"""
        config_file = PROJECT_ROOT / 'config' / 'target_accounts.json'

        if not config_file.exists():
            logger.warning(f"⚠ 目标账号配置文件不存在: {config_file}")
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            accounts = config.get('accounts', [])
            if not accounts:
                logger.warning("⚠ 配置文件中没有账号数据")
                return

            session = self.get_session()
            try:
                added = 0
                updated = 0

                for idx, acc in enumerate(accounts, 1):
                    account_name = acc.get('account_name', 'Unknown')
                    sec_user_id = acc.get('sec_user_id')
                    unique_id = acc.get('unique_id', '')
                    status = acc.get('status', 'active')

                    if not sec_user_id:
                        logger.warning(f"  ⚠ [{account_name}] 缺少 sec_user_id，跳过")
                        continue

                    # 检查是否已存在
                    existing = session.query(TargetAccount).filter_by(sec_user_id=sec_user_id).first()

                    if existing:
                        # 更新现有账号
                        existing.account_name = account_name
                        existing.account_id = unique_id
                        existing.enabled = (status == 'active')
                        existing.priority = idx
                        existing.updated_at = datetime.now()
                        updated += 1
                    else:
                        # 创建新账号
                        new_account = TargetAccount(
                            sec_user_id=sec_user_id,
                            account_name=account_name,
                            account_id=unique_id,
                            homepage_url=f"https://www.douyin.com/user/{sec_user_id}",
                            priority=idx,
                            enabled=(status == 'active')
                        )
                        session.add(new_account)
                        added += 1

                session.commit()

                if added > 0 or updated > 0:
                    logger.info(f"✓ 同步目标账号: 新增 {added} 个, 更新 {updated} 个")

            except Exception as e:
                session.rollback()
                logger.error(f"✗ 同步目标账号失败: {e}")
            finally:
                session.close()

        except Exception as e:
            logger.error(f"✗ 读取目标账号配置失败: {e}")

    def sync_devices(self):
        """从 adb devices 自动同步设备信息到数据库"""
        try:
            # 获取已连接的设备
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split('\n')[1:]  # 跳过第一行标题

            connected_serials = []
            for line in lines:
                if '\t' in line:
                    serial = line.split('\t')[0].strip()
                    connected_serials.append(serial)

            if not connected_serials:
                logger.debug("未检测到已连接的设备")
                return

            session = self.get_session()
            try:
                added = 0

                for idx, serial in enumerate(connected_serials, 1):
                    # 检查设备是否已存在
                    existing = session.query(Device).filter_by(adb_serial=serial).first()

                    if not existing:
                        # 创建新设备记录
                        device_id = f"Device-{idx}"
                        new_device = Device(
                            device_id=device_id,
                            adb_serial=serial,
                            device_name=f"设备-{idx}",
                            device_model="Unknown",
                            status='idle'
                        )
                        session.add(new_device)

                        # 同时创建设备分配记录
                        assignment = DeviceAssignment(
                            device_id=device_id,
                            device_name=f"设备-{idx}",
                            assignment_type='long_term',  # 默认长期设备
                            max_daily_quota=300,
                            is_active=True
                        )
                        session.add(assignment)
                        added += 1

                session.commit()

                if added > 0:
                    logger.info(f"✓ 同步设备信息: 新增 {added} 台设备")

            except Exception as e:
                session.rollback()
                logger.error(f"✗ 同步设备信息失败: {e}")
            finally:
                session.close()

        except subprocess.TimeoutExpired:
            logger.warning("⚠ adb 命令超时")
        except FileNotFoundError:
            logger.debug("adb 命令不可用，跳过设备同步")
        except Exception as e:
            logger.debug(f"设备同步跳过: {e}")

    def get_session(self) -> Session:
        """获取数据库会话（不推荐直接使用，请使用 session_scope）

        Returns:
            Session 对象（需要手动关闭）
        """
        return self.SessionLocal()

    @contextmanager
    def session_scope(self):
        """提供一个事务性的数据库会话 context manager

        使用示例:
            with db.session_scope() as session:
                session.query(Model).all()

        Yields:
            Session 对象
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ========== 目标账号操作 ==========

    def get_target_accounts(self, enabled_only=True):
        """获取所有目标账号

        Args:
            enabled_only: 只获取启用的账号

        Returns:
            TargetAccount 列表
        """
        session = self.get_session()
        try:
            query = session.query(TargetAccount)
            if enabled_only:
                query = query.filter(TargetAccount.enabled == True)
            query = query.order_by(TargetAccount.priority)
            return query.all()
        finally:
            session.close()

    def get_target_account(self, account_id):
        """获取单个目标账号"""
        session = self.get_session()
        try:
            return session.query(TargetAccount).filter(
                TargetAccount.id == account_id
            ).first()
        finally:
            session.close()

    def create_target_account(self, sec_user_id, account_name, account_id, homepage_url, priority=1, tags=None):
        """创建新的目标账号"""
        session = self.get_session()
        try:
            account = TargetAccount(
                sec_user_id=sec_user_id,
                account_name=account_name,
                account_id=account_id,
                homepage_url=homepage_url,
                priority=priority,
                tags=json.dumps(tags) if tags else None
            )
            session.add(account)
            session.commit()
            logger.info(f"✓ 创建目标账号: {account_name}")
            return account
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"✗ 创建目标账号失败: {e}")
            raise
        finally:
            session.close()

    # ========== 互动任务操作 ==========

    def get_interaction_tasks(self, status=None, task_type=None, limit=100):
        """获取互动任务

        Args:
            status: 任务状态（pending, in_progress, completed, failed）
            task_type: 任务类型（realtime, batch）
            limit: 返回的最大任务数

        Returns:
            InteractionTask 列表
        """
        session = self.get_session()
        try:
            query = session.query(InteractionTask)

            if status:
                query = query.filter(InteractionTask.status == status)
            if task_type:
                query = query.filter(InteractionTask.task_type == task_type)

            query = query.order_by(InteractionTask.created_at).limit(limit)
            return query.all()
        finally:
            session.close()

    def get_interaction_task(self, task_id):
        """获取单个互动任务

        Args:
            task_id: 任务ID

        Returns:
            InteractionTask 对象或 None
        """
        session = self.get_session()
        try:
            task = session.query(InteractionTask).filter(
                InteractionTask.id == task_id
            ).first()
            return task
        finally:
            session.close()

    def create_task(self, target_account_id, comment_user_id, comment_user_name,
                   video_id, comment_id=None, task_type='realtime', actions=None):
        """创建新的互动任务

        Args:
            target_account_id: 目标账号ID
            comment_user_id: 评论用户ID
            comment_user_name: 评论用户昵称
            video_id: 视频ID
            comment_id: 评论ID
            task_type: 任务类型（realtime, batch）
            actions: 要执行的操作（dict）

        Returns:
            InteractionTask 对象
        """
        session = self.get_session()
        try:
            task = InteractionTask(
                target_account_id=target_account_id,
                comment_user_id=comment_user_id,
                comment_user_name=comment_user_name,
                video_id=video_id,
                comment_id=comment_id,
                task_type=task_type,
                actions=json.dumps(actions) if actions else InteractionTask.actions.default.arg
            )
            session.add(task)
            session.commit()
            logger.debug(f"✓ 创建任务: {comment_user_name}")
            return task
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"✗ 创建任务失败: {e}")
            raise
        finally:
            session.close()

    def update_task_status(self, task_id, status, assigned_device=None, error_msg=None):
        """更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            assigned_device: 分配的设备
            error_msg: 错误信息
        """
        session = self.get_session()
        try:
            task = session.query(InteractionTask).filter(
                InteractionTask.id == task_id
            ).first()

            if not task:
                logger.warning(f"任务不存在: {task_id}")
                return

            task.status = status
            if assigned_device:
                task.assigned_device = assigned_device
            if error_msg:
                task.error_msg = error_msg

            if status == 'in_progress':
                task.started_at = datetime.now()
            elif status in ['completed', 'failed']:
                task.completed_at = datetime.now()

            session.commit()
            logger.debug(f"✓ 更新任务状态: {task_id} -> {status}")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"✗ 更新任务失败: {e}")
            raise
        finally:
            session.close()

    # ========== 互动日志操作 ==========

    def log_interaction(self, task_id, device_id, action, status, error_msg=None, duration_seconds=None):
        """记录互动操作

        Args:
            task_id: 任务ID
            device_id: 设备ID
            action: 操作类型（like, comment, follow, dm）
            status: 操作状态（success, failed）
            error_msg: 错误信息
            duration_seconds: 操作耗时（秒）
        """
        session = self.get_session()
        try:
            log = InteractionLog(
                task_id=task_id,
                device_id=device_id,
                action=action,
                status=status,
                error_msg=error_msg,
                duration_seconds=duration_seconds
            )
            session.add(log)
            session.commit()
            logger.debug(f"✓ 记录操作: {task_id} - {action} - {status}")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"✗ 记录操作失败: {e}")
            raise
        finally:
            session.close()

    def get_task_logs(self, task_id):
        """获取任务的所有日志"""
        session = self.get_session()
        try:
            return session.query(InteractionLog).filter(
                InteractionLog.task_id == task_id
            ).order_by(InteractionLog.created_at).all()
        finally:
            session.close()

    # ========== 批量处理进度操作 ==========

    def get_batch_progress(self, target_account_id):
        """获取批量处理进度"""
        session = self.get_session()
        try:
            return session.query(BatchProgress).filter(
                BatchProgress.target_account_id == target_account_id
            ).first()
        finally:
            session.close()

    def create_batch_progress(self, target_account_id):
        """创建新的批量处理进度记录"""
        session = self.get_session()
        try:
            progress = BatchProgress(target_account_id=target_account_id)
            session.add(progress)
            session.commit()
            return progress
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"✗ 创建进度记录失败: {e}")
            raise
        finally:
            session.close()

    def update_batch_progress(self, target_account_id, last_video_id, videos_count=0, comments_count=0, tasks_count=0):
        """更新批量处理进度"""
        session = self.get_session()
        try:
            progress = session.query(BatchProgress).filter(
                BatchProgress.target_account_id == target_account_id
            ).first()

            if not progress:
                progress = BatchProgress(target_account_id=target_account_id)
                session.add(progress)

            progress.last_video_id = last_video_id
            progress.last_crawler_time = datetime.now()
            progress.videos_processed += videos_count
            progress.comments_processed += comments_count
            progress.tasks_generated += tasks_count
            progress.updated_at = datetime.now()

            session.commit()
            logger.debug(f"✓ 更新进度: {target_account_id}")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"✗ 更新进度失败: {e}")
            raise
        finally:
            session.close()

    # ========== 设备操作 ==========

    def get_devices(self, status=None):
        """获取设备列表

        Args:
            status: 设备状态（idle, busy, error, offline）

        Returns:
            Device 列表
        """
        session = self.get_session()
        try:
            query = session.query(Device)
            if status:
                query = query.filter(Device.status == status)
            return query.all()
        finally:
            session.close()

    def get_device(self, device_id):
        """获取单个设备"""
        session = self.get_session()
        try:
            return session.query(Device).filter(Device.device_id == device_id).first()
        finally:
            session.close()

    def create_device(self, device_name, device_model, adb_serial, device_id, account_id=None, account_name=None):
        """创建新设备记录"""
        session = self.get_session()
        try:
            device = Device(
                device_name=device_name,
                device_model=device_model,
                adb_serial=adb_serial,
                device_id=device_id,
                account_id=account_id,
                account_name=account_name
            )
            session.add(device)
            session.commit()
            logger.info(f"✓ 创建设备: {device_name}")
            return device
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"✗ 创建设备失败: {e}")
            raise
        finally:
            session.close()

    def update_device_status(self, device_id, status, current_task_id=None):
        """更新设备状态"""
        session = self.get_session()
        try:
            device = session.query(Device).filter(Device.device_id == device_id).first()
            if device:
                device.status = status
                device.last_heartbeat = datetime.now()
                if current_task_id:
                    device.current_task_id = current_task_id
                session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"✗ 更新设备状态失败: {e}")
        finally:
            session.close()

    # ========== 统计操作 ==========

    def get_task_stats(self):
        """获取任务统计信息"""
        session = self.get_session()
        try:
            total = session.query(InteractionTask).count()
            pending = session.query(InteractionTask).filter(
                InteractionTask.status == 'pending'
            ).count()
            in_progress = session.query(InteractionTask).filter(
                InteractionTask.status == 'in_progress'
            ).count()
            completed = session.query(InteractionTask).filter(
                InteractionTask.status == 'completed'
            ).count()
            failed = session.query(InteractionTask).filter(
                InteractionTask.status == 'failed'
            ).count()

            return {
                'total': total,
                'pending': pending,
                'in_progress': in_progress,
                'completed': completed,
                'failed': failed
            }
        finally:
            session.close()

    def get_device_stats(self):
        """获取设备统计信息"""
        session = self.get_session()
        try:
            devices = session.query(Device).all()
            return {
                'total': len(devices),
                'idle': sum(1 for d in devices if d.status == 'idle'),
                'busy': sum(1 for d in devices if d.status == 'busy'),
                'error': sum(1 for d in devices if d.status == 'error'),
                'offline': sum(1 for d in devices if d.status == 'offline'),
            }
        finally:
            session.close()
