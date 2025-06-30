from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import os
import logging
from datetime import datetime

# 导入配置和模型
from config import config, Config
from models import db, User, StorageConfig, BackupTask, BackupLog

# 导入服务
from services.auth_service import AuthService
from services.rclone_service import RcloneService

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
            name = request.form.get('name', '').strip()
            storage_type = request.form.get('storage_type', '').strip()
            
            if not name or not storage_type:
                flash('请填写配置名称和存储类型', 'error')
                return redirect(url_for('storage_configs'))
            
            # 检查名称是否已存在
            if StorageConfig.query.filter_by(name=name).first():
                flash('配置名称已存在', 'error')
                return redirect(url_for('storage_configs'))
            
            # 收集配置数据
            config_data = {}
            if storage_type in ['s3', 'alibaba_oss', 'cloudflare_r2']:
                config_data = {
                    'access_key': request.form.get('access_key', '').strip(),
                    'secret_key': request.form.get('secret_key', '').strip(),
                    'region': request.form.get('region', '').strip(),
                    'endpoint': request.form.get('endpoint', '').strip(),
                    'bucket': request.form.get('bucket', '').strip()
                }

                # 设置默认值
                if storage_type == 's3' and not config_data['region']:
                    config_data['region'] = 'us-east-1'
                elif storage_type == 'alibaba_oss' and not config_data['region']:
                    config_data['region'] = 'oss-cn-hangzhou'

            elif storage_type == 'google_drive':
                config_data = {
                    'client_id': request.form.get('client_id', '').strip(),
                    'client_secret': request.form.get('client_secret', '').strip(),
                    'token': request.form.get('token', '').strip(),
                    'root_folder_id': request.form.get('root_folder_id', '').strip()
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
            
            # 创建rclone配置
            rclone_config_name = f"backup_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if not rclone_service.create_config(rclone_config_name, storage_type, config_data):
                flash('创建rclone配置失败', 'error')
                return redirect(url_for('storage_configs'))
            
            # 测试连接
            success, message = rclone_service.test_connection(rclone_config_name)
            if not success:
                # 删除创建的配置
                rclone_service.delete_config(rclone_config_name)
                flash(f'连接测试失败: {message}', 'error')
                return redirect(url_for('storage_configs'))
            
            # 保存到数据库
            storage_config = StorageConfig(
                name=name,
                storage_type=storage_type,
                rclone_config_name=rclone_config_name,
                config_data=str(config_data)  # 简单存储，实际应该加密
            )
            
            db.session.add(storage_config)
            db.session.commit()
            
            app.logger.info(f"Created storage config: {name}")
            flash('存储配置创建成功', 'success')
            
        except Exception as e:
            app.logger.error(f"Failed to create storage config: {e}")
            flash('创建存储配置时出错', 'error')
            db.session.rollback()
        
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
    
    @app.route('/storage-configs/<int:config_id>/delete', methods=['POST'])
    @login_required
    def delete_storage_config(config_id):
        """删除存储配置"""
        try:
            config = StorageConfig.query.get_or_404(config_id)
            
            # 检查是否有关联的备份任务
            if config.backup_tasks:
                flash('无法删除：存在关联的备份任务', 'error')
                return redirect(url_for('storage_configs'))
            
            # 删除rclone配置文件
            rclone_service.delete_config(config.rclone_config_name)
            
            # 删除数据库记录
            db.session.delete(config)
            db.session.commit()
            
            app.logger.info(f"Deleted storage config: {config.name}")
            flash('存储配置已删除', 'success')
            
        except Exception as e:
            app.logger.error(f"Failed to delete storage config: {e}")
            flash('删除存储配置时出错', 'error')
            db.session.rollback()
        
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

def init_database(app):
    """初始化数据库"""
    with app.app_context():
        db.create_all()
        
        # 创建默认管理员用户
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin')
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("Created default admin user: admin/admin123")

if __name__ == '__main__':
    app = create_app(os.environ.get('FLASK_ENV', 'development'))
    
    # 初始化数据库
    init_database(app)
    
    # 启动应用
    app.run(debug=True, host='0.0.0.0', port=5000)
