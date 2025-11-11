# 🐛 爬虫功能使用指南

## 📋 功能概述

DY-Interaction 提供了三种爬虫模式：

| 模式 | 功能 | 默认行为 |
|------|------|--------|
| **全量爬虫** | 爬取账号的所有历史评论 | 只爬新账号，跳过已爬取 |
| **监控爬虫** | 监控新增评论 | 支持账号灵活选择 |
| **混合爬虫** | 先历史后监控 | 结合两种模式的优点 |

## 🚀 快速开始

### 从菜单启动（推荐）

```bash
python main_menu.py
```

然后选择：
- 选项 **1**: 全量爬虫
- 选项 **2**: 监控爬虫

### 命令行直接启动

```bash
# 全量爬虫 - 交互式选择
python programs/run_crawler.py history --interactive

# 监控爬虫 - 交互式选择
python programs/run_crawler.py monitor --interactive
```

---

## 📖 详细使用说明

### 1️⃣ 全量爬虫（History Crawler）

**用途**: 从头开始爬取账号的历史评论数据

**特点**:
- ✅ 智能去重：默认只爬新账号
- ✅ 自动检查：已爬取过的账号会被标记
- ✅ 灵活重新爬取：可以选择重新爬取已爬取过的账号
- ✅ 并行支持：可启用多服务器并发爬取

#### 使用方式 A: 交互式选择（推荐）

```bash
python programs/run_crawler.py history --interactive
```

**交互菜单示例**:
```
======================================================================
📋 账号列表（共 3 个）
======================================================================

编号   账号名                    抖音ID               状态
----------------------------------------------------------------------
1      账号A                    @account_a           ✓ 已爬取
2      账号B                    @account_b           ⭐ 新账号
3      账号C                    @account_c           ⭐ 新账号

======================================================================
选择方式:
  0 - 全部账号
  n - 仅新账号（2个未爬取）
  1-3 - 单个账号
  1,3,5 - 多个账号（逗号分隔）
======================================================================

请输入选择:
```

**选择示例**:

| 输入 | 行为 | 说明 |
|------|------|------|
| `0` | 爬取全部3个账号 | 包括已爬取的账号A |
| `n` | 爬取新账号B、C | 跳过已爬取的账号A |
| `1` | 爬取账号A | 单选 |
| `2,3` | 爬取账号B、C | 多选 |

#### 使用方式 B: 自动爬取新账号（默认）

```bash
python programs/run_crawler.py history
```

**行为**:
- 自动检查已爬取过的账号
- 仅爬取新账号（未爬过的）
- 跳过所有已爬取账号
- 不需要交互，适合定时任务

**示例输出**:
```
✓ 找到 3 个目标账号
✓ 发现 2 个新账号（未爬取过）
   已跳过 1 个已爬取账号
   提示：使用 --interactive 可以选择重新爬取
```

#### 使用方式 C: 爬取所有账号（包括已爬取）

```bash
python programs/run_crawler.py history --all
```

**行为**:
- 爬取所有3个账号，包括已爬取过的
- 会重新爬取已爬取账号的数据（慎用，会浪费资源）
- 适合数据更新或修复场景

#### 使用方式 D: 指定账号

```bash
# 爬取账号 1 和 3
python programs/run_crawler.py history --accounts 1,3
```

**行为**:
- 只爬取指定编号的账号
- 可用于快速爬取特定账号

#### 使用方式 E: 并行模式（高级）

```bash
# 交互式 + 并行爬取
python programs/run_crawler.py history --interactive --parallel

# 所有账号 + 并行爬取
python programs/run_crawler.py history --all --parallel

# 指定账号 + 并行爬取
python programs/run_crawler.py history --accounts 1,3 --parallel
```

**并行特性**:
- 🚀 多服务器并发爬取
- ⚡ 大幅提升爬取速度
- ⚙️ 需要在 `config/config.json` 中配置多个服务器

**配置示例**:
```json
{
  "api": {
    "servers": [
      {"name": "服务器1", "base_url": "http://server1.com:8008"},
      {"name": "服务器2", "base_url": "http://server2.com:8008"},
      {"name": "服务器3", "base_url": "http://server3.com:8008"}
    ]
  }
}
```

---

### 2️⃣ 监控爬虫（Monitor Crawler）

**用途**: 每天监控新增评论，及时发现和处理

**特点**:
- ✅ 增量检测：只获取最新视频对比
- ✅ 高效缓存：使用 VideoCache 加速
- ✅ 灵活选择：支持账号自由组合
- ✅ 任务生成：自动生成高优先级任务

#### 使用方式 A: 交互式选择（推荐）

```bash
python programs/run_crawler.py monitor --interactive
```

**交互菜单示例**:
```
======================================================================
📋 账号列表（共 3 个）
======================================================================

编号   账号名                    抖音ID
----------------------------------------------------------------------
1      账号A                    @account_a
2      账号B                    @account_b
3      账号C                    @account_c

======================================================================
选择方式:
  0 - 全部账号
  1-3 - 单个账号
  1,3,5 - 多个账号（逗号分隔）
======================================================================

请输入选择:
```

**选择示例**:

| 输入 | 行为 | 说明 |
|------|------|------|
| `0` | 监控全部账号 | 监控A、B、C |
| `1` | 监控账号A | 单选 |
| `1,3` | 监控账号A、C | 多选 |

#### 使用方式 B: 监控所有账号

```bash
python programs/run_crawler.py monitor --all
```

**行为**:
- 监控所有已配置的账号
- 检测每个账号的新增评论
- 自动生成任务供自动化处理
- 适合日常定时监控

#### 使用方式 C: 指定账号

```bash
# 监控账号 1 和 2
python programs/run_crawler.py monitor --accounts 1,2
```

#### 使用方式 D: 并行模式

```bash
# 交互式 + 并行
python programs/run_crawler.py monitor --interactive --parallel

# 所有账号 + 并行
python programs/run_crawler.py monitor --all --parallel
```

---

### 3️⃣ 混合爬虫（Hybrid Crawler）

**用途**: 在一次运行中同时执行历史爬虫和监控爬虫

**执行顺序**:
1. 🔵 **阶段1**: 历史爬虫 → 爬取历史评论
2. 🟢 **阶段2**: 监控爬虫 → 检测新增评论

#### 使用方式

```bash
# 交互式选择账号
python programs/run_crawler.py hybrid --interactive

# 所有账号
python programs/run_crawler.py hybrid --all

# 指定账号
python programs/run_crawler.py hybrid --accounts 1,3

# 并行模式
python programs/run_crawler.py hybrid --all --parallel
```

**输出示例**:
```
════════════════════════════════════════════════════════════════════════════
🔄 混合爬虫模式 - 启动
   执行顺序: 历史爬虫 → 监控爬虫
════════════════════════════════════════════════════════════════════════════

【第1阶段】历史爬虫
  [账号 1/2] 账号A
    ✓ 爬取完成
      - 视频数: 25 个
      - 评论数: 1500 条
      - 生成任务: 1245 个

【第2阶段】监控爬虫
  [账号 1/2] 账号A
    ✓ 监控完成
      - 新增评论: 35 条
      - 生成任务: 28 个

════════════════════════════════════════════════════════════════════════════
📊 混合模式 - 总体统计
════════════════════════════════════════════════════════════════════════════
  历史评论数: 1500
  新增评论数: 35
  总任务数: 1273
════════════════════════════════════════════════════════════════════════════
```

---

## 📊 已爬取状态检查

### 如何判断账号是否已爬取？

当使用交互模式时，会显示每个账号的状态：

```
编号   账号名                    抖音ID               状态
----------------------------------------------------------------------
1      账号A                    @account_a           ✓ 已爬取
2      账号B                    @account_b           ⭐ 新账号
3      账号C                    @account_c           ⭐ 新账号
```

**状态说明**:
- `✓ 已爬取`: 该账号在 `Comment` 表中有数据
- `⭐ 新账号`: 该账号从未爬取过（`Comment` 表中无数据）

### 检查数据库中的爬取记录

```bash
# 查询已爬取的账号列表
sqlite3 data/dy_interaction.db << EOF
SELECT DISTINCT ta.id, ta.account_name, COUNT(*) as comment_count
FROM comments c
JOIN target_accounts ta ON c.target_account_id = ta.id
GROUP BY ta.id, ta.account_name
ORDER BY comment_count DESC;
EOF
```

### 强制重新爬取已爬取账号的提示

当选择了已爬取的账号时，系统会提示：

```
⚠️  注意：选择中包含 1 个已爬取账号，将重新爬取
确认继续？(y/n):
```

输入 `y` 继续，输入 `n` 取消。

---

## 🔧 并行爬虫配置

### 启用并行模式的前置条件

1. **配置多个API服务器** (`config/config.json`)

```json
{
  "api": {
    "servers": [
      {
        "name": "服务器1",
        "base_url": "http://149.88.66.146:8008",
        "priority": 1
      },
      {
        "name": "服务器2",
        "base_url": "http://140.245.55.143:8008",
        "priority": 2
      },
      {
        "name": "服务器3",
        "base_url": "http://140.245.55.143:20002",
        "priority": 3
      }
    ]
  }
}
```

2. **最大并发工作线程数**

- 自动设置为: `min(账号数, 服务器数)`
- 例如: 5个账号 + 3个服务器 = 最多3个并发

3. **启用并行模式**

```bash
python programs/run_crawler.py history --all --parallel
```

### 并行爬虫性能对比

| 场景 | 串行 | 并行(3服务器) | 提升 |
|------|------|-------------|------|
| 10个账号 | ~50分钟 | ~20分钟 | 2.5倍 |
| 5个账号 | ~25分钟 | ~10分钟 | 2.5倍 |
| 20个账号 | ~100分钟 | ~35分钟 | 2.8倍 |

---

## 🔄 定时任务配置（Linux/Mac）

### Crontab 示例

```bash
# 每天早上8点执行 - 爬取新账号
0 8 * * * cd /path/to/DY-Interaction && python programs/run_crawler.py history > logs/cron_history.log 2>&1

# 每小时执行一次 - 监控新增评论
0 * * * * cd /path/to/DY-Interaction && python programs/run_crawler.py monitor --all > logs/cron_monitor.log 2>&1

# 每天凌晨2点 - 混合爬虫（全量 + 监控）
0 2 * * * cd /path/to/DY-Interaction && python programs/run_crawler.py hybrid --all --parallel > logs/cron_hybrid.log 2>&1
```

### Windows 计划任务

在"任务计划程序"中创建：

```
程序: python.exe
参数: programs/run_crawler.py history
工作目录: C:\path\to\DY-Interaction
```

---

## 📊 常见问题与故障排查

### Q: 为什么默认跳过已爬取账号？

**A**: 这是设计特性，避免重复爬取浪费资源。如需重新爬取，使用 `--interactive` 手动选择。

### Q: 监控爬虫和全量爬虫有什么区别？

**A**:
- **全量**: 一次性爬取账号的所有历史评论（首次使用）
- **监控**: 定期检测新增评论（日常使用）

### Q: 如何加快爬虫速度？

**A**: 启用并行模式 `--parallel`（需要配置多个服务器）

### Q: 并行爬虫需要什么硬件要求？

**A**: 无特殊要求。并行是服务器级别的并发，不是本地并发。

### Q: 爬虫失败了怎么办？

**A**:
1. 检查网络连接
2. 检查API服务器是否在线
3. 查看日志文件 `logs/crawler_service.log`
4. 重新运行（会自动跳过已爬取的数据）

### Q: 如何只爬一个特定账号？

**A**: 使用交互模式 `--interactive` 然后输入账号编号，或直接指定：
```bash
python programs/run_crawler.py history --accounts 1
```

---

## 📝 日志和输出

### 日志位置

```
logs/
├── crawler_service.log      # 爬虫服务主日志
├── cron_history.log         # 定时任务日志（历史爬虫）
├── cron_monitor.log         # 定时任务日志（监控爬虫）
└── cron_hybrid.log          # 定时任务日志（混合爬虫）
```

### 实时日志查看

```bash
# 实时查看日志
tail -f logs/crawler_service.log

# 查看最后100行
tail -n 100 logs/crawler_service.log

# 搜索特定账号的日志
grep "账号A" logs/crawler_service.log
```

---

## 🎯 最佳实践

### 推荐工作流程

**第一天**:
```bash
# 首次全量爬虫 - 爬取所有账号的历史评论
python programs/run_crawler.py history --interactive
→ 选择 0（全部）
```

**第二天及以后**:
```bash
# 早上 - 监控新增评论
python programs/run_crawler.py monitor --all

# 或使用菜单
python main_menu.py
→ 选择 2（监控爬虫）
```

**周末/月底**:
```bash
# 混合爬虫 - 更新历史 + 监控新增
python programs/run_crawler.py hybrid --interactive
→ 选择 0（全部）或指定账号
```

### 并行爬虫最佳配置

- 服务器数: 3-5 个
- 账号数: 10-20 个
- 最大并发: min(账号数, 服务器数)
- 预期提升: 2.5-3 倍速度

---

## 📚 相关文档

- [CLAUDE.md](./CLAUDE.md) - 项目整体规范
- [CODE_ANALYSIS.md](./CODE_ANALYSIS.md) - 代码结构分析
- [DEPLOYMENT.md](./DEPLOYMENT.md) - 部署指南

---

**最后更新**: 2025-11-11
**爬虫版本**: v2.0 (统一爬虫服务)
**状态**: ✅ 全部功能已集成
