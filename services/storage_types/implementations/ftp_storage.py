"""
FTP 存储类型实现

直接实现，简单清晰
"""

from typing import Dict, Tuple
from ..base import BaseStorageType


class FTPStorageType(BaseStorageType):
    """FTP 存储类型"""
    
    def get_type_id(self) -> str:
        return "ftp"
    
    def get_display_name(self) -> str:
        return "FTP"
    
    def get_template_name(self) -> str:
        return "storage_types/ftp_config.html"
    
    def get_required_fields(self) -> list:
        return ["host", "username", "password"]
    
    def get_icon_class(self) -> str:
        return "bi bi-folder-symlink"
    
    def get_icon_color(self) -> str:
        return "#6f42c1"
    
    def get_description(self) -> str:
        return "文件传输协议，标准FTP连接"
    
    def process_form_data(self, form_data: dict) -> dict:
        """处理FTP表单数据 - 直接映射字段"""
        config = {}

        # 基本字段映射
        config['host'] = form_data.get('host', '').strip()
        config['user'] = form_data.get('username', '').strip()
        config['pass'] = form_data.get('password', '').strip()

        # 端口（如果不是默认值）
        port = form_data.get('port', '21').strip()
        if port and port != '21':
            config['port'] = port

        # FTP选项
        if form_data.get('tls'):
            config['tls'] = 'true'

        if form_data.get('passive'):
            config['passive'] = 'true'

        return config

    def validate_config(self, config_data: dict) -> Tuple[bool, str]:
        """验证FTP配置"""
        if not config_data.get('host'):
            return False, "主机地址不能为空"

        if not config_data.get('user'):
            return False, "用户名不能为空"

        if not config_data.get('pass'):
            return False, "密码不能为空"

        return True, ""

    def get_rclone_config(self, config_data: dict) -> dict:
        """生成FTP的rclone配置"""
        rclone_config = {'type': 'ftp'}
        rclone_config.update(config_data)
        return rclone_config
