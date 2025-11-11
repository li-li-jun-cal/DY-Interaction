# DY-Interaction 功能测试指南

本文档提供完整的功能测试步骤，帮助验证所有功能是否正常工作。

---

## 📋 测试前准备

### 1. 环境要求
- Python 3.8+
- 已安装依赖：`pip install -r requirements.txt`
- 数据库文件存在：`data/dy_interaction.db`

### 2. 配置要求
- `.env` 文件已配置（从 `.env.example` 复制）
- `config/config.json` 配置文件存在

### 3. 快速检查
```bash
# 检查Python版本
python --version

# 检查依赖
pip list | grep -E "(sqlalchemy|requests)"

# 检查数据库
ls -lh data/dy_interaction.db
```

---

## 🧪 测试分类

### A. 主菜单功能测试
### B. 爬虫服务测试
### C. 自动化服务测试
### D. Docker部署测试

---

## A. 主菜单功能测试

### 测试 1: 启动主菜单
```bash
python main_menu.py
```

**预期结果**:
- ✅ 显示标题和统计信息
- ✅ 显示菜单选项 (1-17)
- ✅ 无错误信息

---

### 测试 2: 查看设备列表 (选项 8)

**步骤**:
1. 运行 `python main_menu.py`
2. 输入 `8`
3. 查看设备列表

**预期结果**:
- ✅ 显示设备列表或"暂无设备"
- ✅ 正常返回主菜单

---

### 测试 3: 查看账号列表 (选项 9)

**步骤**:
1. 运行 `python main_menu.py`
2. 输入 `9`
3. 查看账号列表

**预期结果**:
- ✅ 显示账号列表或"暂无目标账号"
- ✅ 正常返回主菜单

---

### 测试 4: 添加目标账号 (选项 10)

**步骤**:
1. 运行 `python main_menu.py`
2. 输入 `10`
3. 输入测试账号信息:
   - 账号名称: `测试账号`
   - 抖音ID: `123456789`
   - sec_uid: (可选，直接回车)
   - unique_id: (可选，直接回车)
4. 确认添加: 输入 `yes`

**预期结果**:
- ✅ 提示"成功添加账号"
- ✅ 无报错
- ✅ 再次查看账号列表(选项9)能看到新账号

**问题排查**:
- 如果报错 `AttributeError: __enter__`，说明session_scope修复未生效

---

### 测试 5: 删除目标账号 (选项 11)

**步骤**:
1. 运行 `python main_menu.py`
2. 输入 `11`
3. 查看账号列表
4. 输入要删除的账号ID (如: `1`)
5. 输入 `DELETE` 确认

**预期结果**:
- ✅ 显示账号列表
- ✅ 提示"成功删除账号"
- ✅ 无报错
- ✅ 再次查看账号列表，该账号已消失

**问题排查**:
- 如果报错 `AttributeError: __enter__`，说明session_scope修复未生效
- 如果报错 `未找到ID`，检查输入的ID是否存在

---

### 测试 6: 查看详细统计 (选项 7)

**步骤**:
1. 运行 `python main_menu.py`
2. 输入 `7`

**预期结果**:
- ✅ 显示任务统计
- ✅ 显示用户统计
- ✅ 显示操作统计
- ✅ 显示系统资源
- ✅ 无报错

---

## B. 爬虫服务测试

### 测试 7: 爬虫服务 - 语法检查

```bash
python -m py_compile programs/run_crawler.py
echo $?  # 应该输出 0
```

**预期结果**: ✅ 无输出，退出码为 0

---

### 测试 8: 爬虫服务 - 帮助信息

```bash
python programs/run_crawler.py --help
```

**预期结果**:
- ✅ 显示用法说明
- ✅ 显示支持的模式: history, monitor, hybrid
- ✅ 显示选项: --all, --interactive, --accounts

---

### 测试 9: 爬虫服务 - History模式 (Dry Run)

```bash
# 注意：如果没有配置账号或API，可能会失败
# 这个测试主要验证程序能否启动

python programs/run_crawler.py history --accounts 1
```

**预期结果**:
- ✅ 程序启动
- ✅ 显示账号选择
- ✅ 如果没有账号，提示"暂无目标账号"

**取消测试**: 按 `Ctrl+C`

---

### 测试 10: 爬虫服务 - Monitor模式 (Dry Run)

```bash
python programs/run_crawler.py monitor --accounts 1
```

**预期结果**:
- ✅ 程序启动
- ✅ 显示账号选择
- ✅ 如果没有账号，提示"暂无目标账号"

**取消测试**: 按 `Ctrl+C`

---

## C. 自动化服务测试

### 测试 11: 自动化服务 - 语法检查

```bash
python -m py_compile programs/run_automation.py
echo $?  # 应该输出 0
```

**预期结果**: ✅ 无输出，退出码为 0

---

### 测试 12: 自动化服务 - 帮助信息

```bash
python programs/run_automation.py --help
```

**预期结果**:
- ✅ 显示用法说明
- ✅ 显示支持的模式: realtime, recent, longterm, mixed, maintenance
- ✅ 显示选项: --all, --interactive, --devices, --dry-run

---

### 测试 13: 自动化服务 - Dry Run模式

```bash
python programs/run_automation.py realtime --dry-run
```

**预期结果**:
- ✅ 显示任务统计
- ✅ 显示各种任务的待处理数量
- ✅ 输出 "[Dry Run] 统计信息已显示，退出"
- ✅ 无报错

---

### 测试 14: 自动化服务 - 无设备测试

```bash
# 如果没有真实设备，这个测试会失败，这是正常的
python programs/run_automation.py realtime --all
```

**预期结果**:
- ✅ 显示"检测在线设备..."
- ✅ 如果无设备，提示"未检测到任何在线设备"
- ✅ 给出设置建议

**取消测试**: 按 `Ctrl+C`

---

## D. Docker部署测试

### 测试 15: 部署脚本检查

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh --help
```

**预期结果**:
- ✅ 显示部署脚本帮助信息
- ✅ 列出所有可用命令

---

### 测试 16: Docker配置检查

```bash
./scripts/deploy.sh check
```

**预期结果**:
- ✅ 检查Docker是否安装
- ✅ 检查Docker Compose是否安装
- ✅ 检查.env文件是否存在

---

### 测试 17: Docker Compose配置验证

```bash
docker-compose config
```

**预期结果**:
- ✅ 显示完整的docker-compose配置
- ✅ 无语法错误

---

## 📊 测试报告模板

请在完成测试后填写：

```
测试日期: YYYY-MM-DD
测试人:
Python版本:
操作系统:

【主菜单功能】
- 测试1 (启动): ✅/❌
- 测试2 (设备列表): ✅/❌
- 测试3 (账号列表): ✅/❌
- 测试4 (添加账号): ✅/❌
- 测试5 (删除账号): ✅/❌
- 测试6 (详细统计): ✅/❌

【爬虫服务】
- 测试7 (语法): ✅/❌
- 测试8 (帮助): ✅/❌
- 测试9 (History): ✅/❌
- 测试10 (Monitor): ✅/❌

【自动化服务】
- 测试11 (语法): ✅/❌
- 测试12 (帮助): ✅/❌
- 测试13 (Dry Run): ✅/❌
- 测试14 (无设备): ✅/❌

【Docker部署】
- 测试15 (部署脚本): ✅/❌
- 测试16 (环境检查): ✅/❌
- 测试17 (配置验证): ✅/❌

发现的问题:
1.
2.
3.
```

---

## 🐛 常见问题排查

### 问题 1: AttributeError: __enter__
**原因**: session_scope修复未生效
**解决**:
```bash
git pull
python -c "from src.database.manager import DatabaseManager; print('OK')"
```

### 问题 2: ModuleNotFoundError: No module named 'xxx'
**原因**: 依赖未安装
**解决**:
```bash
pip install -r requirements.txt
```

### 问题 3: 数据库连接失败
**原因**: 数据库文件不存在或权限问题
**解决**:
```bash
mkdir -p data
chmod 755 data
python -c "from src.database.manager import DatabaseManager; DatabaseManager().init_db()"
```

### 问题 4: No such file or directory: config/config.json
**原因**: 配置文件缺失
**解决**:
```bash
cp config/config.json.example config/config.json
# 然后编辑 config/config.json
```

---

## 📝 测试注意事项

1. **不要在生产环境测试**: 使用测试数据库和配置
2. **备份数据**: 测试前备份 `data/dy_interaction.db`
3. **清理测试数据**: 测试后删除添加的测试账号
4. **记录问题**: 遇到问题立即记录错误信息
5. **版本确认**: 确保在正确的git分支上测试

---

## ✅ 测试完成检查清单

- [ ] 所有语法检查通过
- [ ] 主菜单所有选项可访问
- [ ] 添加/删除账号功能正常
- [ ] 统计显示无错误
- [ ] 爬虫服务可启动
- [ ] 自动化服务可启动
- [ ] Docker配置正确
- [ ] 所有发现的问题已记录

---

*文档创建: 2025-11-10*
*适用版本: claude/project-refactor-011CUza7t9T1HzKEu9AiKmjk*
