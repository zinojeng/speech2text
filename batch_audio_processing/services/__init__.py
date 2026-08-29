"""
批次音訊處理系統 - 服務模組
Service modules for batch audio processing system

包含各種處理服務：
- 檔案發現和匹配
- 語音轉錄服務
- 智能摘要服務
- 文件生成服務
- 處理協調器
"""

from .file_discovery import (
    FileDiscovery,
    AudioFileScanner,
    AgendaFileMatcher
)

from .transcription_service import TranscriptionService

from .summary_service import SummaryService

from .document_generator import (
    DocumentGenerator,
    MarkdownProcessor,
    DocxConverter
)

from .processing_orchestrator import ProcessingOrchestrator

__all__ = [
    # 檔案發現
    "FileDiscovery",
    "AudioFileScanner", 
    "AgendaFileMatcher",
    
    # 處理服務
    "TranscriptionService",
    "SummaryService",
    "DocumentGenerator",
    "MarkdownProcessor",
    "DocxConverter",
    
    # 協調器
    "ProcessingOrchestrator"
]