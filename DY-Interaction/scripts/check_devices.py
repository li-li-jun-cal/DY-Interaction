"""
设备健康检查工具

功能：
1. 检查设备连接状态
2. 自动重连断开的设备
3. 显示设备信息
"""
import subprocess
import time

def check_devices():
    """检查所有连接的设备"""
    print("\n" + "=" * 80)
    print("设备健康检查")
    print("=" * 80)

    try:
        # 获取设备列表
        result = subprocess.run(['adb', 'devices', '-l'],
                              capture_output=True,
                              text=True,
                              timeout=10)

        lines = result.stdout.strip().split('\n')[1:]  # 跳过第一行标题

        devices = []
        offline_devices = []

        for line in lines:
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) >= 2:
                device_id = parts[0]
                status = parts[1]

                if status == 'device':
                    devices.append(device_id)
                    print(f"  ✓ {device_id:30s} - 在线")
                elif status == 'offline':
                    offline_devices.append(device_id)
                    print(f"  ✗ {device_id:30s} - 离线")
                else:
                    print(f"  ⚠ {device_id:30s} - {status}")

        print("\n" + "=" * 80)
        print(f"总计: {len(devices)} 台在线, {len(offline_devices)} 台离线")
        print("=" * 80)

        if offline_devices:
            print("\n建议:")
            print("  1. 检查USB连接")
            print("  2. 重启 adb: adb kill-server && adb start-server")
            print("  3. 拔插USB线")

        return devices, offline_devices

    except subprocess.TimeoutExpired:
        print("✗ adb命令超时")
        return [], []
    except Exception as e:
        print(f"✗ 检查失败: {e}")
        return [], []

def restart_adb():
    """重启 adb server"""
    print("\n重启 adb server...")
    try:
        subprocess.run(['adb', 'kill-server'], timeout=10)
        time.sleep(1)
        subprocess.run(['adb', 'start-server'], timeout=10)
        time.sleep(2)
        print("✓ adb server 已重启")
        return True
    except Exception as e:
        print(f"✗ 重启失败: {e}")
        return False

if __name__ == "__main__":
    devices, offline = check_devices()

    if offline:
        print("\n发现离线设备，是否重启 adb? [y/N]: ", end='')
        choice = input().strip().lower()

        if choice == 'y':
            if restart_adb():
                print("\n等待设备重连...")
                time.sleep(3)
                print("\n重新检查:")
                check_devices()
