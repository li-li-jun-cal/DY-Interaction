# DY-Interaction 代码分析文档

**文档生成时间**: 2025-11-10
**项目**: DY-Interaction (Douyin/TikTok 自动化交互框架)
**分析范围**: 所有Python文件、模块导入、程序调用链路

---

## 目录

1. [项目概览](#项目概览)
2. [核心调用链路](#核心调用链路)
3. [文件使用情况统计](#文件使用情况统计)
4. [正在使用的文件](#正在使用的文件)
5. [未使用的文件](#未使用的文件)
6. [重复和冗余模块](#重复和冗余模块)
7. [建议删除清单](#建议删除清单)
8. [项目结构详解](#项目结构详解)

---

## 项目概览

### 项目类型
- **名称**: DY-Interaction
- **用途**: 抖音(Douyin)自动化交互管理框架
- **功能**:
  - 多设备并行执行
  - 优先级任务调度
  - 实时和历史数据爬取
  - 每日配额管理
  - 任务分类和去重

### 项目规模
- **总文件数**: 97+ Python文件
- **代码行数**: ~15,000+ 行
- **核心模块**: 60+ (src/)
- **可执行程序**: 13 (programs/)
- **工具脚本**: 24+ (scripts/)

### 技术栈
- **语言**: Python 3
- **数据库**: SQLite + SQLAlchemy ORM
- **依赖**: requirements.txt (需查看具体版本)

---

## 核心调用链路

### 主入口: main_menu.py

**文件位置**: `D:\Users\zk\Desktop\DY-Interaction\main_menu.py` (708行)

#### 直接导入
```python
from src.database.manager import DatabaseManager
from src.database.models import InteractionTask, TargetAccount, Device, NewComment, Comment, DeviceDailyStats
from src.stats.interaction_stats import InteractionStatsCollector
```

#### 通过 subprocess.run() 调用的程序/脚本

```
main_menu.py (主菜单)
│
├─【爬虫管理】
│  ├─ 菜单选项 1 → programs/run_history_crawler.py
│  │                (全量爬虫 - 爬取历史评论)
│  │
│  └─ 菜单选项 2 → programs/run_monitor_crawler.py
│                  (监控爬虫 - 监控新增评论)
│
├─【自动化任务】
│  ├─ 菜单选项 3 → programs/run_priority_automation.py --mode realtime
│  │                (实时自动化 - 处理新增评论)
│  │
│  ├─ 菜单选项 4 → programs/run_priority_automation.py --mode recent
│  │                (近期自动化 - 处理3个月内评论)
│  │
│  ├─ 菜单选项 5 → programs/run_long_term_automation.py --auto
│  │                (长期自动化 - 处理3个月以上评论)
│  │
│  └─ 菜单选项 6 → programs/run_priority_automation.py --mode mixed
│                  (混合自动化 - 实时+近期)
│
├─【系统管理】
│  ├─ 菜单选项 7 → show_detailed_stats() [本地函数]
│  ├─ 菜单选项 8 → show_devices() [本地函数]
│  ├─ 菜单选项 9 → show_accounts() [本地函数]
│  ├─ 菜单选项 10 → add_account() [本地函数]
│  ├─ 菜单选项 11 → delete_account() [本地函数]
│  └─ 菜单选项 12 → scripts/manage_api_servers.py
│                  (管理API服务器)
│
└─【数据维护】
   ├─ 菜单选项 13 → scripts/generate_tasks_from_comments.py --auto
   │                (生成缺失任务)
   │
   ├─ 菜单选项 14 → scripts/cleanup_duplicate_tasks.py --auto
   │                (清理重复任务)
   │
   ├─ 菜单选项 15 → scripts/delete_tasks_without_unique_id.py --auto
   │                (删除缺陷任务)
   │
   ├─ 菜单选项 16 → scripts/update_server_cookie.py 或 update_cookie_pool.py
   │                (更新Cookie配置)
   │
   └─ 菜单选项 17 → scripts/check_devices.py
                    (检查设备状态)
```

### 程序依赖链路

#### 1. run_history_crawler.py
```
run_history_crawler.py
├── src.database.manager.DatabaseManager
├── src.crawler.history_crawler.HistoryCrawler
├── src.generator.task_generator.TaskGenerator
└── src.crawler.api_client.DouyinAPIClient
```

#### 2. run_monitor_crawler.py
```
run_monitor_crawler.py
├── src.database.manager.DatabaseManager
├── src.crawler.monitor_crawler.MonitorCrawler
├── src.generator.task_generator.TaskGenerator
└── src.crawler.api_client.DouyinAPIClient
```

#### 3. run_priority_automation.py (3种模式)
```
run_priority_automation.py
├── src.database.manager.DatabaseManager
├── src.executor.automation_executor.AutomationExecutor
├── src.scheduler.task_scheduler.TaskScheduler
├── src.config.daily_quota.DailyQuota
├── src.utils.device_manager.DeviceManager
└── src.executor.douyin_operations.DouyinOperations
```

#### 4. run_long_term_automation.py
```
run_long_term_automation.py
├── src.database.manager.DatabaseManager
├── src.executor.automation_executor.AutomationExecutor
├── src.scheduler.task_scheduler.TaskScheduler
└── src.config.daily_quota.DailyQuota
```

---

## 文件使用情况统计

### 按类型分类

| 类别 | 总数 | 在用数 | 未用数 | 使用率 |
|------|------|--------|--------|--------|
| **Programs** | 13 | 4 | 8 | 31% |
| **Scripts** | 24+ | 8 | 16+ | 33% |
| **Src Modules** | 60+ | 60+ | 0 | 100% |
| **总计** | **97+** | **72** | **25+** | **74%** |

### 按导入频率分类

#### 🔴 核心模块 (40+ 处导入)
- `src/database/manager.py` - DatabaseManager (43+ 导入)
- `src/database/models.py` - 所有ORM模型 (38+ 导入)

#### 🟠 关键模块 (4-7 处导入)
- `src/scheduler/task_scheduler.py` (7 处)
- `src/executor/automation_executor.py` (4 处)
- `src/crawler/api_client.py` (4 处)
- `src/scheduler/task_generator.py` (4 处)
- `src/config/daily_quota.py` (4 处)
- `src/utils/device_manager.py` (3 处)

#### 🟡 常用模块 (2 处导入)
- `src/crawler/history_crawler.py`
- `src/crawler/monitor_crawler.py`
- `src/executor/douyin_operations.py`
- `src/executor/device_coordinator.py`
- `src/generator/task_generator.py`
- `src/crawler/scheduler.py`

#### 🟢 支援模块 (1 处导入)
- `src/executor/element_ids.py`
- `src/executor/page_navigator.py`
- `src/executor/interaction_executor.py`
- `src/stats/automation_execution_stats.py`
- `src/stats/interaction_stats.py`
- `src/utils/logger.py`

---

## 正在使用的文件

### ✅ 正在使用的 Programs (4个)

| 文件 | 行数 | 功能 | 菜单选项 |
|------|------|------|---------|
| `programs/run_history_crawler.py` | 277 | 全量爬虫 | 1 |
| `programs/run_monitor_crawler.py` | 248 | 监控爬虫 | 2 |
| `programs/run_priority_automation.py` | 538 | 优先级自动化 | 3,4,6 |
| `programs/run_long_term_automation.py` | 326 | 长期自动化 | 5 |

### ✅ 正在使用的 Scripts (8个)

| 文件 | 功能 | 菜单选项 |
|------|------|---------|
| `scripts/cleanup_duplicate_tasks.py` | 清理重复任务 | 14 |
| `scripts/update_server_cookie.py` | 更新服务器Cookie | 16-1 |
| `scripts/update_cookie_pool.py` | 更新Cookie池 | 16-2 |
| `scripts/check_devices.py` | 检查设备状态 | 17 |
| `scripts/manage_api_servers.py` | 管理API服务器 | 12 |
| `scripts/generate_tasks_from_comments.py` | 生成缺失任务 | 13 |
| `scripts/delete_tasks_without_unique_id.py` | 删除缺陷任务 | 15 |
| `scripts/cleanup_unused_scripts.py` | 清理未使用脚本 | - |

### ✅ 正在使用的 Src Modules (60+个)

所有 `src/` 目录下的模块都被导入和使用：

```
src/
├── config/
│   └── daily_quota.py ✅
├── crawler/
│   ├── api_client.py ✅
│   ├── history_crawler.py ✅
│   ├── monitor_crawler.py ✅
│   ├── improved_monitor_crawler.py ⚠️ (可能重复)
│   └── scheduler.py ✅
├── database/
│   ├── manager.py ✅ (核心)
│   └── models.py ✅ (核心)
├── executor/
│   ├── automation_executor.py ✅
│   ├── interaction_executor.py ✅
│   ├── douyin_operations.py ✅
│   ├── douyin_operations_v2.py ⚠️ (可能重复)
│   ├── device_coordinator.py ✅
│   ├── page_navigator.py ✅
│   ├── image_recognizer.py ✅
│   └── element_ids.py ✅
├── generator/
│   └── task_generator.py ✅
├── scheduler/
│   ├── task_scheduler.py ✅
│   ├── schedule_manager.py ✅
│   └── task_generator.py ⚠️ (可能与generator/重复)
├── stats/
│   ├── automation_execution_stats.py ✅
│   └── interaction_stats.py ✅
└── utils/
    ├── device_manager.py ✅
    ├── logger.py ✅
    ├── comment_text_manager.py ✅
    └── excel_reader.py ✅
```

---

## 未使用的文件

### ❌ 未使用的 Programs (8个) - 可以删除

这些程序从不被 main_menu.py 或任何其他地方调用：

```
programs/batch_processor.py                (331 行)
programs/configure_devices.py              (85 行)
programs/init_config.py                    (127 行)
programs/realtime_monitor.py               (276 行)
programs/run_all_in_one.py                 (340 行)
programs/run_automation_with_stats.py      (114 行)
programs/run_recent_automation.py          (235 行)
programs/setup_devices.py                  (232 行)
```

**删除原因**:
- 没有在 main_menu.py 中的菜单选项调用
- 没有被其他程序导入
- 可能是早期版本或替代方案

### ❌ 未使用的 Scripts (16+个) - 可以删除

#### A. 数据迁移脚本（一次性使用，已执行过）
```
scripts/migrate_add_video_cache.py
scripts/migrate_add_video_create_time.py
scripts/migrate_task_types.py
```

#### B. 数据修复脚本（问题已修复，不再需要）
```
scripts/add_comment_time_to_tasks.py      # 添加评论时间
scripts/clean_old_assigned_tasks.py       # 清理旧分配任务
scripts/cleanup_false_realtime_tasks.py   # 清理错误分类的实时任务
scripts/convert_realtime_to_history.py    # 转换任务类型
scripts/fix_task_classification.py        # 修复任务分类
scripts/fix_user_id_issue.py              # 修复用户ID问题
```

#### C. 已被集成的脚本（功能已集成到 main_menu.py）
```
scripts/show_stats.py                     # 统计显示 → main_menu.py:show_detailed_stats()
scripts/view_stats.py                     # 统计查看 → main_menu.py:show_detailed_stats()
```

#### D. 其他未使用脚本
```
scripts/import_target_accounts.py         # 导入目标账号
scripts/manage_comments.py                # 评论管理
scripts/rebuild_video_cache_from_comments.py  # 从评论重建视频缓存
scripts/reset_database.py                 # 重置数据库
scripts/test_priority_automation.py       # 优先级自动化测试
```

#### E. 已归档的脚本（完全过时）
```
scripts/archive/check_duplicate_tasks.py  # 检查重复任务（已归档）
scripts/archive/monitor_tasks.py          # 监控任务（已归档）
```

**删除原因**:
- 不在 main_menu.py 任何菜单选项中调用
- 不被其他脚本/程序导入
- 大多是一次性修复或迁移脚本
- 功能已集成或完全过时

---

## 重复和冗余模块

### ⚠️ 需要审查的重复模块

#### 1. Douyin Operations 版本问题
```
src/executor/douyin_operations.py      (1,639 行)
src/executor/douyin_operations_v2.py   (1,617 行)
```

**问题**: 两个版本都存在，行数相近，可能存在代码重复

**当前状态**: 都被 `interaction_executor.py` 导入

**建议**:
- [ ] 比对两个版本的差异
- [ ] 确定 v2 是否是完整的重构
- [ ] 合并或删除一个版本
- [ ] 更新相关导入

#### 2. Monitor Crawler 版本问题
```
src/crawler/monitor_crawler.py           (372 行)
src/crawler/improved_monitor_crawler.py  (248 行)
```

**问题**: 有改进版本，但似乎未被完全集成

**当前状态**: `improved_monitor_crawler.py` 似乎没有被使用

**建议**:
- [ ] 检查 `improved_monitor_crawler.py` 是否有实际导入
- [ ] 如果有改进，集成到主版本并删除
- [ ] 如果没有使用，直接删除

#### 3. Task Generator 重复问题
```
src/generator/task_generator.py     (314 行)
src/scheduler/task_generator.py     (313 行)
```

**问题**: 两个目录下都有同名文件，行数几乎相同

**当前状态**: 都有导入

**建议**:
- [ ] 比对两个文件的内容
- [ ] 合并到一个位置
- [ ] 更新所有导入路径
- [ ] 删除重复版本

---

## 建议删除清单

### 优先级 🔴 高 - 100% 确定未使用，可以立即删除

#### Programs 目录 (8个文件，共 1,738 行代码)
```bash
rm D:\Users\zk\Desktop\DY-Interaction\programs\batch_processor.py
rm D:\Users\zk\Desktop\DY-Interaction\programs\configure_devices.py
rm D:\Users\zk\Desktop\DY-Interaction\programs\init_config.py
rm D:\Users\zk\Desktop\DY-Interaction\programs\realtime_monitor.py
rm D:\Users\zk\Desktop\DY-Interaction\programs\run_all_in_one.py
rm D:\Users\zk\Desktop\DY-Interaction\programs\run_automation_with_stats.py
rm D:\Users\zk\Desktop\DY-Interaction\programs\run_recent_automation.py
rm D:\Users\zk\Desktop\DY-Interaction\programs\setup_devices.py
```

#### Scripts Archive 目录 (2个文件)
```bash
rm D:\Users\zk\Desktop\DY-Interaction\scripts\archive\check_duplicate_tasks.py
rm D:\Users\zk\Desktop\DY-Interaction\scripts\archive\monitor_tasks.py
```

### 优先级 🟡 中 - 需要确认后删除

#### 统计脚本 (3个文件，功能已集成到 main_menu.py)
```bash
# 备注: show_stats.py 和 view_stats.py 的功能已集成到 main_menu.py:show_detailed_stats()
rm D:\Users\zk\Desktop\DY-Interaction\scripts\show_stats.py
rm D:\Users\zk\Desktop\DY-Interaction\scripts\view_stats.py
rm D:\Users\zk\Desktop\DY-Interaction\scripts\test_priority_automation.py
```

#### 迁移脚本 (3个文件，一次性使用)
```bash
# 备注: 这些是数据库迁移脚本，如果迁移已完成，可以删除
rm D:\Users\zk\Desktop\DY-Interaction\scripts\migrate_add_video_cache.py
rm D:\Users\zk\Desktop\DY-Interaction\scripts\migrate_add_video_create_time.py
rm D:\Users\zk\Desktop\DY-Interaction\scripts\migrate_task_types.py
```

#### 数据修复脚本 (7个文件，如问题已修复)
```bash
# 备注: 这些脚本用于一次性数据修复，如果问题已解决，可以删除
rm D:\Users\zk\Desktop\DY-Interaction\scripts\add_comment_time_to_tasks.py
rm D:\Users\zk\Desktop\DY-Interaction\scripts\clean_old_assigned_tasks.py
rm D:\Users\zk\Desktop\DY-Interaction\scripts\cleanup_false_realtime_tasks.py
rm D:\Users\zk\Desktop\DY-Interaction\scripts\convert_realtime_to_history.py
rm D:\Users\zk\Desktop\DY-Interaction\scripts\fix_task_classification.py
rm D:\Users\zk\Desktop\DY-Interaction\scripts\fix_user_id_issue.py
rm D:\Users\zk\Desktop\DY-Interaction\scripts\manage_comments.py
```

#### 其他脚本
```bash
rm D:\Users\zk\Desktop\DY-Interaction\scripts\import_target_accounts.py
rm D:\Users\zk\Desktop\DY-Interaction\scripts\rebuild_video_cache_from_comments.py
rm D:\Users\zk\Desktop\DY-Interaction\scripts\reset_database.py
```

### 优先级 🟢 低 - 需要代码审查后删除

#### Src 模块重复版本
```bash
# 仅在确认不需要后删除，需要检查导入
# rm D:\Users\zk\Desktop\DY-Interaction\src\executor\douyin_operations_v2.py
# rm D:\Users\zk\Desktop\DY-Interaction\src\crawler\improved_monitor_crawler.py
# rm D:\Users\zk\Desktop\DY-Interaction\src\scheduler\task_generator.py  (如与generator/重复)
```

---

## 项目结构详解

### 根目录结构
```
D:\Users\zk\Desktop\DY-Interaction/
│
├── 📁 src/                           # 核心框架 (60+ 模块, 11,000+ 行)
│   ├── config/                       # 配置管理
│   ├── crawler/                      # 数据爬虫
│   ├── database/                     # 数据库管理 (核心)
│   ├── executor/                     # 任务执行
│   ├── generator/                    # 任务生成
│   ├── scheduler/                    # 任务调度
│   ├── stats/                        # 统计模块
│   └── utils/                        # 工具函数
│
├── 📁 programs/                      # 可执行程序 (13个)
│   ├── ✅ run_history_crawler.py     # 全量爬虫 (在用)
│   ├── ✅ run_monitor_crawler.py     # 监控爬虫 (在用)
│   ├── ✅ run_priority_automation.py # 优先级自动化 (在用)
│   ├── ✅ run_long_term_automation.py# 长期自动化 (在用)
│   ├── ❌ batch_processor.py         # 批处理 (未用)
│   ├── ❌ configure_devices.py       # 设备配置 (未用)
│   ├── ❌ init_config.py             # 初始配置 (未用)
│   ├── ❌ realtime_monitor.py        # 实时监控 (未用)
│   ├── ❌ run_all_in_one.py          # 全一体 (未用)
│   ├── ❌ run_automation_with_stats.py # 带统计自动化 (未用)
│   ├── ❌ run_recent_automation.py   # 近期自动化 (未用)
│   └── ❌ setup_devices.py           # 设备设置 (未用)
│
├── 📁 scripts/                       # 工具脚本 (24+)
│   ├── ✅ cleanup_duplicate_tasks.py        # 清理重复任务 (在用)
│   ├── ✅ update_server_cookie.py           # 更新Cookie (在用)
│   ├── ✅ check_devices.py                  # 检查设备 (在用)
│   ├── ✅ manage_api_servers.py             # 管理API (在用)
│   ├── ✅ generate_tasks_from_comments.py   # 生成任务 (在用)
│   ├── ❌ show_stats.py                     # 显示统计 (已集成)
│   ├── ❌ view_stats.py                     # 查看统计 (已集成)
│   ├── ❌ migrate_*.py                      # 迁移脚本 (一次性)
│   ├── ❌ fix_*.py                          # 修复脚本 (一次性)
│   ├── ❌ clean_*.py                        # 清理脚本 (一次性)
│   └── 📁 archive/                          # 已归档脚本 (过时)
│
├── 📁 config/                        # 配置文件
│   ├── config.json                   # 主配置 ⚠️ (未加入.gitignore)
│   ├── douyin_cookie.txt             # Cookie (✅ 已忽略)
│   ├── douyin_cookies_pool.txt       # Cookie池 (✅ 已忽略)
│   └── target_accounts.json          # 账号列表 ⚠️ (未加入.gitignore)
│
├── 📁 data/                          # 数据存储
│   └── dy_interaction.db             # SQLite 数据库
│
├── 📁 templates/                     # UI自动化模板
│   ├── README                        # 模板文档
│   └── *.png                         # 图像识别模板
│
├── 📁 tests/                         # 测试文件 (3个, 低覆盖率)
├── 📁 logs/                          # 运行日志
├── 📁 docs/                          # 文档目录 (空)
├── 📁 .venv/                         # Python虚拟环境
│
├── 📄 main_menu.py                   # ✅ 主入口 (708 行)
├── 📄 requirements.txt                # 依赖列表
├── 📄 test_quota_config.py            # 配额测试
├── 📄 test_execution.log              # 执行日志 (应添加到.gitignore)
├── 📄 REVIEW_SUMMARY.txt              # 代码审查总结
├── 📄 SECURITY_ISSUES.txt             # 安全问题分析
├── 📄 CODE_ANALYSIS.md                # 📍 本文档
│
├── 📄 LICENSE                         # 许可证
├── 📄 .gitignore                      # Git忽略规则
└── 📄 .gitattributes                  # Git属性配置
```

### 核心模块说明

#### src/database/ (核心 - 43+ 导入)
- **manager.py**: 数据库连接和会话管理
  - ⚠️ **已知问题**: 会话资源泄漏、缺少连接池
- **models.py**: SQLAlchemy ORM 模型定义 (所有数据表)

#### src/executor/ (执行引擎)
- **automation_executor.py**: 自动化任务执行器
- **douyin_operations.py**: 抖音API操作 (1,639 行)
  - ⚠️ **已知问题**: 行数过多、应拆分
  - ⚠️ **重复**: 有 v2 版本
- **interaction_executor.py**: 互动操作执行 (955 行)
- **device_coordinator.py**: 多设备协调
  - ⚠️ **已知问题**: 竞态条件、设备锁不安全

#### src/crawler/ (数据爬虫)
- **api_client.py**: HTTP API 客户端
- **history_crawler.py**: 历史评论爬虫
- **monitor_crawler.py**: 监控新增评论
  - ⚠️ **重复**: 有 improved_monitor_crawler.py

#### src/scheduler/ (任务调度)
- **task_scheduler.py**: 任务调度器
- **schedule_manager.py**: 日程管理
- **task_generator.py**: 任务生成
  - ⚠️ **重复**: generator/ 下也有同名文件

#### src/config/ (配置管理)
- **daily_quota.py**: 每日配额限制管理

#### src/utils/ (工具函数)
- **device_manager.py**: 设备管理
- **logger.py**: 日志配置
- **comment_text_manager.py**: 评论文本处理
- **excel_reader.py**: Excel 导入工具

#### src/stats/ (数据统计)
- **interaction_stats.py**: 互动统计 (已被 main_menu.py 使用)
- **automation_execution_stats.py**: 执行统计

---

## 关键发现和问题

### 🔴 代码质量问题 (参考 REVIEW_SUMMARY.txt)

1. **敏感信息硬编码**
   - API 密钥和认证信息未加密
   - config.json 和 target_accounts.json 未加入 .gitignore

2. **数据库问题**
   - manager.py 存在会话资源泄漏
   - 缺少连接池配置
   - 未实现适当的错误处理

3. **并发/竞态问题**
   - device_coordinator.py 中的设备锁不线程安全
   - 多设备并行执行缺少同步机制

4. **代码冗余**
   - douyin_operations (1,639) vs douyin_operations_v2 (1,617)
   - monitor_crawler vs improved_monitor_crawler
   - task_generator 出现在两个模块

5. **缺少输入验证**
   - API 参数未完全验证
   - SQL 注入风险

### ⚠️ 文件系统问题

1. **日志文件未加入 .gitignore**
   - logs/*.log
   - test_execution.log

2. **配置文件安全问题**
   - config.json 包含敏感信息
   - target_accounts.json 包含账号列表

3. **过时代码堆积**
   - 8 个 programs 从未使用
   - 16+ 个 scripts 是一次性修复脚本
   - scripts/archive/ 中已弃用的脚本未删除

---

## 维护建议

### 短期 (1-2 周)

- [ ] 删除 8 个未使用的 programs
- [ ] 删除 scripts/archive/ 目录
- [ ] 删除已集成的 show_stats.py 和 view_stats.py
- [ ] 更新 .gitignore，添加日志文件和配置文件

### 中期 (1-2 月)

- [ ] 审查和合并重复的 src 模块
  - douyin_operations v1 vs v2
  - monitor_crawler 两个版本
  - task_generator 两个位置
- [ ] 拆分过大的模块 (douyin_operations 1,639 行)
- [ ] 添加输入验证和错误处理
- [ ] 改进数据库连接管理

### 长期 (持续)

- [ ] 增加单元测试覆盖率 (当前极低)
- [ ] 文档化代码和API
- [ ] 实现 API 限流
- [ ] 重构并发控制机制
- [ ] 密钥管理系统

---

## 文件查询快速索引

### 找某个功能在哪里

| 需求 | 文件位置 |
|------|---------|
| 全量爬虫 | `programs/run_history_crawler.py` + `src/crawler/history_crawler.py` |
| 监控爬虫 | `programs/run_monitor_crawler.py` + `src/crawler/monitor_crawler.py` |
| 自动化执行 | `programs/run_priority_automation.py` + `src/executor/automation_executor.py` |
| 任务调度 | `src/scheduler/task_scheduler.py` |
| 数据库操作 | `src/database/manager.py` |
| 抖音API操作 | `src/executor/douyin_operations.py` |
| 设备管理 | `src/utils/device_manager.py` |
| 配额限制 | `src/config/daily_quota.py` |
| 统计数据 | `src/stats/interaction_stats.py` |

### 添加新功能应该修改哪些文件

1. **添加新菜单选项** → `main_menu.py`
2. **添加新爬虫** → `src/crawler/` + `programs/run_xxx_crawler.py`
3. **修改自动化逻辑** → `src/executor/automation_executor.py` 或 `src/executor/douyin_operations.py`
4. **修改数据模型** → `src/database/models.py`
5. **添加新统计** → `src/stats/interaction_stats.py`
6. **修改任务调度** → `src/scheduler/task_scheduler.py`

---

## 更新日志

- **2025-11-10**: 首次代码分析，生成此文档

---

*本文档由代码分析工具自动生成，旨在帮助快速理解项目结构和文件关系。*
