#!/usr/bin/env python3
"""
检查当前配置状态
"""

import os
import sys
import subprocess

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config

def check_directories():
    """检查目录状态"""
    print("=" * 60)
    print("检查目录状态")
    print("=" * 60)
    
    directories = [
        ('数据目录', 'data'),
        ('临时目录', 'data/temp'),
        ('日志目录', 'logs'),
        ('rclone配置目录', Config.RCLONE_CONFIG_DIR)
    ]
    
    for name, path in directories:
        exists = os.path.exists(path)
        print(f"{name}: {path}")
        print(f"  存在: {'是' if exists else '否'}")
        if exists:
            try:
                files = os.listdir(path)
                print(f"  文件数: {len(files)}")
                if files:
                    print(f"  文件: {files[:5]}{'...' if len(files) > 5 else ''}")
            except Exception as e:
                print(f"  错误: {e}")
        print()

def check_rclone_config():
    """检查rclone配置"""
    print("=" * 60)
    print("检查rclone配置")
    print("=" * 60)
    
    config_file = os.path.join(Config.RCLONE_CONFIG_DIR, 'rclone.conf')
    print(f"配置文件路径: {config_file}")
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

def check_rclone_binary():
    """检查rclone二进制文件"""
    print("=" * 60)
    print("检查rclone二进制文件")
    print("=" * 60)
    
    print(f"rclone二进制路径: {Config.RCLONE_BINARY}")
    
    try:
        # 检查rclone版本
        result = subprocess.run([Config.RCLONE_BINARY, 'version'], 
                              capture_output=True, text=True, timeout=10)
        print(f"rclone版本检查返回码: {result.returncode}")
        if result.returncode == 0:
            print("✓ rclone可用")
            version_info = result.stdout.split('\n')[0] if result.stdout else "unknown"
            print(f"版本信息: {version_info}")
        else:
            print("✗ rclone不可用")
            print(f"错误: {result.stderr}")
    except FileNotFoundError:
        print("✗ rclone命令未找到")
    except Exception as e:
        print(f"✗ rclone检查失败: {e}")

def check_logs():
    """检查日志文件"""
    print("=" * 60)
    print("检查日志文件")
    print("=" * 60)
    
    log_file = Config.LOG_FILE
    print(f"日志文件路径: {log_file}")
    print(f"日志文件存在: {os.path.exists(log_file)}")
    
    if os.path.exists(log_file):
        try:
            # 读取最后50行日志
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            print(f"日志文件行数: {len(lines)}")
            print("最后10行日志:")
            print("-" * 40)
            for line in lines[-10:]:
                print(line.rstrip())
            print("-" * 40)
        except Exception as e:
            print(f"读取日志文件失败: {e}")

def main():
    """主函数"""
    print("配置状态检查工具")
    print(f"当前工作目录: {os.getcwd()}")
    print()
    
    # 检查目录
    check_directories()
    
    # 检查rclone配置
    check_rclone_config()
    
    # 检查rclone二进制
    check_rclone_binary()
    
    # 检查日志
    check_logs()
    
    print("=" * 60)
    print("检查完成")
    print("=" * 60)

if __name__ == '__main__':
    main()
