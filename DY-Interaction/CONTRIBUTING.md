# 贡献指南

感谢你对 DY-Interaction 项目的贡献兴趣！

## 开发环境设置

### 1. Fork 和 Clone

```bash
git clone https://github.com/your-username/ATUO.git
cd ATUO
```

### 2. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
make install
# 或
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的配置
```

## 代码规范

### 代码风格

我们使用以下工具确保代码质量：

- **Black**: 代码格式化
- **isort**: import排序
- **flake8**: 代码检查
- **mypy**: 类型检查

### 运行代码检查

```bash
# 自动格式化代码
make format

# 运行所有检查
make lint

# 运行测试
make test

# 完整检查（lint + test）
make check
```

### 提交前检查清单

- [ ] 代码通过 `make lint`
- [ ] 测试通过 `make test`
- [ ] 添加了必要的文档
- [ ] 更新了相关的 README
- [ ] 提交信息清晰明了

## 提交信息规范

使用以下格式：

```
[类型] 简短描述

详细描述（可选）

相关Issue: #123
```

**类型**:
- `[Feature]` - 新功能
- `[Fix]` - Bug修复
- `[Refactor]` - 代码重构
- `[Docs]` - 文档更新
- `[Test]` - 测试相关
- `[Security]` - 安全改进
- `[Quality]` - 代码质量改进

**示例**:
```
[Feature] Add support for batch comment processing

- Implemented batch processing for multiple comments
- Added rate limiting to prevent API throttling
- Updated documentation

Related Issue: #42
```

## Pull Request 流程

### 1. 创建分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/bug-description
```

### 2. 开发和测试

在你的分支上进行开发，确保：
- 代码通过所有检查
- 添加了必要的测试
- 文档已更新

### 3. 提交更改

```bash
git add .
git commit -m "[Feature] Your feature description"
git push origin feature/your-feature-name
```

### 4. 创建 Pull Request

在 GitHub 上创建 PR，包含：
- 清晰的标题和描述
- 相关的 Issue 编号
- 测试截图（如适用）
- 变更清单

### 5. 代码审查

- 响应审查意见
- 进行必要的修改
- 保持 PR 更新

## 开发指南

### 项目结构

```
ATUO/
├── src/              # 核心源代码
│   ├── crawler/      # 爬虫模块
│   ├── executor/     # 执行器模块
│   ├── database/     # 数据库模块
│   └── utils/        # 工具函数
├── programs/         # 主程序入口
├── scripts/          # 工具脚本
├── tests/            # 测试文件
└── config/           # 配置文件
```

### 添加新功能

1. **规划**: 在 Issue 中讨论你的想法
2. **设计**: 考虑模块化和可测试性
3. **实现**: 编写代码和测试
4. **文档**: 更新相关文档
5. **审查**: 提交 PR 并响应反馈

### 修复 Bug

1. **重现**: 创建测试用例重现 bug
2. **定位**: 使用调试工具定位问题
3. **修复**: 编写修复代码
4. **验证**: 确保测试通过
5. **文档**: 在提交信息中描述修复

### 编写测试

```python
# tests/test_example.py
import pytest
from src.your_module import YourClass

def test_your_function():
    """测试描述"""
    # 准备
    obj = YourClass()

    # 执行
    result = obj.your_function()

    # 验证
    assert result == expected_value
```

运行测试：
```bash
pytest tests/test_example.py -v
```

## 安全注意事项

- **永远不要提交敏感信息**（API密钥、密码等）
- 使用 `.env` 文件存储配置
- 定期运行安全扫描：`make security`
- 报告安全问题请私下联系维护者

## 文档

### 代码注释

使用 Google 风格的文档字符串：

```python
def function_name(param1: str, param2: int) -> bool:
    """函数的简短描述

    更详细的描述（可选）

    Args:
        param1: 参数1的描述
        param2: 参数2的描述

    Returns:
        返回值的描述

    Raises:
        ValueError: 何时抛出此异常
    """
    pass
```

### 更新文档

修改代码时，同时更新：
- 函数/类的文档字符串
- README.md（如果影响使用方式）
- 相关的 .md 文档

## 获取帮助

- 查看 [README.md](./README.md)
- 查看 [CODE_ANALYSIS.md](./CODE_ANALYSIS.md)
- 查看 [CLAUDE.md](./CLAUDE.md)
- 提交 Issue 询问

## 许可证

通过贡献代码，你同意你的贡献将在与项目相同的许可证下发布。

---

感谢你的贡献！ 🎉
