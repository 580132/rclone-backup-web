"""
存储类型模块化系统

这个模块提供了一个可扩展的存储配置系统，允许开发者轻松添加新的存储类型
而无需修改核心代码。

使用方法：
1. 在 storage_types 目录下创建新的存储类型模块
2. 继承 BaseStorageType 类
3. 实现必要的方法
4. 在 __init__.py 中导入并注册

示例：
    from .s3_storage import S3StorageType
    StorageTypeRegistry.register(S3StorageType())
"""

from .registry import StorageTypeRegistry
from .base import BaseStorageType

# 导入并注册所有存储类型
from .implementations import (
    S3StorageType,
    AlibabaOSSStorageType,
    CloudflareR2StorageType,
    GoogleDriveStorageType,
    SFTPStorageType,
    FTPStorageType,
    WebDAVStorageType,
    MinIOStorageType,
    RawRcloneStorageType
)

# 注册所有存储类型
StorageTypeRegistry.register(S3StorageType())
StorageTypeRegistry.register(AlibabaOSSStorageType())
StorageTypeRegistry.register(CloudflareR2StorageType())
StorageTypeRegistry.register(GoogleDriveStorageType())
StorageTypeRegistry.register(SFTPStorageType())
StorageTypeRegistry.register(FTPStorageType())
StorageTypeRegistry.register(WebDAVStorageType())
StorageTypeRegistry.register(MinIOStorageType())
StorageTypeRegistry.register(RawRcloneStorageType())  # 原始rclone配置支持

__all__ = ['StorageTypeRegistry', 'BaseStorageType']
