#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API服务器管理脚本

功能:
  - 查看已配置的API服务器
  - 添加新的API服务器
  - 删除API服务器
  - 修改服务器配置
  - 测试服务器连接
"""

import json
import sys
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class ServerManager:
    """API服务器管理器"""

    def __init__(self, config_path: str = None):
        """初始化服务器管理器"""
        if config_path is None:
            config_path = str(PROJECT_ROOT / "config" / "config.json")

        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ 配置文件未找到: {self.config_path}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"❌ 配置文件格式错误: {self.config_path}")
            sys.exit(1)

    def _save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            print(f"✅ 配置已保存到: {self.config_path}")
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")

    def list_servers(self):
        """列出所有服务器"""
        servers = self.config.get('api', {}).get('servers', [])

        print('\n' + '='*70)
        print('📊 API 服务器列表')
        print('='*70 + '\n')

        if not servers:
            print("  暂无服务器配置\n")
            return

        for i, server in enumerate(servers, 1):
            print(f"  {i}. 服务器名称: {server.get('name')}")
            print(f"     地址: {server.get('base_url')}")
            print(f"     优先级: {server.get('priority')}")
            print(f"     API Key: {'已设置' if server.get('api_key') else '未设置'}")
            print()

        # 显示备用服务器
        fallback = self.config.get('api', {}).get('fallback', {})
        if fallback.get('base_url'):
            print(f"  备用服务器 (TikHub):")
            print(f"     地址: {fallback.get('base_url')}")
            print(f"     API Key: {'已设置' if fallback.get('api_key') else '未设置'}")
            print()

        print('='*70 + '\n')

    def add_server(self, name: str = None, base_url: str = None, api_key: str = None):
        """添加新服务器"""
        servers = self.config.get('api', {}).get('servers', [])

        # 获取输入
        if name is None:
            name = input("请输入服务器名称 (例如: 主力服务器3): ").strip()
            if not name:
                print("❌ 服务器名称不能为空")
                return

        if base_url is None:
            base_url = input("请输入服务器地址 (例如: http://xxx.xxx.xxx.xxx:8008): ").strip()
            if not base_url:
                print("❌ 服务器地址不能为空")
                return

        if api_key is None:
            api_key = input("请输入API Key (可选，按Enter跳过): ").strip()

        # 自动分配优先级
        existing_priorities = [s.get('priority', 0) for s in servers]
        new_priority = max(existing_priorities) + 1 if existing_priorities else 1

        # 创建新服务器配置
        new_server = {
            "name": name,
            "base_url": base_url,
            "priority": new_priority,
            "api_key": api_key
        }

        # 添加到配置
        if 'api' not in self.config:
            self.config['api'] = {}
        if 'servers' not in self.config['api']:
            self.config['api']['servers'] = []

        self.config['api']['servers'].append(new_server)

        # 保存配置
        self._save_config()

        print(f"\n✅ 服务器添加成功！")
        print(f"   名称: {name}")
        print(f"   地址: {base_url}")
        print(f"   优先级: {new_priority}")
        print()

    def delete_server(self, index: int = None):
        """删除服务器"""
        servers = self.config.get('api', {}).get('servers', [])

        if not servers:
            print("❌ 没有可删除的服务器")
            return

        if index is None:
            self.list_servers()
            try:
                index = int(input("请输入要删除的服务器编号: ")) - 1
            except ValueError:
                print("❌ 无效的编号")
                return

        if index < 0 or index >= len(servers):
            print("❌ 服务器编号无效")
            return

        deleted_server = servers.pop(index)
        self._save_config()

        print(f"\n✅ 服务器已删除: {deleted_server['name']}\n")

    def modify_server(self, index: int = None):
        """修改服务器"""
        servers = self.config.get('api', {}).get('servers', [])

        if not servers:
            print("❌ 没有可修改的服务器")
            return

        if index is None:
            self.list_servers()
            try:
                index = int(input("请输入要修改的服务器编号: ")) - 1
            except ValueError:
                print("❌ 无效的编号")
                return

        if index < 0 or index >= len(servers):
            print("❌ 服务器编号无效")
            return

        server = servers[index]

        print(f"\n当前配置:")
        print(f"  名称: {server['name']}")
        print(f"  地址: {server['base_url']}")
        print(f"  API Key: {server.get('api_key', '')}")
        print()

        # 修改字段
        name = input("新名称 (留空保持不变): ").strip()
        if name:
            server['name'] = name

        base_url = input("新地址 (留空保持不变): ").strip()
        if base_url:
            server['base_url'] = base_url

        api_key = input("新API Key (留空保持不变): ").strip()
        if api_key:
            server['api_key'] = api_key

        self._save_config()

        print(f"\n✅ 服务器已修改: {server['name']}\n")

    def test_server(self, index: int = None):
        """测试服务器连接"""
        servers = self.config.get('api', {}).get('servers', [])

        if not servers:
            print("❌ 没有可测试的服务器")
            return

        if index is None:
            self.list_servers()
            try:
                index = int(input("请输入要测试的服务器编号: ")) - 1
            except ValueError:
                print("❌ 无效的编号")
                return

        if index < 0 or index >= len(servers):
            print("❌ 服务器编号无效")
            return

        server = servers[index]
        base_url = server['base_url']

        print(f"\n正在测试服务器: {server['name']}")
        print(f"地址: {base_url}")

        try:
            import requests
            response = requests.get(f"{base_url}/api/status", timeout=5)
            if response.status_code == 200:
                print(f"✅ 服务器连接成功！")
            else:
                print(f"⚠️  服务器返回状态码: {response.status_code}")
        except Exception as e:
            print(f"❌ 连接失败: {e}")

        print()


def main():
    """主函数"""
    manager = ServerManager()

    while True:
        print("\n" + "="*70)
        print("⚙️  API 服务器管理")
        print("="*70)
        print("\n  1. 查看服务器列表")
        print("  2. 添加新服务器")
        print("  3. 删除服务器")
        print("  4. 修改服务器")
        print("  5. 测试服务器连接")
        print("  0. 返回主菜单\n")

        choice = input("请选择操作 [0-5]: ").strip()

        if choice == '0':
            break
        elif choice == '1':
            manager.list_servers()
        elif choice == '2':
            manager.add_server()
        elif choice == '3':
            manager.delete_server()
        elif choice == '4':
            manager.modify_server()
        elif choice == '5':
            manager.test_server()
        else:
            print("❌ 无效选择")

        input("按回车键继续...")


if __name__ == '__main__':
    main()
