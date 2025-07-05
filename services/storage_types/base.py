"""
存储类型基类

定义了所有存储类型必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional


class BaseStorageType(ABC):
    """存储类型基类"""
    
    @abstractmethod
    def get_type_id(self) -> str:
        """获取存储类型ID（用于内部标识）"""
        pass
    
    @abstractmethod
    def get_display_name(self) -> str:
        """获取显示名称（用于用户界面）"""
        pass
    
    @abstractmethod
    def get_template_name(self) -> str:
        """获取前端模板文件名"""
        pass
    
    @abstractmethod
    def get_required_fields(self) -> list:
        """获取必填字段列表"""
        pass
    
    @abstractmethod
    def process_form_data(self, form_data: dict) -> dict:
        """
        处理前端表单数据，转换为内部配置格式
        
        Args:
            form_data: 前端表单数据
            
        Returns:
            dict: 处理后的配置数据
        """
        pass
    
    @abstractmethod
    def validate_config(self, config_data: dict) -> Tuple[bool, str]:
        """
        验证配置数据
        
        Args:
            config_data: 配置数据
            
        Returns:
            tuple: (是否有效, 错误信息)
        """
        pass
    
    @abstractmethod
    def get_rclone_config(self, config_data: dict) -> dict:
        """
        生成rclone配置
        
        Args:
            config_data: 内部配置数据
            
        Returns:
            dict: rclone配置参数
        """
        pass
    
    def get_icon_class(self) -> str:
        """获取图标CSS类（可选重写）"""
        return "bi bi-cloud"
    
    def get_icon_color(self) -> str:
        """获取图标颜色（可选重写）"""
        return "#6c757d"
    
    def get_description(self) -> str:
        """获取存储类型描述（可选重写）"""
        return f"{self.get_display_name()} 存储服务"
    
    def supports_test_connection(self) -> bool:
        """是否支持连接测试（可选重写）"""
        return True
    
    def get_default_test_path(self) -> str:
        """获取默认测试路径（可选重写）"""
        return "/"
