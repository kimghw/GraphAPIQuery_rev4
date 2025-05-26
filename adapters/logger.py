"""
로거 어댑터

Core 레이어의 LoggerPort를 구현하는 Python 표준 로깅 어댑터입니다.
"""

import logging
import sys
from typing import Any

from core.domain.ports import LoggerPort


class LoggerAdapter(LoggerPort):
    """Python 표준 로깅을 사용하는 로거 어댑터"""
    
    def __init__(self, name: str = "graphapi", level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # 핸들러가 없으면 콘솔 핸들러 추가
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def info(self, message: str, **kwargs) -> None:
        """정보 로그"""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """경고 로그"""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """오류 로그"""
        self.logger.error(message, extra=kwargs)
    
    def debug(self, message: str, **kwargs) -> None:
        """디버그 로그"""
        self.logger.debug(message, extra=kwargs)


def create_logger(name: str = "graphapi", level: str = "INFO") -> LoggerPort:
    """로거 인스턴스를 생성합니다."""
    return LoggerAdapter(name, level)
