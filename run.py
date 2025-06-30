#!/usr/bin/env python3
"""
RClone备份Web系统启动脚本
"""

import os
import sys
import logging
from app import create_app, init_database

def check_rclone():
    """检查rclone是否已安装"""
    try:
        import subprocess
        result = subprocess.run(['rclone', 'version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        if result.returncode == 0:
            print("✓ rclone已安装")
            return True
        else:
            print("✗ rclone未正确安装")
            return False
    except FileNotFoundError:
        print("✗ 未找到rclone命令")
        return False
    except Exception as e:
        print(f"✗ 检查rclone时出错: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("RClone备份Web系统")
    print("=" * 50)
    
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("✗ 需要Python 3.7或更高版本")
        sys.exit(1)
    print(f"✓ Python版本: {sys.version}")
    
    # 检查rclone
    if not check_rclone():
        print("\n请先安装rclone:")
        print("  Linux/macOS: curl https://rclone.org/install.sh | sudo bash")
        print("  Windows: 下载 https://rclone.org/downloads/")
        print("  或使用包管理器: apt install rclone / brew install rclone")
        sys.exit(1)
    
    # 获取配置
    config_name = os.environ.get('FLASK_ENV', 'development')
    print(f"✓ 运行模式: {config_name}")
    
    # 创建应用
    app = create_app(config_name)

    # 初始化数据库
    print("✓ 初始化数据库...")
    try:
        init_database(app)
        print("✓ 数据库初始化完成")
    except Exception as e:
        print(f"✗ 数据库初始化失败: {e}")
        print("请检查data目录权限或手动创建data目录")
        sys.exit(1)
    
    # 启动信息
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = config_name == 'development'
    
    print(f"✓ 服务器启动中...")
    print(f"  地址: http://{host}:{port}")
    print(f"  默认用户: admin")
    print(f"  默认密码: admin123")
    print("=" * 50)
    
    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
