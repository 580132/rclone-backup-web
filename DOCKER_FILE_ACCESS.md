# Docker环境文件访问解决方案

## 🤔 问题分析

你提出的问题非常关键：

1. **容器内的Python程序能访问到要备份的文件夹吗？**
2. **压缩好的临时文件夹能被rclone访问到吗？**

## ✅ 统一路径解决方案

### 核心思路
- **Docker环境**: 将宿主机根目录挂载到容器的`/host`目录
- **本地环境**: 直接访问根目录`/`
- **代码统一**: 通过路径转换函数实现环境无关的代码

## ✅ 解决方案

### 1. 备份源文件访问

#### 问题
- Docker容器默认是隔离的，无法访问宿主机文件系统
- Python程序需要读取宿主机上的文件进行备份

#### 解决方案
通过Docker卷挂载将宿主机根目录映射到容器的`/host`目录：

```yaml
# docker-compose.yml
volumes:
  # 将宿主机根目录挂载到容器的/host目录
  - /:/host:ro
```

#### 代码适配
添加了路径转换函数，实现环境无关的代码：

```python
# config.py
@staticmethod
def get_host_path(path: str) -> str:
    """获取宿主机路径"""
    if Config.DOCKER_ENV and Config.HOST_ROOT_PREFIX:
        if path.startswith('/'):
            return Config.HOST_ROOT_PREFIX + path  # /home -> /host/home
    return path

@staticmethod
def get_display_path(path: str) -> str:
    """获取显示路径"""
    if Config.DOCKER_ENV and path.startswith(Config.HOST_ROOT_PREFIX):
        return path[len(Config.HOST_ROOT_PREFIX):] or '/'  # /host/home -> /home
    return path
```

### 2. 临时文件共享

#### 问题
- Python程序在容器内创建压缩文件
- rclone容器需要访问这些临时文件进行上传

#### 解决方案
两个容器共享同一个临时目录：

```yaml
# backup-web容器
volumes:
  - ./data/temp:/app/data/temp

# rclone容器  
volumes:
  - ./data/temp:/data/temp
```

#### 路径映射
在`RcloneService`中实现了路径自动映射：

```python
def _build_rclone_command(self, rclone_args, local_paths=None):
    if self.docker_env:
        # 将主机路径映射到容器内路径
        for arg in rclone_args:
            if arg.startswith('/app/data/temp'):
                # 映射到rclone容器内的路径
                container_path = arg.replace('/app/data/temp', '/data/temp')
```

## 📁 目录映射关系

### backup-web容器
```
宿主机路径              →  容器内路径
/home                  →  /backup-sources/home
/etc                   →  /backup-sources/etc
./data/temp            →  /app/data/temp
./data/rclone_configs  →  /app/data/rclone_configs
```

### rclone容器
```
宿主机路径              →  容器内路径
/home                  →  /backup-sources/home
/etc                   →  /backup-sources/etc
./data/temp            →  /data/temp
./data/rclone_configs  →  /config/rclone
```

## 🔄 工作流程

1. **用户选择备份源**
   - Web界面显示`/backup-sources/`下的目录
   - 用户选择要备份的路径（如`/backup-sources/home/user1`）

2. **Python程序创建备份**
   - 读取`/backup-sources/home/user1`中的文件
   - 压缩到`/app/data/temp/backup.tar.gz`

3. **rclone上传文件**
   - 通过`docker exec`调用rclone容器
   - rclone从`/data/temp/backup.tar.gz`读取文件
   - 上传到远程存储

## 🛡️ 安全考虑

### 只读挂载
```yaml
volumes:
  - /home:/backup-sources/home:ro  # :ro 表示只读
```

### 最小权限原则
```yaml
# 推荐：只挂载需要的目录
- /home:/backup-sources/home:ro
- /etc:/backup-sources/etc:ro

# 不推荐：挂载整个根目录
- /:/host-root:ro
```

## 🧪 验证方法

### 1. 使用验证脚本
```bash
chmod +x verify_docker_deployment.sh
./verify_docker_deployment.sh
```

### 2. 使用文件访问测试
```bash
chmod +x test_file_access.sh
./test_file_access.sh
```

### 3. 手动验证
```bash
# 检查backup-web容器能否访问备份源
docker exec rclone-backup-web ls -la /backup-sources/

# 检查rclone容器能否访问备份源
docker exec rclone-service ls -la /backup-sources/

# 测试临时文件共享
docker exec rclone-backup-web touch /app/data/temp/test.txt
docker exec rclone-service ls -la /data/temp/test.txt
```

## 📋 配置检查清单

- [ ] 两个容器的备份源目录挂载一致
- [ ] 临时目录在两个容器间共享
- [ ] rclone配置目录正确挂载
- [ ] 使用只读挂载保护宿主机文件
- [ ] 验证文件访问权限正常

## 🚨 常见问题

### 问题1：权限拒绝
```bash
# 解决方案：检查目录权限
sudo chmod -R 755 ./data/
```

### 问题2：文件不存在
```bash
# 解决方案：检查卷挂载配置
docker-compose config
```

### 问题3：路径映射错误
```bash
# 解决方案：确保两个容器配置一致
grep -A 10 "volumes:" docker-compose.yml
```

## 🎯 总结

通过以上解决方案：

1. ✅ **容器内Python程序可以访问备份文件夹**
   - 通过卷挂载将宿主机目录映射到容器内
   - 代码自动适配Docker环境的路径结构

2. ✅ **rclone可以访问压缩的临时文件**
   - 两个容器共享临时目录
   - 自动处理路径映射和转换

3. ✅ **安全性得到保障**
   - 使用只读挂载保护宿主机文件
   - 最小权限原则，只挂载必要目录

4. ✅ **易于配置和验证**
   - 提供多种配置模板
   - 完整的验证和测试脚本
