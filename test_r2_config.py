#!/usr/bin/env python3
"""
简单测试Cloudflare R2配置生成
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.rclone_service import RcloneService

def test_r2_config():
    print("测试Cloudflare R2配置生成")
    print("=" * 50)
    
    # 创建服务实例
    rclone_service = RcloneService()
    
    # 测试数据
    config_data = {
        'access_key': 'test_access_key_id',
        'secret_key': 'test_secret_access_key', 
        'endpoint': 'account-id.r2.cloudflarestorage.com'
    }
    
    # 生成配置内容
    config_content = rclone_service._generate_config_content('test_r2', 'cloudflare_r2', config_data)
    
    print("生成的配置内容:")
    print("-" * 30)
    print(config_content)
    print("-" * 30)
    
    # 检查配置目录
    print(f"配置目录: {rclone_service.config_dir}")
    print(f"配置目录存在: {os.path.exists(rclone_service.config_dir)}")
    
    # 尝试创建配置文件
    success = rclone_service.create_config('test_r2', 'cloudflare_r2', config_data)
    print(f"配置创建: {'成功' if success else '失败'}")
    
    # 检查配置文件
    config_path = rclone_service.get_config_path('test_r2')
    print(f"配置文件路径: {config_path}")
    print(f"配置文件存在: {os.path.exists(config_path)}")
    
    if os.path.exists(config_path):
        print("\n实际文件内容:")
        print("-" * 30)
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)
        print("-" * 30)
        
        # 清理测试文件
        os.remove(config_path)
        print("✓ 测试文件已清理")

if __name__ == '__main__':
    test_r2_config()
