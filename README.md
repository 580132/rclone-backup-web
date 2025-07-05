# RClone备份Web系统

一个基于rclone的文件备份管理系统，提供Web界面进行备份任务的创建、管理和监控。支持Docker部署和多种云存储服务。

## ✨ 主要特性

- 🔐 **简单认证**: Session-based登录系统
- ☁️ **多云存储**: 支持9种主流云存储服务（S3、阿里云OSS、Google Drive等）
- 📅 **定时备份**: 基于Cron表达式的灵活调度
- 🔒 **加密压缩**: AES-256加密 + tar.gz压缩
- 📊 **任务监控**: 实时备份状态监控和详细日志查看
- 📤 **多目标备份**: 单个任务支持同时备份到多个存储目标
- 🐳 **Docker部署**: 完整的Docker容器化部署方案
- 🎨 **简洁界面**: 基于Flask + Bootstrap的响应式Web界面

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Flask Web应用                        │
├─────────────────┬─────────────────┬─────────────────────┤
│   HTML模板      │    路由处理      │    业务逻辑         │
│  (Jinja2)       │   (Flask)       │   (Services)        │
└─────────────────┴─────────────────┴─────────────────────┘
                           │
                  ┌────────┴────────┐
                  │                 │
        ┌─────────────────┐  ┌─────────────────┐
        │   SQLite数据库   │  │   APScheduler   │
        │   (任务配置)     │  │   (定时调度)     │
        └─────────────────┘  └─────────────────┘
                           │
                  ┌────────┴────────┐
                  │                 │
        ┌─────────────────┐  ┌─────────────────┐
        │  RClone容器      │  │   文件处理      │
        │   (云存储)       │  │  (压缩/加密)    │
        └─────────────────┘  └─────────────────┘
```

## 🛠️ 技术栈

### 后端
- **框架**: Flask 2.3.3 + SQLAlchemy 3.0.5
- **认证**: Session-based认证
- **任务调度**: APScheduler 3.10.4
- **文件处理**: cryptography 41.0.4
- **数据库**: SQLite
- **时区处理**: pytz 2023.3

### 前端
- **模板引擎**: Jinja2
- **UI框架**: Bootstrap 5
- **图标**: Bootstrap Icons
- **JavaScript**: 原生JavaScript + 少量jQuery

### 部署
- **容器化**: Docker + Docker Compose
- **存储后端**: RClone容器

## 📋 功能模块

### 1. 用户认证
- 用户登录/登出
- Session-based认证
- 密码修改

### 2. 存储配置管理
- 支持9种存储类型的配置
- 可视化配置界面
- 配置测试功能
- 配置历史记录
- 模块化存储类型架构

### 3. 备份任务管理
- 任务创建和编辑
- 多存储目标支持（单个任务可备份到多个存储）
- Cron表达式调度（支持可视化编辑）
- 目录树文件路径选择
- 压缩和加密设置
- 基于文件数量的保留策略

### 4. 任务监控
- 实时备份状态监控
- 详细执行日志查看
- 异步任务执行
- 调度器状态监控

### 5. 系统设置
- 管理员密码修改
- 完整数据导出/导入（加密）
- 系统配置管理

## 🚀 快速开始

### 环境要求
- **Docker**: 推荐使用Docker部署
- **Python**: 3.7+ (本地部署)
- **浏览器**: 现代浏览器

### Docker部署（推荐）

1. **克隆项目**
```bash
git clone https://github.com/dong-dong6/rclone-backup-web.git
cd rclone-backup-web
```

2. **启动服务**
```bash
# 使用Docker Compose启动
docker-compose up -d
```

3. **访问系统**
- 打开浏览器访问: http://localhost:5000
- 默认用户名: `admin`
- 默认密码: `admin123`

### 本地部署

1. **安装依赖**
```bash
# 安装Python依赖
pip install -r requirements.txt
```

2. **启动系统**
```bash
# 启动系统
python3 run.py
```

**注意**: 本地部署需要系统已安装rclone命令行工具。

## 🔧 支持的存储类型

系统通过模块化架构支持以下存储类型：

- **Amazon S3** - AWS S3及S3兼容存储
- **阿里云OSS** - 阿里云对象存储服务
- **Cloudflare R2** - Cloudflare R2存储
- **Google Drive** - Google云端硬盘
- **MinIO** - 开源对象存储
- **SFTP** - SSH文件传输协议
- **FTP** - 文件传输协议
- **WebDAV** - Web分布式创作和版本控制
- **原始RClone配置** - 支持直接输入rclone配置

## 🔧 配置说明

### Docker环境变量
```env
# Flask配置
FLASK_ENV=production
SECRET_KEY=your-secret-key-change-this
DATABASE_URL=sqlite:////app/data/database.db

# Docker环境标识
DOCKER_ENV=true

# rclone配置
RCLONE_CONFIG_DIR=/app/data/rclone_configs
```

### Docker Compose配置要点

- **数据持久化**: `./data` 和 `./logs` 目录挂载
- **文件访问**: 宿主机根目录挂载到 `/host` (只读)
- **RClone服务**: 独立的rclone容器提供存储服务
- **网络**: 使用bridge网络连接主应用和rclone容器

## 🔒 安全特性

- **密码加密**: 使用Werkzeug进行密码哈希
- **Session认证**: 基于Flask Session的安全认证
- **文件加密**: AES-256加密备份文件
- **数据加密**: 系统数据导出时完整加密
- **输入验证**: 严格的数据验证和过滤
- **容器隔离**: Docker容器化部署提供安全隔离

## 📊 监控和日志

### 任务监控
- 备份任务执行状态
- 实时日志查看
- 调度器状态监控
- 任务执行历史

### 日志系统
- 详细的备份操作日志
- 系统错误日志记录
- 文件和控制台双重输出
- 支持不同日志级别

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 开发规范
- 遵循PEP 8 Python代码规范
- 更新相关文档
- 测试新功能的完整性

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [rclone](https://rclone.org/) - 强大的云存储同步工具
- [Flask](https://flask.palletsprojects.com/) - 轻量级Web框架
- [Bootstrap](https://getbootstrap.com/) - 响应式CSS框架
- [APScheduler](https://apscheduler.readthedocs.io/) - Python任务调度库

## 📞 支持

如果您遇到问题或有建议，请：

1. 搜索 [Issues](https://github.com/dong-dong6/rclone-backup-web/issues)
2. 创建新的 Issue
3. 联系维护者

---

⭐ 如果这个项目对您有帮助，请给我们一个星标！
