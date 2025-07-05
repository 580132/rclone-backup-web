#!/usr/bin/env python3
"""
备份任务服务
"""

import os
import shutil
import tarfile
import zipfile
import tempfile
import subprocess
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from cryptography.fernet import Fernet
import base64
import hashlib

from models import db, BackupTask, BackupLog, StorageConfig
from services.rclone_service import RcloneService
from config import Config


class BackupService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.rclone_service = RcloneService()
        self.temp_dir = os.path.abspath('data/temp')  # 使用绝对路径

        # 确保临时目录存在
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def create_backup_task(self, task_data: Dict) -> Tuple[bool, str, Optional[BackupTask]]:
        """创建备份任务"""
        try:
            # 验证存储配置是否存在（支持多个存储配置）
            storage_configs_data = task_data.get('storage_configs', [])
            if not storage_configs_data:
                # 向后兼容：检查单个存储配置
                storage_config_id = task_data.get('storage_config_id')
                if storage_config_id:
                    storage_config = StorageConfig.query.get(storage_config_id)
                    if not storage_config:
                        return False, "存储配置不存在", None
                    storage_configs_data = [{
                        'storage_config_id': storage_config_id,
                        'remote_path': task_data.get('remote_path', '')
                    }]
                else:
                    return False, "请至少选择一个存储配置", None

            # 验证所有存储配置是否存在
            for config_data in storage_configs_data:
                storage_config = StorageConfig.query.get(config_data.get('storage_config_id'))
                if not storage_config:
                    return False, f"存储配置ID {config_data.get('storage_config_id')} 不存在", None
            
            # 验证源路径是否存在
            source_path = task_data.get('source_path')
            # 转换为实际的宿主机路径进行验证
            actual_source_path = Config.get_host_path(source_path)
            if not os.path.exists(actual_source_path):
                return False, "源路径不存在", None
            
            # 检查任务名称是否重复
            existing_task = BackupTask.query.filter_by(name=task_data.get('name')).first()
            if existing_task:
                return False, "任务名称已存在", None
            
            # 处理加密密码
            encryption_password = None
            if task_data.get('encryption_enabled') and task_data.get('encryption_password'):
                encryption_password = self._encrypt_password(task_data.get('encryption_password'))
            
            # 创建备份任务（不再直接关联单个存储配置）
            task = BackupTask(
                name=task_data.get('name'),
                description=task_data.get('description', ''),
                source_path=source_path,
                # 保留向后兼容字段
                storage_config_id=storage_configs_data[0].get('storage_config_id') if len(storage_configs_data) == 1 else None,
                remote_path=storage_configs_data[0].get('remote_path') if len(storage_configs_data) == 1 else None,
                cron_expression=task_data.get('cron_expression', ''),
                compression_enabled=task_data.get('compression_enabled', True),
                compression_type=task_data.get('compression_type', 'tar.gz'),
                encryption_enabled=task_data.get('encryption_enabled', False),
                encryption_password=encryption_password,
                retention_count=task_data.get('retention_count', 10),
                is_active=task_data.get('is_active', True)
            )
            
            # 计算下次运行时间
            if task.cron_expression:
                task.next_run_at = self._calculate_next_run_time(task.cron_expression)
            
            db.session.add(task)
            db.session.flush()  # 获取任务ID

            # 创建存储配置关联
            from models import BackupTaskStorageConfig
            for config_data in storage_configs_data:
                task_storage_config = BackupTaskStorageConfig(
                    backup_task_id=task.id,
                    storage_config_id=config_data.get('storage_config_id'),
                    remote_path=config_data.get('remote_path', '')
                )
                db.session.add(task_storage_config)

            db.session.commit()

            self.logger.info(f"Created backup task: {task.name} with {len(storage_configs_data)} storage configs")
            return True, "备份任务创建成功", task
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to create backup task: {e}")
            return False, f"创建备份任务失败: {str(e)}", None
    
    def run_backup_task(self, task_id: int, manual: bool = False) -> Tuple[bool, str]:
        """启动备份任务（异步执行）"""
        try:
            task = BackupTask.query.get(task_id)
            if not task:
                return False, "备份任务不存在"

            if not task.is_active:
                return False, "备份任务已禁用"

            # 检查是否已有正在运行的任务
            running_log = BackupLog.query.filter_by(
                task_id=task_id,
                status='running'
            ).first()

            if running_log:
                return False, "备份任务正在运行中"

            # 启动异步备份任务
            import threading
            from flask import current_app

            # 获取当前应用实例，传递给异步线程
            app = current_app._get_current_object()

            backup_thread = threading.Thread(
                target=self._execute_backup_task_async,
                args=(app, task_id, manual),
                daemon=True
            )
            backup_thread.start()

            return True, f"备份任务 '{task.name}' 已开始执行"

        except Exception as e:
            self.logger.error(f"Failed to start backup task {task_id}: {e}")
            return False, f"启动备份任务失败: {str(e)}"

    def _execute_backup_task_async(self, app, task_id: int, manual: bool = False):
        """异步执行备份任务的实际逻辑"""
        with app.app_context():
            try:
                task = BackupTask.query.get(task_id)
                if not task:
                    self.logger.error(f"Backup task {task_id} not found")
                    return

                # 获取任务的存储配置
                storage_configs = []
                if task.task_storage_configs:
                    # 使用新的多存储配置
                    for task_storage_config in task.task_storage_configs:
                        storage_configs.append({
                            'storage_config': task_storage_config.storage_config,
                            'remote_path': task_storage_config.remote_path
                        })
                elif task.storage_config_id:
                    # 向后兼容：使用旧的单存储配置
                    storage_configs.append({
                        'storage_config': task.storage_config,
                        'remote_path': task.remote_path
                    })

                if not storage_configs:
                    self.logger.error(f"Task {task_id} has no storage configurations")
                    return

                # 执行备份到所有存储配置
                all_success = True
                all_messages = []

                for config_info in storage_configs:
                    storage_config = config_info['storage_config']
                    remote_path = config_info['remote_path']

                    # 为每个存储配置创建单独的备份日志
                    log = BackupLog(
                        task_id=task_id,
                        status='running',
                        start_time=self._get_local_time(),
                        storage_config_id=storage_config.id,
                        remote_path=remote_path
                    )
                    db.session.add(log)
                    db.session.commit()  # 立即提交，确保日志可见

                    try:
                        # 执行备份到当前存储配置
                        success, message = self._execute_backup_to_storage(task, log, storage_config, remote_path)

                        # 更新日志状态
                        log.status = 'success' if success else 'failed'
                        log.end_time = self._get_local_time()
                        if not success:
                            log.error_message = message
                            all_success = False

                        all_messages.append(f"{storage_config.name}: {message}")
                        self.logger.info(f"Backup to {storage_config.name}: {message}")

                    except Exception as e:
                        # 更新日志为失败状态
                        log.status = 'failed'
                        log.end_time = self._get_local_time()
                        log.error_message = str(e)
                        all_success = False
                        all_messages.append(f"{storage_config.name}: 备份失败 - {str(e)}")
                        self.logger.error(f"Backup to {storage_config.name} failed: {e}")

                    # 立即提交每个存储配置的结果
                    db.session.commit()

                # 更新任务的最后运行时间
                task.last_run_at = self._get_local_time()
                if not manual and task.cron_expression:
                    task.next_run_at = self._calculate_next_run_time(task.cron_expression)

                db.session.commit()

                # 记录总体结果
                final_message = "; ".join(all_messages)
                self.logger.info(f"Backup task {task.name} completed. Overall success: {all_success}")

            except Exception as e:
                self.logger.error(f"Failed to execute backup task {task_id}: {e}")
                # 如果有未完成的日志，标记为失败
                try:
                    running_logs = BackupLog.query.filter_by(task_id=task_id, status='running').all()
                    for log in running_logs:
                        log.status = 'failed'
                        log.end_time = self._get_local_time()
                        log.error_message = f"备份任务执行异常: {str(e)}"
                    db.session.commit()
                except Exception as commit_error:
                    self.logger.error(f"Failed to update failed logs: {commit_error}")
                    db.session.rollback()
    
    def _execute_backup_to_storage(self, task: BackupTask, log: BackupLog, storage_config, remote_path: str) -> Tuple[bool, str]:
        """执行具体的备份操作到指定存储配置"""
        temp_file = None
        try:
            # 获取实际的源路径
            actual_source_path = Config.get_host_path(task.source_path)

            # 获取源文件/目录大小
            original_size = self._get_path_size(actual_source_path)
            log.original_size = original_size
            db.session.commit()
            
            # 创建临时文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name = f"{task.name}_{timestamp}"
            
            if task.compression_enabled:
                # 压缩文件
                if task.compression_type == 'tar.gz':
                    temp_file = os.path.join(self.temp_dir, f"{base_name}.tar.gz")
                    success, message = self._create_tar_archive(actual_source_path, temp_file)
                elif task.compression_type == 'zip':
                    temp_file = os.path.join(self.temp_dir, f"{base_name}.zip")
                    success, message = self._create_zip_archive(actual_source_path, temp_file)
                else:
                    return False, f"不支持的压缩格式: {task.compression_type}"
                
                if not success:
                    return False, message
                
                compressed_size = os.path.getsize(temp_file)
                log.compressed_size = compressed_size
            else:
                # 不压缩，直接复制
                if os.path.isfile(actual_source_path):
                    temp_file = os.path.join(self.temp_dir, f"{base_name}_{os.path.basename(actual_source_path)}")
                    shutil.copy2(actual_source_path, temp_file)
                else:
                    return False, "不压缩模式下只支持单个文件备份"
                
                log.compressed_size = original_size
            
            # 加密文件（如果启用）
            if task.encryption_enabled and task.encryption_password:
                encrypted_file = temp_file + '.encrypted'
                success, message = self._encrypt_file(temp_file, encrypted_file, task.encryption_password)
                if not success:
                    return False, message
                
                # 删除未加密文件
                os.remove(temp_file)
                temp_file = encrypted_file
                
                log.final_size = os.path.getsize(temp_file)
            else:
                log.final_size = log.compressed_size
            
            db.session.commit()
            
            # 上传到远程存储
            # 使用目录路径，让rclone自动处理文件名（与脚本行为一致）
            remote_dir_path = remote_path.rstrip('/')  # 确保路径格式正确
            success, message = self.rclone_service.upload_file(
                temp_file,
                remote_dir_path + '/',  # 以/结尾表示目录
                storage_config.rclone_config_name
            )

            if not success:
                return False, f"上传失败: {message}"

            # 清理旧备份文件（基于远程存储中的实际文件）
            self._cleanup_old_backups_from_remote_storage(task, storage_config, remote_path)

            return True, "备份完成"
            
        finally:
            # 清理临时文件
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    self.logger.warning(f"Failed to remove temp file {temp_file}: {e}")
    
    def _get_path_size(self, path: str) -> int:
        """获取文件或目录的总大小"""
        if os.path.isfile(path):
            return os.path.getsize(path)
        
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(file_path)
                except (OSError, IOError):
                    continue
        return total_size
    
    def _create_tar_archive(self, source_path: str, archive_path: str) -> Tuple[bool, str]:
        """创建tar.gz压缩包"""
        try:
            with tarfile.open(archive_path, 'w:gz') as tar:
                if os.path.isfile(source_path):
                    tar.add(source_path, arcname=os.path.basename(source_path))
                else:
                    tar.add(source_path, arcname=os.path.basename(source_path))
            return True, "压缩完成"
        except Exception as e:
            return False, f"压缩失败: {str(e)}"
    
    def _create_zip_archive(self, source_path: str, archive_path: str) -> Tuple[bool, str]:
        """创建zip压缩包"""
        try:
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if os.path.isfile(source_path):
                    zipf.write(source_path, os.path.basename(source_path))
                else:
                    for root, dirs, files in os.walk(source_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, os.path.dirname(source_path))
                            zipf.write(file_path, arcname)
            return True, "压缩完成"
        except Exception as e:
            return False, f"压缩失败: {str(e)}"
    
    def _encrypt_file(self, input_file: str, output_file: str, password: str) -> Tuple[bool, str]:
        """加密文件"""
        try:
            # 解密存储的密码
            decrypted_password = self._decrypt_password(password)
            
            # 生成密钥
            key = self._generate_key_from_password(decrypted_password)
            fernet = Fernet(key)
            
            with open(input_file, 'rb') as infile:
                data = infile.read()
            
            encrypted_data = fernet.encrypt(data)
            
            with open(output_file, 'wb') as outfile:
                outfile.write(encrypted_data)
            
            return True, "加密完成"
        except Exception as e:
            return False, f"加密失败: {str(e)}"
    
    def _encrypt_password(self, password: str) -> str:
        """加密密码用于存储"""
        # 这里使用简单的base64编码，实际应用中应使用更安全的方法
        return base64.b64encode(password.encode()).decode()
    
    def _decrypt_password(self, encrypted_password: str) -> str:
        """解密存储的密码"""
        return base64.b64decode(encrypted_password.encode()).decode()
    
    def _generate_key_from_password(self, password: str) -> bytes:
        """从密码生成加密密钥"""
        # 使用密码的SHA256哈希作为密钥
        key = hashlib.sha256(password.encode()).digest()
        return base64.urlsafe_b64encode(key)
    
    def _calculate_next_run_time(self, cron_expression: str) -> Optional[datetime]:
        """计算下次运行时间"""
        try:
            from apscheduler.triggers.cron import CronTrigger
            import pytz

            # 解析Cron表达式
            cron_parts = cron_expression.split()
            if len(cron_parts) != 5:
                self.logger.error(f"Invalid cron expression: {cron_expression}")
                return None

            minute, hour, day, month, day_of_week = cron_parts

            # 创建Cron触发器
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone=pytz.timezone('Asia/Shanghai')
            )

            # 计算下次运行时间
            now = datetime.now(pytz.timezone('Asia/Shanghai'))
            next_run = trigger.get_next_fire_time(None, now)

            if next_run:
                # 转换为本地时间（无时区信息）
                return next_run.replace(tzinfo=None)

            return None

        except Exception as e:
            self.logger.error(f"Failed to calculate next run time: {e}")
            return None

    def _get_local_time(self) -> datetime:
        """获取本地时间（Asia/Shanghai时区）"""
        try:
            import pytz

            # 获取Asia/Shanghai时区的当前时间
            local_tz = pytz.timezone('Asia/Shanghai')
            local_time = datetime.now(local_tz)
            # 返回无时区信息的本地时间，用于数据库存储
            return local_time.replace(tzinfo=None)
        except Exception as e:
            self.logger.warning(f"Failed to get local time, using system time: {e}")
            # 如果获取本地时间失败，使用系统时间
            return datetime.now()
    
    def update_backup_task(self, task_id: int, task_data: Dict, storage_configs_data: List[Dict] = None) -> Tuple[bool, str, Optional[BackupTask]]:
        """更新备份任务"""
        try:
            task = BackupTask.query.get(task_id)
            if not task:
                return False, "任务不存在", None

            # 验证源路径是否存在
            source_path = task_data.get('source_path')
            # 转换为实际的宿主机路径进行验证
            actual_source_path = Config.get_host_path(source_path)
            if not os.path.exists(actual_source_path):
                return False, "源路径不存在", None

            # 检查任务名称是否重复（排除当前任务）
            existing_task = BackupTask.query.filter(
                BackupTask.name == task_data.get('name'),
                BackupTask.id != task_id
            ).first()
            if existing_task:
                return False, "任务名称已存在", None

            # 处理存储配置数据
            if storage_configs_data:
                # 新的多存储配置模式
                if not storage_configs_data:
                    return False, "至少需要选择一个存储配置", None

                # 验证所有存储配置是否存在
                for config_data in storage_configs_data:
                    storage_config = StorageConfig.query.get(config_data.get('storage_config_id'))
                    if not storage_config:
                        return False, f"存储配置不存在: {config_data.get('storage_config_id')}", None
            else:
                # 向后兼容：旧的单存储配置模式
                storage_config = StorageConfig.query.get(task_data.get('storage_config_id'))
                if not storage_config:
                    return False, "存储配置不存在", None

            # 处理加密密码
            encryption_password = task.encryption_password  # 保持原有密码
            if task_data.get('encryption_enabled') and task_data.get('encryption_password'):
                # 如果提供了新密码，则更新
                if task_data.get('encryption_password') != '':
                    encryption_password = self._encrypt_password(task_data.get('encryption_password'))
            elif not task_data.get('encryption_enabled'):
                # 如果禁用加密，清空密码
                encryption_password = None

            # 更新任务字段
            task.name = task_data.get('name')
            task.description = task_data.get('description', '')
            task.source_path = source_path
            task.cron_expression = task_data.get('cron_expression', '')
            task.compression_enabled = task_data.get('compression_enabled', True)
            task.compression_type = task_data.get('compression_type', 'tar.gz')
            task.encryption_enabled = task_data.get('encryption_enabled', False)
            task.encryption_password = encryption_password
            task.retention_count = task_data.get('retention_count', 10)
            task.is_active = task_data.get('is_active', True)
            task.updated_at = self._get_local_time()

            # 处理存储配置关联
            if storage_configs_data:
                # 新的多存储配置模式：删除旧的关联，创建新的关联
                from models import BackupTaskStorageConfig

                # 删除现有的存储配置关联
                BackupTaskStorageConfig.query.filter_by(backup_task_id=task.id).delete()

                # 创建新的存储配置关联
                for config_data in storage_configs_data:
                    task_storage_config = BackupTaskStorageConfig(
                        backup_task_id=task.id,
                        storage_config_id=config_data.get('storage_config_id'),
                        remote_path=config_data.get('remote_path', '')
                    )
                    db.session.add(task_storage_config)

                # 清空旧的单存储配置字段
                task.storage_config_id = None
                task.remote_path = None
            else:
                # 向后兼容：旧的单存储配置模式
                task.storage_config_id = task_data.get('storage_config_id')
                task.remote_path = task_data.get('remote_path')

            # 重新计算下次运行时间
            if task.cron_expression:
                task.next_run_at = self._calculate_next_run_time(task.cron_expression)
            else:
                task.next_run_at = None

            db.session.commit()

            self.logger.info(f"Updated backup task: {task.name}")
            return True, "任务更新成功", task

        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to update backup task {task_id}: {e}")
            return False, f"更新任务时出错: {str(e)}", None

    def get_backup_task(self, task_id: int) -> Optional[BackupTask]:
        """获取单个备份任务"""
        try:
            return BackupTask.query.get(task_id)
        except Exception as e:
            self.logger.error(f"Failed to get backup task {task_id}: {e}")
            return None

    def delete_backup_task(self, task_id: int) -> Tuple[bool, str]:
        """删除备份任务"""
        try:
            task = BackupTask.query.get(task_id)
            if not task:
                return False, "备份任务不存在"

            # 检查是否有正在运行的任务
            running_log = BackupLog.query.filter_by(
                task_id=task_id,
                status='running'
            ).first()

            if running_log:
                return False, "无法删除正在运行的备份任务"

            # 删除相关的备份日志
            BackupLog.query.filter_by(task_id=task_id).delete()

            # 删除任务
            db.session.delete(task)
            db.session.commit()

            self.logger.info(f"Deleted backup task: {task.name}")
            return True, "备份任务删除成功"

        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to delete backup task: {e}")
            return False, f"删除备份任务失败: {str(e)}"

    def _cleanup_old_backups(self, task: BackupTask):
        """清理旧备份文件，保留指定数量的最新备份"""
        try:
            # 获取成功的备份日志，按时间倒序排列
            successful_logs = BackupLog.query.filter_by(
                task_id=task.id,
                status='success'
            ).order_by(BackupLog.start_time.desc()).all()

            # 如果备份数量超过保留数量，删除多余的备份
            if len(successful_logs) > task.retention_count:
                logs_to_delete = successful_logs[task.retention_count:]

                for log in logs_to_delete:
                    try:
                        # 构建远程文件路径
                        timestamp = log.start_time.strftime('%Y%m%d_%H%M%S')

                        # 尝试不同的文件名格式
                        possible_extensions = []
                        if task.compression_enabled:
                            if task.compression_type == 'tar.gz':
                                possible_extensions.append('.tar.gz')
                            elif task.compression_type == 'zip':
                                possible_extensions.append('.zip')
                        else:
                            # 不压缩时，需要根据源文件确定扩展名
                            if os.path.isfile(task.source_path):
                                _, ext = os.path.splitext(task.source_path)
                                possible_extensions.append(ext)

                        if task.encryption_enabled:
                            possible_extensions = [ext + '.encrypted' for ext in possible_extensions]

                        # 尝试删除远程文件
                        deleted = False
                        for ext in possible_extensions:
                            remote_file_name = f"{task.name}_{timestamp}{ext}"
                            # 确保路径格式与上传时一致
                            remote_dir_path = task.remote_path.rstrip('/')
                            remote_file_path = f"{remote_dir_path}/{remote_file_name}"

                            success, message = self._delete_remote_file(
                                remote_file_path,
                                task.storage_config.rclone_config_name
                            )

                            if success:
                                deleted = True
                                self.logger.info(f"Deleted old backup file: {remote_file_path}")
                                break

                        if not deleted:
                            self.logger.warning(f"Could not delete old backup for log {log.id}")

                        # 删除备份日志记录
                        db.session.delete(log)

                    except Exception as e:
                        self.logger.error(f"Error deleting old backup for log {log.id}: {e}")
                        continue

                # 提交数据库更改
                db.session.commit()

                self.logger.info(f"Cleaned up {len(logs_to_delete)} old backups for task {task.name}")

        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups for task {task.id}: {e}")

    def _cleanup_old_backups_from_remote_storage(self, task: BackupTask, storage_config, remote_path: str):
        """基于远程存储中的实际文件清理旧备份，支持指定存储配置"""
        try:
            self.logger.info(f"Starting cleanup of old backups for task {task.name} in {storage_config.name}")

            # 获取远程目录中的文件列表
            remote_dir_path = remote_path.rstrip('/')
            success, files, message = self.rclone_service.list_files(
                remote_dir_path,
                storage_config.rclone_config_name
            )

            if not success:
                self.logger.error(f"Failed to list remote files in {storage_config.name}: {message}")
                return

            # 过滤出属于当前任务的备份文件
            task_files = []
            for file_info in files:
                file_name = file_info.get('Name', '')
                # 匹配文件名格式：task_name_YYYYMMDD_HHMMSS.*
                if file_name.startswith(f"{task.name}_") and len(file_name.split('_')) >= 3:
                    try:
                        # 提取时间戳部分验证格式
                        parts = file_name.split('_')
                        if len(parts) >= 3:
                            date_part = parts[-2]  # YYYYMMDD
                            time_part = parts[-1].split('.')[0]  # HHMMSS
                            if len(date_part) == 8 and len(time_part) == 6:
                                task_files.append(file_info)
                    except:
                        continue

            self.logger.info(f"Found {len(task_files)} backup files for task {task.name} in {storage_config.name}")

            # 如果文件数量超过保留数量，删除最旧的文件
            if len(task_files) > task.retention_count:
                # 按文件名排序（文件名包含时间戳，所以可以直接排序）
                task_files.sort(key=lambda x: x.get('Name', ''))

                # 计算需要删除的文件数量
                files_to_delete = task_files[:-task.retention_count]  # 保留最新的N个

                self.logger.info(f"Need to delete {len(files_to_delete)} old backup files in {storage_config.name}")

                for file_info in files_to_delete:
                    file_name = file_info.get('Name', '')
                    remote_file_path = f"{remote_dir_path}/{file_name}"

                    success, message = self._delete_remote_file(
                        remote_file_path,
                        storage_config.rclone_config_name
                    )

                    if success:
                        self.logger.info(f"Deleted old backup file: {file_name} from {storage_config.name}")
                    else:
                        self.logger.warning(f"Failed to delete old backup file {file_name} from {storage_config.name}: {message}")

                self.logger.info(f"Cleanup completed for task {task.name} in {storage_config.name}")
            else:
                self.logger.info(f"No cleanup needed for task {task.name} in {storage_config.name} (only {len(task_files)} files, retention: {task.retention_count})")

        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups from {storage_config.name} for task {task.id}: {e}")

    def _cleanup_old_backups_from_remote(self, task: BackupTask):
        """基于远程存储中的实际文件清理旧备份，类似脚本逻辑（向后兼容）"""
        try:
            self.logger.info(f"Starting cleanup of old backups for task {task.name}")

            # 获取远程目录中的文件列表
            remote_dir_path = task.remote_path.rstrip('/')
            success, files, message = self.rclone_service.list_files(
                remote_dir_path,
                task.storage_config.rclone_config_name
            )

            if not success:
                self.logger.error(f"Failed to list remote files: {message}")
                return

            # 过滤出属于当前任务的备份文件
            task_files = []
            for file_info in files:
                file_name = file_info.get('Name', '')
                # 匹配文件名格式：task_name_YYYYMMDD_HHMMSS.*
                if file_name.startswith(f"{task.name}_") and len(file_name.split('_')) >= 3:
                    try:
                        # 提取时间戳部分验证格式
                        parts = file_name.split('_')
                        if len(parts) >= 3:
                            date_part = parts[-2]  # YYYYMMDD
                            time_part = parts[-1].split('.')[0]  # HHMMSS
                            if len(date_part) == 8 and len(time_part) == 6:
                                task_files.append(file_info)
                    except:
                        continue

            self.logger.info(f"Found {len(task_files)} backup files for task {task.name}")

            # 如果文件数量超过保留数量，删除最旧的文件
            if len(task_files) > task.retention_count:
                # 按文件名排序（文件名包含时间戳，所以可以直接排序）
                task_files.sort(key=lambda x: x.get('Name', ''))

                # 计算需要删除的文件数量
                files_to_delete = task_files[:-task.retention_count]  # 保留最新的N个

                self.logger.info(f"Need to delete {len(files_to_delete)} old backup files")

                for file_info in files_to_delete:
                    file_name = file_info.get('Name', '')
                    remote_file_path = f"{remote_dir_path}/{file_name}"

                    success, message = self._delete_remote_file(
                        remote_file_path,
                        task.storage_config.rclone_config_name
                    )

                    if success:
                        self.logger.info(f"Deleted old backup file: {file_name}")
                    else:
                        self.logger.warning(f"Failed to delete old backup file {file_name}: {message}")

                self.logger.info(f"Cleanup completed for task {task.name}")
            else:
                self.logger.info(f"No cleanup needed for task {task.name} (only {len(task_files)} files, retention: {task.retention_count})")

        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups from remote for task {task.id}: {e}")

    def _delete_remote_file(self, remote_path: str, config_name: str) -> Tuple[bool, str]:
        """删除远程文件"""
        try:
            # 使用rclone删除远程文件
            success, message = self.rclone_service.delete_file(remote_path, config_name)
            return success, message
        except Exception as e:
            return False, f"删除远程文件失败: {str(e)}"

    def get_backup_files_count(self, task_id: int) -> int:
        """获取任务的备份文件数量"""
        try:
            count = BackupLog.query.filter_by(
                task_id=task_id,
                status='success'
            ).count()
            return count
        except Exception as e:
            self.logger.error(f"Failed to get backup files count: {e}")
            return 0
