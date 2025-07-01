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
    
    def get_config_path(self, config_name: str = None) -> str:
        """获取配置文件路径"""
        # 使用rclone标准配置文件名
        return os.path.join(self.config_dir, 'rclone.conf')
    
    def create_config(self, name: str, storage_type: str, config_data: Dict) -> bool:
        """创建rclone配置"""
        try:
            config_path = self.get_config_path()
            self.logger.info(f"Creating rclone config '{name}' of type '{storage_type}' at {config_path}")
            self.logger.info(f"Config data: {config_data}")

            # 根据存储类型生成配置内容
            config_content = self._generate_config_content(name, storage_type, config_data)
            if not config_content:
                self.logger.error(f"Failed to generate config content for {name}")
                return False

            self.logger.info(f"Generated config content:\n{config_content}")

            # 读取现有配置文件
            existing_config = ""
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    existing_config = f.read()
                self.logger.info(f"Existing config file size: {len(existing_config)} chars")
            else:
                self.logger.info("No existing config file found")

            # 删除同名配置（如果存在）
            existing_config = self._remove_config_section(existing_config, name)

            # 追加新配置
            new_config = existing_config + "\n" + config_content if existing_config else config_content

            # 写入配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(new_config)

            self.logger.info(f"Successfully created rclone config: {name}")
            self.logger.info(f"Final config file content:\n{new_config}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create rclone config {name}: {e}")
            return False

    def _remove_config_section(self, config_content: str, section_name: str) -> str:
        """从配置内容中删除指定的配置段"""
        lines = config_content.split('\n')
        result_lines = []
        in_target_section = False

        for line in lines:
            line = line.strip()

            # 检查是否是配置段开始
            if line.startswith('[') and line.endswith(']'):
                section = line[1:-1]
                if section == section_name:
                    in_target_section = True
                    continue  # 跳过这一行
                else:
                    in_target_section = False

            # 如果不在目标段中，保留这一行
            if not in_target_section:
                result_lines.append(line)

        return '\n'.join(result_lines).strip()

    def _config_section_exists(self, config_path: str, section_name: str) -> bool:
        """检查配置文件中是否存在指定的配置段"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line == f'[{section_name}]':
                    return True
            return False
        except Exception:
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
                endpoint = config_data['endpoint']
                # 确保endpoint包含https://前缀
                if not endpoint.startswith('https://') and not endpoint.startswith('http://'):
                    endpoint = f"https://{endpoint}"

                return f"""[{name}]
type = s3
provider = Cloudflare
access_key_id = {config_data['access_key']}
secret_access_key = {config_data['secret_key']}
endpoint = {endpoint}
region = auto
"""

            elif storage_type == 'google_drive':
                # Google Drive配置
                config = f"""[{name}]
type = drive
"""
                # 客户端凭据（可选，留空使用rclone默认值）
                if config_data.get('client_id'):
                    config += f"client_id = {config_data['client_id']}\n"
                if config_data.get('client_secret'):
                    config += f"client_secret = {config_data['client_secret']}\n"

                # 服务账户凭据
                if config_data.get('service_account_credentials'):
                    config += f"service_account_credentials = {config_data['service_account_credentials']}\n"

                # 访问范围
                scope = config_data.get('scope', 'drive')
                config += f"scope = {scope}\n"

                # 根文件夹ID
                if config_data.get('root_folder_id'):
                    config += f"root_folder_id = {config_data['root_folder_id']}\n"

                # 如果有访问令牌（OAuth2授权后获得）
                if config_data.get('token'):
                    config += f"token = {config_data['token']}\n"

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
            {'value': 's3', 'label': 'Amazon S3'},
            {'value': 'alibaba_oss', 'label': '阿里云 OSS'},
            {'value': 'cloudflare_r2', 'label': 'Cloudflare R2'},
            {'value': 'google_drive', 'label': 'Google Drive'},
            {'value': 'sftp', 'label': 'SFTP'},
            {'value': 'ftp', 'label': 'FTP'}
        ]
    
    def test_connection(self, config_name: str) -> Tuple[bool, str]:
        """测试rclone连接"""
        try:
            config_path = self.get_config_path()
            self.logger.info(f"Testing connection for {config_name}, config path: {config_path}")

            if not os.path.exists(config_path):
                self.logger.error(f"Config file does not exist: {config_path}")
                return False, "配置文件不存在"

            # 检查配置段是否存在
            if not self._config_section_exists(config_path, config_name):
                self.logger.error(f"Config section '{config_name}' not found in {config_path}")
                return False, f"配置段 '{config_name}' 不存在"

            # 记录配置文件内容（用于调试）
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_content = f.read()
                self.logger.info(f"Config file content:\n{config_content}")
            except Exception as e:
                self.logger.warning(f"Could not read config file for logging: {e}")

            # 对于Cloudflare R2，先验证配置，然后尝试简单的连接测试
            if config_name.find('cloudflare') != -1 or 'r2' in config_name.lower():
                # 第一步：验证配置是否存在
                verify_cmd = [
                    self.rclone_binary, 'config', 'show', config_name,
                    '--config', config_path
                ]

                self.logger.info(f"Verifying config exists: {' '.join(verify_cmd)}")
                verify_result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=10)

                if verify_result.returncode != 0:
                    self.logger.error(f"Config verification failed: {verify_result.stderr}")
                    return False, "配置验证失败"

                self.logger.info(f"Config verification successful, config content:\n{verify_result.stdout}")

                # 第二步：尝试连接测试（允许失败）
                cmd = [
                    self.rclone_binary, 'lsd', f'{config_name}:',
                    '--config', config_path,
                    '--timeout', '15s',
                    '--retries', '1'
                ]
            else:
                # 其他存储类型使用标准测试
                cmd = [
                    self.rclone_binary, 'lsd', f'{config_name}:',
                    '--config', config_path,
                    '--timeout', '30s',
                    '-vv'
                ]

            self.logger.info(f"Executing command: {' '.join(cmd)}")
            
            self.logger.info(f"Starting rclone process with timeout=35s")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=35
            )

            self.logger.info(f"rclone process completed with return code: {result.returncode}")
            self.logger.info(f"rclone stdout: {result.stdout}")
            self.logger.info(f"rclone stderr: {result.stderr}")

            if result.returncode == 0:
                self.logger.info(f"Connection test successful for {config_name}")
                return True, "连接成功"
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                self.logger.error(f"Connection test failed for {config_name}: {error_msg}")

                # 对于Cloudflare R2，如果是权限问题，仍然认为配置是有效的
                if config_name.find('cloudflare') != -1 or 'r2' in config_name.lower():
                    if 'AccessDenied' in error_msg or 'Access Denied' in error_msg:
                        self.logger.info(f"Cloudflare R2 config is valid but has permission issues: {config_name}")
                        return True, "配置有效（权限受限，请检查API Token权限）"
                    elif 'doesn\'t support' in error_msg:
                        self.logger.info(f"Cloudflare R2 config is valid but command not supported: {config_name}")
                        return True, "配置有效（部分功能受限）"

                return False, f"连接失败: {error_msg}"

        except subprocess.TimeoutExpired as e:
            self.logger.error(f"rclone command timed out after 35 seconds for {config_name}")
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
            config_path = self.get_config_path()
            if not os.path.exists(config_path):
                return True  # 配置文件不存在，认为删除成功

            # 读取现有配置
            with open(config_path, 'r', encoding='utf-8') as f:
                existing_config = f.read()

            # 删除指定配置段
            new_config = self._remove_config_section(existing_config, config_name)

            # 写回配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(new_config)

            self.logger.info(f"Deleted rclone config: {config_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete config {config_name}: {e}")
            return False

    def parse_config_file(self) -> Dict[str, Dict[str, str]]:
        """解析rclone配置文件，返回所有配置段"""
        try:
            config_path = self.get_config_path()
            if not os.path.exists(config_path):
                return {}

            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return self._parse_config_content(content)
        except Exception as e:
            self.logger.error(f"Failed to parse config file: {e}")
            return {}

    def get_config_section(self, config_name: str) -> Optional[Dict[str, str]]:
        """获取指定配置段的内容"""
        try:
            all_configs = self.parse_config_file()
            return all_configs.get(config_name)
        except Exception as e:
            self.logger.error(f"Failed to get config section {config_name}: {e}")
            return None

    def _parse_config_content(self, content: str) -> Dict[str, Dict[str, str]]:
        """解析配置文件内容"""
        configs = {}
        current_section = None
        current_config = {}

        for line in content.split('\n'):
            line = line.strip()

            # 跳过空行和注释
            if not line or line.startswith('#') or line.startswith(';'):
                continue

            # 检查是否是配置段开始
            if line.startswith('[') and line.endswith(']'):
                # 保存上一个配置段
                if current_section and current_config:
                    configs[current_section] = current_config

                # 开始新的配置段
                current_section = line[1:-1]
                current_config = {}
            elif current_section and '=' in line:
                # 解析配置项
                key, value = line.split('=', 1)
                current_config[key.strip()] = value.strip()

        # 保存最后一个配置段
        if current_section and current_config:
            configs[current_section] = current_config

        return configs

    def list_config_names(self) -> List[str]:
        """列出所有配置名称"""
        try:
            all_configs = self.parse_config_file()
            return list(all_configs.keys())
        except Exception as e:
            self.logger.error(f"Failed to list config names: {e}")
            return []

    def config_exists_in_file(self, config_name: str) -> bool:
        """检查配置是否存在于rclone配置文件中"""
        try:
            config_names = self.list_config_names()
            return config_name in config_names
        except Exception as e:
            self.logger.error(f"Failed to check config existence: {e}")
            return False

