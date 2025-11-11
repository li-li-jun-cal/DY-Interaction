# CLAUDE.md - DY-Interaction 项目配置

> **重要**: Claude Code 将优先遵守本文档中的指引，优于一般的用户提示。
> 本文档定义了项目的文件结构、工作流和编码标准。

---

## 📋 1. 项目概览

### 项目信息
```
项目名称: DY-Interaction
项目类型: 抖音(Douyin)自动化交互框架
Python 版本: 3.8+
核心功能: 多设备并行执行，优先级任务调度，爬虫，自动化交互
主要依赖: SQLAlchemy, requests, Appium (设备自动化)
```

### 项目目的
DY-Interaction 是一个用于自动化管理抖音视频评论交互的框架。支持历史数据爬取、实时评论监控、多账号自动化操作（关注、点赞、评论、收藏），以及每日配额管理和任务优先级调度。

### 文档索引
- 📄 **CODE_ANALYSIS.md** - 完整的代码结构和文件关系分析
- 📄 **.claude/instructions.md** - 项目快速参考
- 📄 **CLAUDE_TEMPLATE.md** - Python 项目通用模板
- 📄 **REVIEW_SUMMARY.txt** - 代码质量评分
- 📄 **SECURITY_ISSUES.txt** - 安全问题分析

---

## 🎯 2. 核心工作流

### 项目的核心执行流程

```
用户 (main_menu.py)
  │
  ├─【爬虫模块】
  │  ├─ run_history_crawler.py → HistoryCrawler → API Client → DB
  │  └─ run_monitor_crawler.py → MonitorCrawler → API Client → DB
  │
  ├─【自动化模块】
  │  ├─ run_priority_automation.py → TaskScheduler → Executor → Devices
  │  └─ run_long_term_automation.py → TaskScheduler → Executor → Devices
  │
  ├─【数据管理】
  │  └─ scripts/* → 数据修复、配置更新、设备管理
  │
  └─【核心数据库】
     └─ src/database/manager.py ← 所有模块都依赖
```

### 关键数据流
```
评论数据
  ↓ (爬虫)
Database (InteractionTask, NewComment, Comment 表)
  ↓ (任务生成)
待执行任务队列
  ↓ (优先级调度)
多设备并行执行
  ↓ (结果反馈)
更新任务状态 → 统计数据
```

### 模块依赖关系
```
最高层: main_menu.py, programs/*
   ↓
程序层: run_*.py (4个)
   ↓
执行层: src/executor/*, src/scheduler/*
   ↓
数据层: src/database/* (核心, 43+ 导入)
   ↓
工具层: src/utils/*, src/config/*
```

---

## 📁 3. 文件结构与边界

### 核心文件映射

```
D:\Users\zk\Desktop\DY-Interaction\
│
├── 🔴 【严格禁区 - 改动时需特别小心】
│   ├── src/database/manager.py (43+ 导入，核心中的核心)
│   ├── src/database/models.py (38+ 导入，数据模型)
│   ├── src/executor/douyin_operations.py (1,639 行，API 操作)
│   └── src/scheduler/task_scheduler.py (任务调度器)
│
├── 🟡 【谨慎修改 - 可能影响其他模块】
│   ├── src/executor/automation_executor.py (4+ 导入)
│   ├── src/executor/device_coordinator.py (多设备协调)
│   ├── src/crawler/api_client.py (4+ 导入)
│   └── src/utils/device_manager.py (3+ 导入)
│
├── 🟢 【可安全修改 - 影响范围小】
│   ├── programs/*.py (4个在用程序)
│   ├── scripts/*.py (8个在用脚本)
│   ├── main_menu.py (菜单入口)
│   └── config/ (配置文件)
│
└── ⚪ 【可删除的文件】
    ├── programs/ (8个未使用的程序)
    ├── scripts/ (16+个未使用的脚本)
    └── scripts/archive/ (已弃用脚本)
```

### 文件修改规则

#### ✅ 允许的修改
- 在 `main_menu.py` 中添加新菜单选项
- 创建新的 `programs/*.py` (依赖已有的 src 模块)
- 修改 `programs/` 和 `scripts/` 中的文件
- 添加新的 `src/` 模块 (不修改现有模块的接口)
- 修改 `config/` 配置文件

#### ⚠️ 需要谨慎的修改
- 修改 `src/database/models.py` - 需要数据库迁移脚本
- 修改 `src/database/manager.py` - 影响所有模块，需充分测试
- 修改 `src/executor/automation_executor.py` 接口 - 需更新所有调用处
- 修改 `src/scheduler/task_scheduler.py` - 影响任务调度逻辑

#### ❌ 禁止的修改
- 删除现有的 `src/` 模块 (仅标记为弃用)
- 直接修改数据库结构 (应创建迁移脚本)
- 在代码中硬编码 API 密钥或敏感信息
- 忽略异常或没有日志记录

### 不应直接编辑的文件

这些文件需要告诉我，由我来处理：

```
❌ .gitignore - 应告诉我需要忽略的文件
❌ requirements.txt - 应告诉我需要添加/删除的依赖
❌ .gitattributes - 版本控制配置
❌ LICENSE - 许可证
❌ .env - 环境变量 (应在 .gitignore 中)
```

---

## 🔧 4. 开发命令

### 环境设置
```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 运行程序

#### 完整菜单式运行 (推荐)
```bash
python main_menu.py
```

#### 直接运行特定程序
```bash
# 全量爬虫 (菜单选项1)
python programs/run_history_crawler.py

# 监控爬虫 (菜单选项2)
python programs/run_monitor_crawler.py

# 实时自动化 (菜单选项3)
python programs/run_priority_automation.py --mode realtime

# 近期自动化 (菜单选项4)
python programs/run_priority_automation.py --mode recent

# 长期自动化 (菜单选项5)
python programs/run_long_term_automation.py --auto

# 混合自动化 (菜单选项6)
python programs/run_priority_automation.py --mode mixed
```

#### 运行脚本
```bash
# 清理重复任务
python scripts/cleanup_duplicate_tasks.py --auto

# 更新Cookie
python scripts/update_server_cookie.py
python scripts/update_cookie_pool.py

# 检查设备
python scripts/check_devices.py

# 管理API服务器
python scripts/manage_api_servers.py

# 生成任务
python scripts/generate_tasks_from_comments.py --auto

# 删除缺陷任务
python scripts/delete_tasks_without_unique_id.py --auto
```

### 调试和日志
```bash
# 启用详细日志
LOGLEVEL=DEBUG python programs/run_priority_automation.py

# 查看执行日志
tail -f logs/*.log

# 查看数据库状态
# 使用 SQLite 浏览器打开 data/dy_interaction.db
```

### 测试 (当前覆盖率低)
```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_xxx.py -v

# 生成覆盖率报告
pytest --cov=src tests/
```

---

## 📝 5. 编码标准

### Python 代码风格

**遵循**: PEP 8 + 项目约定

```python
# ✅ 推荐的样式
def process_interaction_task(task_id: int, device_id: str) -> bool:
    """处理单个交互任务。

    Args:
        task_id: 任务ID
        device_id: 执行设备ID

    Returns:
        是否处理成功

    Raises:
        DatabaseError: 数据库操作失败
        DeviceNotFound: 设备不存在
    """
    try:
        task = session.query(InteractionTask).filter_by(id=task_id).first()
        if not task:
            logger.warning(f"Task {task_id} not found")
            return False

        # 执行操作
        result = device.execute_interaction(task)
        return result

    except Exception as e:
        logger.error(f"Failed to process task {task_id}: {e}")
        raise
```

### 导入顺序
```python
# 标准库
import os
import sys
from pathlib import Path
from datetime import datetime

# 第三方库
import requests
from sqlalchemy import create_engine

# 项目内导入
from src.database.manager import DatabaseManager
from src.database.models import InteractionTask
from src.utils.logger import get_logger
```

### 类型提示
```python
from typing import List, Dict, Optional, Tuple

def get_pending_tasks(user_id: int, limit: Optional[int] = None) -> List[InteractionTask]:
    """获取待处理任务列表。"""
    pass

def extract_user_info(comment: Dict[str, any]) -> Tuple[str, str]:
    """从评论提取用户信息。"""
    pass
```

### 日志记录标准
```python
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 日志级别使用
logger.debug("详细的调试信息")           # 开发调试
logger.info("重要的业务事件")            # 正常操作
logger.warning("警告，可能有问题")       # 可恢复的错误
logger.error("错误，需要手动介入")       # 严重错误
```

### 异常处理
```python
# ✅ 正确的异常处理
try:
    result = api_client.fetch_comments(video_id)
except requests.Timeout:
    logger.error(f"API timeout for video {video_id}")
    # 处理超时
except requests.RequestException as e:
    logger.error(f"API request failed: {e}")
    # 处理请求错误
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise  # 重新抛出未预期的异常

# ❌ 错误的异常处理
try:
    result = api_client.fetch_comments(video_id)
except:  # ❌ 不要用裸 except
    pass   # ❌ 不要吃掉异常
```

### 数据库操作标准
```python
# ✅ 正确的 ORM 使用
from src.database.manager import DatabaseManager

db = DatabaseManager()
with db.get_session() as session:
    tasks = session.query(InteractionTask).filter(
        InteractionTask.status == 'pending'
    ).limit(10).all()

    for task in tasks:
        task.status = 'assigned'

    session.commit()

# ❌ 错误的用法
# - 不要在循环中创建多个会话
# - 不要忘记 commit
# - 不要在会话外访问关联对象
```

---

## ⚙️ 6. 项目特定指引

### 关键文件速查表

| 文件/模块 | 用途 | 行数 | 导入次数 | 修改风险 |
|----------|------|------|---------|---------|
| `main_menu.py` | 菜单入口 | 708 | - | 🟢 低 |
| `src/database/manager.py` | 数据库管理 | 580 | 43+ | 🔴 高 |
| `src/database/models.py` | 数据模型 | 389 | 38+ | 🔴 高 |
| `src/executor/douyin_operations.py` | 抖音API | 1,639 | 2+ | 🔴 高 |
| `src/scheduler/task_scheduler.py` | 任务调度 | 285 | 7+ | 🟡 中 |
| `src/executor/automation_executor.py` | 执行引擎 | 487 | 4+ | 🟡 中 |
| `src/crawler/api_client.py` | API客户端 | 514 | 4+ | 🟡 中 |
| `programs/run_priority_automation.py` | 优先级自动化 | 538 | - | 🟢 低 |
| `programs/run_history_crawler.py` | 全量爬虫 | 277 | - | 🟢 低 |
| `programs/run_monitor_crawler.py` | 监控爬虫 | 248 | - | 🟢 低 |

### 常见修改场景

#### 场景 1: 添加新菜单功能
```
修改: main_menu.py
  ├─ show_menu() - 添加菜单文本
  ├─ main() - 添加 elif 处理
  └─ 新建函数 - 实现菜单功能

可能还需:
  ├─ 创建 programs/run_xxx.py (如果是新的自动化)
  └─ 创建 scripts/xxx.py (如果是工具脚本)
```

#### 场景 2: 修改爬虫逻辑
```
修改: src/crawler/monitor_crawler.py 或 src/crawler/history_crawler.py
  └─ 修改爬虫算法

可能还需:
  ├─ src/crawler/api_client.py - 如果改 API 调用
  ├─ src/generator/task_generator.py - 如果改任务生成
  └─ 测试修改
```

#### 场景 3: 修改自动化执行逻辑
```
修改: src/executor/automation_executor.py
  └─ 修改执行流程

可能还需:
  ├─ src/executor/douyin_operations.py - 如果改抖音操作
  ├─ src/scheduler/task_scheduler.py - 如果改调度逻辑
  └─ 数据库日志记录
```

#### 场景 4: 修改数据模型
```
修改: src/database/models.py
  ├─ 添加新字段或表
  └─ 修改关联关系

必须做:
  ├─ 创建 scripts/migrate_xxx.py 迁移脚本
  ├─ 备份现有数据库
  ├─ 运行迁移脚本
  └─ 测试

❌ 禁止直接 DROP 或修改现有字段
```

### 已知的代码问题

#### 🔴 Critical Issues

| 问题 | 位置 | 影响 | 修复建议 |
|------|------|------|---------|
| 会话泄漏 | `src/database/manager.py` | 内存泄漏 | 使用连接池 |
| 硬编码密钥 | `config/*.json` | 安全风险 | 使用环境变量 |
| 竞态条件 | `src/executor/device_coordinator.py` | 多设备冲突 | 使用线程锁 |
| 代码过大 | `src/executor/douyin_operations.py` (1,639 行) | 维护困难 | 拆分为子模块 |

#### 🟡 Medium Issues
- 没有 API 限流 (可能被 IP 封禁)
- 没有输入验证 (可能 SQL 注入)
- 低测试覆盖率 (仅 3 个测试文件)
- 缺少错误恢复机制

#### 🟢 Low Priority
- 日志文件未加入 .gitignore
- 配置文件组织可优化
- 文档不完整

### 敏感信息处理规则

#### ✅ 正确做法
```python
# 使用环境变量
import os
API_KEY = os.getenv('DOUYIN_API_KEY')
if not API_KEY:
    raise ValueError("DOUYIN_API_KEY not set in environment")

# 使用配置类
class Config:
    API_KEY = os.getenv('API_KEY')
    DEBUG = os.getenv('DEBUG', 'False') == 'True'

# 读取加密的配置文件
from cryptography.fernet import Fernet
cipher = Fernet(os.getenv('ENCRYPTION_KEY'))
```

#### ❌ 错误做法
```python
# ❌ 硬编码在代码中
API_KEY = "sk-xxxxxxxxxxxxx"
PASSWORD = "admin123"

# ❌ 存储在配置文件中但不加密
config_json = {"api_key": "sk-xxxxx"}

# ❌ 存储在 git 历史中
git log --all --full-history -- config.json
```

#### 文件安全政策
```
✅ 加入 .gitignore:
  - config/.env
  - config/secrets.json
  - config/*_key.txt
  - logs/
  - *.log
  - data/*.db.backup

❌ 不能提交:
  - API 密钥
  - 数据库密码
  - 账户凭证
  - 用户隐私数据
```

---

## 🚀 7. 常见任务与工作流

### 任务 1: 添加新的自动化模式

```
步骤:
1. 确定新模式的特性 (时间范围、优先级等)
2. 在 src/config/daily_quota.py 中定义配额规则
3. 在 src/scheduler/task_scheduler.py 中添加调度逻辑
4. 创建 programs/run_xxx_automation.py 作为入口
5. 在 main_menu.py 中添加菜单选项
6. 编写测试代码
7. 测试全流程

关键文件修改顺序:
  src/config/daily_quota.py →
  src/scheduler/task_scheduler.py →
  programs/run_xxx_automation.py →
  main_menu.py
```

### 任务 2: 修复数据库问题

```
步骤:
1. 使用 SQLite 浏览器检查数据库
2. 识别问题 (重复数据、缺失字段等)
3. 创建修复脚本 scripts/fix_xxx.py
4. 在脚本中备份原数据库
5. 运行修复脚本
6. 验证结果
7. 记录到文档

备份命令:
  cp data/dy_interaction.db data/dy_interaction.db.backup.$(date +%Y%m%d_%H%M%S)
```

### 任务 3: 调试自动化失败

```
步骤:
1. 启用调试日志:
   LOGLEVEL=DEBUG python programs/run_priority_automation.py

2. 查看日志文件:
   tail -f logs/automation*.log

3. 检查失败任务的数据库记录:
   - 任务状态是否为 'failed'
   - 错误信息在 'error_message' 字段

4. 检查设备状态:
   python scripts/check_devices.py

5. 根据错误类型处理:
   - API 错误 → 检查 cookie 或网络
   - 设备错误 → 重启设备或检查连接
   - 数据错误 → 检查任务数据完整性
```

### 任务 4: 性能优化

```
当遇到性能问题时:

1. 识别瓶颈:
   - API 请求慢 → 使用连接池、请求缓存
   - 数据库慢 → 添加索引、优化查询
   - 设备响应慢 → 并行度太高、减少设备数
   - 内存泄漏 → 检查会话管理

2. 修改对应模块:
   - API: src/crawler/api_client.py
   - DB: src/database/manager.py
   - 执行: src/executor/automation_executor.py

3. 测试改进效果:
   - 监控 CPU/内存使用
   - 记录执行时间
   - 对比改进前后

4. 添加监控日志:
   logger.info(f"Processing {count} tasks in {elapsed_time}s")
```

---

## 📌 8. 重要约束与规则

### 必须遵守的规则 ✅

- ✅ **所有新函数必须有文档字符串** (Google 风格)
- ✅ **所有参数和返回值必须有类型提示**
- ✅ **异常必须被捕获并记录日志**
- ✅ **修改 src/ 代码后必须考虑向后兼容性**
- ✅ **大型数据库操作必须有进度提示**
- ✅ **敏感操作必须记录到日志**
- ✅ **删除功能前必须检查是否被依赖**
- ✅ **数据库结构变更必须创建迁移脚本**

### 禁止的操作 ❌

- ❌ **不得在代码中硬编码 API 密钥、密码、账户信息**
- ❌ **不得使用 `except:` 捕获所有异常**
- ❌ **不得吃掉异常而不记录或重新抛出**
- ❌ **不得直接执行 SQL (必须使用 ORM)**
- ❌ **不得在循环中创建多个数据库会话**
- ❌ **不得删除或 DROP 数据库表** (应标记为弃用)
- ❌ **不得使用全局变量存储状态**
- ❌ **不得忽视 REVIEW_SUMMARY.txt 中的 Critical 问题**

### 代码审查清单 (修改代码前检查)

```
□ 代码符合 PEP 8 规范
□ 有完整的文档字符串 (Google 风格)
□ 有类型提示 (参数和返回值)
□ 异常处理完整 (try-except-finally)
□ 关键操作有日志记录 (logger.info/debug)
□ 没有硬编码的敏感信息
□ 不会影响向后兼容性 (或已评估风险)
□ 没有修改 .gitignore 或 requirements.txt (或已告诉我)
□ 修改了 src/database/ → 有迁移计划
□ 修改了 src/executor/ → 已检查依赖处
□ 添加了新功能 → 有相应测试
□ 删除了代码 → 已确认没被其他地方调用
```

---

## 🔍 9. 特殊说明

### 关于 .gitignore 修改

当需要修改 .gitignore 时，我会：
1. 告诉你我想添加的规则和理由
2. 显示会影响哪些文件
3. 等你明确确认后才修改
4. 提交 git 记录此改动

### 关于 requirements.txt 修改

当需要修改依赖时，我会：
1. 告诉你想添加/删除的包
2. 说明理由和版本信息
3. 检查是否有兼容性问题
4. 等你确认后才修改
5. 建议你运行 `pip install -r requirements.txt`

### 关于数据库迁移

当需要修改数据库时，我会：
1. 提出迁移方案和脚本
2. 建议备份方式
3. 说明需要测试的事项
4. 在你确认后执行
5. 记录迁移步骤

示例:
```bash
# 备份
cp data/dy_interaction.db data/dy_interaction.db.backup

# 运行迁移脚本
python scripts/migrate_xxx.py

# 验证
python scripts/check_database.py
```

### 关于敏感信息

当我发现敏感信息时，我会：
1. 🚨 立即提醒安全风险
2. 建议迁移到环保变量或密钥管理
3. 建议加入 .gitignore
4. **绝不会** 在任何日志或输出中暴露密钥
5. **绝不会** 向任何外部服务发送敏感信息

---

## 📊 10. 项目健康检查

### 定期检查项

```bash
# 检查代码质量
flake8 src/ programs/ scripts/

# 检查类型提示
mypy src/

# 查看测试覆盖率
pytest --cov=src --cov-report=term-missing tests/

# 检查依赖安全问题
pip audit

# 查看数据库状态
python scripts/check_database.py

# 查看设备状态
python scripts/check_devices.py
```

### 项目指标

**理想状态**:
- 代码覆盖率: > 70%
- 文档完整度: > 90%
- 类型检查通过: 100%
- 无 Critical 问题: 是

**当前状态** (需要改进):
- 代码覆盖率: ~20% (仅 3 个测试文件)
- 类型检查: 部分 (不是所有代码都有类型提示)
- Critical 问题: 4 个 (见 REVIEW_SUMMARY.txt)

---

## 🔗 11. 相关文档和链接

### 项目文档
- **CODE_ANALYSIS.md** - 完整的文件关系和依赖分析
- **.claude/instructions.md** - 快速参考卡
- **REVIEW_SUMMARY.txt** - 代码质量评分和问题
- **SECURITY_ISSUES.txt** - 安全问题分析

### 官方文档
- [PEP 8 - Python 编码规范](https://pep8.org/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [pytest 文档](https://docs.pytest.org/)
- [Python 类型提示](https://docs.python.org/3/library/typing.html)

### 相关文件快速查找

```
"我想修改爬虫逻辑"
  → src/crawler/monitor_crawler.py 或 history_crawler.py
  → src/crawler/api_client.py

"我想修改自动化逻辑"
  → src/executor/automation_executor.py
  → src/executor/douyin_operations.py

"我想修改任务调度"
  → src/scheduler/task_scheduler.py
  → src/config/daily_quota.py

"我想修改数据模型"
  → src/database/models.py
  → 需要创建迁移脚本

"我想添加新菜单功能"
  → main_menu.py
  → programs/run_xxx.py (可选)
```

---

## 📝 12. 更新日志

- **2025-11-10** - 首次生成，基于完整的代码分析

---

## 💡 如何使用本文档

### 首次使用项目
1. 阅读第 1-3 章 (项目概览、工作流、文件结构)
2. 浏览第 6 章 (项目特定指引)
3. 保存本文档位置，之后参考

### 日常开发
1. 参考第 4-5 章 (命令和编码标准)
2. 查看第 7 章 (常见任务)
3. 参考第 8 章 (约束和规则)

### 遇到问题
1. 查看第 6 章的已知问题表
2. 查看第 7 章的调试任务
3. 查阅 CODE_ANALYSIS.md

### 进行重大修改
1. 确认修改的文件在第 3 章的边界说明中
2. 检查第 8 章的约束和规则
3. 执行代码审查清单

---

**本文档由 Claude Code 自动生成并维护。**
**每次重大改动后应更新此文档以保持准确性。**

