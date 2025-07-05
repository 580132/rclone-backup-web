"""
字段映射构造器

提供表单字段到配置字段的映射功能
"""

from typing import Dict, List, Optional, Any


class FieldMapper:
    """字段映射构造器"""
    
    def __init__(self):
        self.field_mappings = {}
        self.default_values = {}
        self.optional_fields = set()
        self.conditional_fields = {}
    
    def add_mapping(self, form_field: str, config_field: str, required: bool = True) -> 'FieldMapper':
        """添加字段映射"""
        self.field_mappings[form_field] = config_field
        if not required:
            self.optional_fields.add(form_field)
        return self
    
    def add_default(self, config_field: str, default_value: Any) -> 'FieldMapper':
        """添加默认值"""
        self.default_values[config_field] = default_value
        return self
    
    def add_conditional(self, form_field: str, config_field: str, condition_func) -> 'FieldMapper':
        """添加条件字段（只有满足条件时才添加）"""
        self.conditional_fields[form_field] = (config_field, condition_func)
        return self
    
    def map_fields(self, form_data: dict) -> dict:
        """执行字段映射"""
        config = {}
        
        # 处理基本映射
        for form_field, config_field in self.field_mappings.items():
            value = form_data.get(form_field, '').strip()
            if value or form_field in self.optional_fields:
                if value:  # 只有非空值才添加
                    config[config_field] = value
        
        # 处理默认值
        for config_field, default_value in self.default_values.items():
            if config_field not in config:
                config[config_field] = default_value
        
        # 处理条件字段
        for form_field, (config_field, condition_func) in self.conditional_fields.items():
            if condition_func(form_data):
                value = form_data.get(form_field, '').strip()
                if value:
                    config[config_field] = value
        
        return config
    
    @staticmethod
    def create_s3_compatible() -> 'FieldMapper':
        """创建S3兼容存储的字段映射器"""
        return (FieldMapper()
                .add_mapping('access_key', 'access_key_id')
                .add_mapping('secret_key', 'secret_access_key')
                .add_mapping('region', 'region', required=False)
                .add_mapping('endpoint', 'endpoint', required=False)
                .add_mapping('bucket', 'bucket', required=False)
                .add_conditional('endpoint', 'force_path_style', 
                               lambda data: bool(data.get('endpoint', '').strip())))
    
    @staticmethod
    def create_auth_based() -> 'FieldMapper':
        """创建基于认证的字段映射器"""
        return (FieldMapper()
                .add_mapping('host', 'host')
                .add_mapping('username', 'user')
                .add_mapping('port', 'port', required=False))
    
    @staticmethod
    def create_url_based() -> 'FieldMapper':
        """创建基于URL的字段映射器"""
        return (FieldMapper()
                .add_mapping('url', 'url')
                .add_mapping('username', 'user')
                .add_mapping('password', 'pass'))
