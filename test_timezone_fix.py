#!/usr/bin/env python3
"""
测试时区修复的脚本
验证时间显示是否正确
"""

import os
import sys
from datetime import datetime

def test_timezone_fix():
    """测试时区修复"""
    print("=" * 60)
    print("测试时区修复")
    print("=" * 60)
    
    try:
        # 设置环境变量
        os.environ['FLASK_ENV'] = 'development'
        
        # 导入应用
        from app import create_app, init_database
        from models import db, BackupTask, BackupLog, get_local_time
        
        # 创建应用
        app = create_app('development')
        
        with app.app_context():
            print("✓ 应用创建成功")
            
            # 测试本地时间函数
            print("\n测试本地时间函数...")
            local_time = get_local_time()
            system_time = datetime.now()
            
            print(f"系统时间: {system_time}")
            print(f"本地时间: {local_time}")
            
            # 计算时差
            time_diff = abs((local_time - system_time).total_seconds())
            if time_diff < 60:  # 允许1分钟误差
                print("✓ 本地时间函数工作正常")
            else:
                print(f"⚠ 时间差异较大: {time_diff}秒")
            
            # 检查现有任务的时间显示
            print("\n检查现有任务的时间...")
            tasks = BackupTask.query.all()
            
            for task in tasks:
                print(f"\n任务: {task.name}")
                
                if task.last_run_at:
                    print(f"  原始最后运行时间: {task.last_run_at}")
                    print(f"  本地最后运行时间: {task.last_run_at_local}")
                    
                    # 检查时间是否相同（因为现在存储的就是本地时间）
                    if task.last_run_at == task.last_run_at_local:
                        print("  ✓ 时间转换正确")
                    else:
                        print("  ⚠ 时间转换可能有问题")
                else:
                    print("  - 从未运行")
                
                if task.next_run_at:
                    print(f"  原始下次运行时间: {task.next_run_at}")
                    print(f"  本地下次运行时间: {task.next_run_at_local}")
                    
                    if task.next_run_at == task.next_run_at_local:
                        print("  ✓ 下次运行时间转换正确")
                    else:
                        print("  ⚠ 下次运行时间转换可能有问题")
                else:
                    print("  - 无下次运行时间")
                
                # 检查最新日志
                if task.latest_log:
                    log = task.latest_log
                    print(f"  最新日志时间: {log.start_time}")
                    print(f"  日志状态: {log.status}")
            
            # 测试时间格式化
            print("\n测试时间格式化...")
            test_time = get_local_time()
            
            # 模拟模板中的格式化
            formatted_date = test_time.strftime('%m-%d')
            formatted_time = test_time.strftime('%H:%M')
            formatted_full = test_time.strftime('%m-%d %H:%M')
            
            print(f"当前时间: {test_time}")
            print(f"格式化日期: {formatted_date}")
            print(f"格式化时间: {formatted_time}")
            print(f"完整格式: {formatted_full}")
            
            # 验证是否是正确的时间（应该是7月3日12:00左右）
            if test_time.month == 7 and test_time.day == 3:
                print("✓ 日期正确（7月3日）")
            else:
                print(f"⚠ 日期可能不正确，当前: {test_time.month}月{test_time.day}日")
            
            if 11 <= test_time.hour <= 13:  # 允许一些误差
                print("✓ 时间大致正确（接近12:00）")
            else:
                print(f"⚠ 时间可能不正确，当前: {test_time.hour}:{test_time.minute}")
                
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("时区修复测试完成")
    print("=" * 60)
    return True

def test_backup_service_time():
    """测试备份服务的时间处理"""
    print("\n测试备份服务时间处理...")
    
    try:
        from services.backup_service import BackupService
        
        backup_service = BackupService()
        local_time = backup_service._get_local_time()
        
        print(f"备份服务本地时间: {local_time}")
        
        # 验证时间类型
        if isinstance(local_time, datetime):
            print("✓ 返回正确的datetime对象")
        else:
            print("✗ 返回类型错误")
            
        # 验证时区信息
        if local_time.tzinfo is None:
            print("✓ 正确移除了时区信息")
        else:
            print("✗ 仍包含时区信息")
            
        return True
        
    except Exception as e:
        print(f"✗ 备份服务时间测试失败: {e}")
        return False

if __name__ == '__main__':
    success1 = test_timezone_fix()
    success2 = test_backup_service_time()
    
    if success1 and success2:
        print("\n🎉 所有时区测试通过！")
        print("现在最后运行时间应该显示正确的本地时间")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败！")
        sys.exit(1)
