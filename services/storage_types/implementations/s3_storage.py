"""
Amazon S3 存储类型实现

使用S3兼容构造器简化配置逻辑
"""

from typing import Dict, Tuple
from ..base import BaseStorageType
from ..builders import S3CompatibleBuilder


class S3StorageType(BaseStorageType):
    """Amazon S3 存储类型"""
    
    def __init__(self):
        self.builder = S3CompatibleBuilder.create_aws_s3()
    
    def get_type_id(self) -> str:
        return "s3"
    
    def get_display_name(self) -> str:
        return "Amazon S3"
    
    def get_template_name(self) -> str:
        return "storage_types/s3_config.html"
    
    def get_required_fields(self) -> list:
        return ["access_key", "secret_key"]
    
    def get_icon_class(self) -> str:
        return "bi bi-amazon"
    
    def get_icon_color(self) -> str:
        return "#ff9900"
    
    def get_description(self) -> str:
        return "Amazon S3 对象存储服务，支持S3兼容的存储服务"
    
    def process_form_data(self, form_data: dict) -> dict:
        """处理S3表单数据"""
        return self.builder.process_form_data(form_data)
    
    def validate_config(self, config_data: dict) -> Tuple[bool, str]:
        """验证S3配置"""
        return self.builder.validate_config(config_data)
    
    def get_rclone_config(self, config_data: dict) -> dict:
        """生成S3的rclone配置"""
        return self.builder.get_rclone_config(config_data)
