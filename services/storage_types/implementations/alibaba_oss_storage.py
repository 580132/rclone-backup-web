"""
阿里云 OSS 存储类型实现

使用S3兼容构造器简化配置逻辑
"""

from typing import Dict, Tuple
from ..base import BaseStorageType
from ..builders import S3CompatibleBuilder


class AlibabaOSSStorageType(BaseStorageType):
    """阿里云 OSS 存储类型"""
    
    def __init__(self):
        self.builder = S3CompatibleBuilder.create_alibaba_oss()
    
    def get_type_id(self) -> str:
        return "alibaba_oss"
    
    def get_display_name(self) -> str:
        return "阿里云 OSS"
    
    def get_template_name(self) -> str:
        return "storage_types/alibaba_oss_config.html"
    
    def get_required_fields(self) -> list:
        return ["oss_access_key", "oss_secret_key", "oss_endpoint"]
    
    def get_icon_class(self) -> str:
        return "bi bi-cloud"
    
    def get_icon_color(self) -> str:
        return "#ff6a00"
    
    def get_description(self) -> str:
        return "阿里云对象存储服务，使用S3兼容协议访问"
    
    def process_form_data(self, form_data: dict) -> dict:
        """处理阿里云OSS表单数据"""
        return self.builder.process_form_data(form_data)
    
    def validate_config(self, config_data: dict) -> Tuple[bool, str]:
        """验证阿里云OSS配置"""
        return self.builder.validate_config(config_data)
    
    def get_rclone_config(self, config_data: dict) -> dict:
        """生成阿里云OSS的rclone配置"""
        return self.builder.get_rclone_config(config_data)
