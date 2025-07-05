"""
MinIO 存储类型实现

这是一个使用构造器模式的完整示例，展示如何快速添加新的存储类型
"""

from typing import Dict, Tuple
from ..base import BaseStorageType
from ..builders import S3CompatibleBuilder


class MinIOStorageType(BaseStorageType):
    """MinIO 存储类型 - 使用构造器模式的示例"""
    
    def __init__(self):
        # 使用S3兼容构造器，因为MinIO兼容S3 API
        self.builder = (S3CompatibleBuilder('MinIO')
                       .set_endpoint_required(True))  # MinIO需要指定端点
    
    def get_type_id(self) -> str:
        return "minio"
    
    def get_display_name(self) -> str:
        return "MinIO"
    
    def get_template_name(self) -> str:
        return "storage_types/minio_config.html"
    
    def get_required_fields(self) -> list:
        return ["access_key", "secret_key", "endpoint"]
    
    def get_icon_class(self) -> str:
        return "bi bi-hdd-stack"
    
    def get_icon_color(self) -> str:
        return "#c72e29"
    
    def get_description(self) -> str:
        return "MinIO 高性能对象存储，兼容Amazon S3 API"
    
    def process_form_data(self, form_data: dict) -> dict:
        """处理MinIO表单数据 - 使用构造器"""
        return self.builder.process_form_data(form_data)
    
    def validate_config(self, config_data: dict) -> Tuple[bool, str]:
        """验证MinIO配置 - 使用构造器"""
        # 先进行基本验证
        is_valid, error_msg = self.builder.validate_config(config_data)
        if not is_valid:
            return is_valid, error_msg

        # 进行MinIO特有的验证
        return self._validate_minio_endpoint(config_data)
    
    def get_rclone_config(self, config_data: dict) -> dict:
        """生成MinIO的rclone配置 - 使用构造器"""
        return self.builder.get_rclone_config(config_data)
    
    def _validate_minio_endpoint(self, config_data: dict) -> Tuple[bool, str]:
        """MinIO特有的端点验证"""
        endpoint = config_data.get('endpoint', '')
        
        # MinIO端点通常包含端口号
        if ':' not in endpoint:
            return False, "MinIO端点地址通常需要包含端口号，例如：minio.example.com:9000"
        
        # 检查是否是常见的MinIO端口
        if endpoint.endswith(':9000') or endpoint.endswith(':9001'):
            return True, ""
        
        # 其他端口也是有效的，只是给出提示
        return True, ""
