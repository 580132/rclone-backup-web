"""
原始rclone配置存储类型

允许用户直接编写rclone配置，作为保底操作支持所有rclone支持的存储类型
"""

from typing import Dict, Tuple
from ..base import BaseStorageType
import configparser
import io


class RawRcloneStorageType(BaseStorageType):
    """原始rclone配置存储类型"""
    
    def get_type_id(self) -> str:
        return "raw_rclone"
    
    def get_display_name(self) -> str:
        return "原始rclone配置"
    
    def get_template_name(self) -> str:
        return "storage_types/raw_rclone_config.html"
    
    def get_required_fields(self) -> list:
        return ["rclone_config"]
    
    def get_icon_class(self) -> str:
        return "bi bi-code-square"
    
    def get_icon_color(self) -> str:
        return "#6f42c1"
    
    def get_description(self) -> str:
        return "直接编写rclone配置，支持所有rclone支持的存储类型"
    
    def process_form_data(self, form_data: dict) -> dict:
        """处理原始rclone配置数据"""
        config = {}
        
        # 获取用户输入的rclone配置
        raw_config = form_data.get('rclone_config', '').strip()
        if not raw_config:
            return config
        
        try:
            # 解析rclone配置格式
            parsed_config = self._parse_rclone_config(raw_config)
            config.update(parsed_config)
            
            # 保存原始配置文本用于显示
            config['_raw_config'] = raw_config
            
        except Exception as e:
            # 如果解析失败，保存原始配置，在验证时报错
            config['_raw_config'] = raw_config
            config['_parse_error'] = str(e)
        
        return config
    
    def validate_config(self, config_data: dict) -> Tuple[bool, str]:
        """验证rclone配置"""
        # 检查是否有解析错误
        if '_parse_error' in config_data:
            return False, f"rclone配置格式错误: {config_data['_parse_error']}"
        
        # 检查是否有原始配置
        if not config_data.get('_raw_config'):
            return False, "rclone配置不能为空"
        
        # 检查是否有type字段
        if not config_data.get('type'):
            return False, "rclone配置必须包含 type 字段"
        
        return True, ""
    
    def get_rclone_config(self, config_data: dict) -> dict:
        """生成rclone配置"""
        # 移除内部字段
        rclone_config = {}
        for key, value in config_data.items():
            if not key.startswith('_'):
                rclone_config[key] = value
        
        return rclone_config
    
    def _parse_rclone_config(self, raw_config: str) -> dict:
        """解析rclone配置文本"""
        config = {}
        
        # 支持两种格式：
        # 1. key=value 格式
        # 2. INI格式（如果包含[section]）
        
        if '[' in raw_config and ']' in raw_config:
            # INI格式
            config_parser = configparser.ConfigParser()
            config_parser.read_string(raw_config)
            
            # 假设用户只配置了一个section，取第一个非DEFAULT section
            sections = [s for s in config_parser.sections() if s != 'DEFAULT']
            if sections:
                section = sections[0]
                for key, value in config_parser[section].items():
                    config[key] = value
            else:
                raise ValueError("INI格式配置中没有找到有效的section")
        
        else:
            # key=value格式
            for line in raw_config.strip().split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
                else:
                    raise ValueError(f"配置行格式错误: {line}")
        
        return config
    
    def supports_test_connection(self) -> bool:
        """支持连接测试"""
        return True
    
    def get_default_test_path(self) -> str:
        """获取默认测试路径"""
        return "/"
