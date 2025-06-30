#!/bin/bash

# RClone备份Web系统 - Linux自动化测试脚本
# 专为Linux环境设计，用于快速验证系统环境和基本功能

echo "=================================================="
echo "RClone备份Web系统 - Linux环境测试"
echo "=================================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试结果统计
TESTS_PASSED=0
TESTS_FAILED=0

# 测试函数
test_command() {
    local test_name="$1"
    local command="$2"
    local expected_code="${3:-0}"
    
    echo -n "测试 $test_name ... "
    
    if eval "$command" >/dev/null 2>&1; then
        if [ $? -eq $expected_code ]; then
            echo -e "${GREEN}✅ 通过${NC}"
            ((TESTS_PASSED++))
            return 0
        else
            echo -e "${RED}❌ 失败${NC}"
            ((TESTS_FAILED++))
            return 1
        fi
    else
        echo -e "${RED}❌ 失败${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

# 1. 环境检查
echo -e "\n${BLUE}1. 环境检查${NC}"
echo "----------------------------------------"

# 检查Python
test_command "Python环境" "python3 --version"

# 检查rclone
test_command "rclone安装" "rclone version"

# 检查Python依赖
test_command "Flask依赖" "python3 -c 'import flask'"
test_command "SQLAlchemy依赖" "python3 -c 'import sqlalchemy'"

# 2. 文件结构检查
echo -e "\n${BLUE}2. 文件结构检查${NC}"
echo "----------------------------------------"

test_command "主应用文件" "test -f app.py"
test_command "配置文件" "test -f config.py"
test_command "模型文件" "test -f models.py"
test_command "测试应用文件" "test -f test_app.py"
test_command "依赖文件" "test -f requirements.txt"

# 3. 目录权限检查
echo -e "\n${BLUE}3. 目录权限检查${NC}"
echo "----------------------------------------"

# 创建必要目录
mkdir -p data logs
test_command "数据目录创建" "test -d data"
test_command "日志目录创建" "test -d logs"
test_command "数据目录写权限" "test -w data"
test_command "日志目录写权限" "test -w logs"

# 4. 基础功能测试
echo -e "\n${BLUE}4. 基础功能测试${NC}"
echo "----------------------------------------"

# 测试Python导入
test_command "应用模块导入" "python3 -c 'from app import create_app; app = create_app()'"
test_command "配置模块导入" "python3 -c 'import config'"
test_command "模型模块导入" "python3 -c 'import models'"

# 5. rclone功能测试
echo -e "\n${BLUE}5. rclone功能测试${NC}"
echo "----------------------------------------"

# 创建临时配置目录
TEMP_CONFIG_DIR="/tmp/rclone_test_$$"
mkdir -p "$TEMP_CONFIG_DIR"

# 创建测试配置
cat > "$TEMP_CONFIG_DIR/rclone.conf" << EOF
[test]
type = local
EOF

# 测试rclone配置
test_command "rclone配置测试" "rclone lsd test: --config '$TEMP_CONFIG_DIR/rclone.conf'"

# 清理临时文件
rm -rf "$TEMP_CONFIG_DIR"

# 6. Web服务测试
echo -e "\n${BLUE}6. Web服务测试${NC}"
echo "----------------------------------------"

# 启动测试服务器
echo "启动测试Web服务器..."
python3 test_app.py &
TEST_SERVER_PID=$!

# 等待服务器启动
sleep 3

# 测试HTTP响应
test_command "Web服务响应" "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/login | grep -q '200'"

# 停止测试服务器
kill $TEST_SERVER_PID 2>/dev/null
wait $TEST_SERVER_PID 2>/dev/null

# 7. 数据库测试
echo -e "\n${BLUE}7. 数据库测试${NC}"
echo "----------------------------------------"

# 测试SQLite数据库创建
TEST_DB="data/test_$$.db"
test_command "SQLite数据库创建" "python3 -c 'import sqlite3; conn = sqlite3.connect(\"$TEST_DB\"); conn.close()'"

# 清理测试数据库
rm -f "$TEST_DB"

# 测试结果汇总
echo -e "\n${BLUE}测试结果汇总${NC}"
echo "=================================================="
echo -e "通过的测试: ${GREEN}$TESTS_PASSED${NC}"
echo -e "失败的测试: ${RED}$TESTS_FAILED${NC}"
echo -e "总计测试: $((TESTS_PASSED + TESTS_FAILED))"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 所有测试都通过了！系统准备就绪。${NC}"
    echo -e "\n${YELLOW}下一步操作：${NC}"
    echo "1. 运行测试应用: python3 test_app.py"
    echo "2. 运行简化应用: python3 start_app.py"
    echo "3. 运行完整应用: python3 run.py"
    echo "4. 访问 http://localhost:5000"
    echo "5. 使用账户 admin/admin123 登录"
    exit 0
else
    echo -e "\n${RED}❌ 有 $TESTS_FAILED 个测试失败，请检查系统配置。${NC}"
    echo -e "\n${YELLOW}故障排除建议：${NC}"
    echo "1. 检查Python和rclone是否正确安装"
    echo "2. 安装缺失的依赖: pip install -r requirements.txt"
    echo "3. 检查文件权限和目录结构"
    echo "4. 查看详细错误信息重新运行测试"
    echo "5. 参考 TESTING_GUIDE.md 获取更多帮助"
    exit 1
fi
