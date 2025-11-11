#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多服务器API客户端 - 支持手动选择和自动故障转移
来源：从 DY-A 项目复制的完整实现
"""

import json
import logging
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import sys
from enum import Enum

import requests

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class ServerStatus(Enum):
    """服务器状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class APIServer:
    """API服务器配置"""
    def __init__(self, base_url: str, priority: int, name: str, api_key: str = ""):
        self.base_url = base_url.rstrip('/')
        self.priority = priority
        self.name = name
        self.api_key = api_key
        self.status = ServerStatus.HEALTHY
        self.fail_count = 0
        self.last_success_time = time.time()
        self.last_fail_time = 0

    def mark_success(self):
        """标记请求成功"""
        self.status = ServerStatus.HEALTHY
        self.fail_count = 0
        self.last_success_time = time.time()

    def mark_failure(self):
        """标记请求失败"""
        self.fail_count += 1
        self.last_fail_time = time.time()

        if self.fail_count >= 3:
            self.status = ServerStatus.FAILED
        elif self.fail_count >= 1:
            self.status = ServerStatus.DEGRADED

    def should_retry(self) -> bool:
        """判断是否应该重试此服务器"""
        if self.status == ServerStatus.HEALTHY:
            return True
        elif self.status == ServerStatus.DEGRADED:
            return True
        else:  # FAILED
            return (time.time() - self.last_fail_time) > 300


class DouyinAPIClient:
    """抖音API统一客户端 - 多服务器支持"""

    # 接口端点映射（主力服务器专用 - web 接口）
    ENDPOINTS = {
        'user_profile': '/api/douyin/web/handler_user_profile',
        'user_videos': '/api/douyin/web/fetch_user_post_videos',  # 主力服务器用 web 接口
        'video_comments': '/api/douyin/web/fetch_video_comments',
    }

    # 备用接口端点映射（TikHub 专用 - app 接口，支持完整分页）
    FALLBACK_ENDPOINTS = {
        'user_profile': '/api/v1/douyin/web/handler_user_profile',
        'user_videos': '/api/v1/douyin/app/v3/fetch_user_post_videos',  # TikHub 用 app 接口
        'video_comments': '/api/v1/douyin/app/v3/fetch_video_comments',
    }

    def __init__(self, config_path: str = None, prefer_server: str = "auto"):
        """初始化API客户端

        Args:
            config_path: 配置文件路径，默认为 config/config.json
            prefer_server: 优先使用的服务器名称，"auto"表示自动选择
        """
        # 如果没有指定config_path，使用默认路径
        if config_path is None:
            config_path = str(Path(__file__).parent.parent.parent / "config" / "config.json")

        self.config = self._load_config(config_path)
        self.timeout = self.config['api'].get('timeout', 30)
        self.max_retries = self.config['api'].get('max_retries', 3)
        self.request_delay = self.config['api'].get('request_delay', 0.5)

        # 创建logger
        self.logger = logging.getLogger(__name__)
        self.prefer_server = prefer_server

        # 初始化服务器列表
        self.servers = self._init_servers()

        self.logger.info(f"初始化API客户端，共 {len(self.servers)} 个服务器，优先使用: {prefer_server}")

    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # 即使logger还未初始化也要创建一个临时logger
            logger = logging.getLogger(__name__)
            logger.warning(f"配置文件未找到：{config_path}，使用默认配置")
            return {
                'api': {
                    'servers': [],
                    'fallback': {
                        'base_url': 'https://api.tikhub.dev',
                        'api_key': ''
                    },
                    'timeout': 30,
                    'max_retries': 3,
                    'request_delay': 0.5
                }
            }

    def _init_servers(self) -> List[APIServer]:
        """初始化服务器列表"""
        servers = []

        # 从配置加载服务器
        server_configs = self.config['api'].get('servers', [])

        if not server_configs:
            # 如果配置为空，使用硬编码的服务器列表（来自 DY-A）
            server_configs = [
                {
                    'name': '主力服务器1',
                    'base_url': 'http://140.245.55.143:8001',
                    'priority': 1,
                    'api_key': ''
                },
                {
                    'name': '主力服务器2',
                    'base_url': 'http://140.245.55.143:20002',
                    'priority': 2,
                    'api_key': ''
                }
            ]

        # 创建主力服务器
        for config in server_configs:
            server = APIServer(
                base_url=config['base_url'],
                priority=config['priority'],
                name=config['name'],
                api_key=config.get('api_key', '')
            )
            servers.append(server)

        # 添加备用服务器（TikHub）
        fallback_config = self.config['api'].get('fallback', {})
        if fallback_config.get('base_url'):
            fallback_server = APIServer(
                base_url=fallback_config['base_url'],
                priority=999,
                name='备用服务器(TikHub)',
                api_key=fallback_config.get('api_key', '')
            )
            servers.append(fallback_server)

        # 按优先级排序
        servers.sort(key=lambda s: s.priority)

        return servers

    def get_available_servers(self) -> List[Dict]:
        """获取所有可用服务器列表（供前端选择）"""
        return [{
            'name': server.name,
            'base_url': server.base_url,
            'status': server.status.value,
            'priority': server.priority
        } for server in self.servers]

    def set_preferred_server(self, server_name: str):
        """设置优先使用的服务器"""
        self.prefer_server = server_name
        self.logger.info(f"切换优先服务器为: {server_name}")

    def _get_headers(self, server: APIServer) -> Dict[str, str]:
        """构建请求头"""
        headers = {'accept': 'application/json'}
        if server.api_key:
            headers['Authorization'] = f'Bearer {server.api_key}'
        return headers

    def _get_endpoint(self, server: APIServer, endpoint_key: str) -> str:
        """获取端点路径（根据服务器类型）"""
        # 如果是备用服务器（TikHub），使用备用端点
        if server.priority >= 999:
            return self.FALLBACK_ENDPOINTS.get(endpoint_key, self.ENDPOINTS[endpoint_key])
        else:
            return self.ENDPOINTS[endpoint_key]

    def _request_single_server(self, server: APIServer, endpoint_key: str,
                              params: Dict = None) -> Optional[Dict]:
        """向单个服务器发起请求"""
        endpoint = self._get_endpoint(server, endpoint_key)
        url = f"{server.base_url}{endpoint}"
        headers = self._get_headers(server)

        try:
            self.logger.debug(f"请求 {server.name}: {url}")
            response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            response.raise_for_status()

            result = response.json()

            if result.get('code') == 200:
                server.mark_success()
                self.logger.info(f"✓ {server.name} 请求成功")
                return result
            else:
                self.logger.warning(
                    f"✗ {server.name} API返回错误码: {result.get('code')}, "
                    f"消息: {result.get('message', 'N/A')}"
                )
                server.mark_failure()
                return None

        except requests.exceptions.Timeout:
            self.logger.warning(f"✗ {server.name} 请求超时")
            server.mark_failure()
            return None

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 'Unknown'
            self.logger.warning(f"✗ {server.name} HTTP错误: {status_code}")
            server.mark_failure()
            return None

        except requests.exceptions.RequestException as e:
            self.logger.warning(f"✗ {server.name} 请求失败: {str(e)[:100]}")
            server.mark_failure()
            return None
        except Exception as e:
            self.logger.error(f"✗ {server.name} 未知错误: {str(e)[:100]}")
            server.mark_failure()
            return None

    def _get_server_order(self) -> List[APIServer]:
        """获取服务器请求顺序"""
        if self.prefer_server != "auto":
            # 手动选择了服务器
            preferred = None
            others = []

            for server in self.servers:
                if server.name == self.prefer_server:
                    preferred = server
                else:
                    others.append(server)

            if preferred:
                # 优先服务器放在第一位，其他按优先级排序
                others.sort(key=lambda s: s.priority)
                return [preferred] + others

        # 自动模式：返回所有可用服务器，按优先级排序
        available = [s for s in self.servers if s.should_retry()]
        return available if available else self.servers

    def _request_with_failover(self, endpoint_key: str, params: Dict = None) -> Optional[Dict]:
        """带故障转移的请求"""
        server_order = self._get_server_order()

        if not server_order:
            self.logger.error("没有可用的服务器！")
            return None

        for i, server in enumerate(server_order):
            if i == 0:
                self.logger.info(f"使用服务器: {server.name}")
            else:
                self.logger.info(f"故障转移到: {server.name}")

            result = self._request_single_server(server, endpoint_key, params)
            if result:
                return result

            # 请求失败，稍等后尝试下一个服务器
            if i < len(server_order) - 1:
                time.sleep(0.5)

        self.logger.error(f"所有服务器请求 {endpoint_key} 都失败了！")
        return None


    # ========== 用户相关API ==========

    def get_user_profile(self, sec_user_id: str) -> Optional[Dict]:
        """获取用户主页信息"""
        params = {'sec_user_id': sec_user_id}
        response = self._request_with_failover('user_profile', params)

        if not response:
            return None

        user_data = response.get('data', {}).get('user', {})
        return {
            'sec_user_id': sec_user_id,
            'nickname': user_data.get('nickname', ''),
            'unique_id': user_data.get('unique_id', '') or user_data.get('short_id', ''),
            'follower_count': user_data.get('follower_count', 0),
            'following_count': user_data.get('following_count', 0),
            'total_favorited': user_data.get('total_favorited', 0),
            'aweme_count': user_data.get('aweme_count', 0),
            'avatar_url': user_data.get('avatar_larger', {}).get('url_list', [''])[0]
        }

    # ========== 视频相关API ==========

    def get_user_videos(self, sec_user_id: str, max_count: int = None) -> List[Dict]:
        """获取用户所有视频列表

        Args:
            sec_user_id: 用户sec_user_id
            max_count: 最大视频数，None表示获取所有视频

        Returns:
            视频列表
        """
        videos = []
        max_cursor = 0
        count_per_request = 20
        request_count = 0  # 请求次数计数

        self.logger.info(f"开始获取视频，目标数量: {max_count if max_count else '全部'}")
        self.logger.info(f"  使用主力服务器的 web 接口")

        while max_count is None or len(videos) < max_count:
            request_count += 1
            params = {
                'sec_user_id': sec_user_id,
                'max_cursor': max_cursor,
                'count': count_per_request
            }

            self.logger.info(f"  [请求 {request_count}] 请求参数:")
            self.logger.info(f"    - sec_user_id: {sec_user_id}")
            self.logger.info(f"    - max_cursor: {max_cursor}")
            self.logger.info(f"    - count: {count_per_request}")

            # 使用普通的故障转移（主力服务器）
            response = self._request_with_failover('user_videos', params)
            if not response:
                self.logger.error(f"  [请求 {request_count}] 请求失败，response 为空")
                break

            # 解析响应数据
            self.logger.info(f"  [请求 {request_count}] 原始响应:")
            self.logger.info(f"    - response keys: {list(response.keys())}")

            data = response.get('data', {})
            self.logger.info(f"    - data keys: {list(data.keys())}")

            aweme_list = data.get('aweme_list', [])
            has_more = data.get('has_more', 0)
            new_max_cursor = data.get('max_cursor', 0)
            min_cursor = data.get('min_cursor', 0)

            self.logger.info(f"  [请求 {request_count}] 返回数据:")
            self.logger.info(f"    - aweme_list 数量: {len(aweme_list)}")
            self.logger.info(f"    - has_more: {has_more}")
            self.logger.info(f"    - min_cursor: {min_cursor}")
            self.logger.info(f"    - max_cursor (请求): {max_cursor}")
            self.logger.info(f"    - max_cursor (响应): {new_max_cursor}")

            if not aweme_list:
                self.logger.warning(f"  [请求 {request_count}] aweme_list 为空，停止获取")
                self.logger.warning(f"    当前已获取 {len(videos)} 个视频")
                break

            # 添加视频到列表
            for video in aweme_list:
                stats = video.get('statistics', {})
                video_data = {
                    'aweme_id': str(video.get('aweme_id', '')),
                    'video_id': str(video.get('aweme_id', '')),  # 添加 video_id 别名，保持一致
                    'desc': video.get('desc', ''),
                    'video_url': f"https://www.douyin.com/video/{video.get('aweme_id', '')}",
                    'cover_url': video.get('video', {}).get('cover', {}).get('url_list', [''])[0],
                    'create_time': video.get('create_time', 0),
                    'digg_count': stats.get('digg_count', 0),
                    'comment_count': stats.get('comment_count', 0),
                    'share_count': stats.get('share_count', 0),
                    'duration': video.get('duration', 0)
                }
                videos.append(video_data)

            # 更新 cursor 用于下次请求
            max_cursor = new_max_cursor

            self.logger.info(f"  [请求 {request_count}] 累计获取: {len(videos)} 个视频")

            # 判断是否继续
            # 1. 如果新的 cursor 为 0，说明没有更多了
            if new_max_cursor == 0:
                self.logger.info(f"  [请求 {request_count}] max_cursor=0，确认没有更多视频")
                break

            # 2. 如果 cursor 没有变化，说明可能卡住了
            if request_count > 1 and new_max_cursor == params['max_cursor']:
                self.logger.warning(f"  [请求 {request_count}] cursor 未变化 (都是 {new_max_cursor})，可能已到达末尾")
                break

            # 3. 如果已获取足够数量，停止
            if max_count is not None and len(videos) >= max_count:
                self.logger.info(f"  [请求 {request_count}] 已获取足够视频 ({len(videos)}/{max_count})，停止")
                break

            self.logger.info(f"  [请求 {request_count}] 继续请求下一页 (cursor={new_max_cursor})")
            time.sleep(self.request_delay)

        # 如果指定了max_count，返回截断结果
        if max_count is not None:
            result_videos = videos[:max_count]
            self.logger.info(f"获取到 {len(videos)} 个视频，返回 {len(result_videos)} 个")
            return result_videos
        else:
            self.logger.info(f"获取到所有 {len(videos)} 个视频")
            return videos

    # ========== 评论相关API ==========

    def get_video_comments(self, aweme_id: str, max_count: int = None) -> List[Dict]:
        """获取视频所有评论

        Args:
            aweme_id: 视频ID
            max_count: 最大评论数，None表示获取所有评论

        Returns:
            评论列表
        """
        comments = []
        cursor = 0
        count_per_request = 50

        while max_count is None or len(comments) < max_count:
            params = {
                'aweme_id': aweme_id,
                'cursor': cursor,
                'count': count_per_request
            }

            response = self._request_with_failover('video_comments', params)
            if not response:
                break

            comment_list = response.get('data', {}).get('comments', [])
            if not comment_list:
                break

            for comment in comment_list:
                user = comment.get('user', {})
                comments.append({
                    'comment_id': str(comment.get('cid', '')),
                    'text': comment.get('text', ''),
                    'create_time': comment.get('create_time', 0),
                    'digg_count': comment.get('digg_count', 0),
                    'reply_count': comment.get('reply_comment_total', 0),
                    'user': {
                        'uid': user.get('uid', ''),  # 新增：用户数字ID
                        'sec_uid': user.get('sec_uid', ''),
                        'nickname': user.get('nickname', ''),
                        'unique_id': user.get('unique_id', '') or user.get('short_id', ''),
                        'avatar_url': user.get('avatar_thumb', {}).get('url_list', [''])[0]
                    }
                })

            has_more = response.get('data', {}).get('has_more', False)
            cursor = response.get('data', {}).get('cursor', cursor)

            if not has_more:
                break

            time.sleep(0.3)

        self.logger.info(f"获取到 {len(comments)} 条评论")

        # 如果指定了max_count，返回截断结果
        if max_count is not None:
            return comments[:max_count]
        else:
            return comments

    def get_server_status(self) -> List[Dict]:
        """获取所有服务器状态"""
        return [{
            'name': server.name,
            'base_url': server.base_url,
            'priority': server.priority,
            'status': server.status.value,
            'fail_count': server.fail_count,
            'last_success_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(server.last_success_time)),
            'last_fail_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(server.last_fail_time)) if server.last_fail_time > 0 else '从未失败'
        } for server in self.servers]
