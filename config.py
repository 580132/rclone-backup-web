import os
from datetime import timedelta

class Config:
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'rclone-backup-secret-key-2024'

    # 数据库配置 - 根据环境调整路径
    if os.environ.get('DATABASE_URL'):
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    else:
        # 确保数据库文件在data目录中
        db_path = os.path.join('data', 'database.db')
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 会话配置
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    # Docker环境检测
    DOCKER_ENV = os.environ.get('DOCKER_ENV', 'false').lower() == 'true'

    # 文件系统根目录前缀 - Docker环境中宿主机根目录挂载到/host
    if DOCKER_ENV:
        HOST_ROOT_PREFIX = '/host'
    else:
        HOST_ROOT_PREFIX = ''

    # rclone配置 - 根据环境选择配置目录
    if DOCKER_ENV:
        RCLONE_CONFIG_DIR = os.environ.get('RCLONE_CONFIG_DIR') or '/app/data/rclone_configs'
        RCLONE_BINARY = 'docker'  # 在Docker环境中使用docker命令调用rclone容器
        RCLONE_CONTAINER_NAME = os.environ.get('RCLONE_CONTAINER_NAME') or 'rclone-service'
    else:
        RCLONE_CONFIG_DIR = os.environ.get('RCLONE_CONFIG_DIR') or os.path.expanduser('~/.config/rclone')
        RCLONE_BINARY = os.environ.get('RCLONE_BINARY') or 'rclone'
        RCLONE_CONTAINER_NAME = None

    # 备份配置 - 使用相对路径
    BACKUP_TEMP_DIR = 'data/temp'
    MAX_BACKUP_SIZE = 10 * 1024 * 1024 * 1024  # 10GB

    # 日志配置 - 使用相对路径
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = 'logs/app.log'

    # 调度器配置
    SCHEDULER_API_ENABLED = True
    
    @staticmethod
    def get_host_path(path: str) -> str:
        """
        获取宿主机路径
        在Docker环境中，将容器内路径转换为宿主机路径
        在本地环境中，直接返回原路径
        """
        if Config.DOCKER_ENV and Config.HOST_ROOT_PREFIX:
            # 如果路径已经包含前缀，直接返回
            if path.startswith(Config.HOST_ROOT_PREFIX):
                return path
            # 如果是绝对路径，添加前缀
            if path.startswith('/'):
                return Config.HOST_ROOT_PREFIX + path
            # 相对路径，添加前缀和根目录
            return Config.HOST_ROOT_PREFIX + '/' + path
        return path

    @staticmethod
    def get_display_path(path: str) -> str:
        """
        获取显示路径
        在Docker环境中，移除宿主机前缀显示给用户
        在本地环境中，直接返回原路径
        """
        if Config.DOCKER_ENV and Config.HOST_ROOT_PREFIX and path.startswith(Config.HOST_ROOT_PREFIX):
            display_path = path[len(Config.HOST_ROOT_PREFIX):]
            return display_path if display_path else '/'
        return path

    @staticmethod
    def init_app(app):
        # 创建必要的目录
        directories = [
            'data',
            'data/temp',
            'logs',
            Config.RCLONE_CONFIG_DIR  # rclone配置目录
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)

        print("✓ 目录结构创建完成")
        print(f"✓ rclone配置目录: {Config.RCLONE_CONFIG_DIR}")

        if Config.DOCKER_ENV:
            print("✓ Docker环境模式")
            print(f"✓ rclone容器名称: {Config.RCLONE_CONTAINER_NAME}")
            print(f"✓ 宿主机根目录前缀: {Config.HOST_ROOT_PREFIX}")
        else:
            print("✓ 本地环境模式")
            print(f"✓ rclone二进制文件: {Config.RCLONE_BINARY}")

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
