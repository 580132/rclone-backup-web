"""
WebDAV 存储类型实现

直接实现，简单清晰
"""

from typing import Dict, Tuple
from ..base import BaseStorageType


class WebDAVStorageType(BaseStorageType):
    """WebDAV 存储类型"""

    def get_type_id(self) -> str:
        return "webdav"

    def get_display_name(self) -> str:
        return "WebDAV"

    def get_template_name(self) -> str:
        return "storage_types/webdav_config.html"

    def get_required_fields(self) -> list:
        return ["url", "username", "password"]

    def get_icon_class(self) -> str:
        return "bi bi-globe"

    def get_icon_color(self) -> str:
        return "#17a2b8"

    def get_description(self) -> str:
        return "WebDAV协议存储服务，支持多种云存储和NAS设备"

    def process_form_data(self, form_data: dict) -> dict:
        """处理WebDAV表单数据 - 直接映射字段"""
        config = {}

        # 基本字段映射
        config['url'] = form_data.get('url', '').strip()
        config['user'] = form_data.get('username', '').strip()
        config['pass'] = form_data.get('password', '').strip()

        # 可选字段
        vendor = form_data.get('vendor', '').strip()
        if vendor:
            config['vendor'] = vendor

        # SSL设置
        if form_data.get('disable_ssl_verify'):
            config['disable_ssl_verify'] = 'true'

        return config

    def validate_config(self, config_data: dict) -> Tuple[bool, str]:
        """验证WebDAV配置"""
        if not config_data.get('url'):
            return False, "WebDAV URL 不能为空"

        if not config_data.get('user'):
            return False, "用户名不能为空"

        if not config_data.get('pass'):
            return False, "密码不能为空"

        # 验证URL格式
        url = config_data.get('url', '')
        if not (url.startswith('http://') or url.startswith('https://')):
            return False, "WebDAV URL 必须以 http:// 或 https:// 开头"

        return True, ""

    def get_rclone_config(self, config_data: dict) -> dict:
        """生成WebDAV的rclone配置"""
        rclone_config = {'type': 'webdav'}
        rclone_config.update(config_data)
        return rclone_config
