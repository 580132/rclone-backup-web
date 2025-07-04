#!/bin/bash

# Docker容器启动脚本

echo "=== RClone备份Web系统 Docker启动 ==="

# 检查Docker环境
if [ "$DOCKER_ENV" = "true" ]; then
    echo "✓ 检测到Docker环境"
    
    # 检查Docker socket是否可用
    if [ -S /var/run/docker.sock ]; then
        echo "✓ Docker socket可用"
    else
        echo "⚠ Docker socket不可用，rclone功能可能受限"
    fi
    
    # 检查rclone容器是否运行
    if docker ps --format "table {{.Names}}" | grep -q "rclone-service"; then
        echo "✓ rclone服务容器正在运行"
    else
        echo "⚠ rclone服务容器未运行，尝试启动..."
        # 这里可以添加启动rclone容器的逻辑
    fi
else
    echo "✓ 非Docker环境，使用本地rclone"
fi

# 创建必要的目录
mkdir -p /app/data/temp
mkdir -p /app/logs
mkdir -p /app/data/rclone_configs

echo "✓ 目录结构检查完成"

# 设置权限
chmod -R 755 /app/data
chmod -R 755 /app/logs

echo "✓ 权限设置完成"

# 启动应用
echo "✓ 启动应用..."
exec "$@"
