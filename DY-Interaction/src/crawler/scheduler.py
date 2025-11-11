"""
爬虫调度器 - 调度爬取目标账号的视频和评论
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from .api_client import DouyinAPIClient
from ..database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class CrawlerScheduler:
    """爬虫调度器"""

    def __init__(self, db_manager: DatabaseManager, api_client: DouyinAPIClient = None):
        """初始化爬虫调度器

        Args:
            db_manager: 数据库管理器
            api_client: API客户端（可选，不提供则自动创建）
        """
        self.db = db_manager
        self.api_client = api_client or DouyinAPIClient()
        logger.info("✓ 爬虫调度器初始化完成")

    def crawl_target_account(self, target_account, max_videos: int = 10) -> List[Dict]:
        """爬取目标账号的最新视频和评论

        Args:
            target_account: TargetAccount 对象
            max_videos: 最多爬取的视频数

        Returns:
            评论列表
        """
        try:
            logger.info(f"开始爬取账号: {target_account.account_name}")

            # 1. 获取用户的最新视频
            videos = self.api_client.get_user_videos(
                target_account.sec_user_id,
                max_count=max_videos
            )

            if not videos:
                logger.warning(f"未获取到视频: {target_account.account_name}")
                return []

            logger.info(f"获取到 {len(videos)} 个视频")

            all_comments = []

            # 2. 对每个视频，获取评论
            for i, video in enumerate(videos, 1):
                logger.info(f"爬取视频 {i}/{len(videos)}: {video['aweme_id']}")

                comments = self.api_client.get_video_comments(
                    video['aweme_id'],
                    max_count=100
                )

                logger.info(f"  获取到 {len(comments)} 条评论")

                # 为每条评论添加视频信息
                for comment in comments:
                    comment['video_id'] = video['aweme_id']
                    comment['video_desc'] = video['desc']
                    comment['target_account_id'] = target_account.id

                all_comments.extend(comments)

                # 避免请求过快
                time.sleep(0.5)

            logger.info(f"✓ 总共获取到 {len(all_comments)} 条评论")
            return all_comments

        except Exception as e:
            logger.error(f"✗ 爬取失败 {target_account.account_name}: {e}")
            raise

    def crawl_new_comments_since(self, target_account, last_crawl_time: datetime) -> List[Dict]:
        """获取上次爬取后的新评论

        Args:
            target_account: TargetAccount 对象
            last_crawl_time: 上次爬取时间

        Returns:
            新评论列表
        """
        try:
            # 获取最新视频
            videos = self.api_client.get_user_videos(
                target_account.sec_user_id,
                max_count=5  # 只获取最新5个视频
            )

            if not videos:
                return []

            new_comments = []

            # 筛选在last_crawl_time之后发布的视频
            for video in videos:
                video_time = datetime.fromtimestamp(video['create_time'])

                # 如果视频是在上次爬取之后发布的
                if video_time > last_crawl_time:
                    comments = self.api_client.get_video_comments(
                        video['aweme_id'],
                        max_count=100
                    )

                    for comment in comments:
                        comment['video_id'] = video['aweme_id']
                        comment['video_desc'] = video['desc']
                        comment['target_account_id'] = target_account.id

                    new_comments.extend(comments)

            logger.info(f"获取到 {len(new_comments)} 条新评论")
            return new_comments

        except Exception as e:
            logger.error(f"获取新评论失败: {e}")
            return []

    def crawl_historical_videos(self, target_account, look_back_days: int = 90) -> List[Dict]:
        """爬取历史视频（批量处理模式）

        Args:
            target_account: TargetAccount 对象
            look_back_days: 回溯天数

        Returns:
            视频列表
        """
        try:
            logger.info(f"爬取 {look_back_days} 天内的视频")

            # 获取所有视频
            all_videos = self.api_client.get_user_videos(
                target_account.sec_user_id,
                max_count=200  # 最多200个视频
            )

            if not all_videos:
                return []

            # 筛选在指定天数内的视频
            cutoff_time = datetime.now() - timedelta(days=look_back_days)
            cutoff_timestamp = int(cutoff_time.timestamp())

            recent_videos = [
                video for video in all_videos
                if video['create_time'] >= cutoff_timestamp
            ]

            # 按时间倒序排列（最新的在前）
            recent_videos.sort(key=lambda v: v['create_time'], reverse=True)

            logger.info(f"✓ 筛选出 {len(recent_videos)} 个视频")
            return recent_videos

        except Exception as e:
            logger.error(f"爬取历史视频失败: {e}")
            return []

    def crawl_video_comments_batch(self, video_ids: List[str], max_per_video: int = 100) -> Dict[str, List[Dict]]:
        """批量爬取多个视频的评论

        Args:
            video_ids: 视频ID列表
            max_per_video: 每个视频最多爬取的评论数

        Returns:
            {video_id: [comments]} 字典
        """
        result = {}

        for i, video_id in enumerate(video_ids, 1):
            logger.info(f"爬取视频评论 {i}/{len(video_ids)}: {video_id}")

            try:
                comments = self.api_client.get_video_comments(
                    video_id,
                    max_count=max_per_video
                )

                result[video_id] = comments
                logger.info(f"  获取到 {len(comments)} 条评论")

                # 避免请求过快
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"  爬取失败: {e}")
                result[video_id] = []

        return result

    def schedule_realtime(self, target_accounts: List, check_interval: int = 600):
        """定时爬取（实时监控模式）

        Args:
            target_accounts: 目标账号列表
            check_interval: 检查间隔（秒）
        """
        logger.info(f"开始实时监控，间隔 {check_interval} 秒")

        last_crawl_times = {}

        while True:
            try:
                for account in target_accounts:
                    logger.info(f"\n检查账号: {account.account_name}")

                    if account.id in last_crawl_times:
                        # 获取新评论
                        new_comments = self.crawl_new_comments_since(
                            account,
                            last_crawl_times[account.id]
                        )
                        logger.info(f"新评论数: {len(new_comments)}")
                    else:
                        # 首次爬取
                        new_comments = self.crawl_target_account(account, max_videos=5)
                        logger.info(f"首次爬取评论数: {len(new_comments)}")

                    # 更新上次爬取时间
                    last_crawl_times[account.id] = datetime.now()

                    # 这里可以调用任务生成器生成互动任务
                    # generator.generate_realtime_tasks(account, new_comments)

                # 等待下一个检查周期
                logger.info(f"\n等待 {check_interval} 秒...")
                time.sleep(check_interval)

            except KeyboardInterrupt:
                logger.info("收到停止信号，退出实时监控")
                break
            except Exception as e:
                logger.error(f"实时监控错误: {e}")
                time.sleep(60)

    def schedule_batch(self, target_accounts: List, look_back_days: int = 90):
        """批量爬取（批量处理模式）

        Args:
            target_accounts: 目标账号列表
            look_back_days: 回溯天数
        """
        logger.info(f"开始批量爬取，回溯 {look_back_days} 天")

        for account in target_accounts:
            logger.info(f"\n处理账号: {account.account_name}")

            # 获取进度
            progress = self.db.get_batch_progress(account.id)

            if not progress:
                # 首次处理，获取所有历史视频
                logger.info("首次处理，爬取所有历史视频")
                videos = self.crawl_historical_videos(account, look_back_days)

                # 创建进度记录
                self.db.create_batch_progress(account.id)
            else:
                # 继续上次的进度
                logger.info(f"继续上次进度，上次处理到: {progress.last_video_id}")
                videos = self.crawl_historical_videos(account, look_back_days)

            if not videos:
                logger.warning("没有视频需要处理")
                continue

            # 爬取所有视频的评论
            video_ids = [v['aweme_id'] for v in videos]
            all_comments = self.crawl_video_comments_batch(video_ids)

            # 这里可以调用任务生成器生成互动任务
            # generator.generate_batch_tasks(account, all_comments, daily_limit=50)

            logger.info(f"✓ 账号 {account.account_name} 处理完成")
