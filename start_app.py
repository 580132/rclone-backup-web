#!/usr/bin/env python3
"""
简化的应用启动脚本
"""

import os
import sys

def main():
    print("RClone备份Web系统启动")
    print("=" * 40)
    
    # 确保必要目录存在
    directories = ['data', 'data/rclone_configs', 'data/temp', 'logs']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ 创建目录: {directory}")
        else:
            print(f"✓ 目录已存在: {directory}")
    
    try:
        # 导入并创建应用
        from app import create_app, init_database
        
        app = create_app('development')
        print("✓ Flask应用创建成功")
        
        # 初始化数据库
        init_database(app)
        print("✓ 数据库初始化成功")
        
        # 启动应用
        print("✓ 启动Web服务器...")
        print("  访问地址: http://localhost:5000")
        print("  默认用户: admin")
        print("  默认密码: admin123")
        print("=" * 40)
        
        app.run(host='0.0.0.0', port=5000, debug=True)
        
    except Exception as e:
        print(f"✗ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
