#!/usr/bin/env python3
"""
RClone备份Web系统启动脚本
"""

import os
import sys
import logging
from app import create_app, init_database

def check_rclone():
    """检查rclone是否可用"""
    try:
        import subprocess
        from config import Config

        if Config.DOCKER_ENV:
            # Docker环境：检查rclone容器是否运行
            print("检查Docker环境中的rclone容器...")
            result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}'],
                                  capture_output=True,
                                  text=True,
                                  timeout=10)
            if result.returncode == 0 and Config.RCLONE_CONTAINER_NAME in result.stdout:
                print(f"✓ rclone容器 '{Config.RCLONE_CONTAINER_NAME}' 正在运行")

                # 测试容器中的rclone命令
                test_result = subprocess.run(['docker', 'exec', Config.RCLONE_CONTAINER_NAME, 'rclone', 'version'],
                                           capture_output=True,
                                           text=True,
                                           timeout=10)
                if test_result.returncode == 0:
                    print("✓ rclone容器中的rclone命令可用")
                    return True
                else:
                    print("✗ rclone容器中的rclone命令不可用")
                    return False
            else:
                print(f"✗ rclone容器 '{Config.RCLONE_CONTAINER_NAME}' 未运行")
                return False
        else:
            # 本地环境：检查本地rclone二进制文件
            result = subprocess.run(['rclone', 'version'],
                                  capture_output=True,
                                  text=True,
                                  timeout=10)
            if result.returncode == 0:
                print("✓ 本地rclone已安装")
                return True
            else:
                print("✗ 本地rclone未正确安装")
                return False
    except FileNotFoundError:
        if Config.DOCKER_ENV:
            print("✗ 未找到docker命令")
        else:
            print("✗ 未找到rclone命令")
        return False
    except Exception as e:
        print(f"✗ 检查rclone时出错: {e}")
        return False

def init_scheduler(app):
    """初始化调度器"""
    try:
        print("✓ 初始化调度器...")

        # 只在主进程中运行，避免开发模式重载问题
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
            from services.scheduler_service import scheduler_service
            scheduler_service.init_app(app)

            # 在应用上下文中启动调度器
            with app.app_context():
                scheduler_service.start()

            print("✓ 调度器初始化并启动成功")
            app.logger.info("Scheduler initialized and started")
        else:
            print("⚠ 跳过调度器初始化（Flask重载进程）")
            app.logger.info("Skipping scheduler initialization in Flask reloader process")

    except Exception as e:
        print(f"✗ 调度器初始化失败: {e}")
        app.logger.error(f"Failed to initialize scheduler: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        # 调度器失败不应该阻止应用启动
        print("⚠ 调度器初始化失败，但应用将继续启动")

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

    # 获取配置
    config_name = os.environ.get('FLASK_ENV', 'development')
    print(f"✓ 运行模式: {config_name}")

    # 检查rclone（开发模式下可跳过）
    if not check_rclone():
        if config_name == 'development':
            print("⚠ 开发模式：rclone未安装，部分功能可能不可用")
        else:
            print("\n请先安装rclone:")
            print("  Linux/macOS: curl https://rclone.org/install.sh | sudo bash")
            print("  Windows: 下载 https://rclone.org/downloads/")
            print("  或使用包管理器: apt install rclone / brew install rclone")
            sys.exit(1)

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

    # 初始化调度器
    init_scheduler(app)

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
        # 停止调度器
        try:
            from services.scheduler_service import scheduler_service
            if scheduler_service.scheduler and scheduler_service.scheduler.running:
                scheduler_service.stop()
                print("✓ 调度器已停止")
        except:
            pass
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
