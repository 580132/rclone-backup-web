import os
import base64
import json
import logging
from typing import Dict, Any, Optional, Tuple
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

class EncryptionService:
    """数据加密服务类"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.backend = default_backend()
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """从密码派生加密密钥"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # AES-256需要32字节密钥
            salt=salt,
            iterations=100000,  # 迭代次数
            backend=self.backend
        )
        return kdf.derive(password.encode('utf-8'))
    
    def encrypt_data(self, data: Any, password: str) -> Tuple[bool, str]:
        """加密数据"""
        try:
            # 将数据转换为JSON字符串
            if isinstance(data, (dict, list)):
                json_data = json.dumps(data, ensure_ascii=False)
            else:
                json_data = str(data)
            
            # 生成随机盐和IV
            salt = os.urandom(16)  # 16字节盐
            iv = os.urandom(12)    # GCM模式需要12字节IV
            
            # 派生密钥
            key = self._derive_key(password, salt)
            
            # 创建加密器
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv),
                backend=self.backend
            )
            encryptor = cipher.encryptor()
            
            # 加密数据
            ciphertext = encryptor.update(json_data.encode('utf-8')) + encryptor.finalize()
            
            # 组合加密结果
            encrypted_data = {
                'salt': base64.b64encode(salt).decode('utf-8'),
                'iv': base64.b64encode(iv).decode('utf-8'),
                'tag': base64.b64encode(encryptor.tag).decode('utf-8'),
                'ciphertext': base64.b64encode(ciphertext).decode('utf-8')
            }
            
            # 返回base64编码的加密数据
            encrypted_json = json.dumps(encrypted_data)
            return True, base64.b64encode(encrypted_json.encode('utf-8')).decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt data: {e}")
            return False, str(e)
    
    def decrypt_data(self, encrypted_data: str, password: str) -> Tuple[bool, Any, str]:
        """解密数据"""
        try:
            # 解码base64
            encrypted_json = base64.b64decode(encrypted_data.encode('utf-8')).decode('utf-8')
            encrypted_dict = json.loads(encrypted_json)
            
            # 提取加密组件
            salt = base64.b64decode(encrypted_dict['salt'])
            iv = base64.b64decode(encrypted_dict['iv'])
            tag = base64.b64decode(encrypted_dict['tag'])
            ciphertext = base64.b64decode(encrypted_dict['ciphertext'])
            
            # 派生密钥
            key = self._derive_key(password, salt)
            
            # 创建解密器
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv, tag),
                backend=self.backend
            )
            decryptor = cipher.decryptor()
            
            # 解密数据
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # 尝试解析JSON
            try:
                decrypted_data = json.loads(plaintext.decode('utf-8'))
                return True, decrypted_data, ""
            except json.JSONDecodeError:
                # 如果不是JSON，返回字符串
                return True, plaintext.decode('utf-8'), ""
                
        except Exception as e:
            self.logger.error(f"Failed to decrypt data: {e}")
            return False, None, str(e)
    
    def encrypt_sensitive_fields(self, data: Dict[str, Any], password: str, 
                               sensitive_fields: list = None) -> Tuple[bool, Dict[str, Any], str]:
        """加密字典中的敏感字段"""
        try:
            if sensitive_fields is None:
                # 默认的敏感字段列表
                sensitive_fields = [
                    'password', 'secret', 'key', 'token', 'credentials',
                    'access_key', 'secret_key', 'secret_access_key',
                    'client_secret', 'private_key', 'pass', 'key_pass'
                ]
            
            encrypted_data = data.copy()
            
            for field in sensitive_fields:
                if field in encrypted_data and encrypted_data[field]:
                    success, encrypted_value = self.encrypt_data(encrypted_data[field], password)
                    if success:
                        encrypted_data[field] = {
                            '_encrypted': True,
                            '_value': encrypted_value
                        }
                    else:
                        self.logger.warning(f"Failed to encrypt field {field}: {encrypted_value}")
            
            return True, encrypted_data, ""
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt sensitive fields: {e}")
            return False, data, str(e)
    
    def decrypt_sensitive_fields(self, data: Dict[str, Any], password: str) -> Tuple[bool, Dict[str, Any], str]:
        """解密字典中的敏感字段"""
        try:
            decrypted_data = data.copy()
            
            for key, value in data.items():
                if isinstance(value, dict) and value.get('_encrypted'):
                    success, decrypted_value, error = self.decrypt_data(value['_value'], password)
                    if success:
                        decrypted_data[key] = decrypted_value
                    else:
                        return False, data, f"Failed to decrypt field {key}: {error}"
            
            return True, decrypted_data, ""
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt sensitive fields: {e}")
            return False, data, str(e)
    
    def is_encrypted_field(self, value: Any) -> bool:
        """检查字段是否为加密字段"""
        return isinstance(value, dict) and value.get('_encrypted') is True
    
    def get_encryption_info(self, encrypted_data: str) -> Optional[Dict[str, Any]]:
        """获取加密数据的信息（不解密）"""
        try:
            encrypted_json = base64.b64decode(encrypted_data.encode('utf-8')).decode('utf-8')
            encrypted_dict = json.loads(encrypted_json)
            
            return {
                'has_salt': 'salt' in encrypted_dict,
                'has_iv': 'iv' in encrypted_dict,
                'has_tag': 'tag' in encrypted_dict,
                'has_ciphertext': 'ciphertext' in encrypted_dict,
                'ciphertext_length': len(base64.b64decode(encrypted_dict.get('ciphertext', '')))
            }
        except Exception as e:
            self.logger.error(f"Failed to get encryption info: {e}")
            return None
