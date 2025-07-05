"""
简化的S3兼容存储构造器

只负责表单数据到rclone配置的转换
"""

from typing import Dict, Tuple


class S3CompatibleBuilder:
    """简化的S3兼容存储构造器"""

    def __init__(self, provider: str):
        self.provider = provider
        self.field_mappings = {
            'access_key': 'access_key_id',
            'secret_key': 'secret_access_key',
            'region': 'region',
            'endpoint': 'endpoint',
            'bucket': 'bucket'
        }
        self.required_fields = ['access_key', 'secret_key']
        self.endpoint_required = False
        self.default_values = {}  # 默认值字典

    def add_field_mapping(self, form_field: str, rclone_field: str) -> 'S3CompatibleBuilder':
        """添加自定义字段映射"""
        self.field_mappings[form_field] = rclone_field
        return self

    def set_endpoint_required(self, required: bool = True) -> 'S3CompatibleBuilder':
        """设置端点是否必填"""
        self.endpoint_required = required
        if required and 'endpoint' not in self.required_fields:
            self.required_fields.append('endpoint')
        return self

    def add_default_value(self, field: str, value: str) -> 'S3CompatibleBuilder':
        """添加默认值"""
        self.default_values[field] = value
        return self

    def process_form_data(self, form_data: dict) -> dict:
        """处理表单数据，直接生成rclone配置格式"""
        config = {}

        # 映射表单字段到rclone字段
        for form_field, rclone_field in self.field_mappings.items():
            value = form_data.get(form_field, '').strip()
            if value:
                config[rclone_field] = value

        # 添加默认值
        for field, value in self.default_values.items():
            if field not in config:
                config[field] = value

        # 如果有端点，设置path style
        if config.get('endpoint'):
            config['force_path_style'] = 'true'

        return config

    def validate_config(self, config_data: dict) -> Tuple[bool, str]:
        """基本验证 - 只检查必填字段"""
        for field in self.required_fields:
            rclone_field = self.field_mappings.get(field, field)
            if not config_data.get(rclone_field):
                return False, f"{field} 不能为空"

        # 检查端点格式
        endpoint = config_data.get('endpoint', '')
        if endpoint and (endpoint.startswith('http://') or endpoint.startswith('https://')):
            return False, "端点地址不应包含协议前缀"

        return True, ""

    def get_rclone_config(self, config_data: dict) -> dict:
        """生成rclone配置"""
        rclone_config = {
            'type': 's3',
            'provider': self.provider
        }
        rclone_config.update(config_data)
        return rclone_config

    @staticmethod
    def create_aws_s3() -> 'S3CompatibleBuilder':
        """创建AWS S3构造器"""
        return S3CompatibleBuilder('AWS')

    @staticmethod
    def create_alibaba_oss() -> 'S3CompatibleBuilder':
        """创建阿里云OSS构造器"""
        return (S3CompatibleBuilder('Alibaba')
                .add_field_mapping('oss_access_key', 'access_key_id')
                .add_field_mapping('oss_secret_key', 'secret_access_key')
                .add_field_mapping('oss_endpoint', 'endpoint')
                .set_endpoint_required(True))

    @staticmethod
    def create_cloudflare_r2() -> 'S3CompatibleBuilder':
        """创建Cloudflare R2构造器"""
        builder = (S3CompatibleBuilder('Cloudflare')
                  .add_field_mapping('r2_access_key', 'access_key_id')
                  .add_field_mapping('r2_secret_key', 'secret_access_key')
                  .add_field_mapping('r2_endpoint', 'endpoint')
                  .set_endpoint_required(True)
                  .add_default_value('region', 'auto'))  # R2固定使用auto区域
        return builder
