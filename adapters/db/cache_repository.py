"""
데이터베이스 기반 캐시 Repository 어댑터

Redis 대신 데이터베이스를 사용하여 캐시 기능을 제공합니다.
인증 상태 저장 등에 사용됩니다.
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.domain.ports import CacheServicePort, LoggerPort
from .models import CacheModel


class DatabaseCacheServiceAdapter(CacheServicePort):
    """데이터베이스 기반 캐시 서비스 어댑터"""
    
    def __init__(self, session: AsyncSession, logger: LoggerPort):
        self.session = session
        self.logger = logger
    
    async def get(self, key: str) -> Optional[str]:
        """캐시에서 값을 조회합니다."""
        try:
            # 만료되지 않은 캐시 조회
            stmt = select(CacheModel).where(
                and_(
                    CacheModel.key == key,
                    CacheModel.expires_at > datetime.utcnow()
                )
            )
            result = await self.session.execute(stmt)
            cache_model = result.scalar_one_or_none()
            
            if cache_model:
                self.logger.debug(f"캐시 조회 성공: {key}")
                return cache_model.value
            else:
                self.logger.debug(f"캐시 키 없음 또는 만료: {key}")
                # 만료된 캐시 삭제
                await self._cleanup_expired()
                return None
                
        except Exception as e:
            self.logger.error(f"캐시 조회 실패: {key}, 오류: {str(e)}")
            return None
    
    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """캐시에 값을 저장합니다."""
        try:
            # 만료 시간 계산
            expires_at = None
            if expire:
                expires_at = datetime.utcnow() + timedelta(seconds=expire)
            
            # 기존 캐시 확인
            stmt = select(CacheModel).where(CacheModel.key == key)
            result = await self.session.execute(stmt)
            existing_cache = result.scalar_one_or_none()
            
            if existing_cache:
                # 업데이트
                existing_cache.value = value
                existing_cache.expires_at = expires_at
                existing_cache.updated_at = datetime.utcnow()
            else:
                # 새로 생성
                cache_model = CacheModel(
                    key=key,
                    value=value,
                    expires_at=expires_at
                )
                self.session.add(cache_model)
            
            await self.session.commit()
            
            self.logger.debug(f"캐시 저장 성공: {key}, 만료시간: {expire}초")
            return True
            
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"캐시 저장 실패: {key}, 오류: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """캐시에서 값을 삭제합니다."""
        try:
            stmt = delete(CacheModel).where(CacheModel.key == key)
            result = await self.session.execute(stmt)
            await self.session.commit()
            
            deleted = result.rowcount > 0
            if deleted:
                self.logger.debug(f"캐시 삭제 성공: {key}")
            else:
                self.logger.debug(f"캐시 키 없음 (삭제 시도): {key}")
            
            return deleted
            
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"캐시 삭제 실패: {key}, 오류: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """캐시에 키가 존재하는지 확인합니다."""
        try:
            stmt = select(CacheModel.key).where(
                and_(
                    CacheModel.key == key,
                    CacheModel.expires_at > datetime.utcnow()
                )
            )
            result = await self.session.execute(stmt)
            exists = result.scalar_one_or_none() is not None
            
            self.logger.debug(f"캐시 존재 확인: {key} = {exists}")
            return exists
            
        except Exception as e:
            self.logger.error(f"캐시 존재 확인 실패: {key}, 오류: {str(e)}")
            return False
    
    async def _cleanup_expired(self):
        """만료된 캐시를 정리합니다."""
        try:
            stmt = delete(CacheModel).where(
                CacheModel.expires_at <= datetime.utcnow()
            )
            result = await self.session.execute(stmt)
            await self.session.commit()
            
            if result.rowcount > 0:
                self.logger.debug(f"만료된 캐시 {result.rowcount}개 삭제")
                
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"만료 캐시 정리 실패: {str(e)}")
    
    async def get_json(self, key: str) -> Optional[dict]:
        """JSON 형태의 캐시 값을 조회합니다."""
        import json
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
        import json
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
            stmt = select(CacheModel).where(CacheModel.key == key)
            result = await self.session.execute(stmt)
            cache_model = result.scalar_one_or_none()
            
            if not cache_model:
                self.logger.warning(f"캐시 만료시간 설정 실패 (키 없음): {key}")
                return False
            
            cache_model.expires_at = datetime.utcnow() + timedelta(seconds=seconds)
            cache_model.updated_at = datetime.utcnow()
            await self.session.commit()
            
            self.logger.debug(f"캐시 만료시간 설정: {key} = {seconds}초")
            return True
            
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"캐시 만료시간 설정 실패: {key}, 오류: {str(e)}")
            return False
    
    async def ttl(self, key: str) -> Optional[int]:
        """캐시 키의 남은 만료 시간을 조회합니다."""
        try:
            stmt = select(CacheModel).where(CacheModel.key == key)
            result = await self.session.execute(stmt)
            cache_model = result.scalar_one_or_none()
            
            if not cache_model:
                self.logger.debug(f"캐시 TTL 없음 (키 없음): {key}")
                return None
            
            if not cache_model.expires_at:
                self.logger.debug(f"캐시 TTL 없음 (만료시간 미설정): {key}")
                return None
            
            remaining = int((cache_model.expires_at - datetime.utcnow()).total_seconds())
            if remaining <= 0:
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
            # 데이터베이스 세션은 외부에서 관리되므로 여기서는 정리 작업만 수행
            await self._cleanup_expired()
            self.logger.debug("캐시 서비스 종료")
        except Exception as e:
            self.logger.error(f"캐시 서비스 종료 실패: {str(e)}")
