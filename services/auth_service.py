from models import User, db
import logging

class AuthService:
    """认证服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def authenticate(self, username: str, password: str) -> bool:
        """用户认证"""
        try:
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                self.logger.info(f"User {username} authenticated successfully")
                return True
            
            self.logger.warning(f"Authentication failed for user {username}")
            return False
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False
    
    def get_user_by_username(self, username: str) -> User:
        """根据用户名获取用户"""
        return User.query.filter_by(username=username).first()
    
    def get_user_by_id(self, user_id: int) -> User:
        """根据ID获取用户"""
        return User.query.get(user_id)
    
    def create_user(self, username: str, password: str) -> bool:
        """创建用户"""
        try:
            # 检查用户是否已存在
            if User.query.filter_by(username=username).first():
                self.logger.warning(f"User {username} already exists")
                return False
            
            user = User(username=username)
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            self.logger.info(f"User {username} created successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create user {username}: {e}")
            db.session.rollback()
            return False
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """修改密码"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False
            
            if not user.check_password(old_password):
                self.logger.warning(f"Wrong old password for user {user.username}")
                return False
            
            user.set_password(new_password)
            db.session.commit()
            
            self.logger.info(f"Password changed for user {user.username}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to change password: {e}")
            db.session.rollback()
            return False
