import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from models import db, StorageConfig, StorageConfigHistory
from services.rclone_service import RcloneService


class ConfigService:
    """配置管理服务 - 负责配置的同步和历史版本管理"""
    
    def __init__(self):
        self.rclone_service = RcloneService()
        self.logger = logging.getLogger(__name__)

    def process_form_data(self, storage_type: str, form_data: dict) -> Tuple[bool, str, Optional[dict]]:
        """处理前端表单数据"""
        try:
            from .storage_types import StorageTypeRegistry

            # 获取存储类型处理器
            storage_type_handler = StorageTypeRegistry.get_type(storage_type)
            if not storage_type_handler:
                return False, f"不支持的存储类型: {storage_type}", None

            # 处理表单数据
            config_data = storage_type_handler.process_form_data(form_data)

            # 验证配置数据
            is_valid, error_msg = storage_type_handler.validate_config(config_data)
            if not is_valid:
                return False, error_msg, None

            return True, "", config_data

        except Exception as e:
            self.logger.error(f"Failed to process form data: {e}")
            return False, f"处理表单数据时出错: {str(e)}", None
    
    def create_storage_config(self, name: str, storage_type: str, config_data: Dict,
                            description: str = None, test_path: str = None, created_by: str = None) -> Tuple[bool, str, Optional[StorageConfig]]:
        """创建存储配置"""
        try:
            from .storage_types import StorageTypeRegistry

            # 检查名称是否已存在
            if StorageConfig.query.filter_by(name=name).first():
                return False, "配置名称已存在", None

            # 验证存储类型
            storage_type_handler = StorageTypeRegistry.get_type(storage_type)
            if not storage_type_handler:
                return False, f"不支持的存储类型: {storage_type}", None

            # 验证配置数据
            is_valid, error_msg = storage_type_handler.validate_config(config_data)
            if not is_valid:
                return False, error_msg, None

            # 生成rclone配置名称
            rclone_config_name = f"backup_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # 获取rclone配置
            rclone_config = storage_type_handler.get_rclone_config(config_data)

            # 创建rclone配置
            if not self.rclone_service.create_config(rclone_config_name, storage_type, rclone_config):
                return False, "创建rclone配置失败", None

            # 测试连接（如果支持）
            if storage_type_handler.supports_test_connection():
                success, message = self.rclone_service.test_connection(rclone_config_name, test_path)
                if not success:
                    # 删除创建的配置
                    self.rclone_service.delete_config(rclone_config_name)
                    return False, f"连接测试失败: {message}", None
            
            # 创建数据库记录
            storage_config = StorageConfig(
                name=name,
                storage_type=storage_type,
                rclone_config_name=rclone_config_name,
                description=description,
                test_path=test_path
            )
            
            db.session.add(storage_config)
            db.session.flush()  # 获取ID但不提交
            
            # 创建初始配置历史版本
            self._create_config_history(
                storage_config.id, 
                1, 
                config_data, 
                rclone_config_name,
                "初始创建",
                created_by
            )
            
            db.session.commit()
            
            self.logger.info(f"Created storage config: {name}")
            return True, "配置创建成功", storage_config
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to create storage config: {e}")
            return False, f"创建配置时出错: {str(e)}", None
    
    def get_config_from_rclone(self, config_name: str) -> Optional[Dict[str, str]]:
        """从rclone配置文件读取配置"""
        try:
            return self.rclone_service.get_config_section(config_name)
        except Exception as e:
            self.logger.error(f"Failed to get config from rclone: {e}")
            return None
    
    def update_storage_config(self, storage_config_id: int, name: str = None,
                             config_data: Dict = None, description: str = None,
                             test_path: str = None, created_by: str = None) -> Tuple[bool, str]:
        """更新存储配置"""
        try:
            storage_config = StorageConfig.query.get(storage_config_id)
            if not storage_config:
                return False, "配置不存在"

            # 检查名称是否与其他配置冲突
            if name and name != storage_config.name:
                existing_config = StorageConfig.query.filter_by(name=name).first()
                if existing_config:
                    return False, "配置名称已存在"
                storage_config.name = name

            # 更新描述
            if description is not None:
                storage_config.description = description

            # 更新测试路径
            if test_path is not None:
                storage_config.test_path = test_path

            # 如果有配置数据更新，则更新rclone配置文件
            if config_data:
                # 更新rclone配置文件
                if not self.rclone_service.create_config(
                    storage_config.rclone_config_name,
                    storage_config.storage_type,
                    config_data
                ):
                    return False, "更新rclone配置失败"

                # 创建新的历史版本
                latest_version = self._get_latest_version(storage_config_id)
                new_version = latest_version + 1

                self._create_config_history(
                    storage_config_id,
                    new_version,
                    config_data,
                    storage_config.rclone_config_name,
                    "配置更新",
                    created_by
                )

            # 更新修改时间
            storage_config.updated_at = datetime.utcnow()
            db.session.commit()

            self.logger.info(f"Updated storage config: {storage_config.name}")
            return True, "配置更新成功"

        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to update storage config: {e}")
            return False, f"更新配置时出错: {str(e)}"

    def get_storage_config_details(self, storage_config_id: int) -> Optional[Tuple[StorageConfig, Dict]]:
        """获取存储配置详情，包括当前的rclone配置"""
        try:
            storage_config = StorageConfig.query.get(storage_config_id)
            if not storage_config:
                return None

            # 从rclone文件读取当前配置
            rclone_config = self.get_config_from_rclone(storage_config.rclone_config_name)
            if not rclone_config:
                rclone_config = {}

            return storage_config, rclone_config

        except Exception as e:
            self.logger.error(f"Failed to get storage config details: {e}")
            return None

    def sync_config_from_rclone(self, storage_config_id: int, change_reason: str = "手动同步",
                               created_by: str = None) -> Tuple[bool, str]:
        """从rclone配置文件同步配置到历史版本"""
        try:
            storage_config = StorageConfig.query.get(storage_config_id)
            if not storage_config:
                return False, "配置不存在"

            # 从rclone文件读取配置
            rclone_config = self.get_config_from_rclone(storage_config.rclone_config_name)
            if not rclone_config:
                return False, "无法从rclone配置文件读取配置"

            # 获取当前最新版本号
            latest_version = self._get_latest_version(storage_config_id)
            new_version = latest_version + 1

            # 创建新的历史版本
            self._create_config_history(
                storage_config_id,
                new_version,
                rclone_config,
                storage_config.rclone_config_name,
                change_reason,
                created_by
            )

            # 更新配置的修改时间
            storage_config.updated_at = datetime.utcnow()
            db.session.commit()

            self.logger.info(f"Synced config {storage_config.name} to version {new_version}")
            return True, f"配置已同步到版本 {new_version}"

        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to sync config: {e}")
            return False, f"同步配置时出错: {str(e)}"
    
    def get_config_history(self, storage_config_id: int) -> List[StorageConfigHistory]:
        """获取配置历史版本"""
        try:
            return StorageConfigHistory.query.filter_by(
                storage_config_id=storage_config_id
            ).order_by(StorageConfigHistory.version.desc()).all()
        except Exception as e:
            self.logger.error(f"Failed to get config history: {e}")
            return []
    
    def restore_config_version(self, storage_config_id: int, version: int, 
                             created_by: str = None) -> Tuple[bool, str]:
        """恢复配置到指定版本"""
        try:
            storage_config = StorageConfig.query.get(storage_config_id)
            if not storage_config:
                return False, "配置不存在"
            
            # 获取指定版本的配置
            history = StorageConfigHistory.query.filter_by(
                storage_config_id=storage_config_id,
                version=version
            ).first()
            
            if not history:
                return False, f"版本 {version} 不存在"
            
            # 解析配置数据
            config_data = json.loads(history.config_data)
            
            # 更新rclone配置文件
            if not self.rclone_service.create_config(
                storage_config.rclone_config_name, 
                storage_config.storage_type, 
                config_data
            ):
                return False, "更新rclone配置失败"
            
            # 创建新的历史版本记录恢复操作
            latest_version = self._get_latest_version(storage_config_id)
            new_version = latest_version + 1
            
            self._create_config_history(
                storage_config_id,
                new_version,
                config_data,
                storage_config.rclone_config_name,
                f"恢复到版本 {version}",
                created_by
            )
            
            # 更新配置的修改时间
            storage_config.updated_at = datetime.utcnow()
            db.session.commit()
            
            self.logger.info(f"Restored config {storage_config.name} to version {version}")
            return True, f"配置已恢复到版本 {version}"
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to restore config: {e}")
            return False, f"恢复配置时出错: {str(e)}"
    
    def delete_storage_config(self, storage_config_id: int) -> Tuple[bool, str]:
        """删除存储配置"""
        try:
            storage_config = StorageConfig.query.get(storage_config_id)
            if not storage_config:
                return False, "配置不存在"
            
            # 检查是否有关联的备份任务
            if storage_config.backup_tasks:
                return False, "无法删除：存在关联的备份任务"
            
            # 删除rclone配置文件
            self.rclone_service.delete_config(storage_config.rclone_config_name)
            
            # 删除历史版本记录
            StorageConfigHistory.query.filter_by(storage_config_id=storage_config_id).delete()
            
            # 删除配置记录
            db.session.delete(storage_config)
            db.session.commit()
            
            self.logger.info(f"Deleted storage config: {storage_config.name}")
            return True, "配置已删除"
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to delete storage config: {e}")
            return False, f"删除配置时出错: {str(e)}"
    
    def _create_config_history(self, storage_config_id: int, version: int, 
                             config_data: Dict, rclone_config_name: str,
                             change_reason: str, created_by: str = None):
        """创建配置历史版本记录"""
        # 获取rclone配置文件内容
        rclone_config_content = None
        try:
            rclone_config = self.rclone_service.get_config_section(rclone_config_name)
            if rclone_config:
                # 重构为rclone配置格式
                rclone_config_content = f"[{rclone_config_name}]\n"
                for key, value in rclone_config.items():
                    rclone_config_content += f"{key} = {value}\n"
        except Exception as e:
            self.logger.warning(f"Failed to get rclone config content: {e}")
        
        history = StorageConfigHistory(
            storage_config_id=storage_config_id,
            version=version,
            config_data=json.dumps(config_data, ensure_ascii=False),
            rclone_config_content=rclone_config_content,
            change_reason=change_reason,
            created_by=created_by
        )
        
        db.session.add(history)
    
    def _get_latest_version(self, storage_config_id: int) -> int:
        """获取最新版本号"""
        latest = StorageConfigHistory.query.filter_by(
            storage_config_id=storage_config_id
        ).order_by(StorageConfigHistory.version.desc()).first()
        
        return latest.version if latest else 0
    
    def sync_all_configs_from_rclone(self) -> Tuple[int, int, List[str]]:
        """同步所有配置从rclone配置文件"""
        success_count = 0
        error_count = 0
        errors = []
        
        try:
            # 获取所有活跃的配置
            configs = StorageConfig.query.filter_by(is_active=True).all()
            
            for config in configs:
                success, message = self.sync_config_from_rclone(
                    config.id, 
                    "批量同步", 
                    "system"
                )
                
                if success:
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f"{config.name}: {message}")
            
            self.logger.info(f"Batch sync completed: {success_count} success, {error_count} errors")
            return success_count, error_count, errors
            
        except Exception as e:
            self.logger.error(f"Failed to sync all configs: {e}")
            return 0, 1, [f"批量同步失败: {str(e)}"]
