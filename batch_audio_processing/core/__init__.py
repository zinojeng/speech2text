"""
批次音訊處理系統 - 核心模組
Core modules for batch audio processing system

包含系統的核心功能：
- 資料模型和配置
- 錯誤處理和恢復
- 進度追蹤和監控
- 日誌記錄系統
"""

from .models import (
    ProcessingConfig,
    APIConfig,
    FileInfo,
    TranscriptionResult,
    SummaryResult,
    DiscoveryResult,
    TranscriptionModel,
    OutputFormat,
    SummaryModel
)

from .error_handler import (
    ErrorHandler,
    ErrorType,
    ErrorSeverity,
    ErrorInfo,
    RetryConfig,
    create_default_error_handler
)

from .progress_tracker import (
    ProgressTracker,
    ProcessingStage,
    TaskStatus,
    TaskProgress,
    BatchProgress,
    create_progress_tracker
)

from .logging_system import (
    LoggingSystem,
    StructuredLogger,
    PerformanceMonitor,
    LogLevel,
    create_logging_system
)

__all__ = [
    # 模型
    "ProcessingConfig",
    "APIConfig",
    "FileInfo", 
    "TranscriptionResult",
    "SummaryResult",
    "DiscoveryResult",
    "TranscriptionModel",
    "OutputFormat",
    "SummaryModel",
    
    # 錯誤處理
    "ErrorHandler",
    "ErrorType",
    "ErrorSeverity", 
    "ErrorInfo",
    "RetryConfig",
    "create_default_error_handler",
    
    # 進度追蹤
    "ProgressTracker",
    "ProcessingStage",
    "TaskStatus",
    "TaskProgress",
    "BatchProgress", 
    "create_progress_tracker",
    
    # 日誌系統
    "LoggingSystem",
    "StructuredLogger",
    "PerformanceMonitor",
    "LogLevel",
    "create_logging_system"
]