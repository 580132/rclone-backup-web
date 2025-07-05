"""
SFTP 存储类型实现

简化版本 - 只处理表单数据到rclone配置的转换
"""

from typing import Dict, Tuple
from ..base import BaseStorageType


class SFTPStorageType(BaseStorageType):
    """SFTP 存储类型"""

    def get_type_id(self) -> str:
        return "sftp"

    def get_display_name(self) -> str:
        return "SFTP"

    def get_template_name(self) -> str:
        return "storage_types/sftp_config.html"

    def get_required_fields(self) -> list:
        return ["host", "username"]

    def get_icon_class(self) -> str:
        return "bi bi-server"

    def get_icon_color(self) -> str:
        return "#28a745"

    def get_description(self) -> str:
        return "SSH文件传输协议，安全的文件传输服务"

    def process_form_data(self, form_data: dict) -> dict:
        """处理SFTP表单数据 - 直接转换为rclone配置格式"""
        config = {}

        # 基本字段
        config['host'] = form_data.get('host', '').strip()
        config['user'] = form_data.get('username', '').strip()

        # 端口（如果不是默认值）
        port = form_data.get('port', '22').strip()
        if port and port != '22':
            config['port'] = port

        # 认证方式
        auth_type = form_data.get('auth_type', 'password')
        if auth_type == 'password':
            password = form_data.get('password', '').strip()
            if password:
                config['pass'] = password
        elif auth_type == 'key':
            key_file = form_data.get('key_file', '').strip()
            if key_file:
                config['key_file'] = key_file
            key_pass = form_data.get('key_pass', '').strip()
            if key_pass:
                config['key_pass'] = key_pass

        # SFTP特有选项
        if form_data.get('disable_hashcheck'):
            config['disable_hashcheck'] = 'true'

        return config

    def validate_config(self, config_data: dict) -> Tuple[bool, str]:
        """验证SFTP配置"""
        if not config_data.get('host'):
            return False, "主机地址不能为空"

        if not config_data.get('user'):
            return False, "用户名不能为空"

        return True, ""

    def get_rclone_config(self, config_data: dict) -> dict:
        """生成SFTP的rclone配置"""
        rclone_config = {'type': 'sftp'}
        rclone_config.update(config_data)
        return rclone_config
