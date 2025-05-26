"""
캐시 서비스 어댑터

Redis 기반 캐시 서비스를 구현합니다.
인증 상태, 임시 데이터 저장에 사용됩니다.
"""

import json
from typing import Optional

import redis.asyncio as redis

from core.domain.ports import CacheServicePort, LoggerPort


class CacheServiceAdapter(CacheServicePort):
    """Redis 기반 캐시 서비스 어댑터"""
    
    def __init__(self, redis_url: str, logger: LoggerPort):
        self.logger = logger
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        """Redis 연결을 가져옵니다."""
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
        return self._redis
    
    async def get(self, key: str) -> Optional[str]:
        """캐시에서 값을 조회합니다."""
        try:
            redis_client = await self._get_redis()
            value = await redis_client.get(key)
            
            if value is not None:
                self.logger.debug(f"캐시 조회 성공: {key}")
            else:
                self.logger.debug(f"캐시 키 없음: {key}")
            
            return value
            
        except Exception as e:
            self.logger.error(f"캐시 조회 실패: {key}, 오류: {str(e)}")
            return None
    
    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """캐시에 값을 저장합니다."""
        try:
            redis_client = await self._get_redis()
            
            if expire:
                result = await redis_client.setex(key, expire, value)
            else:
                result = await redis_client.set(key, value)
            
            if result:
                self.logger.debug(f"캐시 저장 성공: {key}, 만료시간: {expire}초")
            else:
                self.logger.warning(f"캐시 저장 실패: {key}")
            
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"캐시 저장 실패: {key}, 오류: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """캐시에서 값을 삭제합니다."""
        try:
            redis_client = await self._get_redis()
            result = await redis_client.delete(key)
            
            if result > 0:
                self.logger.debug(f"캐시 삭제 성공: {key}")
                return True
            else:
                self.logger.debug(f"캐시 키 없음 (삭제 시도): {key}")
                return False
                
        except Exception as e:
            self.logger.error(f"캐시 삭제 실패: {key}, 오류: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """캐시에 키가 존재하는지 확인합니다."""
        try:
            redis_client = await self._get_redis()
            result = await redis_client.exists(key)
            
            exists = result > 0
            self.logger.debug(f"캐시 존재 확인: {key} = {exists}")
            
            return exists
            
        except Exception as e:
            self.logger.error(f"캐시 존재 확인 실패: {key}, 오류: {str(e)}")
            return False
    
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
            redis_client = await self._get_redis()
            result = await redis_client.incrby(key, amount)
            
            self.logger.debug(f"캐시 증가: {key} += {amount} = {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"캐시 증가 실패: {key}, 오류: {str(e)}")
            return None
    
    async def expire(self, key: str, seconds: int) -> bool:
        """캐시 키에 만료 시간을 설정합니다."""
        try:
            redis_client = await self._get_redis()
            result = await redis_client.expire(key, seconds)
            
            if result:
                self.logger.debug(f"캐시 만료시간 설정: {key} = {seconds}초")
            else:
                self.logger.warning(f"캐시 만료시간 설정 실패: {key}")
            
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"캐시 만료시간 설정 실패: {key}, 오류: {str(e)}")
            return False
    
    async def ttl(self, key: str) -> Optional[int]:
        """캐시 키의 남은 만료 시간을 조회합니다."""
        try:
            redis_client = await self._get_redis()
            result = await redis_client.ttl(key)
            
            # -2: 키가 존재하지 않음, -1: 만료시간이 설정되지 않음
            if result >= 0:
                self.logger.debug(f"캐시 TTL: {key} = {result}초")
                return result
            else:
                self.logger.debug(f"캐시 TTL 없음: {key} = {result}")
                return None
                
        except Exception as e:
            self.logger.error(f"캐시 TTL 조회 실패: {key}, 오류: {str(e)}")
            return None
    
    async def ping(self) -> bool:
        """Redis 연결 상태를 확인합니다."""
        try:
            redis_client = await self._get_redis()
            result = await redis_client.ping()
            
            if result:
                self.logger.debug("Redis 연결 정상")
                return True
            else:
                self.logger.warning("Redis 연결 실패")
                return False
                
        except Exception as e:
            self.logger.error(f"Redis 연결 확인 실패: {str(e)}")
            return False
    
    async def close(self):
        """Redis 연결을 종료합니다."""
        if self._redis:
            try:
                await self._redis.close()
                self.logger.debug("Redis 연결 종료")
            except Exception as e:
                self.logger.error(f"Redis 연결 종료 실패: {str(e)}")
            finally:
                self._redis = None


class InMemoryCacheServiceAdapter(CacheServicePort):
    """메모리 기반 캐시 서비스 어댑터 (개발/테스트용)"""
    
    def __init__(self, logger: LoggerPort):
        self.logger = logger
        self._cache: dict = {}
        self._expiry: dict = {}
    
    def _is_expired(self, key: str) -> bool:
        """키가 만료되었는지 확인합니다."""
        import time
        
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
        import time
        
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
