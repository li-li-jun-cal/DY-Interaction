# CLAUDE.md - Python 项目通用模板

> **说明**: 这是一个开源通用模板，适用于任何 Python 项目。可根据项目情况进行定制。
> 复制此文件到项目根目录，作为 Claude Code 的配置指引。

---

## 📋 1. 项目概览

### 项目信息
```
项目名称: [项目名称]
项目类型: [类型，如 Web应用/数据分析/自动化框架等]
Python 版本: 3.8+
主要依赖: [列出主要依赖]
```

### 项目目的
[简单描述项目做什么，2-3 句话]

### 文档索引
- 完整分析: `CODE_ANALYSIS.md`
- 快速参考: `QUICKSTART.md` (可选)
- API 文档: `docs/` (可选)

---

## 🎯 2. 核心工作流

### 主要功能模块
- **Module A**: [功能描述]
- **Module B**: [功能描述]
- **Module C**: [功能描述]

### 数据流
```
输入 → 处理 → 输出
```

### 依赖关系
```
高级组件
  ↓
中间层组件
  ↓
基础组件
```

---

## 📁 3. 文件结构与边界

### 核心边界
```
src/              核心代码 (不依赖外部模块)
├── database/     数据库操作
├── utils/        工具函数
├── core/         核心逻辑
└── ...

programs/         可执行程序 (依赖 src/)
scripts/          工具脚本 (可独立运行)
tests/            测试代码
config/           配置文件
docs/             文档
```

### 文件修改规则
- ✅ **src/** 内的文件修改需谨慎，可能影响多个 programs
- ✅ **programs/** 和 **scripts/** 可独立修改
- ✅ **config/** 包含敏感信息，需加入 .gitignore
- ✅ **tests/** 应随代码同步更新

### 不应修改的文件
- `.gitignore` - 需要的话告诉我
- `requirements.txt` - 需要的话告诉我，别直接编辑

---

## 🔧 4. 开发命令

### 环境设置
```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 开发模式安装
pip install -e .
```

### 运行程序
```bash
# 菜单式运行
python main_menu.py

# 直接运行某个 program
python programs/program_name.py

# 运行某个 script
python scripts/script_name.py
```

### 代码质量
```bash
# 代码格式化 (可选，如果配置了)
black src/ programs/ scripts/

# 导入排序 (可选)
isort src/ programs/ scripts/

# 代码检查 (可选)
flake8 src/ programs/ scripts/

# 类型检查 (可选)
mypy src/
```

### 测试
```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_xxx.py

# 查看覆盖率
pytest --cov=src tests/
```

### 调试
```bash
# 启用详细日志
LOGLEVEL=DEBUG python programs/program_name.py

# 交互式调试
python -m pdb programs/program_name.py
```

---

## 📝 5. 编码标准

### Python 风格
- **遵循**: PEP 8 (Python 官方编码规范)
- **格式**: 使用 Black 或 autopep8
- **命名**: snake_case 用于函数/变量，CamelCase 用于类

### 文档字符串
```python
def function_name(param1: str, param2: int) -> bool:
    """简单的一句功能描述。

    更详细的描述（如果需要）。

    Args:
        param1: 参数1描述
        param2: 参数2描述

    Returns:
        返回值描述

    Raises:
        ValueError: 异常情况描述
    """
    pass
```

### 类型提示
```python
from typing import List, Dict, Optional

def process_data(items: List[str], config: Dict[str, int]) -> Optional[str]:
    pass
```

### 导入顺序
```python
# 标准库
import os
import sys
from pathlib import Path

# 第三方库
import requests
import numpy as np

# 项目内导入
from src.utils import helper
from src.database import manager
```

### 异常处理
```python
try:
    result = operation()
except SpecificException as e:
    logger.error(f"特定错误: {e}")
    raise
except Exception as e:
    logger.error(f"未预期的错误: {e}")
    raise
finally:
    cleanup()
```

---

## ⚙️ 6. 项目特定指引

### 关键文件
```
[列出项目最重要的文件和它们的用途]
```

### 常见修改位置
```
添加新功能 → [文件1] + [文件2]
修改配置 → [配置文件]
修改数据模型 → [模型文件]
```

### 已知问题与限制
```
- [已知问题1]: [说明和解决方案]
- [已知问题2]: [说明和解决方案]
```

### 敏感信息处理
```
- API 密钥: 应使用环境变量或密钥管理系统
- 数据库凭证: 不应硬编码在代码中
- 配置文件: .env 应加入 .gitignore
```

---

## 🚀 7. 常见任务

### 任务 1: [具体任务]
1. 修改 [文件]
2. 更新 [配置]
3. 运行 `[命令]` 测试

### 任务 2: [具体任务]
1. 步骤 1
2. 步骤 2
3. 步骤 3

### 调试技巧
- 启用日志: `LOGLEVEL=DEBUG`
- 查看数据库: 使用 SQLite 浏览器
- 检查变量: 在关键位置添加 `logger.debug()`

---

## 📌 8. 重要约束

### 必须遵守
- ✅ 所有新代码必须包含文档字符串
- ✅ 修改 src/ 的代码需要考虑向后兼容性
- ✅ 大型数据操作应添加进度提示
- ✅ 敏感操作应记录到日志

### 禁止事项
- ❌ 不得在代码中硬编码 API 密钥或密码
- ❌ 不得直接修改数据库（应通过 ORM）
- ❌ 不得忽略异常（catch 后必须处理或重新抛出）
- ❌ 不得删除代码（改用版本控制）

### 代码审查清单
- [ ] 代码符合 PEP 8
- [ ] 有适当的文档字符串
- [ ] 有类型提示
- [ ] 异常处理完整
- [ ] 没有硬编码的敏感信息
- [ ] 测试已添加或更新
- [ ] 日志记录适当

---

## 🔍 9. 特殊说明

### 处理 .gitignore 的方式
当需要修改 .gitignore 时，我会：
1. 先询问你是否需要修改
2. 显示计划的改动
3. 等你确认后才执行

### 处理 requirements.txt 的方式
当需要修改依赖时，我会：
1. 告诉你想添加/删除的包
2. 显示版本信息
3. 等你确认后才修改

### 处理数据库迁移的方式
当需要修改数据库结构时，我会：
1. 提出迁移方案
2. 创建备份建议
3. 创建迁移脚本而不是直接修改

### 处理敏感信息的方式
当发现敏感信息时，我会：
1. ⚠️ 立即提醒
2. 建议加入 .gitignore
3. 不会向任何人泄露

---

## 📊 10. 项目健康指标

### 理想状态
```
代码覆盖率: > 80%
文档完整度: > 90%
类型检查通过: 100%
静态检查通过: 100%
```

### 监控方式
```bash
# 覆盖率报告
pytest --cov=src --cov-report=html tests/

# 代码复杂度
radon cc src/ --average

# 依赖审计
pip audit
```

---

## 🔗 11. 链接和资源

### 官方文档
- [PEP 8 - Python 编码规范](https://pep8.org/)
- [Python 类型提示](https://docs.python.org/3/library/typing.html)
- [pytest 文档](https://docs.pytest.org/)

### 本项目文档
- [完整代码分析](./CODE_ANALYSIS.md)
- [项目特定指引](./PROJECT_GUIDE.md) (如果存在)
- [快速开始指南](./QUICKSTART.md) (如果存在)

---

## 📝 更新日志

- **[日期]** - 初版
- **[日期]** - 更新说明

---

## 💡 如何使用本文档

1. **首次使用**: 完整阅读 1-3 章
2. **日常开发**: 参考 4-7 章
3. **遇到问题**: 查看 8-9 章
4. **添加新功能**: 按照 7 章的常见任务步骤

---

*这是一个通用模板。项目可根据需要增删章节。*
