#!/usr/bin/env python3
"""
定时任务调度服务
"""

import logging
from datetime import datetime, timedelta
from typing import List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from models import db, BackupTask


# 全局应用实例引用
_app_instance = None

def set_app_instance(app):
    """设置应用实例引用"""
    global _app_instance
    _app_instance = app

def run_scheduled_backup_task(task_id: int):
    """独立的备份任务执行函数，避免调度器序列化问题"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"Starting scheduled backup task {task_id}")

        # 确保在应用上下文中运行
        if _app_instance:
            with _app_instance.app_context():
                # 动态导入BackupService，避免循环引用
                from services.backup_service import BackupService
                backup_service = BackupService()

                success, message = backup_service.run_backup_task(task_id, manual=False)

                if success:
                    logger.info(f"Scheduled backup task {task_id} completed successfully")
                else:
                    logger.error(f"Scheduled backup task {task_id} failed: {message}")
        else:
            logger.error("App instance not available for scheduled task")

    except Exception as e:
        logger.error(f"Error running scheduled backup task {task_id}: {e}")
        import traceback
        traceback.print_exc()


def run_scheduled_cleanup():
    """独立的清理任务执行函数，避免调度器序列化问题"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting scheduled backup cleanup")

        # 确保在应用上下文中运行
        if _app_instance:
            with _app_instance.app_context():
                # 动态导入所需模块，避免循环引用
                from models import BackupTask
                from services.backup_service import BackupService

                # 获取所有活跃的任务
                tasks = BackupTask.query.filter_by(is_active=True).all()
                backup_service = BackupService()

                for task in tasks:
                    try:
                        # 使用备份服务的清理方法
                        backup_service._cleanup_old_backups(task)
                    except Exception as e:
                        logger.error(f"Error cleaning up backups for task {task.name}: {e}")
                        continue

                logger.info("Completed scheduled backup cleanup")
        else:
            logger.error("App instance not available for scheduled cleanup")

    except Exception as e:
        logger.error(f"Error in scheduled backup cleanup: {e}")
        import traceback
        traceback.print_exc()


def run_scheduled_task_check():
    """独立的任务状态检查函数，避免调度器序列化问题"""
    import logging
    from datetime import datetime, timedelta
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting scheduled task status check")

        # 确保在应用上下文中运行
        if _app_instance:
            with _app_instance.app_context():
                # 动态导入所需模块
                from models import db, BackupLog

                # 检查运行时间过长的任务（超过6小时）
                cutoff_time = datetime.utcnow() - timedelta(hours=6)
                stuck_logs = BackupLog.query.filter(
                    BackupLog.status == 'running',
                    BackupLog.start_time < cutoff_time
                ).all()

                for log in stuck_logs:
                    log.status = 'failed'
                    log.end_time = datetime.utcnow()
                    log.error_message = '任务执行超时，已自动标记为失败'
                    logger.warning(f"Marked stuck backup log {log.id} as failed")

                if stuck_logs:
                    db.session.commit()
                    logger.info(f"Cleaned up {len(stuck_logs)} stuck backup logs")
        else:
            logger.error("App instance not available for scheduled task check")

    except Exception as e:
        logger.error(f"Error checking task status: {e}")
        import traceback
        traceback.print_exc()


class SchedulerService:
    def __init__(self, app=None):
        self.logger = logging.getLogger(__name__)
        self.scheduler = None

        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化调度器"""
        try:
            # 设置应用实例引用，供独立函数使用
            set_app_instance(app)

            # 配置作业存储
            jobstores = {
                'default': SQLAlchemyJobStore(url=app.config['SQLALCHEMY_DATABASE_URI'])
            }
            
            # 配置执行器
            executors = {
                'default': ThreadPoolExecutor(20)
            }
            
            # 作业默认设置
            job_defaults = {
                'coalesce': False,
                'max_instances': 3
            }
            
            # 创建调度器
            self.scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone='Asia/Shanghai'
            )
            
            # 添加系统任务
            self._add_system_jobs()
            
            self.logger.info("Scheduler service initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize scheduler: {e}")
    
    def start(self):
        """启动调度器"""
        try:
            if self.scheduler and not self.scheduler.running:
                self.scheduler.start()
                self.logger.info("Scheduler started")
                
                # 重新加载所有备份任务
                self.reload_backup_tasks()
                
        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {e}")
    
    def stop(self):
        """停止调度器"""
        try:
            if self.scheduler and self.scheduler.running:
                self.scheduler.shutdown()
                self.logger.info("Scheduler stopped")
        except Exception as e:
            self.logger.error(f"Failed to stop scheduler: {e}")
    
    def reload_backup_tasks(self):
        """重新加载所有备份任务"""
        try:
            # 清除现有的备份任务作业
            jobs = self.scheduler.get_jobs()
            for job in jobs:
                if job.id.startswith('backup_task_'):
                    self.scheduler.remove_job(job.id)
            
            # 加载活跃的备份任务
            active_tasks = BackupTask.query.filter_by(is_active=True).all()
            
            for task in active_tasks:
                if task.cron_expression:
                    self.add_backup_task(task)
            
            self.logger.info(f"Reloaded {len(active_tasks)} backup tasks")
            
        except Exception as e:
            self.logger.error(f"Failed to reload backup tasks: {e}")
    
    def add_backup_task(self, task: BackupTask):
        """添加备份任务到调度器"""
        try:
            if not task.cron_expression:
                return
            
            job_id = f"backup_task_{task.id}"
            
            # 移除现有作业（如果存在）
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass
            
            # 解析Cron表达式
            cron_parts = task.cron_expression.split()
            if len(cron_parts) != 5:
                self.logger.error(f"Invalid cron expression for task {task.id}: {task.cron_expression}")
                return
            
            minute, hour, day, month, day_of_week = cron_parts
            
            # 创建Cron触发器
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone='Asia/Shanghai'
            )
            
            # 添加作业
            self.scheduler.add_job(
                func=run_scheduled_backup_task,
                trigger=trigger,
                id=job_id,
                name=f"备份任务: {task.name}",
                args=[task.id],
                replace_existing=True
            )
            
            # 更新下次运行时间
            job = self.scheduler.get_job(job_id)
            if job and job.next_run_time:
                # 确保时间格式一致（转换为本地时间，无时区信息）
                next_run = job.next_run_time
                if next_run.tzinfo:
                    # 转换为本地时间
                    import pytz
                    local_tz = pytz.timezone('Asia/Shanghai')
                    next_run = next_run.astimezone(local_tz).replace(tzinfo=None)

                task.next_run_at = next_run
                db.session.commit()
            
            self.logger.info(f"Added backup task {task.name} to scheduler")
            
        except Exception as e:
            self.logger.error(f"Failed to add backup task {task.id} to scheduler: {e}")

    def remove_backup_task(self, task_id: int):
        """从调度器中移除备份任务"""
        try:
            job_id = f"backup_task_{task_id}"
            self.scheduler.remove_job(job_id)
            self.logger.info(f"Removed backup task {task_id} from scheduler")
        except Exception as e:
            self.logger.error(f"Failed to remove backup task {task_id} from scheduler: {e}")

    def update_backup_task(self, task: BackupTask):
        """更新调度器中的备份任务"""
        try:
            if not task.is_active:
                # 如果任务被禁用，从调度器中移除
                self.remove_backup_task(task.id)
                self.logger.info(f"Removed disabled task {task.name} from scheduler")
            elif task.cron_expression:
                # 如果任务有cron表达式，添加或更新调度器中的任务
                self.add_backup_task(task)
                self.logger.info(f"Updated task {task.name} in scheduler")
            else:
                # 如果任务没有cron表达式（手动执行），从调度器中移除
                self.remove_backup_task(task.id)
                self.logger.info(f"Removed manual task {task.name} from scheduler")
        except Exception as e:
            self.logger.error(f"Failed to update backup task {task.id} in scheduler: {e}")


    def _add_system_jobs(self):
        """添加系统维护任务"""
        try:
            # 每小时检查一次任务状态
            self.scheduler.add_job(
                func=run_scheduled_task_check,
                trigger='cron',
                minute=0,
                id='check_task_status',
                name='检查任务状态',
                replace_existing=True
            )

            # 每天凌晨清理过期备份
            self.scheduler.add_job(
                func=run_scheduled_cleanup,
                trigger='cron',
                hour=1,
                minute=0,
                id='cleanup_old_backups',
                name='清理过期备份',
                replace_existing=True
            )

            self.logger.info("Added system maintenance jobs")
            
        except Exception as e:
            self.logger.error(f"Failed to add system jobs: {e}")
    

    def get_job_status(self) -> List[dict]:
        """获取所有作业状态"""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time,
                    'trigger': str(job.trigger)
                })
            return jobs
        except Exception as e:
            self.logger.error(f"Error getting job status: {e}")
            return []


# 全局调度器实例
scheduler_service = SchedulerService()
