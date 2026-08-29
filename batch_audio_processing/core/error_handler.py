"""
批次音訊處理系統 - 錯誤處理和恢復系統
Error Handling and Recovery System for Batch Audio Processing

此模組實作了完整的錯誤處理和恢復機制，包括：
- ErrorHandler 類別：錯誤分類和處理策略
- 指數退避重試機制
- 錯誤記錄和統計
- 錯誤恢復策略

Requirements: 8.1, 8.2, 8.3, 8.4
"""

import time
import logging
import traceback
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable, Type
from enum import Enum
from pathlib import Path
import json
from datetime import datetime
import random

# 設定日誌
logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """錯誤類型分類"""
    FILE_ERROR = "file_error"
    API_ERROR = "api_error"
    PROCESSING_ERROR = "processing_error"
    NETWORK_ERROR = "network_error"
    PERMISSION_ERROR = "permission_error"
    VALIDATION_ERROR = "validation_error"
    SYSTEM_ERROR = "system_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorSeverity(Enum):
    """錯誤嚴重程度"""
    LOW = "low"          # 可忽略的錯誤
    MEDIUM = "medium"    # 需要注意但不影響整體處理
    HIGH = "high"        # 影響單個檔案處理
    CRITICAL = "critical" # 影響整個批次處理


class RetryStrategy(Enum):
    """重試策略"""
    NO_RETRY = "no_retry"
    IMMEDIATE = "immediate"
    LINEAR_BACKOFF = "linear_backoff"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    CUSTOM = "custom"


@dataclass
class ErrorInfo:
    """錯誤資訊類別"""
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    exception: Optional[Exception] = None
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    file_path: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'error_type': self.error_type.value,
            'severity': self.severity.value,
            'message': self.message,
            'exception_type': type(self.exception).__name__ if self.exception else None,
            'exception_str': str(self.exception) if self.exception else None,
            'context': self.context,
            'timestamp': self.timestamp.isoformat(),
            'file_path': self.file_path,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }


@dataclass
class RetryConfig:
    """重試配置"""
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    
    def calculate_delay(self, attempt: int) -> float:
        """計算重試延遲時間"""
        if self.strategy == RetryStrategy.NO_RETRY:
            return 0.0
        elif self.strategy == RetryStrategy.IMMEDIATE:
            return 0.0
        elif self.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.base_delay * attempt
        elif self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.base_delay * (self.backoff_multiplier ** (attempt - 1))
        else:
            delay = self.base_delay
        
        # 限制最大延遲時間
        delay = min(delay, self.max_delay)
        
        # 添加隨機抖動以避免雷群效應
        if self.jitter and delay > 0:
            jitter_range = delay * 0.1  # 10% 的抖動
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0.0, delay)


@dataclass
class ErrorStatistics:
    """錯誤統計資訊"""
    total_errors: int = 0
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    errors_by_severity: Dict[str, int] = field(default_factory=dict)
    errors_by_file: Dict[str, int] = field(default_factory=dict)
    retry_statistics: Dict[str, int] = field(default_factory=dict)
    recovery_success_rate: float = 0.0
    
    def add_error(self, error_info: ErrorInfo):
        """添加錯誤到統計中"""
        self.total_errors += 1
        
        # 按類型統計
        error_type = error_info.error_type.value
        self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1
        
        # 按嚴重程度統計
        severity = error_info.severity.value
        self.errors_by_severity[severity] = self.errors_by_severity.get(severity, 0) + 1
        
        # 按檔案統計
        if error_info.file_path:
            self.errors_by_file[error_info.file_path] = self.errors_by_file.get(error_info.file_path, 0) + 1
        
        # 重試統計
        if error_info.retry_count > 0:
            retry_key = f"retry_{error_info.retry_count}"
            self.retry_statistics[retry_key] = self.retry_statistics.get(retry_key, 0) + 1
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'total_errors': self.total_errors,
            'errors_by_type': self.errors_by_type,
            'errors_by_severity': self.errors_by_severity,
            'errors_by_file': self.errors_by_file,
            'retry_statistics': self.retry_statistics,
            'recovery_success_rate': self.recovery_success_rate
        }


class ErrorHandler:
    """
    錯誤處理器類別
    
    提供完整的錯誤處理和恢復機制，包括：
    - 錯誤分類和處理策略
    - 指數退避重試機制
    - 錯誤記錄和統計
    
    Requirements: 8.1, 8.2, 8.3, 8.4
    """
    
    def __init__(self, retry_config: Optional[RetryConfig] = None):
        """
        初始化錯誤處理器
        
        Args:
            retry_config: 重試配置，如果未提供則使用預設配置
        """
        self.retry_config = retry_config or RetryConfig()
        self.error_log: List[ErrorInfo] = []
        self.statistics = ErrorStatistics()
        self.error_handlers: Dict[ErrorType, Callable] = {}
        self.recovery_strategies: Dict[ErrorType, Callable] = {}
        
        # 註冊預設的錯誤處理器
        self._register_default_handlers()
        
        logger.info("ErrorHandler 初始化完成")
    
    def _register_default_handlers(self):
        """註冊預設的錯誤處理器"""
        self.error_handlers = {
            ErrorType.FILE_ERROR: self._handle_file_error,
            ErrorType.API_ERROR: self._handle_api_error,
            ErrorType.PROCESSING_ERROR: self._handle_processing_error,
            ErrorType.NETWORK_ERROR: self._handle_network_error,
            ErrorType.PERMISSION_ERROR: self._handle_permission_error,
            ErrorType.VALIDATION_ERROR: self._handle_validation_error,
            ErrorType.SYSTEM_ERROR: self._handle_system_error,
            ErrorType.UNKNOWN_ERROR: self._handle_unknown_error
        }
        
        self.recovery_strategies = {
            ErrorType.FILE_ERROR: self._recover_file_error,
            ErrorType.API_ERROR: self._recover_api_error,
            ErrorType.PROCESSING_ERROR: self._recover_processing_error,
            ErrorType.NETWORK_ERROR: self._recover_network_error,
            ErrorType.PERMISSION_ERROR: self._recover_permission_error
        }
    
    def classify_error(self, exception: Exception, context: Dict[str, Any] = None) -> ErrorInfo:
        """
        分類錯誤並創建 ErrorInfo
        
        Args:
            exception: 發生的異常
            context: 錯誤上下文資訊
            
        Returns:
            分類後的錯誤資訊
        """
        context = context or {}
        
        # 根據異常類型分類錯誤
        error_type, severity = self._classify_exception(exception)
        
        # 創建錯誤資訊
        error_info = ErrorInfo(
            error_type=error_type,
            severity=severity,
            message=str(exception),
            exception=exception,
            context=context,
            file_path=context.get('file_path'),
            max_retries=self.retry_config.max_attempts
        )
        
        logger.debug(f"錯誤分類完成: {error_type.value} - {severity.value}")
        return error_info
    
    def _classify_exception(self, exception: Exception) -> tuple[ErrorType, ErrorSeverity]:
        """
        根據異常類型分類錯誤
        
        Args:
            exception: 異常物件
            
        Returns:
            錯誤類型和嚴重程度的元組
        """
        exception_name = type(exception).__name__
        exception_str = str(exception).lower()
        
        # 檔案相關錯誤
        if isinstance(exception, (FileNotFoundError, IsADirectoryError, NotADirectoryError)):
            return ErrorType.FILE_ERROR, ErrorSeverity.HIGH
        
        # 權限相關錯誤
        if isinstance(exception, PermissionError):
            return ErrorType.PERMISSION_ERROR, ErrorSeverity.HIGH
        
        # 網路相關錯誤
        if isinstance(exception, ConnectionError) or any(keyword in exception_str for keyword in ['connection', 'timeout', 'network', 'dns']):
            return ErrorType.NETWORK_ERROR, ErrorSeverity.MEDIUM
        
        # API 相關錯誤
        if any(keyword in exception_str for keyword in ['api', 'key', 'quota', 'rate limit', 'unauthorized']):
            return ErrorType.API_ERROR, ErrorSeverity.HIGH
        
        # 驗證相關錯誤
        if isinstance(exception, ValueError) or 'validation' in exception_str:
            return ErrorType.VALIDATION_ERROR, ErrorSeverity.MEDIUM
        
        # 處理相關錯誤
        if any(keyword in exception_str for keyword in ['processing', 'conversion', 'format']):
            return ErrorType.PROCESSING_ERROR, ErrorSeverity.MEDIUM
        
        # 系統相關錯誤
        if isinstance(exception, (OSError, SystemError, MemoryError)):
            return ErrorType.SYSTEM_ERROR, ErrorSeverity.CRITICAL
        
        # 未知錯誤
        return ErrorType.UNKNOWN_ERROR, ErrorSeverity.MEDIUM
    
    def handle_error(self, exception: Exception, context: Dict[str, Any] = None) -> ErrorInfo:
        """
        處理錯誤的主要入口點
        
        Args:
            exception: 發生的異常
            context: 錯誤上下文資訊
            
        Returns:
            處理後的錯誤資訊
        """
        # 分類錯誤
        error_info = self.classify_error(exception, context)
        
        # 記錄錯誤
        self._log_error(error_info)
        
        # 添加到統計
        self.statistics.add_error(error_info)
        
        # 呼叫對應的錯誤處理器
        if error_info.error_type in self.error_handlers:
            try:
                self.error_handlers[error_info.error_type](error_info)
            except Exception as handler_error:
                logger.error(f"錯誤處理器執行失敗: {handler_error}")
        
        return error_info
    
    def should_retry(self, error_info: ErrorInfo) -> bool:
        """
        判斷是否應該重試
        
        Args:
            error_info: 錯誤資訊
            
        Returns:
            是否應該重試
        """
        # 檢查重試次數
        if error_info.retry_count >= self.retry_config.max_attempts:
            return False
        
        # 檢查錯誤類型是否支援重試
        non_retryable_types = {
            ErrorType.VALIDATION_ERROR,
            ErrorType.PERMISSION_ERROR
        }
        
        if error_info.error_type in non_retryable_types:
            return False
        
        # 檢查嚴重程度
        if error_info.severity == ErrorSeverity.CRITICAL:
            return False
        
        return True
    
    def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """
        使用退避策略重試函數
        
        Args:
            func: 要重試的函數
            *args: 函數參數
            **kwargs: 函數關鍵字參數
            
        Returns:
            函數執行結果
            
        Raises:
            最後一次執行的異常
        """
        last_exception = None
        
        for attempt in range(1, self.retry_config.max_attempts + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 1:
                    logger.info(f"重試成功，嘗試次數: {attempt}")
                return result
                
            except Exception as e:
                last_exception = e
                error_info = self.classify_error(e, {'attempt': attempt})
                
                if not self.should_retry(error_info):
                    logger.error(f"錯誤不可重試: {e}")
                    break
                
                if attempt < self.retry_config.max_attempts:
                    delay = self.retry_config.calculate_delay(attempt)
                    logger.warning(f"重試 {attempt}/{self.retry_config.max_attempts} 失敗: {e}")
                    logger.info(f"等待 {delay:.2f} 秒後重試...")
                    
                    if delay > 0:
                        time.sleep(delay)
                else:
                    logger.error(f"所有重試嘗試都失敗了: {e}")
        
        # 記錄最終失敗
        if last_exception:
            self.handle_error(last_exception, {'final_attempt': True})
            raise last_exception
    
    def attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """
        嘗試錯誤恢復
        
        Args:
            error_info: 錯誤資訊
            
        Returns:
            恢復是否成功
        """
        if error_info.error_type in self.recovery_strategies:
            try:
                recovery_func = self.recovery_strategies[error_info.error_type]
                success = recovery_func(error_info)
                
                if success:
                    logger.info(f"錯誤恢復成功: {error_info.error_type.value}")
                    return True
                else:
                    logger.warning(f"錯誤恢復失敗: {error_info.error_type.value}")
                    
            except Exception as recovery_error:
                logger.error(f"錯誤恢復過程中發生異常: {recovery_error}")
        
        return False
    
    def _log_error(self, error_info: ErrorInfo):
        """記錄錯誤到日誌和內部列表"""
        self.error_log.append(error_info)
        
        # 根據嚴重程度選擇日誌級別
        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"嚴重錯誤: {error_info.message}")
        elif error_info.severity == ErrorSeverity.HIGH:
            logger.error(f"高級錯誤: {error_info.message}")
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"中級錯誤: {error_info.message}")
        else:
            logger.info(f"低級錯誤: {error_info.message}")
        
        # 記錄詳細資訊
        if error_info.exception:
            logger.debug(f"異常詳情: {traceback.format_exc()}")
    
    # 預設錯誤處理器
    def _handle_file_error(self, error_info: ErrorInfo):
        """處理檔案相關錯誤"""
        logger.debug(f"處理檔案錯誤: {error_info.message}")
        
        # 檢查檔案是否存在
        if error_info.file_path and not Path(error_info.file_path).exists():
            logger.error(f"檔案不存在: {error_info.file_path}")
    
    def _handle_api_error(self, error_info: ErrorInfo):
        """處理 API 相關錯誤"""
        logger.debug(f"處理 API 錯誤: {error_info.message}")
        
        # 檢查是否為配額限制
        if 'quota' in error_info.message.lower() or 'rate limit' in error_info.message.lower():
            logger.warning("API 配額或速率限制，建議增加延遲時間")
    
    def _handle_processing_error(self, error_info: ErrorInfo):
        """處理處理相關錯誤"""
        logger.debug(f"處理處理錯誤: {error_info.message}")
    
    def _handle_network_error(self, error_info: ErrorInfo):
        """處理網路相關錯誤"""
        logger.debug(f"處理網路錯誤: {error_info.message}")
    
    def _handle_permission_error(self, error_info: ErrorInfo):
        """處理權限相關錯誤"""
        logger.debug(f"處理權限錯誤: {error_info.message}")
    
    def _handle_validation_error(self, error_info: ErrorInfo):
        """處理驗證相關錯誤"""
        logger.debug(f"處理驗證錯誤: {error_info.message}")
    
    def _handle_system_error(self, error_info: ErrorInfo):
        """處理系統相關錯誤"""
        logger.debug(f"處理系統錯誤: {error_info.message}")
    
    def _handle_unknown_error(self, error_info: ErrorInfo):
        """處理未知錯誤"""
        logger.debug(f"處理未知錯誤: {error_info.message}")
    
    # 預設恢復策略
    def _recover_file_error(self, error_info: ErrorInfo) -> bool:
        """嘗試恢復檔案錯誤"""
        if error_info.file_path:
            # 嘗試創建父目錄
            try:
                parent_dir = Path(error_info.file_path).parent
                parent_dir.mkdir(parents=True, exist_ok=True)
                return True
            except Exception:
                pass
        return False
    
    def _recover_api_error(self, error_info: ErrorInfo) -> bool:
        """嘗試恢復 API 錯誤"""
        # 對於 API 錯誤，主要依賴重試機制
        return False
    
    def _recover_processing_error(self, error_info: ErrorInfo) -> bool:
        """嘗試恢復處理錯誤"""
        return False
    
    def _recover_network_error(self, error_info: ErrorInfo) -> bool:
        """嘗試恢復網路錯誤"""
        # 網路錯誤通常需要等待，依賴重試機制
        return False
    
    def _recover_permission_error(self, error_info: ErrorInfo) -> bool:
        """嘗試恢復權限錯誤"""
        # 權限錯誤通常無法自動恢復
        return False
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        取得錯誤摘要
        
        Returns:
            錯誤摘要字典
        """
        return {
            'total_errors': len(self.error_log),
            'statistics': self.statistics.to_dict(),
            'recent_errors': [error.to_dict() for error in self.error_log[-10:]]  # 最近 10 個錯誤
        }
    
    def export_error_log(self, file_path: str):
        """
        匯出錯誤日誌到檔案
        
        Args:
            file_path: 匯出檔案路徑
        """
        try:
            error_data = {
                'export_time': datetime.now().isoformat(),
                'total_errors': len(self.error_log),
                'statistics': self.statistics.to_dict(),
                'errors': [error.to_dict() for error in self.error_log]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(error_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"錯誤日誌已匯出到: {file_path}")
            
        except Exception as e:
            logger.error(f"匯出錯誤日誌失敗: {e}")
    
    def clear_error_log(self):
        """清除錯誤日誌"""
        self.error_log.clear()
        self.statistics = ErrorStatistics()
        logger.info("錯誤日誌已清除")


def create_default_error_handler() -> ErrorHandler:
    """
    創建預設的錯誤處理器
    
    Returns:
        預設配置的 ErrorHandler 實例
    """
    retry_config = RetryConfig(
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        max_attempts=3,
        base_delay=1.0,
        max_delay=60.0,
        backoff_multiplier=2.0,
        jitter=True
    )
    
    return ErrorHandler(retry_config)


if __name__ == "__main__":
    """測試錯誤處理器功能"""
    # 設定日誌
    logging.basicConfig(level=logging.INFO)
    
    print("=== 錯誤處理器測試 ===\n")
    
    # 創建錯誤處理器
    error_handler = create_default_error_handler()
    
    # 測試錯誤分類
    print("1. 測試錯誤分類...")
    test_exceptions = [
        FileNotFoundError("檔案不存在"),
        PermissionError("權限不足"),
        ValueError("無效的參數"),
        ConnectionError("網路連線失敗"),
        Exception("未知錯誤")
    ]
    
    for exc in test_exceptions:
        error_info = error_handler.classify_error(exc)
        print(f"   {type(exc).__name__}: {error_info.error_type.value} - {error_info.severity.value}")
    
    # 測試重試機制
    print("\n2. 測試重試機制...")
    
    def failing_function(fail_count=2):
        """測試用的失敗函數"""
        if not hasattr(failing_function, 'call_count'):
            failing_function.call_count = 0
        
        failing_function.call_count += 1
        
        if failing_function.call_count <= fail_count:
            raise ConnectionError(f"模擬失敗 {failing_function.call_count}")
        
        return f"成功！呼叫次數: {failing_function.call_count}"
    
    try:
        result = error_handler.retry_with_backoff(failing_function, fail_count=2)
        print(f"   重試結果: {result}")
    except Exception as e:
        print(f"   重試最終失敗: {e}")
    
    # 測試錯誤統計
    print("\n3. 測試錯誤統計...")
    summary = error_handler.get_error_summary()
    print(f"   總錯誤數: {summary['total_errors']}")
    print(f"   錯誤類型統計: {summary['statistics']['errors_by_type']}")
    
    print("\n=== 測試完成 ===")