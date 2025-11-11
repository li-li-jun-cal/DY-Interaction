# DY-Interaction 部署指南

本文档说明如何使用 Docker 部署 DY-Interaction 项目。

---

## 📦 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 2GB 可用内存
- 至少 10GB 可用磁盘空间

---

## 🚀 快速开始

### 1. 环境配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入实际配置
nano .env
```

必须配置的环境变量：
- `DOUYIN_API_KEY`: 抖音 API 密钥
- `DOUYIN_API_SERVER`: API 服务器地址
- `DATABASE_URL`: 数据库连接字符串（默认使用 SQLite）

### 2. 构建镜像

```bash
# 构建 Docker 镜像
docker-compose build
```

### 3. 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

---

## 📊 服务架构

### 核心服务

1. **crawler** - 爬虫服务
   - 功能：监控新增评论
   - 命令：`python programs/run_crawler.py monitor --all`
   - 重启策略：unless-stopped

2. **automation-realtime** - 实时自动化
   - 功能：处理监控发现的新增评论
   - 命令：`python programs/run_automation.py realtime --all`
   - 重启策略：unless-stopped

3. **automation-longterm** - 长期自动化
   - 功能：处理3个月前的历史评论
   - 命令：`python programs/run_automation.py longterm --all`
   - 重启策略：unless-stopped

### 可选服务

4. **automation-maintenance** - 养号服务
   - 功能：模拟正常用户行为，维护账号活跃度
   - 启动：`docker-compose --profile maintenance up -d`

---

## 🎛️ 服务管理

### 启动/停止服务

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启特定服务
docker-compose restart crawler

# 停止特定服务
docker-compose stop automation-realtime
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f crawler

# 查看最近100行日志
docker-compose logs --tail=100 automation-realtime
```

### 进入容器

```bash
# 进入爬虫服务容器
docker-compose exec crawler bash

# 进入自动化服务容器
docker-compose exec automation-realtime bash
```

---

## 🔧 自定义配置

### 修改服务模式

编辑 `docker-compose.yml`，修改 `command` 字段：

```yaml
services:
  crawler:
    command: python programs/run_crawler.py history --all  # 改为历史爬虫

  automation-realtime:
    command: python programs/run_automation.py mixed --all  # 改为混合模式
```

### 调整资源限制

```yaml
services:
  crawler:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          memory: 512M
```

### 使用外部数据库

如果使用 PostgreSQL/MySQL 而非 SQLite：

```yaml
services:
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: dy_interaction
      POSTGRES_USER: dyuser
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  crawler:
    depends_on:
      - db
    environment:
      - DATABASE_URL=postgresql://dyuser:${DB_PASSWORD}@db:5432/dy_interaction

volumes:
  postgres_data:
```

---

## 📁 数据持久化

### 数据卷

- `./data` - 数据库文件（SQLite）
- `./logs` - 应用日志
- `./config` - 配置文件（只读）

### 备份数据

```bash
# 备份数据库
docker-compose exec crawler python -c "import shutil; shutil.copy('/app/data/dy_interaction.db', '/app/data/backup_$(date +%Y%m%d).db')"

# 复制备份到本地
docker cp dy-crawler:/app/data/backup_20251110.db ./backups/
```

### 恢复数据

```bash
# 停止所有服务
docker-compose down

# 恢复数据库文件
cp ./backups/backup_20251110.db ./data/dy_interaction.db

# 重启服务
docker-compose up -d
```

---

## 🔍 故障排查

### 服务无法启动

```bash
# 查看服务状态
docker-compose ps

# 查看详细日志
docker-compose logs crawler

# 检查配置文件
docker-compose config
```

### 数据库连接失败

1. 检查 `.env` 文件中的 `DATABASE_URL`
2. 确保数据库服务已启动：`docker-compose ps db`
3. 检查网络连接：`docker-compose exec crawler ping db`

### 权限问题

```bash
# 修改数据目录权限
sudo chown -R 1000:1000 ./data ./logs

# 重启服务
docker-compose restart
```

---

## 🌐 生产环境部署

### 使用 Docker Swarm

```bash
# 初始化 Swarm
docker swarm init

# 部署服务栈
docker stack deploy -c docker-compose.yml dy-interaction

# 查看服务
docker stack services dy-interaction

# 扩展服务
docker service scale dy-interaction_automation-realtime=3
```

### 使用 Kubernetes

1. 将 docker-compose.yml 转换为 K8s 配置：
   ```bash
   kompose convert -f docker-compose.yml
   ```

2. 应用配置：
   ```bash
   kubectl apply -f .
   ```

3. 查看 Pod 状态：
   ```bash
   kubectl get pods
   kubectl logs -f dy-crawler-xxxxx
   ```

---

## 📈 监控和告警

### 集成 Prometheus

添加 Prometheus 导出器：

```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
```

### 日志聚合

使用 ELK Stack 或 Loki 进行日志聚合和分析。

---

## 🔐 安全最佳实践

1. **不要在镜像中包含敏感信息**
   - 使用 `.env` 文件或密钥管理服务
   - 使用 Docker secrets（Swarm 模式）

2. **限制容器权限**
   ```yaml
   security_opt:
     - no-new-privileges:true
   read_only: true
   ```

3. **定期更新基础镜像**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

4. **使用网络隔离**
   - 创建独立的 Docker 网络
   - 限制容器间通信

---

## 📚 更多资源

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [项目 README](./README.md)
- [环境配置指南](./ENV_SETUP.md)
- [贡献指南](./CONTRIBUTING.md)

---

## 🆘 获取帮助

如有问题，请：
1. 查看日志：`docker-compose logs -f`
2. 检查服务状态：`docker-compose ps`
3. 提交 Issue：[项目 Issues](https://github.com/your-repo/issues)

---

*最后更新: 2025-11-10*
*Phase 4: 部署支持*
