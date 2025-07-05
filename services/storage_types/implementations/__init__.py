"""
存储类型具体实现模块

包含所有具体的存储类型实现，使用构造器模式减少重复代码
"""

from .s3_storage import S3StorageType
from .alibaba_oss_storage import AlibabaOSSStorageType
from .cloudflare_r2_storage import CloudflareR2StorageType
from .google_drive_storage import GoogleDriveStorageType
from .sftp_storage import SFTPStorageType
from .ftp_storage import FTPStorageType
from .webdav_storage import WebDAVStorageType
from .minio_storage import MinIOStorageType
from .raw_rclone_storage import RawRcloneStorageType

__all__ = [
    'S3StorageType',
    'AlibabaOSSStorageType',
    'CloudflareR2StorageType',
    'GoogleDriveStorageType',
    'SFTPStorageType',
    'FTPStorageType',
    'WebDAVStorageType',
    'MinIOStorageType',
    'RawRcloneStorageType'
]
