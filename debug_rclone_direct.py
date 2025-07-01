#!/usr/bin/env python3
"""
直接测试rclone命令
"""

import subprocess
import tempfile
import os

def test_rclone_version():
    """测试rclone版本"""
    print("=" * 60)
    print("测试rclone版本")
    print("=" * 60)
    
    try:
        result = subprocess.run(['rclone', 'version'], capture_output=True, text=True, timeout=10)
        print(f"返回码: {result.returncode}")
        print(f"输出:\n{result.stdout}")
        if result.stderr:
            print(f"错误:\n{result.stderr}")
        return result.returncode == 0
    except FileNotFoundError:
        print("✗ rclone命令未找到")
        return False
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False

def test_rclone_config():
    """测试rclone配置"""
    print("\n" + "=" * 60)
    print("测试rclone配置")
    print("=" * 60)
    
    # 创建测试配置
    config_content = """[test_cloudflare_r2]
type = s3
provider = Cloudflare
access_key_id = test_access_key_id
secret_access_key = test_secret_access_key
endpoint = https://account-id.r2.cloudflarestorage.com
region = auto
"""
    
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False, encoding='utf-8') as f:
        f.write(config_content)
        config_path = f.name
    
    print(f"创建临时配置文件: {config_path}")
    print("配置内容:")
    print("-" * 40)
    print(config_content)
    print("-" * 40)
    
    try:
        # 测试配置显示
        print("\n1. 测试配置显示:")
        cmd = ['rclone', 'config', 'show', 'test_cloudflare_r2', '--config', config_path]
        print(f"命令: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print(f"返回码: {result.returncode}")
        print(f"输出:\n{result.stdout}")
        if result.stderr:
            print(f"错误:\n{result.stderr}")
        
        # 测试连接（会失败，但可以看到详细错误）
        print("\n2. 测试连接:")
        cmd = ['rclone', 'lsd', 'test_cloudflare_r2:', '--config', config_path, '--timeout', '10s', '-vv']
        print(f"命令: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        print(f"返回码: {result.returncode}")
        print(f"输出:\n{result.stdout}")
        if result.stderr:
            print(f"错误:\n{result.stderr}")
            
    except Exception as e:
        print(f"测试异常: {e}")
    finally:
        # 清理临时文件
        try:
            os.unlink(config_path)
            print(f"\n✓ 清理临时配置文件: {config_path}")
        except:
            pass

def test_standard_config_location():
    """测试标准配置位置"""
    print("\n" + "=" * 60)
    print("测试标准配置位置")
    print("=" * 60)
    
    config_dir = os.path.expanduser('~/.config/rclone')
    config_file = os.path.join(config_dir, 'rclone.conf')
    
    print(f"标准配置目录: {config_dir}")
    print(f"标准配置文件: {config_file}")
    print(f"配置目录存在: {os.path.exists(config_dir)}")
    print(f"配置文件存在: {os.path.exists(config_file)}")
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"配置文件大小: {len(content)} 字符")
            print("配置文件内容:")
            print("-" * 40)
            print(content)
            print("-" * 40)
        except Exception as e:
            print(f"读取配置文件失败: {e}")
    
    # 测试rclone config show（显示所有配置）
    print("\n测试 rclone config show:")
    try:
        result = subprocess.run(['rclone', 'config', 'show'], capture_output=True, text=True, timeout=10)
        print(f"返回码: {result.returncode}")
        print(f"输出:\n{result.stdout}")
        if result.stderr:
            print(f"错误:\n{result.stderr}")
    except Exception as e:
        print(f"测试失败: {e}")

def main():
    """主函数"""
    print("rclone直接测试工具")
    
    # 测试rclone版本
    if not test_rclone_version():
        print("\n✗ rclone不可用，请检查安装")
        return
    
    # 测试rclone配置
    test_rclone_config()
    
    # 测试标准配置位置
    test_standard_config_location()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == '__main__':
    main()
