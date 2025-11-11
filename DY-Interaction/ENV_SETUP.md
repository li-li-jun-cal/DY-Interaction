# 环境变量配置说明

本项目使用环境变量来管理敏感配置信息，避免将密钥、Cookie等敏感数据提交到Git仓库。

## 快速开始

### 1. 创建配置文件

```bash
# 复制示例文件
cp .env.example .env

# 编辑配置文件，填写实际值
nano .env  # 或使用你喜欢的编辑器
```

### 2. 必填配置项

以下配置项是必须的：

- `DOUYIN_API_KEY` - 抖音API密钥
- `DOUYIN_COOKIE` - 抖音Cookie（用于爬虫）
- `DATABASE_URL` - 数据库路径

### 3. 可选配置项

以下配置项有默认值，可根据需要修改：

- `API_RATE_LIMIT` - API限流设置（默认10/秒）
- `LOG_LEVEL` - 日志级别（默认INFO）
- `DAILY_*_QUOTA` - 每日操作配额

## 使用方法

### Python代码中读取环境变量

```python
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 读取配置
api_key = os.getenv('DOUYIN_API_KEY')
cookie = os.getenv('DOUYIN_COOKIE')

# 带默认值读取
log_level = os.getenv('LOG_LEVEL', 'INFO')
```

### 安装依赖

```bash
pip install python-dotenv
```

## 安全提示

⚠️ **重要：不要将 .env 文件提交到Git仓库！**

- `.env` 文件已被添加到 `.gitignore`
- 仅提交 `.env.example` 作为模板
- 定期检查：`git status` 确保 .env 未被跟踪

## 迁移现有配置

如果你已经有 `config/config.json`，可以这样迁移：

### 1. 备份现有配置

```bash
cp config/config.json config/config.json.backup
```

### 2. 提取敏感信息到 .env

从 `config.json` 中提取以下信息并添加到 `.env`：

```json
{
  "api_key": "xxxx"  → DOUYIN_API_KEY=xxxx
  "cookie": "xxxx"   → DOUYIN_COOKIE=xxxx
}
```

### 3. 更新代码读取方式

修改配置读取代码，优先从环境变量读取：

```python
# 旧方式
config = json.load(open('config/config.json'))
api_key = config['api_key']

# 新方式
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('DOUYIN_API_KEY')

# 兼容旧配置（可选）
if not api_key:
    config = json.load(open('config/config.json'))
    api_key = config.get('api_key')
```

## 检查配置

运行以下命令检查配置是否正确加载：

```bash
python -c "
from dotenv import load_dotenv
import os

load_dotenv()
print('API Key:', 'OK' if os.getenv('DOUYIN_API_KEY') else 'Missing')
print('Cookie:', 'OK' if os.getenv('DOUYIN_COOKIE') else 'Missing')
print('Database:', os.getenv('DATABASE_URL', 'Using default'))
"
```

## 常见问题

### Q: .env 文件不生效？
A: 确保在代码开头调用了 `load_dotenv()`

### Q: 如何在Docker中使用？
A: 使用 `docker-compose.yml` 的 `env_file` 选项：

```yaml
services:
  app:
    env_file:
      - .env
```

### Q: 生产环境如何配置？
A: 生产环境建议使用系统环境变量或密钥管理服务（如AWS Secrets Manager），而不是 .env 文件

## 相关文件

- `.env.example` - 环境变量配置模板
- `.gitignore` - 确保 .env 不被提交
- `config/config.json` - 旧的配置方式（建议迁移）

---

*创建日期: 2025-11-10*
*最后更新: 2025-11-10*
