#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备管理工具 - 检测在线设备并支持交互式选择

功能：
1. 检测所有在线的ADB设备
2. 检查设备是否被其他脚本占用
3. 交互式选择设备
4. 自动分配设备
"""

import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class DeviceManager:
    """设备管理器"""

    def __init__(self):
        self.lock_file = project_root / 'data' / 'device_locks.json'
        self.lock_file.parent.mkdir(exist_ok=True)

    def get_online_devices(self) -> List[str]:
        """获取所有在线的ADB设备

        Returns:
            设备ID列表，如: ['127.0.0.1:5555', '127.0.0.1:5556']
        """
        try:
            result = subprocess.run(
                ['adb', 'devices'],
                capture_output=True,
                text=True,
                timeout=5
            )

            devices = []
            lines = result.stdout.strip().split('\n')[1:]  # 跳过第一行标题

            for line in lines:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    devices.append(device_id)

            return devices

        except Exception as e:
            print(f"⚠️  检测设备失败: {e}")
            return []

    def get_device_locks(self) -> Dict:
        """读取设备锁定信息

        Returns:
            {
                'longterm': ['Device-1', 'Device-2'],
                'realtime': ['Device-3'],
                'timestamp': '2025-11-02 18:00:00'
            }
        """
        if not self.lock_file.exists():
            return {'longterm': [], 'realtime': [], 'timestamp': ''}

        try:
            with open(self.lock_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'longterm': [], 'realtime': [], 'timestamp': ''}

    def lock_devices(self, device_ids: List[str], script_type: str):
        """锁定设备（标记为被某个脚本占用）

        Args:
            device_ids: 设备ID列表
            script_type: 'longterm' 或 'realtime'
        """
        from datetime import datetime

        locks = self.get_device_locks()
        locks[script_type] = device_ids
        locks['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with open(self.lock_file, 'w', encoding='utf-8') as f:
            json.dump(locks, f, ensure_ascii=False, indent=2)

    def unlock_devices(self, script_type: str):
        """解锁设备

        Args:
            script_type: 'longterm' 或 'realtime'
        """
        locks = self.get_device_locks()
        locks[script_type] = []

        with open(self.lock_file, 'w', encoding='utf-8') as f:
            json.dump(locks, f, ensure_ascii=False, indent=2)

    def get_available_devices(self, online_devices: List[str]) -> List[str]:
        """获取可用设备（在线且未被锁定）

        Args:
            online_devices: 在线设备列表

        Returns:
            可用设备列表
        """
        locks = self.get_device_locks()
        locked = locks.get('longterm', []) + locks.get('realtime', [])

        # 这里简化处理：假设Device-1对应第一个在线设备
        # 实际使用时可能需要更复杂的映射逻辑
        return [d for d in online_devices if d not in locked]

    def interactive_select_devices(self, online_devices: List[str]) -> List[str]:
        """交互式选择设备（简化版 - 不考虑占用状态）

        Args:
            online_devices: 在线设备列表

        Returns:
            选中的设备列表
        """
        if not online_devices:
            print("❌ 未检测到任何在线设备")
            return []

        print("\n" + "=" * 70)
        print("📱 设备选择")
        print("=" * 70)
        print(f"检测到 {len(online_devices)} 台在线设备:\n")

        # 显示设备列表
        for i, device_id in enumerate(online_devices, 1):
            print(f"  {i}. {device_id}")

        print()

        # 提示输入
        try:
            count = input("请输入用于监控自动化的设备数量 (直接回车使用所有设备): ").strip()

            if not count:
                # 使用所有设备
                print(f"\n✓ 使用所有设备: {len(online_devices)} 台")
                return online_devices

            count = int(count)

            if count <= 0 or count > len(online_devices):
                print(f"❌ 数量无效，应在 1-{len(online_devices)} 之间")
                return []

            # 选择具体设备
            selections = input(f"请选择 {count} 台设备（输入编号，用空格分隔，如: 1 2 3）: ").strip()
            indices = [int(x) for x in selections.split()]

            if len(indices) != count:
                print(f"❌ 需要选择 {count} 台设备，但输入了 {len(indices)} 台")
                return []

            # 验证编号
            selected_devices = []
            for idx in indices:
                if idx < 1 or idx > len(online_devices):
                    print(f"❌ 编号 {idx} 无效")
                    return []

                device_id = online_devices[idx - 1]
                selected_devices.append(device_id)

            print(f"\n✓ 已选择 {len(selected_devices)} 台设备:")
            for device_id in selected_devices:
                print(f"  - {device_id}")

            return selected_devices

        except KeyboardInterrupt:
            print("\n\n[取消] 用户中断")
            return []
        except Exception as e:
            print(f"\n❌ 输入错误: {e}")
            return []

    def map_to_device_names(self, device_ids: List[str]) -> List[str]:
        """将ADB设备ID映射到Device名称

        Args:
            device_ids: ADB设备ID列表，如 ['127.0.0.1:5555']

        Returns:
            Device名称列表，如 ['Device-1', 'Device-2']
        """
        # 获取所有在线设备
        online = self.get_online_devices()

        # 创建映射
        device_names = []
        for device_id in device_ids:
            if device_id in online:
                idx = online.index(device_id) + 1
                device_names.append(f'Device-{idx}')

        return device_names


def main():
    """测试设备检测"""
    manager = DeviceManager()

    print("=" * 70)
    print("设备管理工具")
    print("=" * 70)

    # 检测在线设备
    online = manager.get_online_devices()
    print(f"\n在线设备: {len(online)} 台")
    for i, device in enumerate(online, 1):
        print(f"  {i}. {device}")

    # 查看锁定状态
    locks = manager.get_device_locks()
    print(f"\n设备锁定状态:")
    print(f"  长期自动化: {locks.get('longterm', [])}")
    print(f"  实时自动化: {locks.get('realtime', [])}")
    print(f"  更新时间: {locks.get('timestamp', '未知')}")

    # 交互式选择
    if online:
        print("\n" + "=" * 70)
        selected = manager.interactive_select_devices(online)
        if selected:
            device_names = manager.map_to_device_names(selected)
            print(f"\n映射的设备名称: {device_names}")


if __name__ == '__main__':
    main()
