# 🎯 抖音分享链接生成和唤起 - 完整项目说明

## 📌 项目概述

本项目实现了一个完整的**抖音分享链接生成和自动唤起流程**，包括：

1. ✅ **数据库集成** - 从Comment表获取comment_uid和comment_sec_uid
2. ✅ **API调用** - 生成抖音分享链接（使用备用服务器）
3. ✅ **手机自动化** - 通过uiautomator2控制Android设备
4. ✅ **浏览器操作** - 打开链接并进入抖音APP
5. ✅ **验证流程** - 确认成功跳转到用户主页

## 📂 文件结构

```
scripts/
├── test_douyin_share_link.py       ⭐ 主测试脚本
├── QUICK_DOUYIN_TEST.md             📖 快速开始指南
├── DOUYIN_SHARE_LINK_TEST.md        📚 详细文档
├── get_ui_elements.py               🔧 UI元素定位工具
└── README_DOUYIN_TEST.md            📋 本文件
```

## 🚀 使用流程

### 快速开始（3步）

```bash
# 1. 安装依赖
pip install uiautomator2 requests

# 2. 连接设备
adb devices

# 3. 运行脚本
python scripts/test_douyin_share_link.py --interactive
```

### 详细流程

```
┌─────────────────────────────────────────────────────────┐
│                    输入/获取数据                         │
├─────────────────────────────────────────────────────────┤
│ 方式1: 手动输入 uid + sec_uid                           │
│ 方式2: 从数据库自动查询 Comment表                      │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│                   调用API生成链接                        │
├─────────────────────────────────────────────────────────┤
│ GET /api/v1/douyin/user/share_link?uid=xxx&sec_uid=yyy │
│                                                         │
│ 服务器优先级:                                           │
│ 1. http://149.88.66.146:8008                            │
│ 2. http://140.245.55.143:8008                           │
│ 3. http://140.245.55.143:20002                          │
│ 4. http://38.55.134.72:8008                             │
│ 5. https://api.tikhub.dev (终极备用)                   │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│               在手机中打开分享链接                       │
├─────────────────────────────────────────────────────────┤
│ 步骤1: 打开浏览器 (Chrome)                              │
│ 步骤2: 点击地址栏                                       │
│ 步骤3: 输入分享链接                                     │
│ 步骤4: 点击打开/确定                                    │
│ 步骤5: 等待页面加载                                     │
│ 步骤6: 点击"打开抖音"按钮                               │
│ 步骤7: 等待抖音APP启动                                  │
│ 步骤8: 验证进入用户主页                                 │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│                     任务完成 ✅                          │
└─────────────────────────────────────────────────────────┘
```

## 🔧 各个文件说明

### 1. test_douyin_share_link.py （主脚本）

**功能**: 完整的测试脚本，包含所有逻辑

**类**: `DouYinShareLinkTester`
```python
tester = DouYinShareLinkTester(device_id="emulator-5554")

# 方法1: 从数据库获取
comment_data = tester.get_comment_from_db(target_account_id=1)

# 方法2: 生成链接
share_link = tester.generate_share_link(uid, sec_uid)

# 方法3: 打开链接（手机自动化）
tester.open_link_in_browser(share_link)
```

**运行命令**:
```bash
# 交互模式
python scripts/test_douyin_share_link.py --interactive

# 从数据库模式
python scripts/test_douyin_share_link.py --from-db

# 指定设备
python scripts/test_douyin_share_link.py --device "emulator-5554"
```

**状态**: 🟡 **框架完成，步骤2-8需要填充元素定位ID**

### 2. get_ui_elements.py （UI定位工具）

**功能**: 帮助快速获取Android UI控件的ID

**使用方法**:

**交互模式** (推荐):
```bash
python scripts/get_ui_elements.py
```

**命令行模式**:
```bash
# 导出页面层级（保存为JSON）
python scripts/get_ui_elements.py --dump

# 根据文本查找
python scripts/get_ui_elements.py --find-text "打开"

# 根据ID查找
python scripts/get_ui_elements.py --find-id "com.android.chrome:id/url_bar"

# 列出所有可点击元素
python scripts/get_ui_elements.py --clickable

# 截图
python scripts/get_ui_elements.py --screenshot
```

**输出示例**:
```
✓ 找到 3 个匹配元素:

  ├─ 文本: 打开抖音
  ├─ 类型: android.widget.Button
  ├─ ID: com.android.chrome:id/open_btn
  ├─ 描述: 打开抖音应用
  ├─ 位置: (540, 200)
  └─ 边界: {'left': 480, 'top': 180, 'right': 600, 'bottom': 220}
```

### 3. QUICK_DOUYIN_TEST.md （快速开始）

- 📖 5分钟上手指南
- 🎮 命令参考
- 📝 参数说明
- 🐛 常见问题

**何时阅读**: 首次使用时

### 4. DOUYIN_SHARE_LINK_TEST.md （详细文档）

- 📊 完整工作流程
- 🔧 8个步骤的详细说明
- 📍 元素定位ID的获取方法
- 💡 代码示例
- 🔍 调试技巧

**何时阅读**: 需要填充元素ID时

## 📊 数据库字段映射

| 数据库字段 | 数据类型 | API参数 | 说明 |
|----------|---------|--------|------|
| `comment_uid` | String | `uid` | 用户数字ID（纯数字） |
| `comment_sec_uid` | String | `sec_uid` | 用户安全ID（MS4w开头） |
| `comment_unique_id` | String | - | 抖音号（@xxx） |
| `comment_user_name` | String | - | 显示的用户名 |

**查询示例**:
```sql
SELECT comment_uid, comment_sec_uid, comment_unique_id, comment_user_name
FROM comments
WHERE comment_uid IS NOT NULL AND comment_sec_uid IS NOT NULL
LIMIT 1
```

## 🔑 API参数说明

**API端点**:
```
GET /api/v1/douyin/user/share_link
```

**请求参数**:
- `uid` ✅ 必需 - 用户ID（数字形式，如：96874812426）
- `sec_uid` ✅ 必需 - 用户SEC_UID（MS4w开头，如：MS4wLjAB...）

**响应示例**:
```json
{
  "code": 200,
  "message": "Request successful",
  "data": "https://v.douyin.com/xxxxxxxxx/",
  "cache_url": "https://cache.api.com/xxxxx"
}
```

## 🎯 后续集成步骤

### 短期（完成框架）✅
- ✅ 数据库集成
- ✅ API调用逻辑
- ✅ 手机自动化框架
- ✅ 详细文档

### 中期（填充元素ID）⏳
- ⏳ 获取Chrome浏览器元素ID
- ⏳ 获取抖音APP元素ID
- ⏳ 测试各个步骤的自动化操作
- ⏳ 调试和优化

### 长期（集成主程序）⏳
- ⏳ 添加到 main_menu.py
- ⏳ 实现批量处理
- ⏳ 添加定时任务
- ⏳ 性能优化

## 📱 设备要求

- Android系统手机或模拟器
- USB调试已开启
- 已安装Chrome浏览器
- 已安装抖音APP

## 📦 依赖

```
uiautomator2>=2.0.0      # 手机自动化
requests>=2.20.0         # HTTP请求
python-dotenv>=0.19.0    # 环境变量（可选）
```

## 🐛 故障排查

| 问题 | 解决方案 | 详见 |
|------|--------|------|
| 找不到Android设备 | 检查USB调试、驱动 | QUICK_DOUYIN_TEST.md |
| 元素不存在 | 使用get_ui_elements.py查找 | DOUYIN_SHARE_LINK_TEST.md |
| API返回空链接 | 检查uid和sec_uid | QUICK_DOUYIN_TEST.md |
| 手机没反应 | 填充元素ID代码 | DOUYIN_SHARE_LINK_TEST.md |

## 💡 开发建议

### 验证链接是否有效
```bash
# 在浏览器中手动测试分享链接
https://v.douyin.com/xxxxxxxxx/
```

### 在真实设备上测试
- 模拟器可能无法打开抖音
- 建议在真实Android手机上测试
- 确保手机能访问互联网

### 调试自动化步骤
```bash
# 用get_ui_elements.py逐步查找元素
# 1. 打开要操作的界面
# 2. 运行查找工具
# 3. 记录返回的元素ID
# 4. 在test_douyin_share_link.py中填充代码
```

## 📚 相关文档

- [CLAUDE.md](../CLAUDE.md) - 项目规范和指导
- [interaction_executor.py](../src/executor/interaction_executor.py) - 现有自动化代码参考
- [douyin_operations.py](../src/executor/douyin_operations.py) - 抖音操作示例

## 🔗 项目地址

分支: `claude/cleanup-unused-files-011CV1eNmG6YYM79aVwTh5T3`

## ✅ 检查清单

启动前请确认：
- [ ] 已安装uiautomator2: `pip install uiautomator2`
- [ ] Android设备已连接: `adb devices`
- [ ] 设备已开启USB调试
- [ ] 设备已安装Chrome浏览器
- [ ] 设备已安装抖音APP

## 📞 需要帮助？

1. 查看 [QUICK_DOUYIN_TEST.md](./QUICK_DOUYIN_TEST.md) 的常见问题
2. 查看 [DOUYIN_SHARE_LINK_TEST.md](./DOUYIN_SHARE_LINK_TEST.md) 的调试技巧
3. 使用 `get_ui_elements.py` 诊断UI问题

---

**创建日期**: 2025-11-11  
**状态**: 🟡 **框架完成，待元素ID填充**  
**下一步**: 在实际测试中获取Android UI元素ID，填充步骤2-8的代码
