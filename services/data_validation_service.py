"""
数据验证服务
用于检查和修复数据库中的异常数据
"""

import logging
from models import db, BackupTask, BackupLog
from sqlalchemy import text

class DataValidationService:
    """数据验证服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_and_repair_data(self):
        """验证并修复数据库中的异常数据"""
        try:
            self.logger.info("开始数据验证和修复...")
            
            repairs_made = 0
            
            # 修复备份任务名称异常
            repairs_made += self._repair_task_names()
            
            # 清理孤立的备份日志
            repairs_made += self._cleanup_orphaned_logs()
            
            # 修复空值和异常值
            repairs_made += self._repair_null_values()
            
            if repairs_made > 0:
                db.session.commit()
                self.logger.info(f"数据修复完成，共修复了 {repairs_made} 个异常项目")
            else:
                self.logger.info("数据验证完成，没有发现异常数据")
            
            return True, f"数据验证完成，修复了 {repairs_made} 个异常项目"
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"数据验证和修复失败: {e}")
            return False, f"数据验证失败: {str(e)}"
    
    def _repair_task_names(self):
        """修复备份任务名称异常"""
        repairs_made = 0
        
        try:
            tasks = BackupTask.query.all()
            
            for task in tasks:
                original_name = task.name
                needs_repair = False
                
                if not task.name or task.name.strip() == "":
                    # 修复空任务名称
                    task.name = f"备份任务_{task.id}"
                    needs_repair = True
                    
                elif len(task.name) > 100:
                    # 修复过长的任务名称
                    task.name = task.name[:50] + "..."
                    needs_repair = True
                    
                elif len(set(task.name)) == 1 and len(task.name) > 10:
                    # 修复重复字符的任务名称
                    char = task.name[0]
                    task.name = f"备份任务_{char}_{task.id}"
                    needs_repair = True
                    
                elif task.name and any(substring in task.name for substring in ['cs2', 'test']) and task.name.count(task.name[:3]) > 3:
                    # 修复重复字符串的任务名称
                    base_name = task.name[:3]
                    task.name = f"{base_name}_{task.id}"
                    needs_repair = True
                
                if needs_repair:
                    self.logger.info(f"修复任务 {task.id} 名称: '{original_name}' -> '{task.name}'")
                    repairs_made += 1
            
            return repairs_made
            
        except Exception as e:
            self.logger.error(f"修复任务名称时出错: {e}")
            return 0
    
    def _cleanup_orphaned_logs(self):
        """清理孤立的备份日志"""
        repairs_made = 0
        
        try:
            # 查找孤立的备份日志（对应的任务不存在）
            orphaned_logs = db.session.execute(text("""
                SELECT bl.id, bl.task_id 
                FROM backup_logs bl 
                LEFT JOIN backup_tasks bt ON bl.task_id = bt.id 
                WHERE bt.id IS NULL
            """)).fetchall()
            
            if orphaned_logs:
                self.logger.info(f"发现 {len(orphaned_logs)} 个孤立的备份日志，将删除...")
                
                for log_id, task_id in orphaned_logs:
                    log = BackupLog.query.get(log_id)
                    if log:
                        db.session.delete(log)
                        repairs_made += 1
                        self.logger.info(f"删除孤立日志 {log_id} (任务ID: {task_id})")
            
            return repairs_made
            
        except Exception as e:
            self.logger.error(f"清理孤立日志时出错: {e}")
            return 0
    
    def _repair_null_values(self):
        """修复空值和异常值"""
        repairs_made = 0
        
        try:
            # 修复备份任务中的空值
            tasks = BackupTask.query.filter(
                (BackupTask.retention_count == None) | 
                (BackupTask.retention_count <= 0)
            ).all()
            
            for task in tasks:
                task.retention_count = 10  # 默认保留10个备份
                repairs_made += 1
                self.logger.info(f"修复任务 {task.id} 的保留数量设置")
            
            # 修复备份日志中的异常状态
            logs = BackupLog.query.filter(
                ~BackupLog.status.in_(['running', 'success', 'failed'])
            ).all()
            
            for log in logs:
                log.status = 'failed'  # 将异常状态设为失败
                repairs_made += 1
                self.logger.info(f"修复日志 {log.id} 的状态")
            
            return repairs_made
            
        except Exception as e:
            self.logger.error(f"修复空值时出错: {e}")
            return 0
    
    def get_data_statistics(self):
        """获取数据统计信息"""
        try:
            stats = {
                'total_tasks': BackupTask.query.count(),
                'active_tasks': BackupTask.query.filter_by(is_active=True).count(),
                'total_logs': BackupLog.query.count(),
                'success_logs': BackupLog.query.filter_by(status='success').count(),
                'failed_logs': BackupLog.query.filter_by(status='failed').count(),
                'running_logs': BackupLog.query.filter_by(status='running').count(),
            }
            
            return True, stats
            
        except Exception as e:
            self.logger.error(f"获取数据统计时出错: {e}")
            return False, {}

# 创建全局实例
data_validation_service = DataValidationService()
