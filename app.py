from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import os
import logging
from datetime import datetime

# 导入配置和模型
from config import config, Config
from models import db, User, StorageConfig, StorageConfigHistory, BackupTask, BackupLog

# 导入服务
from services.auth_service import AuthService
from services.rclone_service import RcloneService
from services.config_service import ConfigService

def create_app(config_name='default'):
    """应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # 初始化配置
    Config.init_app(app)
    
    # 初始化数据库
    db.init_app(app)
    
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, app.config['LOG_LEVEL']),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(app.config['LOG_FILE']),
            logging.StreamHandler()
        ]
    )
    
    # 初始化服务
    auth_service = AuthService()
    rclone_service = RcloneService()
    config_service = ConfigService()
    
    # 登录装饰器
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    
    # 路由定义
    @app.route('/')
    @login_required
    def dashboard():
        """仪表板"""
        try:
            # 获取任务统计
            total_tasks = BackupTask.query.count()
            active_tasks = BackupTask.query.filter_by(is_active=True).count()
            
            # 获取最近的备份日志
            recent_logs = BackupLog.query.order_by(BackupLog.start_time.desc()).limit(10).all()
            
            # 获取今日备份统计
            today = datetime.now().date()
            today_logs = BackupLog.query.filter(
                db.func.date(BackupLog.start_time) == today
            ).all()
            
            today_success = len([log for log in today_logs if log.status == 'success'])
            today_failed = len([log for log in today_logs if log.status == 'failed'])
            
            return render_template('dashboard.html',
                                 total_tasks=total_tasks,
                                 active_tasks=active_tasks,
                                 recent_logs=recent_logs,
                                 today_success=today_success,
                                 today_failed=today_failed)
        except Exception as e:
            app.logger.error(f"Dashboard error: {e}")
            flash('加载仪表板时出错', 'error')
            return render_template('dashboard.html',
                                 total_tasks=0,
                                 active_tasks=0,
                                 recent_logs=[],
                                 today_success=0,
                                 today_failed=0)
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """登录页面"""
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if not username or not password:
                flash('请输入用户名和密码', 'error')
                return render_template('login.html')
            
            if auth_service.authenticate(username, password):
                user = auth_service.get_user_by_username(username)
                session['user_id'] = user.id
                session['username'] = user.username
                session.permanent = True
                
                app.logger.info(f"User {username} logged in")
                flash('登录成功', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('用户名或密码错误', 'error')
        
        return render_template('login.html')
    
    @app.route('/logout')
    def logout():
        """退出登录"""
        username = session.get('username', 'Unknown')
        session.clear()
        app.logger.info(f"User {username} logged out")
        flash('已退出登录', 'info')
        return redirect(url_for('login'))
    
    @app.route('/storage-configs')
    @login_required
    def storage_configs():
        """存储配置页面"""
        configs = StorageConfig.query.all()
        storage_types = rclone_service.get_supported_types()
        return render_template('storage_configs.html', 
                             configs=configs, 
                             storage_types=storage_types)
    
    @app.route('/storage-configs/create', methods=['POST'])
    @login_required
    def create_storage_config():
        """创建存储配置"""
        try:
            # 记录所有表单数据用于调试
            app.logger.debug(f"Form data received: {dict(request.form)}")

            name = request.form.get('name', '').strip()
            storage_type = request.form.get('storage_type', '').strip()
            description = request.form.get('description', '').strip()

            app.logger.info(f"Creating storage config - name: '{name}', type: '{storage_type}'")

            if not name or not storage_type:
                app.logger.error(f"Missing required fields - name: '{name}', storage_type: '{storage_type}'")
                flash('请填写配置名称和存储类型', 'error')
                return redirect(url_for('storage_configs'))

            # 收集配置数据
            config_data = {}
            if storage_type in ['s3', 'alibaba_oss', 'cloudflare_r2']:
                # 根据存储类型读取对应的字段
                if storage_type == 's3':
                    raw_access_key = request.form.get('access_key', '')
                    raw_secret_key = request.form.get('secret_key', '')
                    raw_region = request.form.get('region', '')
                    raw_endpoint = request.form.get('endpoint', '')
                    raw_bucket = request.form.get('bucket', '')
                elif storage_type == 'alibaba_oss':
                    raw_access_key = request.form.get('oss_access_key', '')  # 阿里云OSS使用专用字段名
                    raw_secret_key = request.form.get('oss_secret_key', '')
                    raw_region = request.form.get('region', '')
                    raw_endpoint = request.form.get('oss_endpoint', '')
                    raw_bucket = request.form.get('bucket', '')
                elif storage_type == 'cloudflare_r2':
                    raw_access_key = request.form.get('r2_access_key', '')  # R2使用专用字段名
                    raw_secret_key = request.form.get('r2_secret_key', '')
                    raw_region = request.form.get('region', '')
                    raw_endpoint = request.form.get('r2_endpoint', '')
                    raw_bucket = request.form.get('bucket', '')

                config_data = {
                    'access_key': raw_access_key.strip(),
                    'secret_key': raw_secret_key.strip(),
                    'region': raw_region.strip(),
                    'endpoint': raw_endpoint.strip(),
                    'bucket': raw_bucket.strip()
                }

                # 设置默认值
                if storage_type == 's3' and not config_data['region']:
                    config_data['region'] = 'us-east-1'
                elif storage_type == 'alibaba_oss' and not config_data['region']:
                    config_data['region'] = 'oss-cn-hangzhou'
                elif storage_type == 'cloudflare_r2':
                    config_data['region'] = 'auto'  # Cloudflare R2 固定使用 auto

                # 验证必填字段
                if storage_type == 'cloudflare_r2':
                    if not config_data['access_key'] or not config_data['secret_key'] or not config_data['endpoint']:
                        flash('请填写所有必填字段：Access Key ID、Secret Access Key、Endpoint', 'error')
                        return redirect(url_for('storage_configs'))

            elif storage_type == 'google_drive':
                config_data = {
                    'client_id': request.form.get('client_id', '').strip(),
                    'client_secret': request.form.get('client_secret', '').strip(),
                    'scope': request.form.get('scope', 'drive').strip(),
                    'root_folder_id': request.form.get('root_folder_id', '').strip(),
                    'service_account_credentials': request.form.get('service_account_credentials', '').strip()
                }

            elif storage_type == 'sftp':
                config_data = {
                    'host': request.form.get('host', '').strip(),
                    'username': request.form.get('username', '').strip(),
                    'password': request.form.get('password', '').strip(),
                    'port': request.form.get('port', '22').strip(),
                    'key_file': request.form.get('key_file', '').strip(),
                    'key_pass': request.form.get('key_pass', '').strip(),
                    'use_insecure_cipher': request.form.get('use_insecure_cipher') == 'on',
                    'disable_hashcheck': request.form.get('disable_hashcheck') == 'on'
                }

            elif storage_type == 'ftp':
                config_data = {
                    'host': request.form.get('host', '').strip(),
                    'username': request.form.get('username', '').strip(),
                    'password': request.form.get('password', '').strip(),
                    'port': request.form.get('port', '21').strip()
                }
            else:
                flash(f'不支持的存储类型: {storage_type}', 'error')
                return redirect(url_for('storage_configs'))

            # 使用ConfigService创建配置
            current_user = session.get('username', 'unknown')
            success, message, storage_config = config_service.create_storage_config(
                name=name,
                storage_type=storage_type,
                config_data=config_data,
                description=description,
                created_by=current_user
            )

            if success:
                app.logger.info(f"Created storage config: {name}")
                flash('存储配置创建成功', 'success')
            else:
                app.logger.error(f"Failed to create storage config: {message}")
                flash(message, 'error')

        except Exception as e:
            app.logger.error(f"Failed to create storage config: {e}")
            flash('创建存储配置时出错', 'error')

        return redirect(url_for('storage_configs'))
    
    @app.route('/storage-configs/<int:config_id>/test')
    @login_required
    def test_storage_config(config_id):
        """测试存储配置"""
        try:
            config = StorageConfig.query.get_or_404(config_id)
            success, message = rclone_service.test_connection(config.rclone_config_name)
            
            return jsonify({
                'success': success,
                'message': message
            })
        except Exception as e:
            app.logger.error(f"Storage config test error: {e}")
            return jsonify({
                'success': False,
                'message': f'测试失败: {str(e)}'
            })
    
    @app.route('/storage-configs/<int:config_id>/edit')
    @login_required
    def edit_storage_config(config_id):
        """编辑存储配置页面"""
        try:
            config_details = config_service.get_storage_config_details(config_id)
            if not config_details:
                flash('配置不存在', 'error')
                return redirect(url_for('storage_configs'))

            storage_config, rclone_config = config_details
            storage_types = rclone_service.get_supported_types()

            return render_template('edit_storage_config.html',
                                 config=storage_config,
                                 rclone_config=rclone_config,
                                 storage_types=storage_types)
        except Exception as e:
            app.logger.error(f"Failed to load edit page: {e}")
            flash('加载编辑页面时出错', 'error')
            return redirect(url_for('storage_configs'))

    @app.route('/storage-configs/<int:config_id>/update', methods=['POST'])
    @login_required
    def update_storage_config(config_id):
        """更新存储配置"""
        try:
            # 获取基本信息
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()

            # 获取当前配置信息
            config_details = config_service.get_storage_config_details(config_id)
            if not config_details:
                flash('配置不存在', 'error')
                return redirect(url_for('storage_configs'))

            storage_config, _ = config_details
            storage_type = storage_config.storage_type

            if not name:
                flash('请填写配置名称', 'error')
                return redirect(url_for('edit_storage_config', config_id=config_id))

            # 收集配置数据
            config_data = {}
            if storage_type in ['s3', 'alibaba_oss', 'cloudflare_r2']:
                # 根据存储类型读取对应的字段
                if storage_type == 's3':
                    raw_access_key = request.form.get('access_key', '')
                    raw_secret_key = request.form.get('secret_key', '')
                    raw_region = request.form.get('region', '')
                    raw_endpoint = request.form.get('endpoint', '')
                    raw_bucket = request.form.get('bucket', '')
                elif storage_type == 'alibaba_oss':
                    raw_access_key = request.form.get('oss_access_key', '')
                    raw_secret_key = request.form.get('oss_secret_key', '')
                    raw_region = request.form.get('region', '')
                    raw_endpoint = request.form.get('oss_endpoint', '')
                    raw_bucket = request.form.get('bucket', '')
                elif storage_type == 'cloudflare_r2':
                    raw_access_key = request.form.get('r2_access_key', '')
                    raw_secret_key = request.form.get('r2_secret_key', '')
                    raw_region = request.form.get('region', '')
                    raw_endpoint = request.form.get('r2_endpoint', '')
                    raw_bucket = request.form.get('bucket', '')

                config_data = {
                    'access_key': raw_access_key.strip(),
                    'secret_key': raw_secret_key.strip(),
                    'region': raw_region.strip(),
                    'endpoint': raw_endpoint.strip(),
                    'bucket': raw_bucket.strip()
                }

                # 设置默认值
                if storage_type == 's3' and not config_data['region']:
                    config_data['region'] = 'us-east-1'
                elif storage_type == 'alibaba_oss' and not config_data['region']:
                    config_data['region'] = 'oss-cn-hangzhou'
                elif storage_type == 'cloudflare_r2':
                    config_data['region'] = 'auto'

                # 验证必填字段
                if storage_type == 'cloudflare_r2':
                    if not config_data['access_key'] or not config_data['secret_key'] or not config_data['endpoint']:
                        flash('请填写所有必填字段：Access Key ID、Secret Access Key、Endpoint', 'error')
                        return redirect(url_for('edit_storage_config', config_id=config_id))

            elif storage_type == 'google_drive':
                config_data = {
                    'client_id': request.form.get('client_id', '').strip(),
                    'client_secret': request.form.get('client_secret', '').strip(),
                    'scope': request.form.get('scope', 'drive').strip(),
                    'root_folder_id': request.form.get('root_folder_id', '').strip(),
                    'service_account_credentials': request.form.get('service_account_credentials', '').strip()
                }

            elif storage_type == 'sftp':
                config_data = {
                    'host': request.form.get('host', '').strip(),
                    'username': request.form.get('username', '').strip(),
                    'password': request.form.get('password', '').strip(),
                    'port': request.form.get('port', '22').strip(),
                    'key_file': request.form.get('key_file', '').strip(),
                    'key_pass': request.form.get('key_pass', '').strip(),
                    'use_insecure_cipher': request.form.get('use_insecure_cipher') == 'on',
                    'disable_hashcheck': request.form.get('disable_hashcheck') == 'on'
                }

            elif storage_type == 'ftp':
                config_data = {
                    'host': request.form.get('host', '').strip(),
                    'username': request.form.get('username', '').strip(),
                    'password': request.form.get('password', '').strip(),
                    'port': request.form.get('port', '21').strip()
                }

            # 使用ConfigService更新配置
            current_user = session.get('username', 'unknown')
            success, message = config_service.update_storage_config(
                storage_config_id=config_id,
                name=name,
                config_data=config_data,
                description=description,
                created_by=current_user
            )

            if success:
                app.logger.info(f"Updated storage config: {config_id}")
                flash('存储配置更新成功', 'success')
                return redirect(url_for('storage_configs'))
            else:
                app.logger.error(f"Failed to update storage config: {message}")
                flash(message, 'error')
                return redirect(url_for('edit_storage_config', config_id=config_id))

        except Exception as e:
            app.logger.error(f"Failed to update storage config: {e}")
            flash('更新存储配置时出错', 'error')
            return redirect(url_for('edit_storage_config', config_id=config_id))

    @app.route('/storage-configs/<int:config_id>/delete', methods=['POST'])
    @login_required
    def delete_storage_config(config_id):
        """删除存储配置"""
        try:
            # 使用ConfigService删除配置
            success, message = config_service.delete_storage_config(config_id)

            if success:
                app.logger.info(f"Deleted storage config: {config_id}")
                flash('存储配置已删除', 'success')
            else:
                app.logger.error(f"Failed to delete storage config: {message}")
                flash(message, 'error')

        except Exception as e:
            app.logger.error(f"Failed to delete storage config: {e}")
            flash('删除存储配置时出错', 'error')

        return redirect(url_for('storage_configs'))

    @app.route('/storage-configs/<int:config_id>/history')
    @login_required
    def storage_config_history(config_id):
        """查看存储配置历史版本"""
        try:
            config = StorageConfig.query.get_or_404(config_id)
            history = config_service.get_config_history(config_id)

            return render_template('storage_config_history.html',
                                 config=config,
                                 history=history)
        except Exception as e:
            app.logger.error(f"Failed to get config history: {e}")
            flash('获取配置历史时出错', 'error')
            return redirect(url_for('storage_configs'))

    @app.route('/storage-configs/<int:config_id>/sync', methods=['POST'])
    @login_required
    def sync_storage_config(config_id):
        """同步存储配置从rclone文件"""
        try:
            current_user = session.get('username', 'unknown')
            success, message = config_service.sync_config_from_rclone(
                config_id,
                "手动同步",
                current_user
            )

            if success:
                flash(message, 'success')
            else:
                flash(message, 'error')

        except Exception as e:
            app.logger.error(f"Failed to sync config: {e}")
            flash('同步配置时出错', 'error')

        return redirect(url_for('storage_configs'))

    @app.route('/storage-configs/<int:config_id>/restore/<int:version>', methods=['POST'])
    @login_required
    def restore_storage_config(config_id, version):
        """恢复存储配置到指定版本"""
        try:
            current_user = session.get('username', 'unknown')
            success, message = config_service.restore_config_version(
                config_id,
                version,
                current_user
            )

            if success:
                flash(message, 'success')
            else:
                flash(message, 'error')

        except Exception as e:
            app.logger.error(f"Failed to restore config: {e}")
            flash('恢复配置时出错', 'error')

        return redirect(url_for('storage_config_history', config_id=config_id))

    @app.route('/storage-configs/sync-all', methods=['POST'])
    @login_required
    def sync_all_storage_configs():
        """批量同步所有存储配置"""
        try:
            success_count, error_count, errors = config_service.sync_all_configs_from_rclone()

            if error_count == 0:
                flash(f'成功同步 {success_count} 个配置', 'success')
            else:
                flash(f'同步完成：{success_count} 个成功，{error_count} 个失败', 'warning')
                for error in errors:
                    app.logger.error(f"Sync error: {error}")

        except Exception as e:
            app.logger.error(f"Failed to sync all configs: {e}")
            flash('批量同步时出错', 'error')

        return redirect(url_for('storage_configs'))

    @app.route('/backup-tasks')
    @login_required
    def backup_tasks():
        """备份任务页面"""
        tasks = BackupTask.query.all()
        storage_configs = StorageConfig.query.filter_by(is_active=True).all()
        return render_template('backup_tasks.html',
                             tasks=tasks,
                             storage_configs=storage_configs)

    @app.route('/backup-tasks', methods=['POST'])
    @login_required
    def create_backup_task():
        """创建备份任务"""
        try:
            from services.backup_service import BackupService
            backup_service = BackupService()

            # 获取表单数据
            task_data = {
                'name': request.form.get('name'),
                'description': request.form.get('description', ''),
                'source_path': request.form.get('source_path'),
                'storage_config_id': int(request.form.get('storage_config_id')),
                'remote_path': request.form.get('remote_path'),
                'cron_expression': request.form.get('cron_expression', ''),
                'compression_enabled': request.form.get('compression_enabled') == 'on',
                'compression_type': request.form.get('compression_type', 'tar.gz'),
                'encryption_enabled': request.form.get('encryption_enabled') == 'on',
                'encryption_password': request.form.get('encryption_password', ''),
                'retention_count': int(request.form.get('retention_count', 10)),
                'is_active': request.form.get('is_active') == 'on'
            }

            # 验证必填字段
            if not all([task_data['name'], task_data['source_path'], task_data['remote_path']]):
                flash('请填写所有必填字段', 'error')
                return redirect(url_for('backup_tasks'))

            # 创建备份任务
            success, message, task = backup_service.create_backup_task(task_data)

            if success:
                # 添加任务到调度器
                try:
                    from services.scheduler_service import scheduler_service
                    if scheduler_service.scheduler and scheduler_service.scheduler.running:
                        # 添加任务到调度器
                        scheduler_service.add_backup_task(task)
                        app.logger.info(f"Added task {task.name} to scheduler")
                    else:
                        app.logger.warning("Scheduler not running, task not added to scheduler")
                except Exception as e:
                    app.logger.error(f"Failed to add task {task.name} to scheduler: {e}")
                    # 调度器添加失败不应该影响任务创建的成功状态

                flash(f'备份任务 "{task.name}" 创建成功', 'success')
            else:
                flash(message, 'error')

        except Exception as e:
            app.logger.error(f"Failed to create backup task: {e}")
            flash('创建备份任务时出错', 'error')

        return redirect(url_for('backup_tasks'))

    @app.route('/backup-tasks/<int:task_id>/edit')
    @login_required
    def edit_backup_task(task_id):
        """编辑备份任务页面"""
        try:
            task = BackupTask.query.get(task_id)
            if not task:
                flash('任务不存在', 'error')
                return redirect(url_for('backup_tasks'))

            storage_configs = StorageConfig.query.filter_by(is_active=True).all()
            return render_template('edit_backup_task.html',
                                 task=task,
                                 storage_configs=storage_configs)
        except Exception as e:
            app.logger.error(f"Failed to load edit task page: {e}")
            flash('加载编辑页面时出错', 'error')
            return redirect(url_for('backup_tasks'))

    @app.route('/backup-tasks/<int:task_id>/edit', methods=['POST'])
    @login_required
    def update_backup_task(task_id):
        """更新备份任务"""
        try:
            from services.backup_service import BackupService
            backup_service = BackupService()

            # 获取表单数据
            task_data = {
                'name': request.form.get('name'),
                'description': request.form.get('description', ''),
                'source_path': request.form.get('source_path'),
                'storage_config_id': int(request.form.get('storage_config_id')),
                'remote_path': request.form.get('remote_path'),
                'cron_expression': request.form.get('cron_expression', ''),
                'compression_enabled': request.form.get('compression_enabled') == 'on',
                'compression_type': request.form.get('compression_type', 'tar.gz'),
                'encryption_enabled': request.form.get('encryption_enabled') == 'on',
                'encryption_password': request.form.get('encryption_password', ''),
                'retention_count': int(request.form.get('retention_count', 10)),
                'is_active': request.form.get('is_active') == 'on'
            }

            # 验证必填字段
            if not all([task_data['name'], task_data['source_path'], task_data['remote_path']]):
                flash('请填写所有必填字段', 'error')
                return redirect(url_for('edit_backup_task', task_id=task_id))

            # 更新备份任务
            success, message, task = backup_service.update_backup_task(task_id, task_data)

            if success:
                # 更新调度器中的任务
                try:
                    from services.scheduler_service import scheduler_service
                    if scheduler_service.scheduler and scheduler_service.scheduler.running:
                        # 更新调度器中的任务
                        scheduler_service.update_backup_task(task)
                        app.logger.info(f"Updated scheduler for task {task.name}")
                    else:
                        app.logger.warning("Scheduler not running, task schedule not updated")
                except Exception as e:
                    app.logger.error(f"Failed to update scheduler for task {task.name}: {e}")
                    # 调度器更新失败不应该影响任务更新的成功状态

                flash(f'备份任务 "{task.name}" 更新成功', 'success')
                return redirect(url_for('backup_tasks'))
            else:
                flash(message, 'error')
                return redirect(url_for('edit_backup_task', task_id=task_id))

        except Exception as e:
            app.logger.error(f"Failed to update backup task: {e}")
            flash('更新备份任务时出错', 'error')
            return redirect(url_for('edit_backup_task', task_id=task_id))

    @app.route('/backup-tasks/<int:task_id>/run', methods=['POST'])
    @login_required
    def run_backup_task(task_id):
        """手动运行备份任务"""
        try:
            from services.backup_service import BackupService
            backup_service = BackupService()

            success, message = backup_service.run_backup_task(task_id, manual=True)

            if success:
                flash(f'备份任务已开始执行: {message}', 'success')
            else:
                flash(f'启动备份任务失败: {message}', 'error')

        except Exception as e:
            app.logger.error(f"Failed to run backup task: {e}")
            flash('运行备份任务时出错', 'error')

        return redirect(url_for('backup_tasks'))

    @app.route('/backup-tasks/<int:task_id>/delete', methods=['POST'])
    @login_required
    def delete_backup_task(task_id):
        """删除备份任务"""
        try:
            from services.backup_service import BackupService
            backup_service = BackupService()

            success, message = backup_service.delete_backup_task(task_id)

            if success:
                # 从调度器中移除任务
                try:
                    from services.scheduler_service import scheduler_service
                    if scheduler_service.scheduler and scheduler_service.scheduler.running:
                        scheduler_service.remove_backup_task(task_id)
                        app.logger.info(f"Removed task {task_id} from scheduler")
                    else:
                        app.logger.warning("Scheduler not running, task not removed from scheduler")
                except Exception as e:
                    app.logger.error(f"Failed to remove task {task_id} from scheduler: {e}")
                    # 调度器移除失败不应该影响任务删除的成功状态

                flash(message, 'success')
            else:
                flash(message, 'error')

        except Exception as e:
            app.logger.error(f"Failed to delete backup task: {e}")
            flash('删除备份任务时出错', 'error')

        return redirect(url_for('backup_tasks'))

    @app.route('/api/browse-directory')
    @login_required
    def browse_directory():
        """浏览本地目录结构"""
        import json
        import stat
        from pathlib import Path

        try:
            # 获取请求的路径，默认为根目录
            path = request.args.get('path', '/')

            # 安全检查：确保路径是绝对路径
            if not os.path.isabs(path):
                path = os.path.abspath(path)

            # 检查路径是否存在
            if not os.path.exists(path):
                return jsonify({'error': '路径不存在'}), 404

            # 检查是否有读取权限
            if not os.access(path, os.R_OK):
                return jsonify({'error': '没有读取权限'}), 403

            directories = []
            files = []

            try:
                # 获取目录内容
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)

                    try:
                        # 获取文件状态
                        stat_info = os.stat(item_path)
                        is_dir = stat.S_ISDIR(stat_info.st_mode)

                        item_info = {
                            'name': item,
                            'path': item_path,
                            'is_directory': is_dir,
                            'size': stat_info.st_size if not is_dir else 0,
                            'modified': stat_info.st_mtime
                        }

                        if is_dir:
                            # 检查是否有子目录
                            try:
                                has_children = any(
                                    os.path.isdir(os.path.join(item_path, child))
                                    for child in os.listdir(item_path)
                                )
                                item_info['has_children'] = has_children
                            except (PermissionError, OSError):
                                item_info['has_children'] = False

                            directories.append(item_info)
                        else:
                            files.append(item_info)

                    except (PermissionError, OSError):
                        # 跳过无法访问的文件/目录
                        continue

            except (PermissionError, OSError) as e:
                return jsonify({'error': f'无法读取目录: {str(e)}'}), 403

            # 按名称排序
            directories.sort(key=lambda x: x['name'].lower())
            files.sort(key=lambda x: x['name'].lower())

            # 获取父目录路径
            parent_path = os.path.dirname(path) if path != '/' else None

            return jsonify({
                'current_path': path,
                'parent_path': parent_path,
                'directories': directories,
                'files': files
            })

        except Exception as e:
            app.logger.error(f"Browse directory error: {e}")
            return jsonify({'error': '服务器内部错误'}), 500

    @app.route('/api/backup-tasks/<int:task_id>/status')
    @login_required
    def get_backup_task_status(task_id):
        """获取备份任务状态"""
        try:
            task = BackupTask.query.get(task_id)
            if not task:
                return jsonify({'error': '任务不存在'}), 404

            latest_log = task.latest_log
            status_info = {
                'task_id': task.id,
                'name': task.name,
                'is_active': task.is_active,
                'last_run_at': task.last_run_at.isoformat() if task.last_run_at else None,
                'next_run_at': task.next_run_at.isoformat() if task.next_run_at else None,
                'latest_log': None
            }

            if latest_log:
                status_info['latest_log'] = {
                    'id': latest_log.id,
                    'status': latest_log.status,
                    'start_time': latest_log.start_time.isoformat(),
                    'end_time': latest_log.end_time.isoformat() if latest_log.end_time else None,
                    'error_message': latest_log.error_message
                }

            return jsonify(status_info)

        except Exception as e:
            app.logger.error(f"Failed to get task status: {e}")
            return jsonify({'error': '获取任务状态失败'}), 500

    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return render_template('error.html', 
                             error_code=404, 
                             error_message='页面未找到'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('error.html',
                             error_code=500,
                             error_message='服务器内部错误'), 500

    @app.route('/scheduler-status')
    @login_required
    def scheduler_status():
        """调度器状态检查页面"""
        try:
            from services.scheduler_service import scheduler_service, _app_instance
            from datetime import datetime

            status_info = {
                'current_time': datetime.now(),
                'scheduler_exists': scheduler_service.scheduler is not None,
                'scheduler_running': False,
                'app_instance_set': _app_instance is not None,
                'jobs': [],
                'active_tasks': [],
                'error': None
            }

            if scheduler_service.scheduler:
                status_info['scheduler_running'] = scheduler_service.scheduler.running

                # 获取作业信息
                jobs = scheduler_service.scheduler.get_jobs()
                for job in jobs:
                    status_info['jobs'].append({
                        'id': job.id,
                        'name': job.name,
                        'next_run_time': job.next_run_time,
                        'trigger': str(job.trigger),
                        'func_name': job.func.__name__ if hasattr(job.func, '__name__') else str(job.func)
                    })

            # 获取活跃任务
            active_tasks = BackupTask.query.filter_by(is_active=True).all()
            for task in active_tasks:
                status_info['active_tasks'].append({
                    'id': task.id,
                    'name': task.name,
                    'cron_expression': task.cron_expression,
                    'next_run_at': task.next_run_at,
                    'has_scheduler_job': scheduler_service.scheduler and
                                       scheduler_service.scheduler.get_job(f"backup_task_{task.id}") is not None
                })

            return jsonify(status_info)

        except Exception as e:
            return jsonify({
                'error': str(e),
                'current_time': datetime.now()
            }), 500

    @app.route('/scheduler')
    @login_required
    def scheduler_page():
        """调度器状态页面"""
        return render_template('scheduler_status.html')

    @app.route('/backup-logs')
    @login_required
    def backup_logs():
        """备份日志页面"""
        try:
            # 获取查询参数
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            task_id = request.args.get('task_id', type=int)
            status = request.args.get('status')

            # 构建查询
            query = BackupLog.query

            # 按任务筛选
            if task_id:
                query = query.filter_by(task_id=task_id)

            # 按状态筛选
            if status:
                query = query.filter_by(status=status)

            # 按时间倒序排列并分页
            logs = query.order_by(BackupLog.start_time.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )

            # 获取所有任务用于筛选
            tasks = BackupTask.query.all()

            return render_template('backup_logs.html',
                                 logs=logs,
                                 tasks=tasks,
                                 current_task_id=task_id,
                                 current_status=status)

        except Exception as e:
            app.logger.error(f"Failed to load backup logs: {e}")
            flash('加载备份日志时出错', 'error')
            return redirect(url_for('dashboard'))

    @app.route('/backup-logs/<int:log_id>')
    @login_required
    def backup_log_detail(log_id):
        """备份日志详情页面"""
        try:
            log = BackupLog.query.get(log_id)
            if not log:
                flash('备份日志不存在', 'error')
                return redirect(url_for('backup_logs'))

            return render_template('backup_log_detail.html', log=log)

        except Exception as e:
            app.logger.error(f"Failed to load backup log detail: {e}")
            flash('加载日志详情时出错', 'error')
            return redirect(url_for('backup_logs'))

    @app.route('/api/backup-logs/<int:log_id>')
    @login_required
    def get_backup_log_api(log_id):
        """获取备份日志API"""
        try:
            log = BackupLog.query.get(log_id)
            if not log:
                return jsonify({'error': '日志不存在'}), 404

            log_data = {
                'id': log.id,
                'task_id': log.task_id,
                'task_name': log.task.name if log.task else '未知任务',
                'status': log.status,
                'start_time': log.start_time.isoformat() if log.start_time else None,
                'end_time': log.end_time.isoformat() if log.end_time else None,
                'duration': str(log.duration) if log.duration else None,
                'original_size': log.original_size,
                'compressed_size': log.compressed_size,
                'final_size': log.final_size,
                'compression_ratio': log.compression_ratio,
                'error_message': log.error_message,
                'log_details': log.log_details
            }

            return jsonify(log_data)

        except Exception as e:
            app.logger.error(f"Failed to get backup log: {e}")
            return jsonify({'error': '获取日志失败'}), 500

    @app.route('/system-settings')
    @login_required
    def system_settings():
        """系统设置页面"""
        try:
            import sys
            import platform

            # 获取系统统计信息
            stats = {
                'total_users': User.query.count(),
                'total_storage_configs': StorageConfig.query.count(),
                'active_storage_configs': StorageConfig.query.filter_by(is_active=True).count(),
                'total_backup_tasks': BackupTask.query.count(),
                'active_backup_tasks': BackupTask.query.filter_by(is_active=True).count(),
                'total_backup_logs': BackupLog.query.count(),
                'successful_backups': BackupLog.query.filter_by(status='success').count(),
                'failed_backups': BackupLog.query.filter_by(status='failed').count(),
                'running_backups': BackupLog.query.filter_by(status='running').count()
            }

            # 获取系统信息
            system_info = {
                'version': '1.0.0',
                'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                'platform': platform.platform(),
                'database_path': app.config['SQLALCHEMY_DATABASE_URI'],
                'rclone_config_dir': app.config.get('RCLONE_CONFIG_DIR', '~/.config/rclone'),
                'backup_temp_dir': app.config.get('BACKUP_TEMP_DIR', 'data/temp'),
                'log_file': app.config.get('LOG_FILE', 'logs/app.log'),
                'debug_mode': app.config.get('DEBUG', False)
            }

            # 获取当前用户信息
            current_user = auth_service.get_user_by_id(session['user_id'])

            return render_template('system_settings.html',
                                 stats=stats,
                                 system_info=system_info,
                                 current_user=current_user)

        except Exception as e:
            app.logger.error(f"Failed to load system settings: {e}")
            flash('加载系统设置时出错', 'error')
            return redirect(url_for('dashboard'))

    @app.route('/system-settings/change-password', methods=['POST'])
    @login_required
    def change_password():
        """修改密码"""
        try:
            old_password = request.form.get('old_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not old_password or not new_password or not confirm_password:
                flash('请填写所有密码字段', 'error')
                return redirect(url_for('system_settings'))

            if new_password != confirm_password:
                flash('新密码和确认密码不匹配', 'error')
                return redirect(url_for('system_settings'))

            if len(new_password) < 6:
                flash('新密码长度至少为6位', 'error')
                return redirect(url_for('system_settings'))

            # 使用AuthService修改密码
            success = auth_service.change_password(
                session['user_id'],
                old_password,
                new_password
            )

            if success:
                flash('密码修改成功', 'success')
                app.logger.info(f"Password changed for user {session['username']}")
            else:
                flash('原密码错误', 'error')

        except Exception as e:
            app.logger.error(f"Failed to change password: {e}")
            flash('修改密码时出错', 'error')

        return redirect(url_for('system_settings'))

    @app.route('/system-settings/export-data')
    @login_required
    def export_system_data():
        """导出系统数据（显示加密选项页面）"""
        return render_template('export_data.html')

    @app.route('/system-settings/export-data/download', methods=['POST'])
    @login_required
    def download_export_data():
        """下载导出的系统数据"""
        try:
            import json
            from datetime import datetime
            from flask import make_response
            from services.encryption_service import EncryptionService

            # 获取加密密码
            encryption_password = request.form.get('encryption_password', '')
            if not encryption_password:
                flash('请输入加密密码', 'error')
                return redirect(url_for('export_system_data'))

            if len(encryption_password) < 8:
                flash('加密密码长度至少为8位', 'error')
                return redirect(url_for('export_system_data'))

            encryption_service = EncryptionService()

            # 收集所有数据
            export_data = {
                'export_info': {
                    'timestamp': datetime.now().isoformat(),
                    'exported_by': session['username'],
                    'version': '2.0',  # 版本2.0支持加密
                    'encrypted': True,
                    'encryption_note': '此文件包含加密的敏感数据，导入时需要提供正确的解密密码'
                },
                'users': [],
                'storage_configs': [],
                'backup_tasks': [],
                'backup_logs': []
            }

            # 导出用户数据（包含密码哈希）
            users = User.query.all()
            for user in users:
                export_data['users'].append({
                    'id': user.id,
                    'username': user.username,
                    'password_hash': user.password_hash,  # 包含密码哈希
                    'created_at': user.created_at.isoformat() if user.created_at else None
                })

            # 导出存储配置（包含完整的rclone配置和敏感数据）
            storage_configs = StorageConfig.query.all()
            for config in storage_configs:
                config_data = {
                    'id': config.id,
                    'name': config.name,
                    'storage_type': config.storage_type,
                    'rclone_config_name': config.rclone_config_name,
                    'description': config.description,
                    'is_active': config.is_active,
                    'created_at': config.created_at.isoformat() if config.created_at else None,
                    'updated_at': config.updated_at.isoformat() if config.updated_at else None,
                    'rclone_config': None,
                    'config_history': []
                }

                # 获取rclone配置内容
                try:
                    from services.rclone_service import RcloneService
                    rclone_service = RcloneService()
                    rclone_config = rclone_service.get_config_section(config.rclone_config_name)
                    if rclone_config:
                        config_data['rclone_config'] = rclone_config  # 保存完整配置，稍后统一加密
                except Exception as e:
                    app.logger.error(f"Failed to get rclone config for {config.name}: {e}")

                # 导出配置历史
                for history in config.config_history:
                    history_data = {
                        'version': history.version,
                        'config_data': history.config_data,
                        'rclone_config_content': history.rclone_config_content,
                        'change_reason': history.change_reason,
                        'created_at': history.created_at.isoformat() if history.created_at else None,
                        'created_by': history.created_by
                    }
                    config_data['config_history'].append(history_data)

                export_data['storage_configs'].append(config_data)

            # 导出备份任务
            backup_tasks = BackupTask.query.all()
            for task in backup_tasks:
                export_data['backup_tasks'].append({
                    'id': task.id,
                    'name': task.name,
                    'description': task.description,
                    'source_path': task.source_path,
                    'remote_path': task.remote_path,
                    'storage_config_id': task.storage_config_id,
                    'cron_expression': task.cron_expression,
                    'compression_enabled': task.compression_enabled,
                    'encryption_enabled': task.encryption_enabled,
                    'retention_count': task.retention_count,
                    'is_active': task.is_active,
                    'last_run_at': task.last_run_at.isoformat() if task.last_run_at else None,
                    'next_run_at': task.next_run_at.isoformat() if task.next_run_at else None,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'updated_at': task.updated_at.isoformat() if task.updated_at else None
                })

            # 导出备份日志（最近1000条）
            backup_logs = BackupLog.query.order_by(BackupLog.start_time.desc()).limit(1000).all()
            for log in backup_logs:
                export_data['backup_logs'].append({
                    'id': log.id,
                    'task_id': log.task_id,
                    'status': log.status,
                    'start_time': log.start_time.isoformat() if log.start_time else None,
                    'end_time': log.end_time.isoformat() if log.end_time else None,
                    'original_size': log.original_size,
                    'compressed_size': log.compressed_size,
                    'final_size': log.final_size,
                    'error_message': log.error_message,
                    'log_details': log.log_details
                })

            # 对整个数据结构进行加密
            success, encrypted_data_str = encryption_service.encrypt_data(export_data, encryption_password)
            if not success:
                flash(f'数据加密失败: {encrypted_data_str}', 'error')
                return redirect(url_for('export_system_data'))

            # 创建最终的导出结构
            final_export = {
                'export_info': {
                    'timestamp': datetime.now().isoformat(),
                    'exported_by': session['username'],
                    'version': '2.0',
                    'encrypted': True,
                    'encryption_note': '此文件包含完全加密的系统数据，导入时需要提供正确的解密密码'
                },
                'encrypted_data': encrypted_data_str
            }

            # 生成JSON响应
            json_data = json.dumps(final_export, indent=2, ensure_ascii=False)

            # 创建响应
            response = make_response(json_data)
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename=rclone_backup_system_encrypted_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

            app.logger.info(f"Fully encrypted system data exported by user {session['username']}")
            flash('系统数据导出成功，请妥善保管加密密码', 'success')
            return response

        except Exception as e:
            app.logger.error(f"Failed to export system data: {e}")
            flash(f'导出系统数据时出错: {str(e)}', 'error')
            return redirect(url_for('export_system_data'))

    @app.route('/system-settings/import-data')
    @login_required
    def import_system_data():
        """导入系统数据页面"""
        return render_template('import_data.html')

    @app.route('/system-settings/import-data/upload', methods=['POST'])
    @login_required
    def upload_import_data():
        """上传并导入系统数据"""
        try:
            import json
            from services.encryption_service import EncryptionService
            from services.rclone_service import RcloneService

            # 检查文件上传
            if 'import_file' not in request.files:
                flash('请选择要导入的文件', 'error')
                return redirect(url_for('import_system_data'))

            file = request.files['import_file']
            if file.filename == '':
                flash('请选择要导入的文件', 'error')
                return redirect(url_for('import_system_data'))

            # 获取解密密码和覆盖选项
            decryption_password = request.form.get('decryption_password', '')
            if not decryption_password:
                flash('请输入解密密码', 'error')
                return redirect(url_for('import_system_data'))

            # 获取覆盖选项（默认为True以确保完整覆盖）
            force_overwrite = request.form.get('force_overwrite', 'on') == 'on'

            # 读取文件内容
            try:
                file_content = file.read().decode('utf-8')
                import_data = json.loads(file_content)
            except Exception as e:
                flash(f'文件格式错误: {str(e)}', 'error')
                return redirect(url_for('import_system_data'))

            # 检查文件版本和加密状态
            export_info = import_data.get('export_info', {})
            if not export_info.get('encrypted'):
                flash('此文件不包含加密数据，无法导入', 'error')
                return redirect(url_for('import_system_data'))

            # 获取加密的数据
            encrypted_data_str = import_data.get('encrypted_data')
            if not encrypted_data_str:
                flash('文件格式错误：缺少加密数据', 'error')
                return redirect(url_for('import_system_data'))

            encryption_service = EncryptionService()
            rclone_service = RcloneService()

            # 解密完整数据
            success, decrypted_data, error = encryption_service.decrypt_data(encrypted_data_str, decryption_password)
            if not success:
                flash(f'解密失败：{error}。请检查密码是否正确。', 'error')
                return redirect(url_for('import_system_data'))

            # 统计导入结果
            import_stats = {
                'users': {'success': 0, 'failed': 0, 'errors': []},
                'storage_configs': {'success': 0, 'failed': 0, 'errors': []},
                'backup_tasks': {'success': 0, 'failed': 0, 'errors': []},
                'total_processed': 0
            }

            # 导入用户数据
            for user_data in decrypted_data.get('users', []):
                try:
                    import_stats['total_processed'] += 1

                    # 检查用户名是否已存在
                    existing_user = User.query.filter_by(username=user_data['username']).first()
                    if existing_user:
                        # 更新现有用户的密码哈希（完全恢复）
                        existing_user.password_hash = user_data['password_hash']
                        import_stats['users']['success'] += 1
                        app.logger.info(f"Updated existing user: {user_data['username']}")
                    else:
                        # 创建新用户
                        new_user = User(
                            username=user_data['username'],
                            password_hash=user_data['password_hash']
                        )
                        if user_data.get('created_at'):
                            try:
                                from datetime import datetime
                                new_user.created_at = datetime.fromisoformat(user_data['created_at'])
                            except:
                                pass  # 使用默认时间

                        db.session.add(new_user)
                        import_stats['users']['success'] += 1
                        app.logger.info(f"Created new user: {user_data['username']}")

                except Exception as e:
                    import_stats['users']['failed'] += 1
                    import_stats['users']['errors'].append(f"导入用户 '{user_data.get('username', 'Unknown')}' 时出错: {str(e)}")
                    app.logger.error(f"Failed to import user: {e}")

            # 导入存储配置
            for config_data in decrypted_data.get('storage_configs', []):
                try:
                    import_stats['total_processed'] += 1

                    # 检查配置名称是否已存在
                    existing_config = StorageConfig.query.filter_by(name=config_data['name']).first()
                    if existing_config:
                        if force_overwrite:
                            # 完整覆盖：删除现有配置及其相关数据
                            try:
                                # 删除相关的备份任务
                                related_tasks = BackupTask.query.filter_by(storage_config_id=existing_config.id).all()
                                for task in related_tasks:
                                    # 删除任务的备份日志
                                    BackupLog.query.filter_by(task_id=task.id).delete()
                                    db.session.delete(task)

                                # 删除配置历史
                                StorageConfigHistory.query.filter_by(storage_config_id=existing_config.id).delete()

                                # 删除rclone配置文件
                                if existing_config.rclone_config_name:
                                    rclone_service.delete_config(existing_config.rclone_config_name)

                                # 删除存储配置记录
                                db.session.delete(existing_config)
                                db.session.flush()  # 确保删除操作完成

                                app.logger.info(f"Deleted existing storage config for overwrite: {config_data['name']}")
                            except Exception as e:
                                app.logger.error(f"Failed to delete existing config {config_data['name']}: {e}")
                                import_stats['storage_configs']['failed'] += 1
                                import_stats['storage_configs']['errors'].append(f"删除现有存储配置 '{config_data['name']}' 时出错: {str(e)}")
                                continue
                        else:
                            import_stats['storage_configs']['failed'] += 1
                            import_stats['storage_configs']['errors'].append(f"存储配置 '{config_data['name']}' 已存在")
                            continue

                    # 处理rclone配置（数据已经解密）
                    rclone_config = config_data.get('rclone_config')
                    if rclone_config:
                        # 创建新的rclone配置
                        from datetime import datetime
                        new_rclone_name = f"backup_{config_data['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                        # 生成rclone配置内容并创建
                        if not rclone_service.create_config(new_rclone_name, config_data['storage_type'], rclone_config):
                            import_stats['storage_configs']['failed'] += 1
                            import_stats['storage_configs']['errors'].append(f"创建rclone配置 '{config_data['name']}' 失败")
                            continue

                        # 创建数据库记录
                        new_config = StorageConfig(
                            name=config_data['name'],
                            storage_type=config_data['storage_type'],
                            rclone_config_name=new_rclone_name,
                            description=config_data.get('description', ''),
                            is_active=config_data.get('is_active', True)
                        )

                        db.session.add(new_config)
                        db.session.flush()  # 获取ID

                        # 导入配置历史（数据已经解密）
                        for history_data in config_data.get('config_history', []):
                            try:
                                # 创建历史记录
                                from services.config_service import ConfigService
                                config_service = ConfigService()
                                config_service._save_config_history(
                                    new_config.id,
                                    json.loads(history_data['config_data']) if history_data.get('config_data') else {},
                                    history_data.get('rclone_config_content', ''),
                                    history_data.get('change_reason', '导入的历史配置'),
                                    history_data.get('created_by', session['username']),
                                    history_data.get('version', 1)
                                )
                            except Exception as e:
                                app.logger.warning(f"Failed to import config history: {e}")

                        import_stats['storage_configs']['success'] += 1

                except Exception as e:
                    import_stats['storage_configs']['failed'] += 1
                    import_stats['storage_configs']['errors'].append(f"导入存储配置 '{config_data.get('name', 'Unknown')}' 时出错: {str(e)}")
                    app.logger.error(f"Failed to import storage config: {e}")

            # 导入备份任务
            for task_data in decrypted_data.get('backup_tasks', []):
                try:
                    import_stats['total_processed'] += 1

                    # 检查任务名称是否已存在
                    existing_task = BackupTask.query.filter_by(name=task_data['name']).first()
                    if existing_task:
                        if force_overwrite:
                            # 完整覆盖：删除现有任务及其相关数据
                            try:
                                # 删除任务的备份日志
                                BackupLog.query.filter_by(task_id=existing_task.id).delete()

                                # 删除备份任务记录
                                db.session.delete(existing_task)
                                db.session.flush()  # 确保删除操作完成

                                app.logger.info(f"Deleted existing backup task for overwrite: {task_data['name']}")
                            except Exception as e:
                                app.logger.error(f"Failed to delete existing task {task_data['name']}: {e}")
                                import_stats['backup_tasks']['failed'] += 1
                                import_stats['backup_tasks']['errors'].append(f"删除现有备份任务 '{task_data['name']}' 时出错: {str(e)}")
                                continue
                        else:
                            import_stats['backup_tasks']['failed'] += 1
                            import_stats['backup_tasks']['errors'].append(f"备份任务 '{task_data['name']}' 已存在")
                            continue

                    # 查找对应的存储配置
                    storage_config = None
                    if task_data.get('storage_config_id'):
                        # 尝试通过原ID查找，如果找不到则通过名称查找
                        storage_config = StorageConfig.query.get(task_data['storage_config_id'])
                        if not storage_config:
                            # 通过名称查找（可能是新导入的配置）
                            for config in decrypted_data.get('storage_configs', []):
                                if config['id'] == task_data['storage_config_id']:
                                    storage_config = StorageConfig.query.filter_by(name=config['name']).first()
                                    break

                    if not storage_config:
                        import_stats['backup_tasks']['failed'] += 1
                        import_stats['backup_tasks']['errors'].append(f"备份任务 '{task_data['name']}' 的存储配置不存在")
                        continue

                    # 创建备份任务
                    new_task = BackupTask(
                        name=task_data['name'],
                        description=task_data.get('description', ''),
                        source_path=task_data['source_path'],
                        remote_path=task_data['remote_path'],
                        storage_config_id=storage_config.id,
                        cron_expression=task_data.get('cron_expression'),
                        compression_enabled=task_data.get('compression_enabled', False),
                        encryption_enabled=task_data.get('encryption_enabled', False),
                        retention_count=task_data.get('retention_count', 7),
                        is_active=task_data.get('is_active', True)
                    )

                    # 设置时间字段
                    if task_data.get('last_run_at'):
                        try:
                            from datetime import datetime
                            new_task.last_run_at = datetime.fromisoformat(task_data['last_run_at'])
                        except:
                            pass

                    if task_data.get('next_run_at'):
                        try:
                            from datetime import datetime
                            new_task.next_run_at = datetime.fromisoformat(task_data['next_run_at'])
                        except:
                            pass

                    if task_data.get('created_at'):
                        try:
                            from datetime import datetime
                            new_task.created_at = datetime.fromisoformat(task_data['created_at'])
                        except:
                            pass

                    db.session.add(new_task)
                    import_stats['backup_tasks']['success'] += 1

                except Exception as e:
                    import_stats['backup_tasks']['failed'] += 1
                    import_stats['backup_tasks']['errors'].append(f"导入备份任务 '{task_data.get('name', 'Unknown')}' 时出错: {str(e)}")
                    app.logger.error(f"Failed to import backup task: {e}")

            # 提交数据库更改
            db.session.commit()

            # 生成导入报告
            total_success = import_stats['users']['success'] + import_stats['storage_configs']['success'] + import_stats['backup_tasks']['success']
            total_failed = import_stats['users']['failed'] + import_stats['storage_configs']['failed'] + import_stats['backup_tasks']['failed']

            if total_success > 0:
                overwrite_mode = "完整覆盖模式" if force_overwrite else "跳过重名模式"
                flash(f'导入完成（{overwrite_mode}）：成功 {total_success} 个项目，失败 {total_failed} 个项目', 'success')
                flash(f'详细统计 - 用户: {import_stats["users"]["success"]}成功/{import_stats["users"]["failed"]}失败, '
                      f'存储配置: {import_stats["storage_configs"]["success"]}成功/{import_stats["storage_configs"]["failed"]}失败, '
                      f'备份任务: {import_stats["backup_tasks"]["success"]}成功/{import_stats["backup_tasks"]["failed"]}失败', 'info')
                if force_overwrite:
                    flash('已启用完整覆盖模式：所有重名的配置和任务已被完全替换，包括相关的历史记录和日志', 'warning')
            else:
                flash(f'导入失败：{total_failed} 个项目导入失败', 'error')

            # 记录错误详情
            for category in ['users', 'storage_configs', 'backup_tasks']:
                for error in import_stats[category]['errors']:
                    app.logger.warning(f"Import error ({category}): {error}")

            app.logger.info(f"System data imported by user {session['username']}: {total_success} success, {total_failed} failed")
            return redirect(url_for('system_settings'))

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Failed to import system data: {e}")
            flash(f'导入系统数据时出错: {str(e)}', 'error')
            return redirect(url_for('import_system_data'))

    return app

def check_database_structure():
    """检查数据库结构是否符合当前模型"""
    try:
        # 检查必需的表是否存在
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()

        required_tables = ['users', 'storage_configs', 'storage_config_history', 'backup_tasks', 'backup_logs', 'system_configs']
        missing_tables = [table for table in required_tables if table not in existing_tables]

        if missing_tables:
            print(f"缺少表: {missing_tables}")
            return False

        # 检查storage_configs表结构
        if 'storage_configs' in existing_tables:
            columns = [col['name'] for col in inspector.get_columns('storage_configs')]
            required_columns = ['id', 'name', 'storage_type', 'rclone_config_name', 'description', 'is_active', 'created_at', 'updated_at']
            missing_columns = [col for col in required_columns if col not in columns]

            if missing_columns:
                print(f"storage_configs表缺少字段: {missing_columns}")
                return False

        # 检查storage_config_history表结构
        if 'storage_config_history' in existing_tables:
            columns = [col['name'] for col in inspector.get_columns('storage_config_history')]
            required_columns = ['id', 'storage_config_id', 'version', 'config_data', 'rclone_config_content', 'change_reason', 'created_at', 'created_by']
            missing_columns = [col for col in required_columns if col not in columns]

            if missing_columns:
                print(f"storage_config_history表缺少字段: {missing_columns}")
                return False

        return True

    except Exception as e:
        print(f"检查数据库结构时出错: {e}")
        return False

def backup_and_recreate_database():
    """备份并重新创建数据库"""
    try:
        import shutil
        from datetime import datetime

        db_path = 'database.db'

        # 备份现有数据库
        if os.path.exists(db_path):
            backup_path = f'database_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
            shutil.copy2(db_path, backup_path)
            print(f"数据库已备份到: {backup_path}")

            # 删除旧数据库
            os.remove(db_path)
            print("已删除旧数据库文件")

        # 重新创建所有表
        db.create_all()
        print("数据库表结构已重新创建")

        return True

    except Exception as e:
        print(f"重新创建数据库时出错: {e}")
        return False

def init_database(app):
    """初始化数据库"""
    with app.app_context():
        try:
            print("开始数据库初始化...")

            # 强制创建所有表
            print("调用 db.create_all()...")
            db.create_all()
            print("db.create_all() 完成")

            # 验证表是否创建成功
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            print(f"当前数据库中的表: {existing_tables}")

            # 创建默认管理员用户
            try:
                if not User.query.filter_by(username='admin').first():
                    admin_user = User(username='admin')
                    admin_user.set_password('admin123')
                    db.session.add(admin_user)
                    db.session.commit()
                    print("已创建默认管理员用户: admin/admin123")
                else:
                    print("默认管理员用户已存在")
            except Exception as e:
                print(f"创建默认用户时出错: {e}")

        except Exception as e:
            print(f"数据库初始化失败: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == '__main__':
    app = create_app(os.environ.get('FLASK_ENV', 'development'))
    
    # 初始化数据库
    init_database(app)
    
    # 启动应用
    app.run(debug=True, host='0.0.0.0', port=5000)
