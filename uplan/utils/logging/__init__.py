"""
uplan 로깅 유틸리티의 메인 진입점.

이 모듈은 로깅 설정, 포맷터, 트레이싱 데코레이터 등
세부 구현을 포함하는 하위 모듈들의 주요 기능을 다시 내보냅니다.
"""

# 로거 인스턴스 및 설정 함수 가져오기
from .logging_setup import get_logger, setup_logging

# 트레이싱 데코레이터 가져오기
from .logging_trace import trace

# 명시적으로 다시 내보낼 항목 정의 (선택 사항이지만 권장)
__all__ = [
    "get_logger",
    "setup_logging",  # 필요에 따라 설정 함수도 내보낼 수 있음
    "trace",
]

# 참고: 원래 logging.py에 있던 다른 임포트나 코드는
# 각 기능별 모듈(logging_config, logging_formatter 등)로 이동되었으므로
# 여기서는 더 이상 필요하지 않습니다.
