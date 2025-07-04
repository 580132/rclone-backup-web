# Docker部署指南

本项目支持使用Docker进行部署，提供了完整的容器化解决方案。

## 🐳 Docker部署特性

- **官方rclone镜像**: 使用rclone官方Docker镜像，确保版本稳定
- **外挂配置文件**: rclone配置文件外挂，便于管理和备份
- **自动环境检测**: 代码自动检测Docker环境，调整rclone调用方式
- **数据持久化**: 数据库、日志、配置文件持久化存储
- **网络隔离**: 使用Docker网络确保服务间通信安全

## 📋 部署要求

- Docker Engine 20.10+
- Docker Compose 2.0+
- 至少2GB可用内存
- 至少5GB可用磁盘空间

## 🚀 快速部署

### 1. 克隆项目
```bash
git clone <repository-url>
cd rclone-backup-web
```

### 2. 验证部署环境（可选）
```bash
# 运行部署验证脚本
chmod +x verify_docker_deployment.sh
./verify_docker_deployment.sh
```

### 3. 配置环境变量
复制并编辑docker-compose.yml中的环境变量：
```yaml
environment:
  - SECRET_KEY=your-secret-key-change-this  # 修改为随机密钥
  - DATABASE_URL=sqlite:///data/database.db
  - LOG_LEVEL=INFO
```

### 4. 创建数据目录
```bash
mkdir -p data/rclone_configs
mkdir -p data/temp
mkdir -p logs
mkdir -p backup-sources
```

### 5. 启动服务
```bash
docker-compose up -d
```

### 6. 验证部署
```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs backup-web
```

### 7. 访问系统
- 访问地址: http://localhost:5000
- 默认用户名: `admin`
- 默认密码: `admin123`

## 📁 目录结构

```
rclone-backup-web/
├── data/                    # 数据目录（持久化）
│   ├── rclone_configs/     # rclone配置文件
│   ├── temp/               # 临时文件
│   └── database.db         # SQLite数据库
├── logs/                   # 日志目录（持久化）
├── backup-sources/         # 备份源目录（可选）
├── docker-compose.yml      # Docker Compose配置
├── Dockerfile             # 主应用镜像
└── docker-entrypoint.sh   # 容器启动脚本
```

## ⚙️ 配置说明

### Docker Compose配置

主要服务：
- **backup-web**: 主应用容器
- **rclone**: rclone服务容器

重要配置项：
```yaml
volumes:
  - ./data:/app/data                           # 数据持久化
  - ./logs:/app/logs                          # 日志持久化
  - /var/run/docker.sock:/var/run/docker.sock # Docker socket
  - ./data/rclone_configs:/app/data/rclone_configs # rclone配置
```

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `DOCKER_ENV` | `true` | Docker环境标识 |
| `RCLONE_CONTAINER_NAME` | `rclone-service` | rclone容器名称 |
| `RCLONE_CONFIG_DIR` | `/app/data/rclone_configs` | rclone配置目录 |
| `SECRET_KEY` | - | Flask密钥（必须修改） |
| `DATABASE_URL` | `sqlite:///data/database.db` | 数据库连接 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

## 🔧 高级配置

### 自定义rclone镜像版本
```yaml
rclone:
  image: rclone/rclone:1.64.0  # 指定版本
```

### 添加备份源目录
```yaml
volumes:
  - /path/to/your/data:/backup-sources/data:ro
  - /path/to/your/configs:/backup-sources/configs:ro
```

### 修改端口
```yaml
ports:
  - "8080:5000"  # 映射到8080端口
```

## 🛠️ 管理命令

### 查看服务状态
```bash
docker-compose ps
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs backup-web
docker-compose logs rclone
```

### 重启服务
```bash
docker-compose restart
```

### 停止服务
```bash
docker-compose down
```

### 更新服务
```bash
# 重新构建并启动
docker-compose up -d --build
```

## 🔍 故障排除

### 1. rclone容器无法启动
检查Docker socket权限：
```bash
ls -la /var/run/docker.sock
sudo chmod 666 /var/run/docker.sock
```

### 2. 配置文件权限问题
设置正确的目录权限：
```bash
sudo chown -R 1000:1000 data/
sudo chmod -R 755 data/
```

### 3. 端口冲突
修改docker-compose.yml中的端口映射：
```yaml
ports:
  - "5001:5000"  # 使用其他端口
```

### 4. 查看详细日志
```bash
# 查看容器内部日志
docker exec -it rclone-backup-web tail -f /app/logs/app.log

# 查看rclone容器日志
docker exec -it rclone-service rclone version
```

## 📊 监控和维护

### 数据备份
定期备份重要数据：
```bash
# 备份数据库
cp data/database.db data/database.db.backup

# 备份rclone配置
tar -czf rclone-configs-backup.tar.gz data/rclone_configs/
```

### 日志轮转
配置日志轮转防止日志文件过大：
```bash
# 添加到crontab
0 0 * * * find /path/to/logs -name "*.log" -size +100M -delete
```

## 🔒 安全建议

1. **修改默认密码**: 首次登录后立即修改admin密码
2. **使用强密钥**: 设置复杂的SECRET_KEY
3. **限制网络访问**: 使用防火墙限制访问端口
4. **定期更新**: 定期更新Docker镜像
5. **备份配置**: 定期备份rclone配置和数据库

## 📝 注意事项

- Docker环境中rclone命令通过容器执行，性能可能略低于本地安装
- 确保Docker有足够权限访问备份源目录
- 大文件备份时注意磁盘空间和网络带宽
- 生产环境建议使用外部数据库（如PostgreSQL）
