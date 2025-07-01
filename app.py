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
