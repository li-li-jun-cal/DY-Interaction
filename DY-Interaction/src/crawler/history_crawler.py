"""
历史评论爬虫（3个月一次性爬取）
优化版：构建VideoCache缓存，提升监控爬虫性能
"""

import logging
from datetime import datetime
from src.database.models import Comment, VideoCache
from src.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class HistoryCrawler:
    """爬取3个月历史评论"""

    def __init__(self, db_manager, api_client):
        """初始化历史爬虫

        Args:
            db_manager: 数据库管理器
            api_client: API 客户端
        """
        self.db = db_manager
        self.api = api_client

    def crawl_history(self, target_account, days=90):
        """爬取历史评论

        Args:
            target_account: 目标账号对象
            days: 历史天数（默认90天=3个月）- 注意：现在会爬取所有视频，days参数仅用于区分优先级

        Returns:
            {
                'account_id': int,
                'total_comments': int,
                'total_videos': int,
                'status': 'success' or 'failed',
                'error': 错误信息（如有）
            }
        """
        session = self.db.get_session()
        try:
            logger.info(f"开始爬取账号 {target_account.account_id} 的历史评论")

            # ======== 第一步：获取用户信息，确定视频总数 ========
            logger.info(f"  [1/4] 获取用户信息...")
            user_profile = self.api.get_user_profile(
                sec_user_id=target_account.sec_user_id
            )

            if not user_profile:
                logger.error(f"  [!] 无法获取用户信息")
                return {
                    'account_id': target_account.id,
                    'total_comments': 0,
                    'total_videos': 0,
                    'status': 'failed',
                    'error': '无法获取用户信息'
                }

            aweme_count = user_profile.get('aweme_count', 0)
            logger.info(f"    ✓ 用户昵称: {user_profile.get('nickname', 'N/A')}")
            logger.info(f"    ✓ 视频总数: {aweme_count} 个")
            logger.info(f"    ✓ 粉丝数: {user_profile.get('follower_count', 0)}")

            if aweme_count == 0:
                logger.warning(f"  [!] 该用户没有发布视频")
                return {
                    'account_id': target_account.id,
                    'total_comments': 0,
                    'total_videos': 0,
                    'status': 'success'
                }

            # ======== 第二步：获取所有视频（使用 aweme_count 作为 max_count） ========
            logger.info(f"  [2/4] 获取用户所有视频列表（共 {aweme_count} 个）...")
            videos = self.api.get_user_videos(
                sec_user_id=target_account.sec_user_id,
                max_count=aweme_count  # 使用用户实际视频数量
            )

            if not videos:
                logger.warning(f"  [!] 未找到视频")
                return {
                    'account_id': target_account.id,
                    'total_comments': 0,
                    'total_videos': 0,
                    'status': 'success'
                }

            logger.info(f"  ✓ 实际获取到 {len(videos)} 个视频")

            # ======== 第三步：构建VideoCache（优化监控性能） ========
            logger.info(f"  [3/4] 保存视频元数据到 VideoCache...")
            video_cache_count = 0

            for video in videos:
                video_id = video.get('video_id') or video.get('aweme_id')
                if not video_id:
                    continue

                # 检查是否已存在
                existing_cache = session.query(VideoCache).filter_by(
                    video_id=video_id
                ).first()

                if existing_cache:
                    # 更新统计数据
                    existing_cache.comment_count = video.get('comment_count', 0)
                    existing_cache.digg_count = video.get('digg_count', 0)
                    existing_cache.share_count = video.get('share_count', 0)
                    existing_cache.updated_at = datetime.now()
                else:
                    # 创建新记录
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
                    video_cache_count += 1

            # 提交缓存
            session.commit()
            logger.info(f"    ✓ 缓存了 {video_cache_count} 个新视频")

            # 标记Top 5视频（用于监控优化）
            logger.info(f"  [缓存] 标记评论最多的 Top 5 视频...")

            # 先取消所有Top标记
            session.query(VideoCache)\
                .filter_by(target_account_id=target_account.id)\
                .update({'is_top_video': False})

            # 标记新的Top 5
            top_videos = session.query(VideoCache)\
                .filter_by(target_account_id=target_account.id)\
                .order_by(VideoCache.comment_count.desc())\
                .limit(5)\
                .all()

            for idx, video in enumerate(top_videos, 1):
                video.is_top_video = True
                logger.info(f"    Top {idx}: {video.video_id} - {video.comment_count} 条评论")

            session.commit()
            logger.info(f"    ✓ Top 5 视频已标记")
            # ======== VideoCache构建完成 ========

            total_comments = 0
            total_videos = len(videos)

            # 爬取每个视频的评论
            logger.info(f"  [4/4] 爬取评论...")
            for idx, video in enumerate(videos, 1):
                if idx % 5 == 0:
                    logger.info(f"    进度: {idx}/{total_videos}")

                # 获取 aweme_id (视频ID)
                aweme_id = video.get('video_id') or video.get('aweme_id')
                if not aweme_id:
                    continue

                try:
                    # 获取视频信息
                    video_desc = video.get('desc', '')
                    video_url = f"https://www.douyin.com/video/{aweme_id}"
                    video_digg_count = video.get('digg_count', 0)
                    video_comment_count = video.get('comment_count', 0)
                    video_share_count = video.get('share_count', 0)
                    video_create_time = datetime.fromtimestamp(video.get('create_time', 0)) if video.get('create_time') else None

                    # 获取该视频的所有评论
                    comments = self.api.get_video_comments(
                        aweme_id=aweme_id,
                        max_count=1000
                    )

                    for comment in comments:
                        # 提取用户信息（comment['user'] 是嵌套对象）
                        user = comment.get('user', {})
                        user_uid = user.get('uid', '')  # 用户数字ID
                        user_sec_uid = user.get('sec_uid', '')  # 安全用户ID
                        user_name = user.get('nickname', '')  # 昵称
                        user_unique_id = user.get('unique_id', '')  # 抖音号 - 重要！

                        # ✅ 必须有user_unique_id才能创建任务（抖音搜索需要用户名/抖音号）
                        if not user_unique_id:
                            logger.debug(f"          ⊗ 跳过评论: {user_name} (缺少 unique_id，无法搜索用户)")
                            continue

                        # 检查是否已存在
                        existing = session.query(Comment).filter_by(
                            target_account_id=target_account.id,
                            video_id=aweme_id,
                            comment_user_id=user_sec_uid
                        ).first()

                        if not existing:
                            new_comment = Comment(
                                target_account_id=target_account.id,
                                video_id=aweme_id,
                                comment_user_id=user_sec_uid,  # 保持用 sec_uid 作为主ID
                                comment_user_name=user_name,
                                comment_uid=user_uid,  # 新增：用户数字ID
                                comment_unique_id=user_unique_id,  # 新增：抖音号
                                comment_sec_uid=user_sec_uid,  # 新增：sec_uid
                                comment_text=comment.get('text', ''),
                                comment_time=datetime.fromtimestamp(comment.get('create_time', 0)) if comment.get('create_time') else None,
                                digg_count=comment.get('digg_count', 0),
                                reply_count=comment.get('reply_count', 0),
                                # 新增：视频信息
                                video_url=video_url,
                                video_desc=video_desc,
                                video_digg_count=video_digg_count,
                                video_comment_count=video_comment_count,
                                video_share_count=video_share_count,
                                video_create_time=video_create_time,  # 新增：视频发布时间
                                status='new'
                            )
                            session.add(new_comment)
                            total_comments += 1

                except Exception as e:
                    logger.warning(f"    [!] 爬取视频 {aweme_id} 评论失败: {e}")
                    continue

            session.commit()

            logger.info(f"✓ 爬取完成: {total_videos} 个视频, {total_comments} 条新增评论")

            return {
                'account_id': target_account.id,
                'total_comments': total_comments,
                'total_videos': total_videos,
                'status': 'success'
            }

        except Exception as e:
            session.rollback()
            logger.error(f"✗ 爬取失败: {e}")
            return {
                'account_id': target_account.id,
                'status': 'failed',
                'error': str(e)
            }
        finally:
            session.close()
