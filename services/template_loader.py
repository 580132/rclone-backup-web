"""
模板加载器

用于动态加载存储类型的配置模板
"""

import os
from flask import current_app
from .storage_types import StorageTypeRegistry


class TemplateLoader:
    """模板加载器"""
    
    @staticmethod
    def get_storage_config_templates():
        """获取所有存储类型的配置模板内容"""
        templates = {}
        
        for type_id in StorageTypeRegistry.list_registered_types():
            storage_type = StorageTypeRegistry.get_type(type_id)
            if storage_type:
                template_name = storage_type.get_template_name()
                template_path = os.path.join(current_app.template_folder, template_name)
                
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        templates[type_id] = f.read()
                except FileNotFoundError:
                    current_app.logger.warning(f"Template not found: {template_path}")
                    templates[type_id] = f"<!-- Template not found for {type_id} -->"
                except Exception as e:
                    current_app.logger.error(f"Error loading template {template_path}: {e}")
                    templates[type_id] = f"<!-- Error loading template for {type_id} -->"
        
        return templates
    
    @staticmethod
    def get_storage_type_info():
        """获取所有存储类型的信息"""
        info = {}
        
        for type_id in StorageTypeRegistry.list_registered_types():
            storage_type = StorageTypeRegistry.get_type(type_id)
            if storage_type:
                info[type_id] = {
                    'display_name': storage_type.get_display_name(),
                    'icon_class': storage_type.get_icon_class(),
                    'icon_color': storage_type.get_icon_color(),
                    'description': storage_type.get_description(),
                    'required_fields': storage_type.get_required_fields()
                }
        
        return info
