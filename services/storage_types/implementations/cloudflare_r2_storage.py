"""
Cloudflare R2 存储类型实现

使用S3兼容构造器简化配置逻辑
"""

from typing import Dict, Tuple
from ..base import BaseStorageType
from ..builders import S3CompatibleBuilder


class CloudflareR2StorageType(BaseStorageType):
    """Cloudflare R2 存储类型"""
    
    def __init__(self):
        self.builder = S3CompatibleBuilder.create_cloudflare_r2()
    
    def get_type_id(self) -> str:
        return "cloudflare_r2"
    
    def get_display_name(self) -> str:
        return "Cloudflare R2"
    
    def get_template_name(self) -> str:
        return "storage_types/cloudflare_r2_config.html"
    
    def get_required_fields(self) -> list:
        return ["r2_access_key", "r2_secret_key", "r2_endpoint"]
    
    def get_icon_class(self) -> str:
        return "bi bi-cloud"
    
    def get_icon_color(self) -> str:
        return "#f38020"
    
    def get_description(self) -> str:
        return "Cloudflare R2 对象存储服务，使用S3兼容协议访问"
    
    def process_form_data(self, form_data: dict) -> dict:
        """处理Cloudflare R2表单数据"""
        return self.builder.process_form_data(form_data)
    
    def validate_config(self, config_data: dict) -> Tuple[bool, str]:
        """验证Cloudflare R2配置"""
        return self.builder.validate_config(config_data)
    
    def get_rclone_config(self, config_data: dict) -> dict:
        """生成Cloudflare R2的rclone配置"""
        return self.builder.get_rclone_config(config_data)
