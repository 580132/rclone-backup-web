#!/usr/bin/env python3
"""
测试调度器集成的脚本
验证调度器是否正确同步到run.py，以及编辑任务后是否正确更新调度器
"""

import os
import sys
import time
from datetime import datetime

def test_scheduler_integration():
    """测试调度器集成"""
    print("=" * 60)
    print("测试调度器集成")
    print("=" * 60)
    
    try:
        # 设置环境变量
        os.environ['FLASK_ENV'] = 'development'
        
        # 导入应用
        from app import create_app, init_database
        from models import db, BackupTask, StorageConfig
        
        # 创建应用
        app = create_app('development')
        
        with app.app_context():
            print("✓ 应用创建成功")
            
            # 初始化数据库
            try:
                init_database(app)
                print("✓ 数据库初始化成功")
            except Exception as e:
                print(f"⚠ 数据库初始化警告: {e}")
            
            # 测试调度器初始化
            print("\n测试调度器初始化...")
            try:
                from services.scheduler_service import scheduler_service, _app_instance
                
                # 检查应用实例是否设置
                if _app_instance:
                    print("✓ 应用实例已设置")
                else:
                    print("✗ 应用实例未设置")
                
                # 检查调度器是否存在
                if scheduler_service.scheduler:
                    print("✓ 调度器已创建")
                    
                    # 检查调度器是否运行
                    if scheduler_service.scheduler.running:
                        print("✓ 调度器正在运行")
                    else:
                        print("⚠ 调度器未运行，尝试启动...")
                        scheduler_service.start()
                        if scheduler_service.scheduler.running:
                            print("✓ 调度器启动成功")
                        else:
                            print("✗ 调度器启动失败")
                else:
                    print("✗ 调度器未创建")
                    
            except Exception as e:
                print(f"✗ 调度器测试失败: {e}")
                import traceback
                traceback.print_exc()
            
            # 测试任务管理
            print("\n测试任务管理...")
            try:
                # 检查现有任务
                tasks = BackupTask.query.all()
                print(f"✓ 找到 {len(tasks)} 个备份任务")
                
                # 检查活跃任务
                active_tasks = BackupTask.query.filter_by(is_active=True).all()
                print(f"✓ 其中 {len(active_tasks)} 个任务处于活跃状态")
                
                # 检查调度器中的作业
                if scheduler_service.scheduler:
                    jobs = scheduler_service.scheduler.get_jobs()
                    backup_jobs = [job for job in jobs if job.id.startswith('backup_task_')]
                    print(f"✓ 调度器中有 {len(backup_jobs)} 个备份作业")
                    
                    # 检查任务和作业的对应关系
                    for task in active_tasks:
                        if task.cron_expression:
                            job_id = f"backup_task_{task.id}"
                            job = scheduler_service.scheduler.get_job(job_id)
                            if job:
                                print(f"  ✓ 任务 {task.name} 在调度器中有对应作业")
                            else:
                                print(f"  ✗ 任务 {task.name} 在调度器中没有对应作业")
                        else:
                            print(f"  - 任务 {task.name} 为手动执行，无需调度器作业")
                
            except Exception as e:
                print(f"✗ 任务管理测试失败: {e}")
                import traceback
                traceback.print_exc()
            
            # 测试调度器方法
            print("\n测试调度器方法...")
            try:
                # 测试重新加载任务
                scheduler_service.reload_backup_tasks()
                print("✓ 重新加载任务成功")
                
                # 测试更新任务方法
                if active_tasks:
                    test_task = active_tasks[0]
                    scheduler_service.update_backup_task(test_task)
                    print(f"✓ 更新任务 {test_task.name} 成功")
                
            except Exception as e:
                print(f"✗ 调度器方法测试失败: {e}")
                import traceback
                traceback.print_exc()
            
            # 停止调度器
            try:
                if scheduler_service.scheduler and scheduler_service.scheduler.running:
                    scheduler_service.stop()
                    print("✓ 调度器已停止")
            except Exception as e:
                print(f"⚠ 停止调度器时出错: {e}")
                
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("调度器集成测试完成")
    print("=" * 60)
    return True

def test_run_py_integration():
    """测试run.py中的调度器集成"""
    print("\n测试run.py中的调度器集成...")
    
    try:
        # 检查run.py中是否有调度器初始化代码
        with open('run.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'init_scheduler' in content:
            print("✓ run.py中包含调度器初始化函数")
        else:
            print("✗ run.py中缺少调度器初始化函数")
            
        if 'scheduler_service' in content:
            print("✓ run.py中包含调度器服务引用")
        else:
            print("✗ run.py中缺少调度器服务引用")
            
        if 'WERKZEUG_RUN_MAIN' in content:
            print("✓ run.py中包含Flask重载检查")
        else:
            print("✗ run.py中缺少Flask重载检查")
            
    except Exception as e:
        print(f"✗ 检查run.py失败: {e}")
        return False
    
    return True

if __name__ == '__main__':
    success1 = test_run_py_integration()
    success2 = test_scheduler_integration()
    
    if success1 and success2:
        print("\n🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败！")
        sys.exit(1)
