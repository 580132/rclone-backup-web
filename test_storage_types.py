#!/usr/bin/env python3
"""
测试存储类型配置
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rclone_service import RCloneService

def test_storage_types():
    """测试支持的存储类型"""
    rclone_service = RCloneService()
    
    print("支持的存储类型：")
    print("=" * 50)
    
    storage_types = rclone_service.get_supported_types()
    
    for storage_type in storage_types:
        print(f"ID: {storage_type['id']}")
        print(f"名称: {storage_type['name']}")
        print(f"描述: {storage_type['description']}")
        print(f"图标: {storage_type['icon']}")
        print("-" * 30)

def test_config_generation():
    """测试配置生成"""
    rclone_service = RCloneService()
    
    print("\n配置生成测试：")
    print("=" * 50)
    
    # 测试阿里云OSS配置
    oss_config = {
        'access_key': 'test_access_key',
        'secret_key': 'test_secret_key',
        'endpoint': 'oss-cn-hangzhou.aliyuncs.com',
        'region': 'oss-cn-hangzhou'
    }
    
    oss_result = rclone_service._generate_config_content('test_oss', 'alibaba_oss', oss_config)
    print("阿里云OSS配置:")
    print(oss_result)
    print("-" * 30)
    
    # 测试Cloudflare R2配置
    r2_config = {
        'access_key': 'test_access_key',
        'secret_key': 'test_secret_key',
        'endpoint': 'account-id.r2.cloudflarestorage.com'
    }
    
    r2_result = rclone_service._generate_config_content('test_r2', 'cloudflare_r2', r2_config)
    print("Cloudflare R2配置:")
    print(r2_result)
    print("-" * 30)
    
    # 测试Google Drive配置
    drive_config = {
        'client_id': 'test_client_id',
        'client_secret': 'test_client_secret',
        'scope': 'drive',
        'root_folder_id': ''
    }
    
    drive_result = rclone_service._generate_config_content('test_drive', 'google_drive', drive_config)
    print("Google Drive配置:")
    print(drive_result)
    print("-" * 30)
    
    # 测试SFTP配置
    sftp_config = {
        'host': 'sftp.example.com',
        'username': 'testuser',
        'password': 'testpass',
        'port': '22',
        'key_file': '',
        'use_insecure_cipher': False,
        'disable_hashcheck': False
    }
    
    sftp_result = rclone_service._generate_config_content('test_sftp', 'sftp', sftp_config)
    print("SFTP配置:")
    print(sftp_result)

if __name__ == '__main__':
    test_storage_types()
    test_config_generation()
