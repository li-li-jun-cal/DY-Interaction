#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新主力服务器的抖音Cookie
用于解决API请求被反爬拦截的问题
"""

import json
import sys
import requests
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def read_cookie_from_file():
    """从配置文件读取Cookie"""
    cookie_file = project_root / 'config' / 'douyin_cookie.txt'

    if not cookie_file.exists():
        print(f"❌ Cookie文件不存在: {cookie_file}")
        print("   请先创建文件并填入Cookie")
        sys.exit(1)

    with open(cookie_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 跳过注释行，找到Cookie
    cookie = None
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            cookie = line
            break

    if not cookie or cookie == "你的Cookie粘贴在这里":
        print("❌ 请先在 config/douyin_cookie.txt 中填入你的抖音Cookie")
        print("   参考文件中的说明获取Cookie")
        sys.exit(1)

    return cookie


def load_config():
    """加载服务器配置"""
    config_file = project_root / 'config' / 'config.json'

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    return config


def update_cookie_on_server(base_url, cookie, server_name):
    """更新指定服务器的Cookie"""
    print(f"\n{'='*70}")
    print(f"正在更新服务器: {server_name}")
    print(f"服务器地址: {base_url}")
    print(f"{'='*70}")

    # 构建更新Cookie的URL
    update_url = f"{base_url}/api/hybrid/update_cookie"

    # 准备请求参数
    params = {
        'service': 'douyin',  # 注意：这里是 "douyin" 不是 "douyin_web"
        'cookie': cookie
    }

    print(f"\n📤 发送更新请求...")
    print(f"   服务名称: douyin")
    print(f"   Cookie长度: {len(cookie)} 字符")
    print(f"   Cookie前50字符: {cookie[:50]}...")

    try:
        # 发送POST请求
        response = requests.post(
            update_url,
            json=params,
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )

        print(f"\n📥 响应状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Cookie更新成功!")
            print(f"   响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return True
        else:
            print(f"❌ Cookie更新失败!")
            print(f"   响应内容: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print(f"❌ 请求超时，服务器可能无法访问")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return False


def main():
    print("="*70)
    print("抖音Cookie更新工具")
    print("="*70)

    # 读取Cookie
    print("\n📖 读取Cookie配置...")
    cookie = read_cookie_from_file()
    print(f"✅ Cookie读取成功 (长度: {len(cookie)} 字符)")

    # 加载服务器配置
    print("\n📖 加载服务器配置...")
    config = load_config()
    servers = config['api']['servers']
    print(f"✅ 找到 {len(servers)} 个主力服务器")

    # 更新每个服务器的Cookie
    success_count = 0
    fail_count = 0

    for server in servers:
        result = update_cookie_on_server(
            server['base_url'],
            cookie,
            server['name']
        )

        if result:
            success_count += 1
        else:
            fail_count += 1

    # 显示汇总结果
    print("\n" + "="*70)
    print("📊 更新结果汇总")
    print("="*70)
    print(f"✅ 成功: {success_count} 个服务器")
    print(f"❌ 失败: {fail_count} 个服务器")

    if success_count > 0:
        print("\n💡 提示:")
        print("   Cookie已更新，现在可以重新运行历史爬虫测试")
        print("   python programs/run_history_crawler.py --accounts 2")

    print("="*70)


if __name__ == '__main__':
    main()
