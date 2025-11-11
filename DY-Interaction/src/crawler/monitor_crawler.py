"""
监控爬虫（每天更新Top 5视频的新增评论）
优化版：使用VideoCache缓存 + 增量检测新视频
"""

import logging
from datetime import datetime
from src.database.models import Comment, NewComment, VideoCache
from src.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class MonitorCrawler:
    """每天监控新增评论（优化版）"""

    def __init__(self, db_manager, api_client):
        """初始化监控爬虫

        Args:
            db_manager: 数据库管理器
            api_client: API 客户端
        """
        self.db = db_manager
        self.api = api_client

    def monitor_daily(self, target_account, top_n=5):
        """每天监控新增评论（优化版）

        优化要点:
        1. 使用VideoCache缓存，避免重复获取3个月视频列表
        2. 增量检测新视频，只在有新视频时更新缓存
        3. 从缓存直接读取Top N视频，而不是每次排序

        Args:
            target_account: 目标账号对象
            top_n: 监控的Top N视频（默认5）

        Returns:
            {
                'account_id': int,
                'new_comments_count': int,
                'status': 'success' or 'failed',
                'error': 错误信息（如有）
            }
        """
        session = self.db.get_session()
        try:
            logger.info(f"开始监控账号 {target_account.account_id} 的新增评论")

            # ======== 步骤1: 检测新视频（增量检测） ========
            logger.info(f"  [1/3] 检测新视频...")
            new_videos = self.detect_new_videos(target_account, session)

            if new_videos:
                logger.info(f"    ✓ 发现 {len(new_videos)} 个新视频")
                # 更新VideoCache
                self.update_video_cache(target_account, new_videos, session)
                # 重新计算Top N
                self.refresh_top_videos(target_account, session, top_n)
            else:
                logger.info(f"    ℹ️  无新视频")

            # ======== 步骤2: 获取Top视频（从缓存读取） ========
            logger.info(f"  [2/3] 获取Top {top_n}视频（从缓存）...")
            top_videos = self.get_top_videos_from_cache(target_account, session, top_n)

            if not top_videos:
                logger.warning(f"  [!] VideoCache中无数据，请先运行历史爬虫构建缓存")
                # 回退到原有逻辑
                logger.info(f"  [回退] 使用传统方式获取Top视频...")
                top_videos_fallback = self.get_top_videos(target_account, top_n)
                if not top_videos_fallback:
                    return {
                        'account_id': target_account.id,
                        'new_comments_count': 0,
                        'status': 'success'
                    }

                # 将回退获取的视频包装成VideoCache对象样式
                class FallbackVideo:
                    def __init__(self, video_dict):
                        self.video_id = video_dict.get('video_id')

                top_videos = [FallbackVideo(v) for v in top_videos_fallback]

            logger.info(f"    ✓ 找到 {len(top_videos)} 个Top视频")

            # ======== 步骤3: 检查新增评论 ========
            logger.info(f"  [3/3] 检查新增评论...")
            new_comments_count = 0

            for video_cache in top_videos:
                video_id = video_cache.video_id

                try:
                    # 获取该视频的所有评论（API客户端已处理分页）
                    logger.info(f"    检查视频 {video_id[:20]}... 的评论")

                    # 调用API获取所有评论（无限制）
                    all_comments = self.api.get_video_comments(
                        aweme_id=video_id,
                        max_count=None  # None表示获取所有评论，无限制
                    )

                    if not all_comments:
                        logger.debug(f"      未获取到评论")
                        continue

                    logger.info(f"      共获取 {len(all_comments)} 条评论")

                    # 与数据库对比，找出新增的
                    for comment in all_comments:
                        # 从comment中提取用户信息
                        user = comment.get('user', {})

                        # 提取所有用户ID字段
                        comment_user_id = user.get('sec_uid', '')  # sec_uid (MS4w...)
                        comment_uid = user.get('uid', '')  # 数字ID
                        comment_unique_id = user.get('unique_id', '')  # 抖音号
                        comment_user_name = user.get('nickname', '')
                        comment_text = comment.get('text', '')

                        if not comment_user_id:
                            # 如果没有sec_uid，跳过
                            continue

                        # ✅ 必须有comment_unique_id才能创建任务（抖音搜索需要用户名/抖音号）
                        if not comment_unique_id:
                            logger.debug(f"        ⊗ 跳过评论: {comment_user_name} (缺少 comment_unique_id，无法搜索用户)")
                            continue

                        # 检查是否在历史评论中（使用sec_uid去重）
                        existing_in_history = session.query(Comment).filter_by(
                            target_account_id=target_account.id,
                            video_id=video_id,
                            comment_user_id=comment_user_id  # comment_user_id字段存储的是sec_uid
                        ).first()

                        # 如果不在历史评论中，则为新增
                        if not existing_in_history:
                            # 检查是否已在 new_comments 表中
                            existing_in_new = session.query(NewComment).filter_by(
                                target_account_id=target_account.id,
                                video_id=video_id,
                                comment_user_id=comment_user_id
                            ).first()

                            if not existing_in_new:
                                new_comment = NewComment(
                                    target_account_id=target_account.id,
                                    video_id=video_id,
                                    comment_user_id=comment_user_id,
                                    comment_user_name=comment_user_name,
                                    comment_uid=comment_uid,
                                    comment_unique_id=comment_unique_id,
                                    comment_text=comment_text,
                                    discovered_at=datetime.now()
                                )
                                session.add(new_comment)
                                new_comments_count += 1

                                logger.debug(f"        ✓ 新评论: {comment_user_name} - {comment_text[:30]}...")

                    # 更新监控时间（如果是VideoCache对象）
                    if hasattr(video_cache, 'last_monitored'):
                        video_cache.last_monitored = datetime.now()

                except Exception as e:
                    logger.warning(f"    [!] 检查视频 {video_id} 失败: {e}")
                    continue

            session.commit()

            logger.info(f"✓ 监控完成: 发现 {new_comments_count} 条新增评论")

            return {
                'account_id': target_account.id,
                'new_comments_count': new_comments_count,
                'status': 'success'
            }

        except Exception as e:
            session.rollback()
            logger.error(f"✗ 监控失败: {e}")
            return {
                'account_id': target_account.id,
                'new_comments_count': 0,
                'status': 'failed',
                'error': str(e)
            }
        finally:
            session.close()

    def detect_new_videos(self, target_account, session):
        """检测新视频（增量检测）

        Args:
            target_account: 目标账号
            session: 数据库session

        Returns:
            新视频列表，或None
        """
        try:
            # 获取缓存中最新视频的创建时间
            latest_cache = session.query(VideoCache)\
                .filter_by(target_account_id=target_account.id)\
                .order_by(VideoCache.create_time.desc())\
                .first()

            if not latest_cache:
                # 首次监控，无缓存，返回None让程序回退到传统方式
                logger.info("    首次监控，VideoCache无数据")
                return None

            latest_time = latest_cache.create_time

            # 获取用户最新视频（只获取最新10个）
            logger.debug(f"    最新缓存视频时间: {latest_time}")
            videos = self.api.get_user_videos(
                sec_user_id=target_account.sec_user_id,
                max_count=10  # 只获取最新10个，性能优化！
            )

            if not videos:
                logger.debug("    API未返回视频")
                return None

            # 筛选出比缓存更新的视频
            new_videos = []
            for video in videos:
                video_create_time = datetime.fromtimestamp(video.get('create_time', 0)) if video.get('create_time') else None
                if video_create_time and latest_time and video_create_time > latest_time:
                    new_videos.append(video)

            return new_videos if new_videos else None

        except Exception as e:
            logger.warning(f"    检测新视频失败: {e}")
            return None

    def update_video_cache(self, target_account, new_videos, session):
        """更新视频缓存

        Args:
            target_account: 目标账号
            new_videos: 新视频列表
            session: 数据库session
        """
        for video in new_videos:
            video_id = video.get('aweme_id') or video.get('video_id')
            if not video_id:
                continue

            # 检查是否已存在（避免重复）
            existing = session.query(VideoCache).filter_by(video_id=video_id).first()
            if existing:
                continue

            cache = VideoCache(
                target_account_id=target_account.id,
                video_id=video_id,
                video_title=video.get('desc', '')[:100] if video.get('desc') else '',
                video_desc=video.get('desc', ''),
                video_url=f"https://www.douyin.com/video/{video_id}",
                create_time=datetime.fromtimestamp(video.get('create_time', 0)) if video.get('create_time') else None,
                comment_count=video.get('comment_count', 0),
                digg_count=video.get('digg_count', 0),
                share_count=video.get('share_count', 0)
            )
            session.add(cache)
            logger.debug(f"      新视频缓存: {video_id} - {cache.comment_count} 条评论")

        session.commit()
        logger.info(f"    ✓ 更新了 {len(new_videos)} 个新视频到缓存")

    def refresh_top_videos(self, target_account, session, top_n=5):
        """重新计算Top N视频

        Args:
            target_account: 目标账号
            session: 数据库session
            top_n: Top数量
        """
        # 取消所有Top标记
        session.query(VideoCache)\
            .filter_by(target_account_id=target_account.id)\
            .update({'is_top_video': False})

        # 标记新的Top N
        top_videos = session.query(VideoCache)\
            .filter_by(target_account_id=target_account.id)\
            .order_by(VideoCache.comment_count.desc())\
            .limit(top_n)\
            .all()

        for idx, video in enumerate(top_videos, 1):
            video.is_top_video = True
            logger.debug(f"      Top {idx}: {video.video_id} - {video.comment_count} 条评论")

        session.commit()
        logger.info(f"    ✓ 更新Top {top_n}视频标记")

    def get_top_videos_from_cache(self, target_account, session, top_n=5):
        """从VideoCache读取Top N视频（优化版）

        Args:
            target_account: 目标账号
            session: 数据库session
            top_n: Top数量

        Returns:
            VideoCache对象列表
        """
        top_videos = session.query(VideoCache)\
            .filter_by(target_account_id=target_account.id, is_top_video=True)\
            .order_by(VideoCache.comment_count.desc())\
            .limit(top_n)\
            .all()

        return top_videos if top_videos else None

    def get_top_videos(self, target_account, top_n=5):
        """获取评论最多的Top N视频（传统方式，作为回退）

        Args:
            target_account: 目标账号
            top_n: 返回数量

        Returns:
            视频列表，每个视频包含 video_id（实际是aweme_id）和comment_count
        """
        try:
            # 从API获取用户视频
            videos = self.api.get_user_videos(
                sec_user_id=target_account.sec_user_id
            )

            if not videos:
                logger.warning(f"  [!] 未获取到视频数据")
                return []

            logger.info(f"  获取到 {len(videos)} 个视频")

            # 视频数据已经包含comment_count字段，直接按评论数排序
            # 同时将aweme_id重命名为video_id以保持兼容
            for video in videos:
                if 'aweme_id' in video and 'video_id' not in video:
                    video['video_id'] = video['aweme_id']

            # 按评论数排序，取前N个
            sorted_videos = sorted(
                videos,
                key=lambda x: x.get('comment_count', 0),
                reverse=True
            )

            top_videos = sorted_videos[:top_n]

            # 打印Top视频信息
            logger.info(f"  评论最多的前 {len(top_videos)} 个视频:")
            for i, video in enumerate(top_videos, 1):
                logger.info(f"    {i}. 视频 {video.get('video_id', '')[:20]}... - {video.get('comment_count', 0)} 条评论")

            return top_videos

        except Exception as e:
            logger.error(f"获取Top视频失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
