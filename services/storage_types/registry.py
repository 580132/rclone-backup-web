"""
存储类型注册器

提供存储类型的注册、查找和管理功能
"""

from typing import Dict, List, Optional
from .base import BaseStorageType


class StorageTypeRegistry:
    """存储类型注册器"""
    
    _storage_types: Dict[str, BaseStorageType] = {}
    
    @classmethod
    def register(cls, storage_type: BaseStorageType) -> None:
        """注册存储类型"""
        if not isinstance(storage_type, BaseStorageType):
            raise TypeError("存储类型必须继承自 BaseStorageType")
        
        cls._storage_types[storage_type.get_type_id()] = storage_type
    
    @classmethod
    def get_type(cls, type_id: str) -> Optional[BaseStorageType]:
        """获取指定的存储类型"""
        return cls._storage_types.get(type_id)
    
    @classmethod
    def get_all_types(cls) -> List[Dict[str, str]]:
        """获取所有注册的存储类型"""
        return [
            {
                'value': type_id,
                'label': storage_type.get_display_name()
            }
            for type_id, storage_type in cls._storage_types.items()
        ]
    
    @classmethod
    def get_template_name(cls, type_id: str) -> Optional[str]:
        """获取存储类型的模板名称"""
        storage_type = cls.get_type(type_id)
        return storage_type.get_template_name() if storage_type else None
    
    @classmethod
    def process_form_data(cls, type_id: str, form_data: dict) -> Optional[dict]:
        """处理表单数据"""
        storage_type = cls.get_type(type_id)
        return storage_type.process_form_data(form_data) if storage_type else None
    
    @classmethod
    def validate_config(cls, type_id: str, config_data: dict) -> tuple[bool, str]:
        """验证配置数据"""
        storage_type = cls.get_type(type_id)
        if not storage_type:
            return False, f"未知的存储类型: {type_id}"
        
        return storage_type.validate_config(config_data)
    
    @classmethod
    def get_rclone_config(cls, type_id: str, config_data: dict) -> Optional[dict]:
        """获取rclone配置"""
        storage_type = cls.get_type(type_id)
        return storage_type.get_rclone_config(config_data) if storage_type else None
    
    @classmethod
    def list_registered_types(cls) -> List[str]:
        """列出所有已注册的存储类型ID"""
        return list(cls._storage_types.keys())
