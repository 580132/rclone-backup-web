from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """检查密码"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class StorageConfig(db.Model):
    """存储配置模型 - 现在主要作为索引，实际配置从rclone文件读取"""
    __tablename__ = 'storage_configs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    storage_type = db.Column(db.String(50), nullable=False)  # s3, google_drive, etc.
    rclone_config_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)  # 配置描述
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联的备份任务
    backup_tasks = db.relationship('BackupTask', backref='storage_config', lazy=True)

    # 关联的配置历史版本
    config_history = db.relationship('StorageConfigHistory', backref='storage_config',
                                   lazy=True, order_by='StorageConfigHistory.version.desc()')

    @property
    def latest_config_version(self):
        """获取最新的配置版本"""
        return self.config_history[0] if self.config_history else None

    def __repr__(self):
        return f'<StorageConfig {self.name}>'


class StorageConfigHistory(db.Model):
    """存储配置历史版本模型 - 存储配置的历史版本"""
    __tablename__ = 'storage_config_history'

    id = db.Column(db.Integer, primary_key=True)
    storage_config_id = db.Column(db.Integer, db.ForeignKey('storage_configs.id'), nullable=False)
    version = db.Column(db.Integer, nullable=False)  # 版本号
    config_data = db.Column(db.Text, nullable=False)  # JSON格式的配置数据
    rclone_config_content = db.Column(db.Text)  # rclone配置文件内容
    change_reason = db.Column(db.String(255))  # 变更原因
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100))  # 创建者

    # 复合唯一索引：同一配置的版本号不能重复
    __table_args__ = (db.UniqueConstraint('storage_config_id', 'version', name='_storage_config_version_uc'),)

    def __repr__(self):
        return f'<StorageConfigHistory {self.storage_config_id} v{self.version}>'


class BackupTask(db.Model):
    """备份任务模型"""
    __tablename__ = 'backup_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    source_path = db.Column(db.String(500), nullable=False)
    storage_config_id = db.Column(db.Integer, db.ForeignKey('storage_configs.id'), nullable=False)
    remote_path = db.Column(db.String(500), nullable=False)
    cron_expression = db.Column(db.String(100))  # cron表达式
    
    # 压缩和加密设置
    compression_enabled = db.Column(db.Boolean, default=True)
    compression_type = db.Column(db.String(20), default='tar.gz')  # tar.gz, zip
    encryption_enabled = db.Column(db.Boolean, default=False)
    encryption_password = db.Column(db.String(255))  # 加密密码（已加密存储）
    
    # 保留策略
    retention_count = db.Column(db.Integer, default=10)  # 保留备份份数
    
    # 状态信息
    is_active = db.Column(db.Boolean, default=True)
    last_run_at = db.Column(db.DateTime)
    next_run_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联的备份日志
    backup_logs = db.relationship('BackupLog', backref='task', lazy=True, order_by='BackupLog.start_time.desc()')
    
    @property
    def latest_log(self):
        """获取最新的备份日志"""
        return self.backup_logs[0] if self.backup_logs else None
    
    @property
    def success_rate(self):
        """计算成功率"""
        if not self.backup_logs:
            return 0
        
        total = len(self.backup_logs)
        success = len([log for log in self.backup_logs if log.status == 'success'])
        return round((success / total) * 100, 1)
    
    def __repr__(self):
        return f'<BackupTask {self.name}>'

class BackupLog(db.Model):
    """备份日志模型"""
    __tablename__ = 'backup_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('backup_tasks.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # running, success, failed
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    
    # 文件信息
    original_size = db.Column(db.BigInteger)  # 原始文件大小
    compressed_size = db.Column(db.BigInteger)  # 压缩后大小
    final_size = db.Column(db.BigInteger)  # 最终上传大小（加密后）
    
    # 错误信息
    error_message = db.Column(db.Text)
    log_details = db.Column(db.Text)  # 详细日志
    
    @property
    def duration(self):
        """计算执行时长"""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def compression_ratio(self):
        """计算压缩比"""
        if self.original_size and self.compressed_size and self.original_size > 0:
            return round((1 - self.compressed_size / self.original_size) * 100, 1)
        return 0
    
    def __repr__(self):
        return f'<BackupLog {self.task_id} - {self.status}>'

class SystemConfig(db.Model):
    """系统配置模型"""
    __tablename__ = 'system_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemConfig {self.key}>'
