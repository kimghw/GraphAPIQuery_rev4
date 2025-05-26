"""
캐시 서비스 어댑터

메모리 기반 캐시 서비스를 구현합니다.
인증 상태, 임시 데이터 저장에 사용됩니다.
"""

import json
import time
from typing import Optional

from core.domain.ports import CacheServicePort, LoggerPort


class InMemoryCacheServiceAdapter(CacheServicePort):
    """메모리 기반 캐시 서비스 어댑터"""
    
    def __init__(self, logger: LoggerPort):
        self.logger = logger
        self._cache: dict = {}
        self._expiry: dict = {}
    
    def _is_expired(self, key: str) -> bool:
        """키가 만료되었는지 확인합니다."""
        if key not in self._expiry:
            return False
        
        if time.time() > self._expiry[key]:
            # 만료된 키 삭제
            self._cache.pop(key, None)
            self._expiry.pop(key, None)
            return True
        
        return False
    
    async def get(self, key: str) -> Optional[str]:
        """캐시에서 값을 조회합니다."""
        if self._is_expired(key):
            self.logger.debug(f"캐시 만료: {key}")
            return None
        
        value = self._cache.get(key)
        if value is not None:
            self.logger.debug(f"캐시 조회 성공: {key}")
        else:
            self.logger.debug(f"캐시 키 없음: {key}")
        
        return value
    
    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """캐시에 값을 저장합니다."""
        self._cache[key] = value
        
        if expire:
            self._expiry[key] = time.time() + expire
        else:
            self._expiry.pop(key, None)
        
        self.logger.debug(f"캐시 저장 성공: {key}, 만료시간: {expire}초")
        return True
    
    async def delete(self, key: str) -> bool:
        """캐시에서 값을 삭제합니다."""
        existed = key in self._cache
        self._cache.pop(key, None)
        self._expiry.pop(key, None)
        
        if existed:
            self.logger.debug(f"캐시 삭제 성공: {key}")
        else:
            self.logger.debug(f"캐시 키 없음 (삭제 시도): {key}")
        
        return existed
    
    async def exists(self, key: str) -> bool:
        """캐시에 키가 존재하는지 확인합니다."""
        if self._is_expired(key):
            return False
        
        exists = key in self._cache
        self.logger.debug(f"캐시 존재 확인: {key} = {exists}")
        return exists
    
    async def get_json(self, key: str) -> Optional[dict]:
        """JSON 형태의 캐시 값을 조회합니다."""
        try:
            value = await self.get(key)
            if value is None:
                return None
            
            return json.loads(value)
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 파싱 실패: {key}, 오류: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"JSON 캐시 조회 실패: {key}, 오류: {str(e)}")
            return None
    
    async def set_json(self, key: str, value: dict, expire: Optional[int] = None) -> bool:
        """JSON 형태로 캐시에 값을 저장합니다."""
        try:
            json_value = json.dumps(value, ensure_ascii=False)
            return await self.set(key, json_value, expire)
            
        except json.JSONEncodeError as e:
            self.logger.error(f"JSON 직렬화 실패: {key}, 오류: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"JSON 캐시 저장 실패: {key}, 오류: {str(e)}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """캐시 값을 증가시킵니다."""
        try:
            current_value = await self.get(key)
            if current_value is None:
                new_value = amount
            else:
                new_value = int(current_value) + amount
            
            await self.set(key, str(new_value))
            self.logger.debug(f"캐시 증가: {key} += {amount} = {new_value}")
            return new_value
            
        except (ValueError, TypeError) as e:
            self.logger.error(f"캐시 증가 실패 (타입 오류): {key}, 오류: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"캐시 증가 실패: {key}, 오류: {str(e)}")
            return None
    
    async def expire(self, key: str, seconds: int) -> bool:
        """캐시 키에 만료 시간을 설정합니다."""
        try:
            if key not in self._cache:
                self.logger.warning(f"캐시 만료시간 설정 실패 (키 없음): {key}")
                return False
            
            self._expiry[key] = time.time() + seconds
            self.logger.debug(f"캐시 만료시간 설정: {key} = {seconds}초")
            return True
            
        except Exception as e:
            self.logger.error(f"캐시 만료시간 설정 실패: {key}, 오류: {str(e)}")
            return False
    
    async def ttl(self, key: str) -> Optional[int]:
        """캐시 키의 남은 만료 시간을 조회합니다."""
        try:
            if key not in self._cache:
                self.logger.debug(f"캐시 TTL 없음 (키 없음): {key}")
                return None
            
            if key not in self._expiry:
                self.logger.debug(f"캐시 TTL 없음 (만료시간 미설정): {key}")
                return None
            
            remaining = int(self._expiry[key] - time.time())
            if remaining <= 0:
                # 만료된 키 정리
                self._cache.pop(key, None)
                self._expiry.pop(key, None)
                self.logger.debug(f"캐시 TTL 만료: {key}")
                return None
            
            self.logger.debug(f"캐시 TTL: {key} = {remaining}초")
            return remaining
                
        except Exception as e:
            self.logger.error(f"캐시 TTL 조회 실패: {key}, 오류: {str(e)}")
            return None
    
    async def ping(self) -> bool:
        """캐시 서비스 상태를 확인합니다."""
        try:
            # 간단한 테스트 키로 동작 확인
            test_key = "__ping_test__"
            await self.set(test_key, "ping", expire=1)
            result = await self.get(test_key)
            await self.delete(test_key)
            
            if result == "ping":
                self.logger.debug("캐시 서비스 연결 정상")
                return True
            else:
                self.logger.warning("캐시 서비스 연결 실패")
                return False
                
        except Exception as e:
            self.logger.error(f"캐시 서비스 연결 확인 실패: {str(e)}")
            return False
    
    async def close(self):
        """캐시 서비스 연결을 종료합니다."""
        try:
            self._cache.clear()
            self._expiry.clear()
            self.logger.debug("캐시 서비스 종료")
        except Exception as e:
            self.logger.error(f"캐시 서비스 종료 실패: {str(e)}")


# 기본 캐시 서비스 어댑터 (InMemory 사용)
CacheServiceAdapter = InMemoryCacheServiceAdapter
