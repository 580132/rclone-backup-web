"""
Google Drive 存储类型实现

Google Drive有特殊的OAuth认证流程，不使用通用构造器
"""

from typing import Dict, Tuple
from ..base import BaseStorageType


class GoogleDriveStorageType(BaseStorageType):
    """Google Drive 存储类型"""
    
    def get_type_id(self) -> str:
        return "google_drive"
    
    def get_display_name(self) -> str:
        return "Google Drive"
    
    def get_template_name(self) -> str:
        return "storage_types/google_drive_config.html"
    
    def get_required_fields(self) -> list:
        return []  # Google Drive可以使用默认OAuth配置
    
    def get_icon_class(self) -> str:
        return "bi bi-google"
    
    def get_icon_color(self) -> str:
        return "#4285f4"
    
    def get_description(self) -> str:
        return "Google Drive 云存储服务，支持OAuth2授权"
    
    def process_form_data(self, form_data: dict) -> dict:
        """处理Google Drive表单数据"""
        config = {}
        
        # 授权方式
        auth_type = form_data.get('drive_auth_type', 'oauth')
        config['auth_type'] = auth_type
        
        if auth_type == 'oauth':
            # OAuth2配置
            client_id = form_data.get('client_id', '').strip()
            if client_id:
                config['client_id'] = client_id
            
            client_secret = form_data.get('client_secret', '').strip()
            if client_secret:
                config['client_secret'] = client_secret
        
        elif auth_type == 'service_account':
            # 服务账户配置
            service_account_file = form_data.get('service_account_file', '').strip()
            if service_account_file:
                config['service_account_file'] = service_account_file
        
        # 其他可选配置
        scope = form_data.get('scope', 'drive')
        if scope:
            config['scope'] = scope
        
        return config
    
    def validate_config(self, config_data: dict) -> Tuple[bool, str]:
        """验证Google Drive配置"""
        auth_type = config_data.get('auth_type', 'oauth')
        
        if auth_type == 'service_account':
            if not config_data.get('service_account_file'):
                return False, "服务账户模式需要提供服务账户文件路径"
        
        # OAuth2模式可以使用默认配置，无需额外验证
        
        return True, ""
    
    def get_rclone_config(self, config_data: dict) -> dict:
        """生成Google Drive的rclone配置"""
        rclone_config = {
            'type': 'drive'
        }
        
        # 客户端配置
        if 'client_id' in config_data:
            rclone_config['client_id'] = config_data['client_id']
        
        if 'client_secret' in config_data:
            rclone_config['client_secret'] = config_data['client_secret']
        
        # 服务账户配置
        if 'service_account_file' in config_data:
            rclone_config['service_account_file'] = config_data['service_account_file']
        
        # 权限范围
        scope = config_data.get('scope', 'drive')
        rclone_config['scope'] = scope
        
        return rclone_config
    
    def supports_test_connection(self) -> bool:
        """Google Drive需要OAuth授权，不支持简单的连接测试"""
        return False
