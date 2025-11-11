#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量更新主力服务器的抖音Cookie池
支持多个Cookie轮换，提高稳定性
"""

import json
import sys
import requests
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def read_cookies_from_pool():
    """从Cookie池配置文件读取所有Cookie"""
    cookie_file = project_root / 'config' / 'douyin_cookies_pool.txt'

    if not cookie_file.exists():
        print(f"❌ Cookie池文件不存在: {cookie_file}")
        print("   请先创建文件并填入Cookie")
        sys.exit(1)

    with open(cookie_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 跳过注释行和空行，提取所有Cookie
    cookies = []
    for i, line in enumerate(lines, 1):
        line = line.strip()

        # 跳过注释和空行
        if not line or line.startswith('#'):
            continue

        # 跳过示例Cookie
        if 'Cookie1内容' in line or 'Cookie2内容' in line or 'Cookie3内容' in line:
            continue

        cookies.append({
            'cookie': line,
            'line': i
        })

    if not cookies:
        print("❌ 未找到有效的Cookie")
        print("   请在 config/douyin_cookies_pool.txt 中填入至少一个Cookie")
        sys.exit(1)

    return cookies


def load_config():
    """加载服务器配置"""
    config_file = project_root / 'config' / 'config.json'

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    return config


def update_cookie_on_server(base_url, cookie, server_name, cookie_index):
    """更新指定服务器的Cookie"""
    print(f"\n{'='*70}")
    print(f"服务器: {server_name}")
    print(f"Cookie编号: #{cookie_index}")
    print(f"{'='*70}")

    # 构建更新Cookie的URL
    update_url = f"{base_url}/api/hybrid/update_cookie"

    # 准备请求参数
    params = {
        'service': 'douyin',
        'cookie': cookie
    }

    print(f"📤 发送更新请求...")
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

        print(f"📥 响应状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Cookie更新成功!")
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
    print("抖音Cookie池批量更新工具")
    print("="*70)

    # 读取Cookie池
    print("\n📖 读取Cookie池配置...")
    cookies = read_cookies_from_pool()
    print(f"✅ 找到 {len(cookies)} 个Cookie")

    for i, cookie_info in enumerate(cookies, 1):
        print(f"   Cookie {i}: 长度 {len(cookie_info['cookie'])} 字符 (第{cookie_info['line']}行)")

    # 加载服务器配置
    print("\n📖 加载服务器配置...")
    config = load_config()
    servers = config['api']['servers']
    print(f"✅ 找到 {len(servers)} 个主力服务器")

    # 询问用户选择哪个Cookie
    print("\n" + "="*70)
    print("选择操作模式:")
    print("="*70)
    print("1. 使用第一个Cookie更新所有服务器（推荐）")
    print("2. 为每个服务器使用不同的Cookie（轮换模式）")
    print("3. 手动选择Cookie编号")

    choice = input("\n请输入选项 (1/2/3) [默认:1]: ").strip() or "1"

    success_count = 0
    fail_count = 0

    if choice == "1":
        # 使用第一个Cookie更新所有服务器
        cookie = cookies[0]['cookie']
        print(f"\n使用 Cookie #1 更新所有服务器...")

        for server in servers:
            result = update_cookie_on_server(
                server['base_url'],
                cookie,
                server['name'],
                1
            )

            if result:
                success_count += 1
            else:
                fail_count += 1

            time.sleep(0.5)  # 避免请求过快

    elif choice == "2":
        # 轮换模式：为每个服务器分配不同的Cookie
        print(f"\n轮换模式：为每个服务器分配不同的Cookie...")

        for i, server in enumerate(servers):
            # 循环使用Cookie池
            cookie_index = i % len(cookies)
            cookie = cookies[cookie_index]['cookie']

            result = update_cookie_on_server(
                server['base_url'],
                cookie,
                server['name'],
                cookie_index + 1
            )

            if result:
                success_count += 1
            else:
                fail_count += 1

            time.sleep(0.5)

    elif choice == "3":
        # 手动选择Cookie
        cookie_num = int(input(f"\n请输入要使用的Cookie编号 (1-{len(cookies)}): "))

        if 1 <= cookie_num <= len(cookies):
            cookie = cookies[cookie_num - 1]['cookie']
            print(f"\n使用 Cookie #{cookie_num} 更新所有服务器...")

            for server in servers:
                result = update_cookie_on_server(
                    server['base_url'],
                    cookie,
                    server['name'],
                    cookie_num
                )

                if result:
                    success_count += 1
                else:
                    fail_count += 1

                time.sleep(0.5)
        else:
            print(f"❌ 无效的Cookie编号")
            sys.exit(1)

    else:
        print("❌ 无效的选项")
        sys.exit(1)

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
