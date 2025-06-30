import subprocess
import json
import os
import logging
import tempfile
from typing import Dict, List, Optional, Tuple
from config import Config

class RcloneService:
    """rclone服务类"""
    
    def __init__(self):
        self.config_dir = Config.RCLONE_CONFIG_DIR
        self.rclone_binary = Config.RCLONE_BINARY
        self.logger = logging.getLogger(__name__)
        
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
    
    def get_config_path(self, config_name: str) -> str:
        """获取配置文件路径"""
        return os.path.join(self.config_dir, f"{config_name}.conf")
    
    def create_config(self, name: str, storage_type: str, config_data: Dict) -> bool:
        """创建rclone配置"""
        try:
            config_path = self.get_config_path(name)
            
            # 根据存储类型生成配置内容
            config_content = self._generate_config_content(name, storage_type, config_data)
            if not config_content:
                return False
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            self.logger.info(f"Created rclone config: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create rclone config {name}: {e}")
            return False
    
    def _generate_config_content(self, name: str, storage_type: str, config_data: Dict) -> Optional[str]:
        """生成rclone配置内容"""
        try:
            if storage_type == 's3':
                # 支持AWS S3和兼容S3的服务
                config = f"""[{name}]
type = s3
access_key_id = {config_data['access_key']}
secret_access_key = {config_data['secret_key']}
region = {config_data.get('region', 'us-east-1')}
"""
                # 根据endpoint判断provider
                endpoint = config_data.get('endpoint', '').strip()
                if endpoint:
                    if 'aliyuncs.com' in endpoint:
                        config += f"provider = Alibaba\nendpoint = {endpoint}\n"
                    elif 'r2.cloudflarestorage.com' in endpoint:
                        config += f"provider = Cloudflare\nendpoint = {endpoint}\n"
                    else:
                        config += f"provider = Other\nendpoint = {endpoint}\n"
                else:
                    config += "provider = AWS\n"

                # 添加可选配置
                if config_data.get('bucket'):
                    config += f"bucket = {config_data['bucket']}\n"
                if config_data.get('location_constraint'):
                    config += f"location_constraint = {config_data['location_constraint']}\n"

                return config

            elif storage_type == 'alibaba_oss':
                # 阿里云OSS专用配置
                return f"""[{name}]
type = s3
provider = Alibaba
access_key_id = {config_data['access_key']}
secret_access_key = {config_data['secret_key']}
endpoint = {config_data['endpoint']}
region = {config_data.get('region', 'oss-cn-hangzhou')}
location_constraint = {config_data.get('region', 'oss-cn-hangzhou')}
"""

            elif storage_type == 'cloudflare_r2':
                # Cloudflare R2专用配置
                return f"""[{name}]
type = s3
provider = Cloudflare
access_key_id = {config_data['access_key']}
secret_access_key = {config_data['secret_key']}
endpoint = {config_data['endpoint']}
region = auto
"""

            elif storage_type == 'google_drive':
                # Google Drive配置
                config = f"""[{name}]
type = drive
"""
                # 如果有客户端凭据
                if config_data.get('client_id') and config_data.get('client_secret'):
                    config += f"client_id = {config_data['client_id']}\n"
                    config += f"client_secret = {config_data['client_secret']}\n"

                # 如果有访问令牌
                if config_data.get('token'):
                    config += f"token = {config_data['token']}\n"

                # 设置范围
                config += "scope = drive\n"

                # 可选配置
                if config_data.get('root_folder_id'):
                    config += f"root_folder_id = {config_data['root_folder_id']}\n"

                return config

            elif storage_type == 'sftp':
                # SFTP配置
                config = f"""[{name}]
type = sftp
host = {config_data['host']}
user = {config_data['username']}
port = {config_data.get('port', 22)}
"""
                # 认证方式
                if config_data.get('password'):
                    config += f"pass = {config_data['password']}\n"

                if config_data.get('key_file'):
                    config += f"key_file = {config_data['key_file']}\n"

                if config_data.get('key_pass'):
                    config += f"key_pass = {config_data['key_pass']}\n"

                # 可选配置
                if config_data.get('use_insecure_cipher'):
                    config += f"use_insecure_cipher = {config_data['use_insecure_cipher']}\n"

                if config_data.get('disable_hashcheck'):
                    config += f"disable_hashcheck = {config_data['disable_hashcheck']}\n"

                return config

            elif storage_type == 'ftp':
                return f"""[{name}]
type = ftp
host = {config_data['host']}
user = {config_data['username']}
pass = {config_data['password']}
port = {config_data.get('port', 21)}
"""
            else:
                self.logger.error(f"Unsupported storage type: {storage_type}")
                return None
        except KeyError as e:
            self.logger.error(f"Missing required config parameter: {e}")
            return None

    def get_supported_types(self) -> List[Dict[str, str]]:
        """获取支持的存储类型"""
        return [
            {
                'id': 's3',
                'name': 'Amazon S3',
                'description': 'Amazon S3 兼容存储',
                'icon': 'bi-amazon'
            },
            {
                'id': 'alibaba_oss',
                'name': '阿里云 OSS',
                'description': '阿里云对象存储服务',
                'icon': 'bi-cloud'
            },
            {
                'id': 'cloudflare_r2',
                'name': 'Cloudflare R2',
                'description': 'Cloudflare R2 对象存储',
                'icon': 'bi-cloud'
            },
            {
                'id': 'google_drive',
                'name': 'Google Drive',
                'description': 'Google Drive 云存储',
                'icon': 'bi-google'
            },
            {
                'id': 'sftp',
                'name': 'SFTP',
                'description': 'SSH 文件传输协议',
                'icon': 'bi-shield-lock'
            },
            {
                'id': 'ftp',
                'name': 'FTP',
                'description': '文件传输协议',
                'icon': 'bi-hdd-network'
            }
        ]
    
    def test_connection(self, config_name: str) -> Tuple[bool, str]:
        """测试rclone连接"""
        try:
            config_path = self.get_config_path(config_name)
            if not os.path.exists(config_path):
                return False, "配置文件不存在"
            
            cmd = [
                self.rclone_binary, 'lsd', f'{config_name}:',
                '--config', config_path,
                '--timeout', '30s'
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=35
            )
            
            if result.returncode == 0:
                self.logger.info(f"Connection test successful for {config_name}")
                return True, "连接成功"
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                self.logger.error(f"Connection test failed for {config_name}: {error_msg}")
                return False, f"连接失败: {error_msg}"
                
        except subprocess.TimeoutExpired:
            return False, "连接超时"
        except Exception as e:
            self.logger.error(f"Connection test error for {config_name}: {e}")
            return False, f"测试失败: {str(e)}"
    
    def upload_file(self, local_path: str, remote_path: str, config_name: str) -> Tuple[bool, str]:
        """上传文件到远程存储"""
        try:
            config_path = self.get_config_path(config_name)
            if not os.path.exists(config_path):
                return False, "配置文件不存在"
            
            if not os.path.exists(local_path):
                return False, "本地文件不存在"
            
            cmd = [
                self.rclone_binary, 'copy',
                local_path,
                f'{config_name}:{remote_path}',
                '--config', config_path,
                '--progress',
                '--stats', '1s'
            ]
            
            self.logger.info(f"Starting upload: {local_path} -> {config_name}:{remote_path}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )
            
            if result.returncode == 0:
                self.logger.info(f"Upload successful: {local_path}")
                return True, "上传成功"
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                self.logger.error(f"Upload failed: {error_msg}")
                return False, f"上传失败: {error_msg}"
                
        except subprocess.TimeoutExpired:
            return False, "上传超时"
        except Exception as e:
            self.logger.error(f"Upload error: {e}")
            return False, f"上传失败: {str(e)}"
    
    def download_file(self, remote_path: str, local_path: str, config_name: str) -> Tuple[bool, str]:
        """从远程存储下载文件"""
        try:
            config_path = self.get_config_path(config_name)
            if not os.path.exists(config_path):
                return False, "配置文件不存在"
            
            # 确保本地目录存在
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            cmd = [
                self.rclone_binary, 'copy',
                f'{config_name}:{remote_path}',
                local_path,
                '--config', config_path,
                '--progress'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            if result.returncode == 0:
                self.logger.info(f"Download successful: {remote_path}")
                return True, "下载成功"
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                self.logger.error(f"Download failed: {error_msg}")
                return False, f"下载失败: {error_msg}"
                
        except subprocess.TimeoutExpired:
            return False, "下载超时"
        except Exception as e:
            self.logger.error(f"Download error: {e}")
            return False, f"下载失败: {str(e)}"
    
    def list_files(self, remote_path: str, config_name: str) -> Tuple[bool, List[Dict], str]:
        """列出远程文件"""
        try:
            config_path = self.get_config_path(config_name)
            if not os.path.exists(config_path):
                return False, [], "配置文件不存在"
            
            cmd = [
                self.rclone_binary, 'lsjson',
                f'{config_name}:{remote_path}',
                '--config', config_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                files = json.loads(result.stdout) if result.stdout.strip() else []
                return True, files, "获取成功"
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                return False, [], f"获取失败: {error_msg}"
                
        except json.JSONDecodeError:
            return False, [], "解析文件列表失败"
        except subprocess.TimeoutExpired:
            return False, [], "获取文件列表超时"
        except Exception as e:
            self.logger.error(f"List files error: {e}")
            return False, [], f"获取失败: {str(e)}"
    
    def delete_config(self, config_name: str) -> bool:
        """删除rclone配置"""
        try:
            config_path = self.get_config_path(config_name)
            if os.path.exists(config_path):
                os.remove(config_path)
                self.logger.info(f"Deleted rclone config: {config_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete config {config_name}: {e}")
            return False
    
    def get_supported_types(self) -> List[Dict[str, str]]:
        """获取支持的存储类型"""
        return [
            {'value': 's3', 'label': 'Amazon S3'},
            {'value': 'google_drive', 'label': 'Google Drive'},
            {'value': 'onedrive', 'label': 'Microsoft OneDrive'},
            {'value': 'dropbox', 'label': 'Dropbox'},
            {'value': 'ftp', 'label': 'FTP'},
            {'value': 'sftp', 'label': 'SFTP'},
        ]
