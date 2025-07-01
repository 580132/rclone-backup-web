#!/usr/bin/env python3
"""
手动测试rclone配置
"""

import os
import subprocess
import tempfile

def create_test_config():
    """创建测试配置文件"""
    config_content = """[test_r2]
type = s3
provider = Cloudflare
access_key_id = test_access_key_id
secret_access_key = test_secret_access_key
endpoint = account-id.r2.cloudflarestorage.com
region = auto
"""
    
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False, encoding='utf-8') as f:
        f.write(config_content)
        config_path = f.name
    
    print(f"创建测试配置文件: {config_path}")
    print("配置内容:")
    print("-" * 40)
    print(config_content)
    print("-" * 40)
    
    return config_path

def test_rclone_commands(config_path):
    """测试rclone命令"""
    print("测试rclone命令:")
    print("=" * 50)
    
    # 1. 检查rclone版本
    print("1. 检查rclone版本:")
    try:
        result = subprocess.run(['rclone', 'version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✓ rclone可用")
            version_line = result.stdout.split('\n')[0] if result.stdout else "unknown"
            print(f"版本: {version_line}")
        else:
            print("✗ rclone不可用")
            print(f"错误: {result.stderr}")
            return
    except Exception as e:
        print(f"✗ rclone检查失败: {e}")
        return
    
    # 2. 检查配置文件语法
    print("\n2. 检查配置文件语法:")
    try:
        cmd = ['rclone', 'config', 'show', 'test_r2', '--config', config_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        print(f"命令: {' '.join(cmd)}")
        print(f"返回码: {result.returncode}")
        
        if result.returncode == 0:
            print("✓ 配置文件语法正确")
            print("配置显示:")
            print(result.stdout)
        else:
            print("✗ 配置文件语法错误")
            print("错误:")
            print(result.stderr)
    except Exception as e:
        print(f"✗ 配置检查失败: {e}")
    
    # 3. 测试连接（使用lsd命令）
    print("\n3. 测试连接:")
    try:
        cmd = ['rclone', 'lsd', 'test_r2:', '--config', config_path, '--timeout', '10s', '-v']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        print(f"命令: {' '.join(cmd)}")
        print(f"返回码: {result.returncode}")
        
        if result.returncode == 0:
            print("✓ 连接测试成功")
            print("输出:")
            print(result.stdout)
        else:
            print("✗ 连接测试失败")
            print("标准输出:")
            print(result.stdout)
            print("错误输出:")
            print(result.stderr)
    except Exception as e:
        print(f"✗ 连接测试异常: {e}")

def main():
    """主函数"""
    print("手动测试rclone配置")
    print("=" * 50)
    
    # 创建测试配置
    config_path = create_test_config()
    
    try:
        # 测试rclone命令
        test_rclone_commands(config_path)
    finally:
        # 清理测试文件
        if os.path.exists(config_path):
            os.remove(config_path)
            print(f"\n✓ 清理测试配置文件: {config_path}")

if __name__ == '__main__':
    main()
