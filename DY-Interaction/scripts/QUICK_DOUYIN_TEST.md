# 🚀 抖音分享链接测试 - 快速开始

## 5分钟快速上手

### 第1步: 安装依赖
```bash
pip install uiautomator2 requests
```

### 第2步: 连接设备
```bash
# 检查连接
adb devices

# 如果提示未找到设备，请：
# 1. 确保手机USB调试已开启
# 2. 使用命令 adb usb
```

### 第3步: 运行脚本

#### 方式1: 手动输入（推荐新手）
```bash
python scripts/test_douyin_share_link.py --interactive
```

出现提示后，输入：
```
📍 请输入 UID (用户ID，如: 96874812426): 96874812426
📍 请输入 SEC_UID (如: MS4wLjABAAAA9y04iBlVdeMQqTJbqsQZKb...): MS4wLjABAAAA9y04iBlVdeMQqTJbqsQZKb-tqWqWW29jPVJqideHT70
```

#### 方式2: 从数据库获取
```bash
python scripts/test_douyin_share_link.py --from-db
```

### 第4步: 查看结果

脚本会：
1. ✓ 生成分享链接
2. 📱 在手机浏览器中打开链接
3. 🎯 点击进入抖音APP
4. ✅ 验证是否成功跳转到用户主页

## 📊 完整流程

```
手动输入或从数据库获取 uid + sec_uid
                    ↓
        调用API服务器生成分享链接
                    ↓
        使用uiautomator2进行手机自动化
                    ↓
        ├─ 打开浏览器
        ├─ 输入分享链接
        ├─ 点击打开
        ├─ 等待抖音APP启动
        └─ 验证是否进入用户主页
                    ↓
                  完成
```

## 🎮 命令参考

| 命令 | 说明 |
|------|------|
| `python scripts/test_douyin_share_link.py` | 默认交互模式 |
| `python scripts/test_douyin_share_link.py --interactive` | 手动输入uid和sec_uid |
| `python scripts/test_douyin_share_link.py --from-db` | 从数据库获取数据 |
| `python scripts/test_douyin_share_link.py --device "emulator-5554"` | 指定设备 |
| `python scripts/test_douyin_share_link.py --account-id 2` | 指定账号ID |

## 📝 输入参数说明

### UID (用户ID)
- **格式**: 纯数字
- **长度**: 通常10-20位
- **示例**: `96874812426`
- **来源**: 数据库Comment表的`comment_uid`字段

### SEC_UID (用户安全ID)
- **格式**: `MS4w` 开头 + Base64编码
- **长度**: 通常40-60字符
- **示例**: `MS4wLjABAAAA9y04iBlVdeMQqTJbqsQZKb-tqWqWW29jPVJqideHT70`
- **来源**: 数据库Comment表的`comment_sec_uid`字段

## ✨ 主要特性

✅ **自动化完整** - 覆盖从API到APP的全流程
✅ **智能重试** - 多个服务器自动切换
✅ **实时日志** - 清晰的执行步骤提示
✅ **灵活配置** - 支持多种输入方式
✅ **错误恢复** - 自动备选方案

## 🐛 常见问题

**Q: 脚本运行后卡住了？**
A: 可能在等待用户输入或手机反应。按Ctrl+C可中断。

**Q: 提示"未检测到Android设备"？**
A: 检查:
   - USB线是否插好
   - 手机USB调试是否打开
   - 驱动是否安装正确
   - 运行: `adb kill-server` 然后 `adb devices`

**Q: API返回空链接？**
A: 可能原因:
   - uid或sec_uid不正确
   - API服务器故障
   - 网络连接问题

  尝试:
   - 检查输入的uid和sec_uid是否正确
   - 检查网络连接
   - 手动访问 http://149.88.66.146:8008 测试服务器是否在线

**Q: 手机没有打开浏览器？**
A: 可能需要填充元素定位ID。详见 [DOUYIN_SHARE_LINK_TEST.md](./DOUYIN_SHARE_LINK_TEST.md)

## 📚 详细文档

完整的配置和调试指南请查看: [DOUYIN_SHARE_LINK_TEST.md](./DOUYIN_SHARE_LINK_TEST.md)

包含:
- 8个步骤的详细说明
- 元素定位ID的获取方法
- 常见问题排查
- 代码示例

## 🔧 扩展使用

### 批量测试多个用户

```python
from scripts.test_douyin_share_link import DouYinShareLinkTester

tester = DouYinShareLinkTester()

# 用户列表
users = [
    ('96874812426', 'MS4wLjABAAAA9y04iBlVdeMQqTJbqsQZKb-tqWqWW29jPVJqideHT70'),
    ('12345678901', 'MS4wLjABAAAA...'),
    # 更多用户
]

for uid, sec_uid in users:
    link = tester.generate_share_link(uid, sec_uid)
    if link:
        print(f"✓ {uid}: {link}")
    else:
        print(f"✗ {uid}: 生成失败")
```

### 集成到项目主程序

参考 [CLAUDE.md](../CLAUDE.md) 的"常见修改场景"部分，将此功能集成到main_menu.py

## 📞 反馈

遇到问题？记录这些信息会有帮助：
- 设备型号和Android版本
- 抖音APP版本
- 完整的错误日志
- 运行命令

---

**快速开始指南** | [详细文档](./DOUYIN_SHARE_LINK_TEST.md)
