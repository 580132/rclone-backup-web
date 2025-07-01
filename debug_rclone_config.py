#!/usr/bin/env python3
"""
调试rclone配置生成和测试
"""

import os
import sys
import subprocess
import tempfile
from services.rclone_service import RcloneService

def test_cloudflare_r2_config():
    """测试Cloudflare R2配置生成"""
    print("=" * 60)
    print("测试Cloudflare R2配置生成")
    print("=" * 60)
    
    # 创建RcloneService实例
    rclone_service = RcloneService()
    
    # 测试配置数据
    config_data = {
        'access_key': 'test_access_key_id',
        'secret_key': 'test_secret_access_key',
        'endpoint': 'account-id.r2.cloudflarestorage.com',
        'region': 'auto'
    }
    
    # 生成配置内容
    config_name = 'test_cloudflare_r2'
    config_content = rclone_service._generate_config_content(config_name, 'cloudflare_r2', config_data)
    
    print("生成的配置内容:")
    print("-" * 40)
    print(config_content)
    print("-" * 40)
    
    # 创建配置文件
    success = rclone_service.create_config(config_name, 'cloudflare_r2', config_data)
    print(f"配置文件创建: {'成功' if success else '失败'}")
    
    # 检查配置文件是否存在
    config_path = rclone_service.get_config_path(config_name)
    print(f"配置文件路径: {config_path}")
    print(f"配置文件存在: {os.path.exists(config_path)}")
    
    if os.path.exists(config_path):
        print("\n实际配置文件内容:")
        print("-" * 40)
        with open(config_path, 'r', encoding='utf-8') as f:
            print(f.read())
        print("-" * 40)
        
        # 测试rclone命令
        test_rclone_command(config_name, config_path)
    
    return config_path

def test_rclone_command(config_name, config_path):
    """测试rclone命令"""
    print(f"\n测试rclone命令:")
    print("-" * 40)
    
    # 检查rclone是否可用
    try:
        result = subprocess.run(['rclone', 'version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✓ rclone命令可用")
            print(f"rclone版本: {result.stdout.split()[1] if len(result.stdout.split()) > 1 else 'unknown'}")
        else:
            print("✗ rclone命令不可用")
            return
    except Exception as e:
        print(f"✗ rclone命令检查失败: {e}")
        return
    
    # 测试配置文件语法
    print(f"\n测试配置文件语法:")
    try:
        cmd = ['rclone', 'config', 'show', config_name, '--config', config_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        print(f"命令: {' '.join(cmd)}")
        print(f"返回码: {result.returncode}")
        
        if result.returncode == 0:
            print("✓ 配置文件语法正确")
            print("配置内容:")
            print(result.stdout)
        else:
            print("✗ 配置文件语法错误")
            print("错误信息:")
            print(result.stderr)
            
    except Exception as e:
        print(f"✗ 配置测试失败: {e}")
    
    # 测试连接（使用lsd命令）
    print(f"\n测试连接:")
    try:
        cmd = ['rclone', 'lsd', f'{config_name}:', '--config', config_path, '--timeout', '10s']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        print(f"命令: {' '.join(cmd)}")
        print(f"返回码: {result.returncode}")
        
        if result.returncode == 0:
            print("✓ 连接测试成功")
            print("输出:")
            print(result.stdout)
        else:
            print("✗ 连接测试失败")
            print("错误信息:")
            print(result.stderr)
            
    except Exception as e:
        print(f"✗ 连接测试异常: {e}")

def check_directories():
    """检查目录结构"""
    print("=" * 60)
    print("检查目录结构")
    print("=" * 60)
    
    from config import Config
    
    directories = [
        Config.RCLONE_CONFIG_DIR,
        'data',
        'data/rclone_configs',
        'data/temp',
        'logs'
    ]
    
    for directory in directories:
        exists = os.path.exists(directory)
        print(f"{directory}: {'存在' if exists else '不存在'}")
        if not exists:
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"  -> 已创建")
            except Exception as e:
                print(f"  -> 创建失败: {e}")

def main():
    """主函数"""
    print("rclone配置调试工具")
    print("=" * 60)
    
    # 检查目录
    check_directories()
    
    # 测试Cloudflare R2配置
    config_path = test_cloudflare_r2_config()
    
    # 清理测试文件
    if config_path and os.path.exists(config_path):
        try:
            os.remove(config_path)
            print(f"\n✓ 清理测试配置文件: {config_path}")
        except Exception as e:
            print(f"\n✗ 清理测试配置文件失败: {e}")

if __name__ == '__main__':
    main()
