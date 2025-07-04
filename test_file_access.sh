#!/bin/bash

# Docker环境文件访问测试脚本

echo "=== Docker环境文件访问测试 ==="
echo

# 检查容器是否运行
echo "1. 检查容器状态..."
if ! docker ps | grep -q "rclone-backup-web"; then
    echo "✗ backup-web容器未运行"
    exit 1
fi

if ! docker ps | grep -q "rclone-service"; then
    echo "✗ rclone-service容器未运行"
    exit 1
fi

echo "✓ 两个容器都在运行"
echo

# 测试backup-web容器的文件访问
echo "2. 测试backup-web容器文件访问..."
echo "检查宿主机根目录挂载："
docker exec rclone-backup-web ls -la /host | head -5 || echo "✗ 未找到/host目录挂载"

echo
echo "检查临时目录："
docker exec rclone-backup-web ls -la /app/data/temp || echo "✗ 临时目录不存在"

echo
echo "检查rclone配置目录："
docker exec rclone-backup-web ls -la /app/data/rclone_configs || echo "✗ rclone配置目录不存在"

echo

# 测试rclone容器的文件访问
echo "3. 测试rclone容器文件访问..."
echo "检查宿主机根目录挂载："
docker exec rclone-service ls -la /host | head -5 || echo "✗ 未找到/host目录挂载"

echo
echo "检查临时目录："
docker exec rclone-service ls -la /data/temp || echo "✗ 临时目录不存在"

echo
echo "检查rclone配置目录："
docker exec rclone-service ls -la /config/rclone || echo "✗ rclone配置目录不存在"

echo

# 测试文件共享
echo "4. 测试文件共享..."
echo "在backup-web容器中创建测试文件..."
docker exec rclone-backup-web touch /app/data/temp/test-file.txt
docker exec rclone-backup-web echo "test content" > /app/data/temp/test-file.txt

echo "检查rclone容器是否能访问该文件..."
if docker exec rclone-service ls -la /data/temp/test-file.txt > /dev/null 2>&1; then
    echo "✓ 文件共享正常"
    # 清理测试文件
    docker exec rclone-backup-web rm -f /app/data/temp/test-file.txt
else
    echo "✗ 文件共享失败"
fi

echo

# 测试rclone命令
echo "5. 测试rclone命令..."
if docker exec rclone-service rclone version > /dev/null 2>&1; then
    echo "✓ rclone命令可用"
    docker exec rclone-service rclone version | head -1
else
    echo "✗ rclone命令不可用"
fi

echo

# 检查宿主机目录挂载内容
echo "6. 检查宿主机目录挂载内容..."
echo "检查/host目录内容："
if docker exec rclone-backup-web ls -la /host >/dev/null 2>&1; then
    echo "✓ /host目录存在，内容："
    docker exec rclone-backup-web ls -la /host | head -10
    echo

    echo "检查常见系统目录："
    for dir in "home" "etc" "var" "usr" "opt"; do
        if docker exec rclone-backup-web ls -la "/host/$dir" >/dev/null 2>&1; then
            echo "  ✓ /host/$dir 可访问"
        else
            echo "  ✗ /host/$dir 不可访问"
        fi
    done
else
    echo "✗ /host目录不存在或不可访问"
fi

echo
echo "=== 测试完成 ==="
echo
echo "建议："
echo "1. 确保两个容器都能访问相同的备份源目录"
echo "2. 确保临时文件目录在两个容器间正确共享"
echo "3. 如果发现问题，检查docker-compose.yml中的卷挂载配置"
