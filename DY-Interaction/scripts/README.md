# Scripts - 工具脚本目录

本目录包含所有的工具脚本。

## 活跃脚本 (当前使用)

这些脚本当前正在使用，用于日常维护和管理。

### 数据清理

**cleanup_duplicate_tasks.py** - 清理重复的交互任务
- 使用场景：定期清理数据库中的重复任务
- 用法：`python cleanup_duplicate_tasks.py --auto`
- 频率：每周运行一次

**delete_tasks_without_unique_id.py** - 删除缺陷任务
- 使用场景：数据清理，删除没有unique_id的任务
- 用法：`python delete_tasks_without_unique_id.py --auto`
- 频率：按需运行

### Cookie 管理

**update_server_cookie.py** - 更新服务器 Cookie
- 使用场景：Cookie 过期时更新
- 用法：`python update_server_cookie.py`
- 频率：Cookie失效时运行（通常1-2周）

**update_cookie_pool.py** - 更新 Cookie 池
- 使用场景：维护多个 Cookie 备份
- 用法：`python update_cookie_pool.py`
- 频率：定期更新备用Cookie

### 设备管理

**check_devices.py** - 检查手机设备状态
- 使用场景：监控设备是否在线
- 用法：`python check_devices.py`
- 频率：自动化运行前检查

### API 管理

**manage_api_servers.py** - 管理 API 服务器配置
- 使用场景：切换 API 服务器或添加新服务器
- 用法：`python manage_api_servers.py`
- 频率：按需运行

### 任务管理

**generate_tasks_from_comments.py** - 从评论生成新任务
- 使用场景：批量生成待执行任务
- 用法：`python generate_tasks_from_comments.py --auto`
- 频率：爬虫后运行

## 过期脚本

过期的脚本已移到 archive/ 目录，按类别分类：

- `archive/migrations/` - 数据库迁移脚本 (3个)
- `archive/fixes/` - 数据修复脚本 (7个)
- `archive/setup/` - 初始化脚本 (3个)
- `archive/deprecated/` - 已弃用脚本 (4个)

详见 [`archive/README.md`](./archive/README.md)

## 使用建议

### 日常维护流程

```bash
# 1. 检查设备状态
python scripts/check_devices.py

# 2. 运行爬虫 (通过 main_menu.py)
python main_menu.py

# 3. 清理重复任务
python scripts/cleanup_duplicate_tasks.py --auto

# 4. 检查Cookie是否过期
# 如果过期，运行:
python scripts/update_server_cookie.py
```

### 定期维护

- **每周一次**: cleanup_duplicate_tasks.py
- **每月一次**: update_cookie_pool.py
- **按需**: 其他脚本

## 添加新脚本

如果需要添加新的工具脚本：

1. 放在 scripts/ 根目录
2. 添加文档字符串说明用途
3. 更新本 README
4. 遵循命名规范：`verb_noun.py`

---
*最后更新: 2025-11-10*
*Phase 0.3 重构*
