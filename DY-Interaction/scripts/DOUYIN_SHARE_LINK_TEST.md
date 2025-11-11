# 抖音分享链接生成和唤起测试指南

## 📋 概述

这个脚本用于测试抖音分享链接的完整流程：

```
数据库查询 → API生成链接 → 手机浏览器打开 → 进入抖音APP → 用户主页
   ↓           ↓              ↓               ↓          ↓
Comment表  服务器API    uiautomator2   自动化点击   验证元素
```

## 🚀 快速开始

### 1. 交互式模式（手动输入uid和sec_uid）

```bash
# 基础运行
python scripts/test_douyin_share_link.py --interactive

# 指定设备ID
python scripts/test_douyin_share_link.py --interactive --device "emulator-5554"
```

### 2. 从数据库模式（自动获取）

```bash
# 从数据库获取数据
python scripts/test_douyin_share_link.py --from-db

# 从数据库获取，指定账号ID
python scripts/test_douyin_share_link.py --from-db --account-id 1
```

## 📊 脚本工作流程

### 阶段 1: 获取uid和sec_uid

**两种方式:**

#### 方式A: 手动输入

```
输入prompt → uid: 96874812426
输入prompt → sec_uid: MS4wLjABAAAA9y04iBlVdeMQqTJbqsQZKb-tqWqWW29jPVJqideHT70
```

#### 方式B: 从数据库获取

```python
# 查询Comment表
SELECT comment_uid, comment_sec_uid FROM comments
WHERE comment_uid IS NOT NULL AND comment_sec_uid IS NOT NULL
LIMIT 1
```

**数据库字段说明:**

| 字段 | 含义 | 示例 |
|------|------|------|
| `comment_uid` | 用户数字ID | `96874812426` |
| `comment_sec_uid` | 用户安全ID（固定格式） | `MS4wLjAB...` |
| `comment_unique_id` | 抖音号（@xxx） | `username123` |
| `comment_user_name` | 显示的用户名 | `用户名显示` |

### 阶段 2: 调用API生成分享链接

**API端点:**
```
GET /api/v1/douyin/user/share_link?uid={uid}&sec_uid={sec_uid}
```

**请求参数:**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| uid | string | ✅ | 用户ID（数字形式） |
| sec_uid | string | ✅ | 用户SEC_UID（MS4w开头） |

**响应示例:**
```json
{
  "code": 200,
  "message": "Request successful",
  "data": "https://v.douyin.com/xxxxxxxxxxxx/",
  "cache_url": "https://cache.api.com/xxxx"
}
```

**服务器优先级:**

脚本会按优先级尝试以下服务器：

| 优先级 | 服务器 | 地址 | 备注 |
|--------|--------|------|------|
| 1 | 主力服务器1 | http://149.88.66.146:8008 | 主要 |
| 2 | 主力服务器2 | http://140.245.55.143:8008 | 主要 |
| 3 | 主力服务3 | http://140.245.55.143:20002 | 主要 |
| 4 | 备用服务器 | http://38.55.134.72:8008 | 备用 |
| - | 终极备用 | https://api.tikhub.dev | 最后选择 |

### 阶段 3: 在手机浏览器中打开链接

这部分需要使用 `uiautomator2` 进行手机自动化操作。

**当前状态:** 🔶 **框架已完成，需要填充元素定位ID**

## 🔧 配置和准备

### 前置要求

1. **Android设备/模拟器**
   ```bash
   # 检查设备连接
   adb devices
   ```

2. **Python依赖**
   ```bash
   pip install uiautomator2 requests
   ```

3. **设备USB调试**
   - 设置 → 开发者选项 → USB调试（打开）

4. **数据库配置**
   - 确保项目的 `config/config.json` 包含API服务器信息
   - 或者设置环境变量

### 安装依赖

```bash
# 如果还未安装uiautomator2
pip install uiautomator2

# 初始化设备（仅需一次）
python -m uiautomator2 init
```

## 🎯 逐步填充元素定位ID

现在脚本框架已完成，这8个步骤需要在实际测试中逐个填充元素定位ID。

### 步骤 1: 打开浏览器应用

**当前代码:**
```python
self.device.app_start('com.android.chrome')
time.sleep(2)
```

**说明:**
- 启动Chrome浏览器（包名: `com.android.chrome`）
- 如果要用其他浏览器，可改包名：
  - 小米浏览器: `com.android.browser`
  - 火狐: `org.mozilla.firefox`
  - UC浏览器: `com.uc.browser`

**测试命令:**
```bash
# 获取当前打开的APP
device.app_current()
```

### 步骤 2: 点击地址栏

**日志中提示的可能ID:**
```
- com.android.chrome:id/url_bar
- com.android.chrome:id/location_bar
- android.widget.EditText
```

**获取准确ID的方法:**

**方法1: 使用dump_hierarchy()**
```python
import uiautomator2 as u2

device = u2.connect()

# 打开Chrome
device.app_start('com.android.chrome')
time.sleep(2)

# 获取页面层级
device.dump_hierarchy()  # 保存到当前目录的hierarchy.xml

# 查看地址栏元素
# 在hierarchy.xml中搜索 "url" 或 "address"
```

**方法2: 使用UI Inspector**
```python
# 实时查看元素属性
device.screen()  # 截图
device.selector().child(text="xxx")  # 选择器方式
```

**方法3: 使用uiautomator app（推荐）**
```bash
# 安装UI自动化测试工具
adb install -r uiautomator.apk

# 或使用Python脚本启动
python -m uiautomator2 weditor
```

**填充代码示例:**
```python
# 方式A: 使用resource id
address_bar = self.device(resourceId="com.android.chrome:id/url_bar")
if address_bar.exists:
    address_bar.click()
    time.sleep(1)
else:
    # 备选方案：点击屏幕上方（通常是地址栏位置）
    self.device.click(0.5, 0.08)  # (x, y) 屏幕坐标，0-1范围
    time.sleep(1)

# 方式B: 使用className
address_bar = self.device(className="android.widget.EditText")
if address_bar.exists:
    address_bar.click()

# 方式C: 使用text
address_bar = self.device(text="Search or type web address")
if address_bar.exists:
    address_bar.click()
```

### 步骤 3: 输入分享链接

**日志中提示:**
```
需要键盘和文本输入配置
```

**填充代码示例:**
```python
# 方式A: 使用device.send_keys()
self.device.send_keys(share_link)
time.sleep(1)

# 方式B: 使用click() + 粘贴板
import subprocess
# 把链接复制到剪贴板
subprocess.run(['adb', 'shell', 'echo', share_link, '|', 'xclip'],
               capture_output=True)
# 粘贴
self.device.press('ctrl', 'v')
time.sleep(1)

# 方式C: 使用set_text()
address_bar.set_text(share_link)
time.sleep(1)
```

### 步骤 4: 点击打开/确定按钮

**日志中提示的可能ID:**
```
- android.widget.Button
- 回车键 (Enter key)
```

**填充代码示例:**
```python
# 方式A: 按回车键（最简单）
self.device.press('enter')
time.sleep(3)  # 等待页面加载

# 方式B: 查找并点击按钮
open_btn = self.device(text="打开")
if open_btn.exists:
    open_btn.click()
    time.sleep(3)

# 方式C: 点击特定位置
self.device.click(0.9, 0.08)  # 右侧（搜索/打开按钮位置）
time.sleep(3)
```

### 步骤 5: 等待页面加载

**说明:** 网页加载需要时间，通常2-3秒

**可改进的代码:**
```python
# 等待页面加载完成
timeout = 10
for i in range(timeout):
    # 检查是否有"打开抖音"按钮出现（标志页面加载完成）
    if self.device(text="打开抖音").exists:
        logger.info(f"✓ 页面加载完成 ({i+1}秒)")
        break
    time.sleep(1)
else:
    logger.warning(f"⚠️  {timeout}秒后页面仍未加载完成")
```

### 步骤 6: 检查并点击"打开抖音"按钮

**日志中提示的可能ID:**
```
- android.widget.Button (包含'打开')
- android.widget.TextView (包含'抖音')
- com.android.chrome:id/xxx
```

**填充代码示例:**
```python
# 方式A: 精确查找（推荐）
open_douyin_btn = self.device(text="打开抖音")
if open_douyin_btn.exists:
    logger.info(f"✓ 找到'打开抖音'按钮，点击中...")
    open_douyin_btn.click()
    time.sleep(2)
else:
    logger.warning(f"⚠️  未找到'打开抖音'按钮")
    # 备选方案：模糊匹配
    open_btn = self.device(text__contains="打开")
    if open_btn.exists:
        open_btn.click()
        time.sleep(2)

# 方式B: 使用xpath
self.device.xpath('//android.widget.Button[@text="打开抖音"]').click()

# 方式C: 按钮通常在页面中央
self.device.click(0.5, 0.5)
time.sleep(2)
```

### 步骤 7: 验证是否进入抖音APP

**日志中提示:**
```
需要验证APP启动的方式
```

**填充代码示例:**
```python
# 方式A: 检查APP包名（推荐）
max_wait = 10
douyin_packages = [
    'com.ss.android.ugc.aweme',  # 国内抖音
    'com.bytedance.android.tiktok',  # TikTok
    'com.bytedance.android.ema'   # 火山小视频
]

for i in range(max_wait):
    current_app = self.device.app_current()
    if any(pkg in current_app['package'] for pkg in douyin_packages):
        logger.info(f"✓ 抖音APP已启动: {current_app['package']}")
        return True
    time.sleep(1)

logger.warning(f"⚠️  {max_wait}秒后仍未检测到抖音APP")

# 方式B: 等待窗口变化
activity_changed = self.device.wait_activity(timeout=10)
if activity_changed:
    logger.info(f"✓ APP已启动")
```

### 步骤 8: 验证是否成功跳转到用户主页

**日志中提示的可能特征:**
```
- 用户头像元素
- 用户名称显示
- 关注按钮
- 用户视频列表
```

**获取用户主页元素ID的方法:**

首先在用户主页打开UI层级查看：

```bash
# 连接设备并进入抖音用户主页
adb shell am start -a android.intent.action.VIEW -d "douyin://user/xxx"

# 然后执行
python -m uiautomator2 weditor
```

**常见的用户主页特征元素:**

| 元素 | 可能的ID | 说明 |
|------|---------|------|
| 用户头像 | `com.ss.android.ugc.aweme:id/j49` | 圆形头像 |
| 用户名 | `com.ss.android.ugc.aweme:id/xxx` | 显示用户昵称 |
| 关注按钮 | `com.ss.android.ugc.aweme:id/follow_btn` | 按钮文本为"关注" |
| 视频列表 | `android.widget.FrameLayout` | 包含用户视频 |
| 返回按钮 | `com.ss.android.ugc.aweme:id/back_btn` | 左上角返回 |

**填充代码示例:**
```python
# 方式A: 检查用户头像（最可靠）
try:
    avatar = self.device(resourceId="com.ss.android.ugc.aweme:id/j49")
    if avatar.exists:
        logger.info(f"✓ 成功进入用户主页")
        return True
except:
    pass

# 方式B: 检查关注按钮状态
follow_btn = self.device(text="关注")
if follow_btn.exists:
    logger.info(f"✓ 未关注，说明进入了用户主页")
    return True

# 方式C: 检查用户名显示
username_view = self.device(resourceId="com.ss.android.ugc.aweme:id/nickname")
if username_view.exists:
    username = username_view.get_text()
    logger.info(f"✓ 进入用户主页: {username}")
    return True

# 方式D: 使用activity名称
current_activity = self.device.app_current()
if 'douyin' in current_activity['package'] and \
   ('user' in current_activity['activity'] or 'profile' in current_activity['activity']):
    logger.info(f"✓ 已进入用户主页")
    return True

logger.warning(f"⚠️  未检测到用户主页特征")
return False
```

## 📝 测试流程总结

### 完整测试步骤

1. **准备阶段**
   ```bash
   # 连接设备
   adb devices

   # 安装依赖
   pip install uiautomator2
   ```

2. **运行脚本**
   ```bash
   # 交互模式
   python scripts/test_douyin_share_link.py --interactive

   # 或从数据库
   python scripts/test_douyin_share_link.py --from-db
   ```

3. **输入参数**
   ```
   输入UID: 96874812426
   输入SEC_UID: MS4wLjABAAAA9y04iBlVdeMQqTJbqsQZKb-tqWqWW29jPVJqideHT70
   ```

4. **查看API响应**
   ```
   ✓ 成功生成分享链接:
     https://v.douyin.com/xxxxxxxxx/
   ```

5. **点击继续**
   ```
   按Enter键继续在浏览器中打开链接...
   ```

6. **自动化执行**
   ```
   [步骤 1/8] 打开浏览器应用 ✓
   [步骤 2/8] 点击地址栏 🔶 (待填充ID)
   [步骤 3/8] 输入分享链接 🔶 (待填充ID)
   ...
   ```

### 输出日志示例

```
==================== 抖音分享链接测试 ===================

[11:22:33] ✓ 分享链接测试器已初始化，设备: emulator-5554
[11:22:34] ✓ 自动检测到设备: emulator-5554
[11:22:35] ✓ 已连接到设备: emulator-5554

[11:22:36] ✓ 从数据库获取评论数据:
            - 用户名: 用户名显示
            - UID: 96874812426
            - SEC_UID: MS4wLjABAAAA9y04iBlVdeMQqTJbqsQZKb-tqWqWW29jPVJqideHT70
            - 抖音号: username123

[11:22:37] 📡 尝试服务器 (优先级1): http://149.88.66.146:8008
[11:22:39] ✓ 成功生成分享链接 (服务器1):
            https://v.douyin.com/xxxxxxxxx/

[11:22:40] =====================================================
            下一步: 在手机浏览器中打开分享链接
            =====================================================

[11:22:50] [步骤 1/8] 打开浏览器应用 ✓
[11:22:52] [步骤 2/8] 点击地址栏 🔶 [待完成]
[11:22:53] [步骤 3/8] 输入分享链接 🔶 [待完成]
...

========================================
📱 自动化流程框架已准备完成
========================================
✓ 所有步骤均已定义
✓ 请在实际测试中填充各步骤的元素定位ID
✓ 建议使用 uiautomator2 的dump()方法获取控件ID
========================================

✅ 测试完成
```

## 🔍 调试技巧

### 获取UI层级

```python
import uiautomator2 as u2

device = u2.connect()

# 保存页面层级到XML
device.dump_hierarchy()  # 生成hierarchy.xml

# 或者导出为JSON
import json
hierarchy = device.dump_hierarchy()
print(json.dumps(hierarchy, indent=2))
```

### 实时查看页面

```bash
# 启动UI Inspector（推荐）
python -m uiautomator2 weditor

# 或使用官方工具
adb shell uiautomator dump /sdcard/layout.xml
adb pull /sdcard/layout.xml
```

### 截图和分析

```python
# 截图
device.screenshot('screenshot.png')

# 查找元素
element = device.xpath('//android.widget.Button[@text="打开"]')
print(element.get_text())
print(element.center())  # 获取中心坐标
```

### 常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|--------|
| 找不到元素 | ID可能不对 | 使用dump_hierarchy()确认ID |
| 点击无反应 | 元素可能被覆盖 | 使用screenshot()查看实际情况 |
| APP未启动 | 包名不对 | 使用app_current()确认包名 |
| 超时 | 网络慢或加载失败 | 增加sleep时间或检查网络 |

## 📚 相关文档

- [uiautomator2文档](https://github.com/openatomi/uiautomator2)
- [CLAUDE.md](../CLAUDE.md) - 项目配置指南
- [interaction_executor.py](../src/executor/interaction_executor.py) - 现有自动化代码参考
- [douyin_operations.py](../src/executor/douyin_operations.py) - 抖音APP操作示例

## 💡 下一步计划

✅ 阶段1: 脚本框架完成
⏳ 阶段2: 填充元素定位ID（在实际测试中）
⏳ 阶段3: 验证完整流程
⏳ 阶段4: 集成到项目主程序

## 📞 反馈和改进

如果在测试中遇到问题，请记录：
1. 设备型号和Android版本
2. 抖音APP版本
3. 浏览器版本
4. 具体错误日志
5. UI层级结构（hierarchy.xml）

---

**创建日期**: 2025-11-11
**脚本位置**: `scripts/test_douyin_share_link.py`
**状态**: 🟡 **框架完成，待元素定位ID填充**
