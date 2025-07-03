#!/usr/bin/env python3
"""
生产模式启动脚本（无调试模式，确保调度器正常工作）
"""

import os
import sys

def main():
    print("RClone备份Web系统启动 (生产模式)")
    print("=" * 50)
    
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
        
        # 创建生产模式应用（无调试）
        app = create_app('development')  # 使用development配置但不开启debug
        print("✓ Flask应用创建成功")
        
        # 初始化数据库
        init_database(app)
        print("✓ 数据库初始化成功")
        
        # 手动初始化调度器
        print("✓ 初始化调度器...")
        try:
            from services.scheduler_service import scheduler_service
            
            with app.app_context():
                # 强制初始化调度器
                scheduler_service.init_app(app)
                scheduler_service.start()
                
                # 检查调度器状态
                jobs = scheduler_service.scheduler.get_jobs()
                print(f"✓ 调度器启动成功，包含 {len(jobs)} 个作业")
                
                # 显示作业信息
                for job in jobs:
                    print(f"  - {job.id}: 下次运行 {job.next_run_time}")
                
        except Exception as e:
            print(f"✗ 调度器启动失败: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
        # 启动应用（非调试模式）
        print("✓ 启动Web服务器...")
        print("  访问地址: http://localhost:5000")
        print("  默认用户: admin")
        print("  默认密码: admin123")
        print("  模式: 生产模式（调度器已启用）")
        print("=" * 50)
        
        # 非调试模式启动，避免重载问题
        app.run(host='0.0.0.0', port=5000, debug=False)
        
    except Exception as e:
        print(f"✗ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
