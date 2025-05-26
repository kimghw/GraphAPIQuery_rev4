"""
암호화 서비스 어댑터

토큰 및 민감한 데이터의 암호화/복호화를 담당하는 어댑터입니다.
Fernet 대칭 암호화를 사용합니다.
"""

import base64
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from core.domain.ports import EncryptionServicePort, LoggerPort


class EncryptionServiceAdapter(EncryptionServicePort):
    """암호화 서비스 어댑터"""
    
    def __init__(self, encryption_key: str, logger: LoggerPort):
        self.logger = logger
        self._fernet = self._create_fernet(encryption_key)
    
    def _create_fernet(self, password: str) -> Fernet:
        """암호화 키로부터 Fernet 인스턴스를 생성합니다."""
        # 고정된 salt 사용 (실제 운영에서는 계정별로 다른 salt 사용 권장)
        salt = b'graph_api_salt_2024'
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)
    
    async def encrypt(self, data: str) -> str:
        """데이터를 암호화합니다."""
        try:
            if not data:
                return ""
            
            encrypted_data = self._fernet.encrypt(data.encode())
            result = base64.urlsafe_b64encode(encrypted_data).decode()
            
            self.logger.debug("데이터 암호화 성공")
            return result
            
        except Exception as e:
            self.logger.error(f"데이터 암호화 실패: {str(e)}")
            raise Exception(f"암호화 실패: {str(e)}")
    
    async def decrypt(self, encrypted_data: str) -> str:
        """암호화된 데이터를 복호화합니다."""
        try:
            if not encrypted_data:
                return ""
            
            # Base64 디코딩
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            
            # 복호화
            decrypted_data = self._fernet.decrypt(encrypted_bytes)
            result = decrypted_data.decode()
            
            self.logger.debug("데이터 복호화 성공")
            return result
            
        except Exception as e:
            self.logger.error(f"데이터 복호화 실패: {str(e)}")
            raise Exception(f"복호화 실패: {str(e)}")
    
    def verify_key(self, test_data: str = "test_encryption") -> bool:
        """암호화 키가 올바른지 검증합니다."""
        try:
            # 테스트 데이터 암호화/복호화
            encrypted = self._fernet.encrypt(test_data.encode())
            decrypted = self._fernet.decrypt(encrypted).decode()
            
            return decrypted == test_data
            
        except Exception as e:
            self.logger.error(f"암호화 키 검증 실패: {str(e)}")
            return False
