import os
from datetime import timedelta

class Config:
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'rclone-backup-secret-key-2024'

    # 数据库配置 - 使用相对路径
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 会话配置
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # rclone配置 - 使用相对路径
    RCLONE_CONFIG_DIR = 'data/rclone_configs'
    RCLONE_BINARY = os.environ.get('RCLONE_BINARY') or 'rclone'

    # 备份配置 - 使用相对路径
    BACKUP_TEMP_DIR = 'data/temp'
    MAX_BACKUP_SIZE = 10 * 1024 * 1024 * 1024  # 10GB

    # 日志配置 - 使用相对路径
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = 'logs/app.log'
    
    # 调度器配置
    SCHEDULER_API_ENABLED = True
    
    @staticmethod
    def init_app(app):
        # 创建必要的目录（使用相对路径）
        directories = [
            'data',
            'data/rclone_configs',
            'data/temp',
            'logs'
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)

        print("✓ 目录结构创建完成")

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
