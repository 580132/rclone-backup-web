#!/bin/bash

# Docker部署验证脚本

echo "=== RClone备份Web系统 Docker部署验证 ==="
echo

# 检查Docker是否安装
echo "1. 检查Docker环境..."
if command -v docker &> /dev/null; then
    echo "✓ Docker已安装: $(docker --version)"
else
    echo "✗ Docker未安装，请先安装Docker"
    exit 1
fi

# 检查Docker Compose是否安装
if command -v docker-compose &> /dev/null; then
    echo "✓ Docker Compose已安装: $(docker-compose --version)"
else
    echo "✗ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

echo

# 检查必要的目录
echo "2. 检查目录结构..."
directories=("data" "data/rclone_configs" "data/temp" "logs")
for dir in "${directories[@]}"; do
    if [ -d "$dir" ]; then
        echo "✓ 目录存在: $dir"
    else
        echo "⚠ 创建目录: $dir"
        mkdir -p "$dir"
    fi
done

echo

# 检查Docker Compose文件
echo "3. 检查配置文件..."
if [ -f "docker-compose.yml" ]; then
    echo "✓ docker-compose.yml存在"
else
    echo "✗ docker-compose.yml不存在"
    exit 1
fi

if [ -f "Dockerfile" ]; then
    echo "✓ Dockerfile存在"
else
    echo "✗ Dockerfile不存在"
    exit 1
fi

echo

# 检查Docker服务状态
echo "4. 检查Docker服务..."
if docker info &> /dev/null; then
    echo "✓ Docker服务正在运行"
else
    echo "✗ Docker服务未运行，请启动Docker"
    exit 1
fi

echo

# 检查端口占用
echo "5. 检查端口占用..."
if netstat -tuln 2>/dev/null | grep -q ":5000 "; then
    echo "⚠ 端口5000已被占用，可能需要修改docker-compose.yml中的端口映射"
else
    echo "✓ 端口5000可用"
fi

echo

# 检查备份源配置
echo "6. 检查备份源配置..."
if [ -f "docker-compose.yml" ]; then
    if grep -q "/backup-sources/" docker-compose.yml; then
        echo "✓ 发现备份源目录配置"
    elif grep -q "/host-root:" docker-compose.yml; then
        echo "⚠ 使用完整根目录挂载（有安全风险）"
    else
        echo "⚠ 未发现备份源目录配置，请检查docker-compose.yml"
    fi

    # 检查两个容器的卷挂载是否一致
    backup_web_volumes=$(grep -A 20 "backup-web:" docker-compose.yml | grep -E "^\s*-\s*/.*:" | sort)
    rclone_volumes=$(grep -A 20 "rclone:" docker-compose.yml | grep -E "^\s*-\s*/.*:" | sort)

    if [ "$backup_web_volumes" = "$rclone_volumes" ]; then
        echo "✓ 两个容器的卷挂载配置一致"
    else
        echo "⚠ 两个容器的卷挂载配置不一致，可能导致文件访问问题"
    fi
else
    echo "✗ docker-compose.yml不存在"
fi

echo

# 提供启动建议
echo "7. 部署建议..."
echo "✓ 环境检查完成，可以开始部署"
echo
echo "配置建议："
echo "  1. 使用 docker-compose.example.yml 作为安全配置模板"
echo "  2. 根据需要调整备份源目录挂载"
echo "  3. 确保两个容器的卷挂载配置一致"
echo
echo "启动命令："
echo "  docker-compose up -d"
echo
echo "验证命令："
echo "  docker-compose ps"
echo "  docker exec rclone-backup-web ls -la /backup-sources/"
echo "  docker exec rclone-service ls -la /backup-sources/"
echo
echo "查看日志："
echo "  docker-compose logs -f"
echo
echo "停止服务："
echo "  docker-compose down"
echo
echo "访问地址："
echo "  http://localhost:5000"
echo
echo "默认登录："
echo "  用户名: admin"
echo "  密码: admin123"

echo
echo "=== 验证完成 ==="
