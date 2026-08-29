"""
批次音訊處理系統
Batch Audio Processing System

一個完整的批次音訊處理解決方案，包括語音轉錄、智能摘要和文件生成功能。

主要功能：
- 批次音訊檔案處理
- 語音轉錄 (OpenAI Whisper)
- 智能摘要 (Google Gemini)
- 文件生成 (Markdown, DOCX)
- 錯誤處理和恢復
- 進度追蹤和監控
- 結構化日誌記錄

使用方式：
    from batch_audio_processing import BatchProcessor
    
    processor = BatchProcessor()
    processor.process_folder("/path/to/audio/files")
"""

__version__ = "1.0.0"
__author__ = "Batch Audio Processing Team"

# 導入主要類別
from .core.models import (
    ProcessingConfig,
    APIConfig,
    FileInfo,
    TranscriptionResult,
    SummaryResult,
    DiscoveryResult
)

from .core.error_handler import (
    ErrorHandler,
    ErrorType,
    ErrorSeverity,
    create_default_error_handler
)

from .core.progress_tracker import (
    ProgressTracker,
    ProcessingStage,
    TaskStatus,
    create_progress_tracker
)

from .core.logging_system import (
    LoggingSystem,
    create_logging_system
)

from .services.file_discovery import FileDiscovery
from .services.transcription_service import TranscriptionService
from .services.summary_service import SummaryService
from .services.document_generator import DocumentGenerator
from .services.processing_orchestrator import ProcessingOrchestrator

# 主要入口點
from .batch_processor import BatchProcessor

__all__ = [
    # 版本資訊
    "__version__",
    "__author__",
    
    # 核心模型
    "ProcessingConfig",
    "APIConfig", 
    "FileInfo",
    "TranscriptionResult",
    "SummaryResult",
    "DiscoveryResult",
    
    # 核心系統
    "ErrorHandler",
    "ErrorType", 
    "ErrorSeverity",
    "create_default_error_handler",
    "ProgressTracker",
    "ProcessingStage",
    "TaskStatus", 
    "create_progress_tracker",
    "LoggingSystem",
    "create_logging_system",
    
    # 服務
    "FileDiscovery",
    "TranscriptionService",
    "SummaryService", 
    "DocumentGenerator",
    "ProcessingOrchestrator",
    
    # 主要處理器
    "BatchProcessor"
]