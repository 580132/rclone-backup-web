# RClone备份Web系统

一个基于rclone的Linux文件备份管理系统，提供Web界面进行备份任务的创建、管理和监控。

## ✨ 主要特性

- 🔐 **简单认证**: 基础登录系统，无复杂权限管理
- ☁️ **多云存储**: 基于rclone支持70+种云存储服务
- 📅 **定时备份**: 基于Cron表达式的灵活调度
- 🔒 **加密压缩**: AES-256加密 + tar.gz压缩
- 📊 **任务监控**: 备份状态监控和日志查看
- 📤 **配置管理**: 存储配置和任务管理
- 🎨 **简洁界面**: 基于Flask + Bootstrap的Web界面

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
        │   rclone命令     │  │   文件处理      │
        │   (云存储)       │  │  (压缩/加密)    │
        └─────────────────┘  └─────────────────┘
```

## 🛠️ 技术栈

### 后端
- **框架**: Flask + SQLAlchemy + Jinja2
- **认证**: Session-based认证
- **任务调度**: APScheduler
- **文件处理**: Python原生SDK + cryptography
- **数据库**: SQLite

### 前端
- **模板引擎**: Jinja2
- **UI框架**: Bootstrap 5
- **图标**: Bootstrap Icons
- **JavaScript**: jQuery

### 部署
- **容器化**: Docker + Docker Compose
- **Web服务器**: Nginx
- **进程管理**: Supervisor

## 📋 功能模块

### 1. 用户管理
- 用户注册/登录
- 权限分级（普通用户/管理员）
- 个人信息管理

### 2. 存储配置
- rclone配置管理
- 支持主流云存储服务
- 连接测试功能
- 配置加密存储

### 3. 备份任务
- 任务创建和编辑
- Cron表达式调度
- 文件路径选择
- 压缩和加密设置
- 保留策略配置

### 4. 任务监控
- 实时状态监控
- 执行日志查看
- 进度跟踪
- 错误报告

### 5. 系统管理
- 任务配置导出/导入
- 系统状态监控
- 日志管理
- 用户管理（管理员）

## 🚀 快速开始

### 环境要求
- **操作系统**: Linux (推荐Ubuntu 20.04+)
- **Python**: 3.7+
- **rclone**: 1.50+
- **浏览器**: 现代浏览器

### 安装步骤

1. **安装rclone**
```bash
# Linux/macOS
curl https://rclone.org/install.sh | sudo bash

# 或使用包管理器
sudo apt install rclone  # Ubuntu/Debian
brew install rclone      # macOS
```

2. **安装Python依赖**
```bash
# 克隆或下载项目
cd rclone-backup-web

# 安装依赖
pip install -r requirements.txt
```

3. **启动系统**

**方法1: Docker部署（推荐）**
```bash
# 使用Docker Compose启动
docker-compose up -d
```

**方法2: 本地部署**
```bash
# 启动系统
python3 run.py
```

4. **访问系统**
- 打开浏览器访问: http://localhost:5000
- 默认用户名: `admin`
- 默认密码: `admin123`

## 📖 文档

- [🐳 Docker部署指南](./DOCKER_DEPLOYMENT.md) - Docker容器化部署完整指南
- [🧪 测试教程](./TESTING_GUIDE.md) - 完整的测试指南和故障排除
- [📋 系统设计](./SIMPLIFIED_DESIGN.md) - 系统设计和架构说明
- [🚀 安装指南](./INSTALL_GUIDE.md) - 详细的安装和配置说明
- [⚡ 快速开始](./QUICK_START_GUIDE.md) - 快速上手指南

## 🔧 配置说明

### 环境变量
```env
# Flask配置
FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///backup_system.db

# JWT配置
JWT_SECRET_KEY=your-jwt-secret

# rclone配置
RCLONE_CONFIG_DIR=/app/rclone_configs
BACKUP_TEMP_DIR=/tmp/backups

# 其他配置
MAX_BACKUP_SIZE=10GB
DEFAULT_RETENTION_DAYS=30
```

### 存储配置
系统通过Web界面配置rclone，支持的存储类型包括：

**当前支持**：
- Amazon S3 (及S3兼容存储如阿里云OSS)
- FTP/SFTP

**计划支持**：
- Google Drive
- Microsoft OneDrive
- Dropbox
- 其他rclone支持的70+种存储服务

## 🔒 安全特性

- **密码加密**: 使用bcrypt进行密码哈希
- **JWT认证**: 无状态的Token认证
- **配置加密**: rclone配置文件加密存储
- **文件加密**: AES-256-GCM加密备份文件
- **权限控制**: 基于角色的访问控制
- **输入验证**: 严格的输入验证和过滤

## 📊 监控和日志

### 系统监控
- 任务执行状态
- 系统资源使用
- 存储空间监控
- 错误率统计

### 日志管理
- 应用日志轮转
- 备份操作日志
- 错误日志记录
- 审计日志跟踪

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 开发规范
- 遵循PEP 8 (Python) 和 ESLint (JavaScript) 代码规范
- 编写单元测试
- 更新相关文档
- 使用Conventional Commits提交信息格式

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [rclone](https://rclone.org/) - 强大的云存储同步工具
- [Flask](https://flask.palletsprojects.com/) - 轻量级Web框架
- [Vue.js](https://vuejs.org/) - 渐进式JavaScript框架
- [Element Plus](https://element-plus.org/) - Vue 3组件库

## 📞 支持

如果您遇到问题或有建议，请：

1. 查看 [FAQ](./docs/FAQ.md)
2. 搜索 [Issues](https://github.com/your-username/rclone-backup-web/issues)
3. 创建新的 Issue
4. 联系维护者

---

⭐ 如果这个项目对您有帮助，请给我们一个星标！
