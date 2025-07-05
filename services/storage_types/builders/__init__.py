"""
存储类型构造器模块

只保留真正有价值的S3兼容构造器
"""

from .s3_compatible_builder import S3CompatibleBuilder

__all__ = [
    'S3CompatibleBuilder'
]
