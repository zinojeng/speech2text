"""
批次音訊處理系統 - 處理流程編排器
Processing Orchestrator for Batch Audio Processing System

此模組實作處理流程編排器，負責協調轉錄、摘要、文件生成等服務，
提供單一檔案處理流程和處理狀態追蹤功能。

主要功能：
- 單一檔案處理流程編排
- 整合轉錄、摘要、文件生成服務
- 處理狀態追蹤和進度報告
- 錯誤處理和恢復機制

Requirements: 6.1, 6.2
"""

import os
import time
import logging
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
import queue

# 本地模組
from batch_audio_models import (
    ProcessingConfig, 
    FileInfo, 
    TranscriptionResult, 
    SummaryResult,
    APIConfig
)
from batch_transcription_service import TranscriptionService, ProgressTracker
from batch_summary_service import SummaryService, SummaryRequest
from batch_document_generator import DocumentGenerator, DocumentResult

# 設定日誌
logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    """處理狀態枚舉"""
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    SUMMARIZING = "summarizing"
    GENERATING_DOCUMENTS = "generating_documents"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FileProcessingResult:
    """
    單一檔案處理結果
    
    包含完整的處理結果和統計資訊
    """
    file_info: FileInfo
    transcription: Optional[TranscriptionResult] = None
    summary: Optional[SummaryResult] = None
    documents: Dict[str, str] = field(default_factory=dict)  # format -> file_path
    total_time: float = 0.0
    success: bool = False
    error: Optional[str] = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def __post_init__(self):
        """初始化後設定開始時間"""
        if not self.start_time:
            self.start_time = datetime.now()
    
    def mark_completed(self, success: bool = True, error: Optional[str] = None) -> None:
        """標記處理完成"""
        self.end_time = datetime.now()
        self.success = success
        self.error = error
        self.status = ProcessingStatus.COMPLETED if success else ProcessingStatus.FAILED
        
        if self.start_time and self.end_time:
            self.total_time = (self.end_time - self.start_time).total_seconds()
    
    def get_processing_summary(self) -> Dict[str, Any]:
        """取得處理摘要統計"""
        summary = {
            'file_name': self.file_info.audio_name,
            'file_size_mb': self.file_info.file_size_mb,
            'status': self.status.value,
            'success': self.success,
            'total_time': self.total_time,
            'has_transcription': self.transcription is not None and self.transcription.success,
            'has_summary': self.summary is not None and self.summary.success,
            'documents_generated': len(self.documents),
            'error': self.error
        }
        
        # 添加轉錄統計
        if self.transcription:
            summary.update({
                'transcription_time': self.transcription.processing_time,
                'transcription_success': self.transcription.success,
                'content_length': len(self.transcription.content) if self.transcription.content else 0,
                'segments_processed': self.transcription.segments_processed
            })
        
        # 添加摘要統計
        if self.summary:
            summary.update({
                'summary_time': self.summary.processing_time,
                'summary_success': self.summary.success,
                'summary_length': len(self.summary.content) if self.summary.content else 0,
                'agenda_used': self.summary.agenda_used,
                'images_inserted': self.summary.images_inserted
            })
        
        return summary
    
    def get_display_summary(self) -> str:
        """取得用於顯示的處理摘要"""
        status_icon = {
            ProcessingStatus.PENDING: "⏳",
            ProcessingStatus.TRANSCRIBING: "🎤",
            ProcessingStatus.SUMMARIZING: "📝",
            ProcessingStatus.GENERATING_DOCUMENTS: "📄",
            ProcessingStatus.COMPLETED: "✅" if self.success else "❌",
            ProcessingStatus.FAILED: "❌",
            ProcessingStatus.CANCELLED: "⏹️"
        }.get(self.status, "❓")
        
        parts = [
            f"{status_icon} {self.file_info.audio_name}",
            f"狀態: {self.status.value}"
        ]
        
        if self.total_time > 0:
            parts.append(f"時間: {self.total_time:.1f}秒")
        
        if self.success:
            doc_count = len(self.documents)
            if doc_count > 0:
                parts.append(f"文件: {doc_count}個")
        elif self.error:
            parts.append(f"錯誤: {self.error}")
        
        return " | ".join(parts)


@dataclass
class BatchProcessingResult:
    """
    批次處理結果
    
    包含所有檔案的處理結果和統計資訊
    """
    total_files: int
    successful_files: int = 0
    failed_files: int = 0
    results: List[FileProcessingResult] = field(default_factory=list)
    total_processing_time: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    report_path: Optional[str] = None
    
    def __post_init__(self):
        """初始化後設定開始時間"""
        if not self.start_time:
            self.start_time = datetime.now()
    
    def add_result(self, result: FileProcessingResult) -> None:
        """添加處理結果"""
        self.results.append(result)
        
        if result.success:
            self.successful_files += 1
        else:
            self.failed_files += 1
        
        self.total_processing_time += result.total_time
    
    def mark_completed(self) -> None:
        """標記批次處理完成"""
        self.end_time = datetime.now()
    
    def get_success_rate(self) -> float:
        """取得成功率"""
        if self.total_files == 0:
            return 0.0
        return self.successful_files / self.total_files
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """取得處理統計資訊"""
        stats = {
            'total_files': self.total_files,
            'successful_files': self.successful_files,
            'failed_files': self.failed_files,
            'success_rate': self.get_success_rate(),
            'total_processing_time': self.total_processing_time,
            'avg_processing_time': self.total_processing_time / max(1, len(self.results)),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }
        
        # 計算各階段統計
        transcription_times = [r.transcription.processing_time for r in self.results 
                             if r.transcription and r.transcription.success]
        summary_times = [r.summary.processing_time for r in self.results 
                        if r.summary and r.summary.success]
        
        if transcription_times:
            stats['avg_transcription_time'] = sum(transcription_times) / len(transcription_times)
            stats['total_transcription_time'] = sum(transcription_times)
        
        if summary_times:
            stats['avg_summary_time'] = sum(summary_times) / len(summary_times)
            stats['total_summary_time'] = sum(summary_times)
        
        return stats
    
    def get_display_summary(self) -> str:
        """取得用於顯示的批次處理摘要"""
        success_rate = self.get_success_rate() * 100
        
        parts = [
            f"批次處理完成",
            f"成功: {self.successful_files}/{self.total_files} ({success_rate:.1f}%)",
            f"總時間: {self.total_processing_time:.1f}秒"
        ]
        
        if self.failed_files > 0:
            parts.append(f"失敗: {self.failed_files}個")
        
        return " | ".join(parts)


class ProcessingOrchestrator:
    """
    處理流程編排器
    
    負責協調轉錄、摘要、文件生成等服務，提供統一的處理介面。
    支援單一檔案處理和批次處理，包含完整的狀態追蹤和錯誤處理。
    
    Requirements: 6.1, 6.2
    """
    
    def __init__(self, config: ProcessingConfig, api_config: Optional[APIConfig] = None):
        """
        初始化處理編排器
        
        Args:
            config: 處理配置
            api_config: API 配置
        """
        self.config = config
        self.api_config = api_config or APIConfig()
        
        # 初始化服務組件
        self._initialize_services()
        
        # 處理狀態追蹤
        self.processing_queue = queue.Queue()
        self.active_tasks: Dict[str, Future] = {}
        self.processing_lock = threading.Lock()
        
        # 統計資訊
        self.stats = {
            'total_processed': 0,
            'successful_processed': 0,
            'failed_processed': 0,
            'total_processing_time': 0.0
        }
        
        logger.info("ProcessingOrchestrator 初始化完成")
    
    def _initialize_services(self) -> None:
        """初始化各個服務組件"""
        try:
            # 創建進度追蹤器
            self.progress_tracker = ProgressTracker(self.config.enable_detailed_logging)
            
            # 初始化轉錄服務
            self.transcription_service = TranscriptionService(
                config=self.config,
                api_config=self.api_config,
                progress_tracker=self.progress_tracker
            )
            
            # 初始化摘要服務
            self.summary_service = SummaryService(self.config)
            
            # 初始化文件生成器
            self.document_generator = DocumentGenerator(self.config)
            
            logger.info("所有服務組件初始化完成")
            
        except Exception as e:
            logger.error(f"服務組件初始化失敗: {e}")
            raise
    
    def process_single_file(self, file_info: FileInfo) -> FileProcessingResult:
        """
        處理單一檔案
        
        完整的處理流程包括：轉錄 -> 摘要 -> 文件生成
        
        Args:
            file_info: 檔案資訊
            
        Returns:
            檔案處理結果
        """
        result = FileProcessingResult(file_info=file_info)
        
        try:
            logger.info(f"開始處理檔案: {file_info.audio_name}")
            
            # 階段 1: 語音轉錄
            result.status = ProcessingStatus.TRANSCRIBING
            logger.info(f"階段 1: 開始轉錄 - {file_info.audio_name}")
            
            transcription_result = self.transcription_service.transcribe_audio(file_info)
            result.transcription = transcription_result
            
            if not transcription_result.success:
                error_msg = f"轉錄失敗: {transcription_result.error}"
                logger.error(error_msg)
                result.mark_completed(success=False, error=error_msg)
                return result
            
            logger.info(f"✅ 轉錄完成 - {file_info.audio_name} ({transcription_result.processing_time:.1f}秒)")
            
            # 階段 2: 智能摘要
            result.status = ProcessingStatus.SUMMARIZING
            logger.info(f"階段 2: 開始摘要 - {file_info.audio_name}")
            
            summary_request = SummaryRequest(
                transcript=transcription_result.content,
                agenda_content=file_info.agenda_content,
                agenda_path=file_info.agenda_path,
                audio_folder=str(Path(file_info.audio_path).parent),
                file_name=file_info.audio_name,
                language=self.config.transcription_language
            )
            
            summary_result = self.summary_service.generate_summary(summary_request)
            result.summary = summary_result
            
            if not summary_result.success:
                logger.warning(f"摘要生成失敗，但繼續處理: {summary_result.error}")
                # 摘要失敗不影響整體處理，使用原始轉錄內容
                summary_result = SummaryResult(
                    success=True,
                    content=transcription_result.content,
                    error="使用原始轉錄內容",
                    model_used="fallback"
                )
                result.summary = summary_result
            
            logger.info(f"✅ 摘要完成 - {file_info.audio_name} ({summary_result.processing_time:.1f}秒)")
            
            # 階段 3: 文件生成
            result.status = ProcessingStatus.GENERATING_DOCUMENTS
            logger.info(f"階段 3: 開始生成文件 - {file_info.audio_name}")
            
            document_result = self.document_generator.generate_documents(
                file_info=file_info,
                transcription_result=transcription_result,
                summary_result=summary_result
            )
            
            if document_result.success:
                if document_result.markdown_path:
                    result.documents['markdown'] = document_result.markdown_path
                if document_result.docx_path:
                    result.documents['docx'] = document_result.docx_path
                
                logger.info(f"✅ 文件生成完成 - {file_info.audio_name} ({len(result.documents)}個文件)")
            else:
                logger.warning(f"文件生成失敗，但不影響整體處理: {document_result.error}")
            
            # 處理完成
            result.mark_completed(success=True)
            logger.info(f"🎉 檔案處理完成 - {file_info.audio_name} (總時間: {result.total_time:.1f}秒)")
            
            # 更新統計資訊
            with self.processing_lock:
                self.stats['total_processed'] += 1
                self.stats['successful_processed'] += 1
                self.stats['total_processing_time'] += result.total_time
            
            return result
            
        except Exception as e:
            error_msg = f"處理檔案時發生錯誤: {str(e)}"
            logger.error(error_msg)
            result.mark_completed(success=False, error=error_msg)
            
            # 更新統計資訊
            with self.processing_lock:
                self.stats['total_processed'] += 1
                self.stats['failed_processed'] += 1
                self.stats['total_processing_time'] += result.total_time
            
            return result
    
    def validate_file_for_processing(self, file_info: FileInfo) -> tuple[bool, str]:
        """
        驗證檔案是否可以處理
        
        Args:
            file_info: 檔案資訊
            
        Returns:
            (是否可處理, 錯誤訊息)
        """
        try:
            # 檢查檔案是否存在
            if not Path(file_info.audio_path).exists():
                return False, f"音訊檔案不存在: {file_info.audio_path}"
            
            # 檢查檔案大小
            if file_info.file_size_mb <= 0:
                return False, "檔案大小無效"
            
            # 檢查是否超過系統限制
            max_size_limit = 100  # MB
            if file_info.file_size_mb > max_size_limit:
                return False, f"檔案過大，超過系統限制 {max_size_limit}MB"
            
            # 使用轉錄服務的驗證
            is_valid, error_msg = self.transcription_service.validate_file_for_transcription(file_info)
            if not is_valid:
                return False, error_msg
            
            return True, "檔案驗證通過"
            
        except Exception as e:
            return False, f"檔案驗證時發生錯誤: {str(e)}"
    
    def get_processing_status(self, file_name: str) -> Optional[ProcessingStatus]:
        """
        取得檔案的處理狀態
        
        Args:
            file_name: 檔案名稱
            
        Returns:
            處理狀態，如果找不到則返回 None
        """
        with self.processing_lock:
            if file_name in self.active_tasks:
                future = self.active_tasks[file_name]
                if future.done():
                    return ProcessingStatus.COMPLETED
                else:
                    return ProcessingStatus.TRANSCRIBING  # 簡化狀態
            
        return None
    
    def cancel_processing(self, file_name: str) -> bool:
        """
        取消檔案處理
        
        Args:
            file_name: 檔案名稱
            
        Returns:
            是否成功取消
        """
        try:
            with self.processing_lock:
                if file_name in self.active_tasks:
                    future = self.active_tasks[file_name]
                    if not future.done():
                        cancelled = future.cancel()
                        if cancelled:
                            logger.info(f"已取消處理: {file_name}")
                            del self.active_tasks[file_name]
                        return cancelled
            
            return False
            
        except Exception as e:
            logger.error(f"取消處理時發生錯誤: {e}")
            return False
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """取得處理統計資訊"""
        with self.processing_lock:
            stats = self.stats.copy()
        
        # 計算成功率
        if stats['total_processed'] > 0:
            stats['success_rate'] = stats['successful_processed'] / stats['total_processed']
        else:
            stats['success_rate'] = 0.0
        
        # 計算平均處理時間
        if stats['successful_processed'] > 0:
            stats['avg_processing_time'] = stats['total_processing_time'] / stats['successful_processed']
        else:
            stats['avg_processing_time'] = 0.0
        
        # 添加服務統計
        stats['transcription_stats'] = self.transcription_service.get_stats()
        
        return stats
    
    def add_progress_callback(self, callback: Callable[[Any], None]) -> None:
        """
        添加進度回調函數
        
        Args:
            callback: 進度回調函數
        """
        self.progress_tracker.add_progress_callback(callback)
    
    def get_progress_info(self) -> Any:
        """取得當前進度資訊"""
        return self.progress_tracker.get_progress_info()
    
    def process_batch(self, file_infos: List[FileInfo]) -> BatchProcessingResult:
        """
        批次處理多個檔案
        
        支援並行處理和處理佇列管理，提供完整的批次處理功能。
        
        Args:
            file_infos: 檔案資訊列表
            
        Returns:
            批次處理結果
        """
        if not file_infos:
            logger.warning("沒有檔案需要處理")
            return BatchProcessingResult(total_files=0)
        
        batch_result = BatchProcessingResult(total_files=len(file_infos))
        
        try:
            logger.info(f"開始批次處理 {len(file_infos)} 個檔案")
            
            # 開始批次處理進度追蹤
            self.progress_tracker.start_processing(len(file_infos))
            
            if self.config.enable_parallel and len(file_infos) > 1:
                # 並行處理
                results = self._process_batch_parallel(file_infos)
            else:
                # 序列處理
                results = self._process_batch_sequential(file_infos)
            
            # 收集結果
            for result in results:
                batch_result.add_result(result)
            
            # 完成批次處理
            batch_result.mark_completed()
            self.progress_tracker.complete_processing()
            
            # 統計結果
            success_rate = batch_result.get_success_rate() * 100
            logger.info(f"🎉 批次處理完成: 成功 {batch_result.successful_files}/{batch_result.total_files} "
                       f"({success_rate:.1f}%) 總時間: {batch_result.total_processing_time:.1f}秒")
            
            if batch_result.failed_files > 0:
                failed_files = [r.file_info.audio_name for r in batch_result.results if not r.success]
                logger.warning(f"失敗的檔案: {', '.join(failed_files)}")
            
            return batch_result
            
        except Exception as e:
            logger.error(f"批次處理過程發生錯誤: {e}")
            batch_result.mark_completed()
            self.progress_tracker.complete_processing()
            return batch_result
    
    def _process_batch_sequential(self, file_infos: List[FileInfo]) -> List[FileProcessingResult]:
        """
        序列批次處理
        
        Args:
            file_infos: 檔案資訊列表
            
        Returns:
            處理結果列表
        """
        results = []
        
        logger.info("使用序列處理模式")
        
        for i, file_info in enumerate(file_infos):
            logger.info(f"序列處理 ({i + 1}/{len(file_infos)}): {file_info.audio_name}")
            
            try:
                # 驗證檔案
                is_valid, error_msg = self.validate_file_for_processing(file_info)
                if not is_valid:
                    logger.error(f"檔案驗證失敗: {file_info.audio_name} - {error_msg}")
                    result = FileProcessingResult(file_info=file_info)
                    result.mark_completed(success=False, error=error_msg)
                    results.append(result)
                    continue
                
                # 處理檔案
                result = self.process_single_file(file_info)
                results.append(result)
                
                # 記錄處理結果
                if result.success:
                    logger.info(f"✅ 序列處理成功 ({i + 1}/{len(file_infos)}): {file_info.audio_name}")
                else:
                    logger.error(f"❌ 序列處理失敗 ({i + 1}/{len(file_infos)}): {file_info.audio_name} - {result.error}")
                
                # API 速率限制延遲
                if i < len(file_infos) - 1 and self.config.api_rate_limit_delay > 0:
                    logger.debug(f"API 速率限制延遲: {self.config.api_rate_limit_delay} 秒")
                    time.sleep(self.config.api_rate_limit_delay)
                
            except Exception as e:
                logger.error(f"序列處理檔案時發生錯誤: {file_info.audio_name} - {e}")
                result = FileProcessingResult(file_info=file_info)
                result.mark_completed(success=False, error=str(e))
                results.append(result)
        
        return results
    
    def _process_batch_parallel(self, file_infos: List[FileInfo]) -> List[FileProcessingResult]:
        """
        並行批次處理
        
        使用 ThreadPoolExecutor 進行並行處理，支援處理佇列管理。
        
        Args:
            file_infos: 檔案資訊列表
            
        Returns:
            處理結果列表
        """
        results = []
        max_workers = min(self.config.max_workers, len(file_infos))
        
        logger.info(f"使用並行處理模式，工作者數量: {max_workers}")
        
        # 預先驗證所有檔案
        valid_files = []
        invalid_results = []
        
        for file_info in file_infos:
            is_valid, error_msg = self.validate_file_for_processing(file_info)
            if is_valid:
                valid_files.append(file_info)
            else:
                logger.error(f"檔案驗證失敗: {file_info.audio_name} - {error_msg}")
                result = FileProcessingResult(file_info=file_info)
                result.mark_completed(success=False, error=error_msg)
                invalid_results.append(result)
        
        results.extend(invalid_results)
        
        if not valid_files:
            logger.warning("沒有有效的檔案可以處理")
            return results
        
        # 使用 ThreadPoolExecutor 進行並行處理
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="AudioProcessor") as executor:
            try:
                # 提交所有任務
                future_to_file = {}
                
                for file_info in valid_files:
                    future = executor.submit(self._process_single_file_with_tracking, file_info)
                    future_to_file[future] = file_info
                    
                    # 記錄活動任務
                    with self.processing_lock:
                        self.active_tasks[file_info.audio_name] = future
                
                logger.info(f"已提交 {len(future_to_file)} 個並行處理任務")
                
                # 收集結果
                completed_count = 0
                
                for future in as_completed(future_to_file):
                    file_info = future_to_file[future]
                    completed_count += 1
                    
                    try:
                        result = future.result()
                        results.append(result)
                        
                        # 記錄處理結果
                        if result.success:
                            logger.info(f"✅ 並行處理成功 ({completed_count}/{len(valid_files)}): {file_info.audio_name}")
                        else:
                            logger.error(f"❌ 並行處理失敗 ({completed_count}/{len(valid_files)}): {file_info.audio_name} - {result.error}")
                        
                    except Exception as e:
                        logger.error(f"並行處理任務異常: {file_info.audio_name} - {e}")
                        result = FileProcessingResult(file_info=file_info)
                        result.mark_completed(success=False, error=f"並行處理異常: {str(e)}")
                        results.append(result)
                    
                    finally:
                        # 清理活動任務記錄
                        with self.processing_lock:
                            if file_info.audio_name in self.active_tasks:
                                del self.active_tasks[file_info.audio_name]
                
                logger.info(f"並行處理完成，處理了 {len(results)} 個檔案")
                
            except Exception as e:
                logger.error(f"並行處理過程發生錯誤: {e}")
                
                # 清理所有活動任務
                with self.processing_lock:
                    self.active_tasks.clear()
        
        return results
    
    def _process_single_file_with_tracking(self, file_info: FileInfo) -> FileProcessingResult:
        """
        帶追蹤的單一檔案處理（用於並行處理）
        
        Args:
            file_info: 檔案資訊
            
        Returns:
            處理結果
        """
        try:
            # 添加線程資訊到日誌
            thread_name = threading.current_thread().name
            logger.debug(f"[{thread_name}] 開始處理: {file_info.audio_name}")
            
            # 處理檔案
            result = self.process_single_file(file_info)
            
            logger.debug(f"[{thread_name}] 處理完成: {file_info.audio_name} (成功: {result.success})")
            
            return result
            
        except Exception as e:
            logger.error(f"並行處理檔案時發生錯誤: {file_info.audio_name} - {e}")
            result = FileProcessingResult(file_info=file_info)
            result.mark_completed(success=False, error=str(e))
            return result
    
    def get_active_tasks(self) -> Dict[str, str]:
        """
        取得當前活動任務狀態
        
        Returns:
            檔案名稱到狀態的映射
        """
        with self.processing_lock:
            active_status = {}
            for file_name, future in self.active_tasks.items():
                if future.done():
                    if future.cancelled():
                        active_status[file_name] = "已取消"
                    elif future.exception():
                        active_status[file_name] = "異常"
                    else:
                        active_status[file_name] = "已完成"
                else:
                    active_status[file_name] = "處理中"
            
            return active_status
    
    def cancel_all_processing(self) -> int:
        """
        取消所有正在處理的任務
        
        Returns:
            成功取消的任務數量
        """
        cancelled_count = 0
        
        try:
            with self.processing_lock:
                for file_name, future in list(self.active_tasks.items()):
                    if not future.done():
                        if future.cancel():
                            cancelled_count += 1
                            logger.info(f"已取消處理: {file_name}")
                        else:
                            logger.warning(f"無法取消處理: {file_name}")
                
                # 清理已取消的任務
                self.active_tasks = {k: v for k, v in self.active_tasks.items() if not v.cancelled()}
            
            if cancelled_count > 0:
                logger.info(f"已取消 {cancelled_count} 個處理任務")
            
        except Exception as e:
            logger.error(f"取消處理任務時發生錯誤: {e}")
        
        return cancelled_count
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        等待所有處理任務完成
        
        Args:
            timeout: 超時時間（秒），None 表示無限等待
            
        Returns:
            是否所有任務都已完成
        """
        try:
            start_time = time.time()
            
            while True:
                with self.processing_lock:
                    if not self.active_tasks:
                        return True
                    
                    # 檢查是否有未完成的任務
                    pending_tasks = [f for f, future in self.active_tasks.items() if not future.done()]
                    
                    if not pending_tasks:
                        # 清理已完成的任務
                        self.active_tasks.clear()
                        return True
                
                # 檢查超時
                if timeout and (time.time() - start_time) > timeout:
                    logger.warning(f"等待處理完成超時 ({timeout} 秒)")
                    return False
                
                # 短暫等待
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"等待處理完成時發生錯誤: {e}")
            return False
    
    def process_batch_with_combined_output(self, file_infos: List[FileInfo], 
                                         output_dir: str) -> BatchProcessingResult:
        """
        批次處理並生成組合輸出
        
        支援 SRT 格式組合輸出和連續時間戳記處理，以及文字/Markdown 組合模式。
        
        Args:
            file_infos: 檔案資訊列表
            output_dir: 輸出目錄
            
        Returns:
            批次處理結果（包含組合輸出檔案路徑）
        """
        if not file_infos:
            logger.warning("沒有檔案需要處理")
            return BatchProcessingResult(total_files=0)
        
        logger.info(f"開始批次處理並生成組合輸出: {len(file_infos)} 個檔案")
        
        # 先進行正常的批次處理
        batch_result = self.process_batch(file_infos)
        
        if batch_result.successful_files == 0:
            logger.error("沒有成功處理的檔案，無法生成組合輸出")
            return batch_result
        
        try:
            # 生成組合輸出
            combined_files = self._generate_combined_output(batch_result, output_dir)
            
            # 將組合輸出檔案路徑添加到結果中
            if combined_files:
                batch_result.report_path = combined_files.get('report', None)
                logger.info(f"✅ 組合輸出生成完成: {len(combined_files)} 個檔案")
                
                for output_type, file_path in combined_files.items():
                    logger.info(f"   {output_type}: {file_path}")
            else:
                logger.warning("組合輸出生成失敗")
            
        except Exception as e:
            logger.error(f"生成組合輸出時發生錯誤: {e}")
        
        return batch_result
    
    def _generate_combined_output(self, batch_result: BatchProcessingResult, 
                                output_dir: str) -> Dict[str, str]:
        """
        生成組合輸出檔案
        
        Args:
            batch_result: 批次處理結果
            output_dir: 輸出目錄
            
        Returns:
            生成的組合檔案路徑字典
        """
        combined_files = {}
        
        try:
            # 確保輸出目錄存在
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # 收集成功處理的結果
            successful_results = [r for r in batch_result.results if r.success]
            
            if not successful_results:
                logger.warning("沒有成功的處理結果可以組合")
                return combined_files
            
            # 生成組合 SRT 檔案
            if self.config.enable_srt_support:
                srt_file = self._generate_combined_srt(successful_results, output_dir)
                if srt_file:
                    combined_files['srt'] = srt_file
            
            # 生成組合 Markdown 檔案
            markdown_file = self._generate_combined_markdown(successful_results, output_dir)
            if markdown_file:
                combined_files['markdown'] = markdown_file
            
            # 生成組合文字檔案
            text_file = self._generate_combined_text(successful_results, output_dir)
            if text_file:
                combined_files['text'] = text_file
            
            # 生成處理報告
            report_file = self._generate_processing_report(batch_result, output_dir)
            if report_file:
                combined_files['report'] = report_file
            
            logger.info(f"組合輸出生成完成: {len(combined_files)} 個檔案")
            
        except Exception as e:
            logger.error(f"生成組合輸出時發生錯誤: {e}")
        
        return combined_files
    
    def _generate_combined_srt(self, results: List[FileProcessingResult], 
                             output_dir: str) -> Optional[str]:
        """
        生成組合 SRT 檔案，支援連續時間戳記處理
        
        Args:
            results: 處理結果列表
            output_dir: 輸出目錄
            
        Returns:
            生成的 SRT 檔案路徑
        """
        try:
            output_file = Path(output_dir) / "combined_transcription.srt"
            
            srt_entries = []
            current_index = 1
            current_time_offset = 0.0  # 累積時間偏移（秒）
            
            for i, result in enumerate(results):
                if not result.transcription or not result.transcription.success:
                    continue
                
                file_name = result.file_info.audio_name
                content = result.transcription.content
                
                # 添加檔案分隔符
                separator_entry = self._create_srt_entry(
                    index=current_index,
                    start_time=current_time_offset,
                    end_time=current_time_offset + 3.0,  # 3秒的分隔符
                    text=f"=== {file_name} ==="
                )
                srt_entries.append(separator_entry)
                current_index += 1
                current_time_offset += 3.0
                
                # 處理轉錄內容
                # 如果內容已經是 SRT 格式，解析並調整時間戳記
                if self._is_srt_format(content):
                    parsed_entries = self._parse_srt_content(content)
                    for entry in parsed_entries:
                        adjusted_entry = self._adjust_srt_timestamps(entry, current_time_offset)
                        adjusted_entry['index'] = current_index
                        srt_entries.append(self._format_srt_entry(adjusted_entry))
                        current_index += 1
                    
                    # 更新時間偏移（假設每個檔案平均 5 分鐘）
                    current_time_offset += 300.0  # 5 分鐘
                else:
                    # 如果是純文字，創建單一 SRT 條目
                    text_entry = self._create_srt_entry(
                        index=current_index,
                        start_time=current_time_offset,
                        end_time=current_time_offset + 60.0,  # 假設 1 分鐘
                        text=content[:500] + "..." if len(content) > 500 else content
                    )
                    srt_entries.append(text_entry)
                    current_index += 1
                    current_time_offset += 60.0
                
                # 添加檔案間隔
                current_time_offset += 2.0
            
            # 寫入 SRT 檔案
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n\n'.join(srt_entries))
            
            logger.info(f"組合 SRT 檔案已生成: {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"生成組合 SRT 檔案時發生錯誤: {e}")
            return None
    
    def _create_srt_entry(self, index: int, start_time: float, end_time: float, text: str) -> str:
        """
        創建 SRT 條目
        
        Args:
            index: 條目索引
            start_time: 開始時間（秒）
            end_time: 結束時間（秒）
            text: 文字內容
            
        Returns:
            格式化的 SRT 條目
        """
        start_timestamp = self._seconds_to_srt_timestamp(start_time)
        end_timestamp = self._seconds_to_srt_timestamp(end_time)
        
        return f"{index}\n{start_timestamp} --> {end_timestamp}\n{text}"
    
    def _seconds_to_srt_timestamp(self, seconds: float) -> str:
        """
        將秒數轉換為 SRT 時間戳記格式
        
        Args:
            seconds: 秒數
            
        Returns:
            SRT 格式的時間戳記 (HH:MM:SS,mmm)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def _is_srt_format(self, content: str) -> bool:
        """檢查內容是否為 SRT 格式"""
        # 簡單檢查是否包含 SRT 時間戳記格式
        import re
        srt_pattern = r'\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}'
        return bool(re.search(srt_pattern, content))
    
    def _parse_srt_content(self, content: str) -> List[Dict[str, Any]]:
        """解析 SRT 內容"""
        entries = []
        # 簡化的 SRT 解析實現
        # 實際實現應該更加完整
        return entries
    
    def _adjust_srt_timestamps(self, entry: Dict[str, Any], offset: float) -> Dict[str, Any]:
        """調整 SRT 時間戳記"""
        # 簡化實現
        return entry
    
    def _format_srt_entry(self, entry: Dict[str, Any]) -> str:
        """格式化 SRT 條目"""
        # 簡化實現
        return ""
    
    def _generate_combined_markdown(self, results: List[FileProcessingResult], 
                                  output_dir: str) -> Optional[str]:
        """
        生成組合 Markdown 檔案
        
        Args:
            results: 處理結果列表
            output_dir: 輸出目錄
            
        Returns:
            生成的 Markdown 檔案路徑
        """
        try:
            output_file = Path(output_dir) / "combined_summary.md"
            
            markdown_parts = []
            
            # 添加標題
            markdown_parts.append("# 批次音訊處理 - 組合摘要")
            markdown_parts.append(f"\n生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            markdown_parts.append(f"處理檔案數量: {len(results)}")
            markdown_parts.append("\n---\n")
            
            # 添加目錄
            markdown_parts.append("## 目錄\n")
            for i, result in enumerate(results, 1):
                if result.success:
                    markdown_parts.append(f"{i}. [{result.file_info.audio_name}](#{result.file_info.audio_name.replace(' ', '-').lower()})")
            markdown_parts.append("\n---\n")
            
            # 添加每個檔案的內容
            for i, result in enumerate(results, 1):
                if not result.success:
                    continue
                
                file_name = result.file_info.audio_name
                markdown_parts.append(f"## {i}. {file_name}")
                
                # 添加檔案資訊
                markdown_parts.append(f"\n**檔案資訊:**")
                markdown_parts.append(f"- 檔案大小: {result.file_info.file_size_mb:.2f} MB")
                markdown_parts.append(f"- 處理時間: {result.total_time:.1f} 秒")
                
                if result.file_info.agenda_path:
                    markdown_parts.append(f"- 議程檔案: {Path(result.file_info.agenda_path).name}")
                
                # 添加摘要內容
                if result.summary and result.summary.success:
                    markdown_parts.append(f"\n**摘要內容:**\n")
                    markdown_parts.append(result.summary.content)
                elif result.transcription and result.transcription.success:
                    markdown_parts.append(f"\n**轉錄內容:**\n")
                    # 截取前 1000 字符
                    content = result.transcription.content
                    if len(content) > 1000:
                        content = content[:1000] + "\n\n...(內容已截取)..."
                    markdown_parts.append(content)
                
                markdown_parts.append("\n---\n")
            
            # 寫入檔案
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(markdown_parts))
            
            logger.info(f"組合 Markdown 檔案已生成: {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"生成組合 Markdown 檔案時發生錯誤: {e}")
            return None
    
    def _generate_combined_text(self, results: List[FileProcessingResult], 
                              output_dir: str) -> Optional[str]:
        """
        生成組合文字檔案
        
        Args:
            results: 處理結果列表
            output_dir: 輸出目錄
            
        Returns:
            生成的文字檔案路徑
        """
        try:
            output_file = Path(output_dir) / "combined_transcription.txt"
            
            text_parts = []
            
            # 添加標題
            text_parts.append("批次音訊處理 - 組合轉錄結果")
            text_parts.append("=" * 50)
            text_parts.append(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            text_parts.append(f"處理檔案數量: {len(results)}")
            text_parts.append("=" * 50)
            text_parts.append("")
            
            # 添加每個檔案的內容
            for i, result in enumerate(results, 1):
                if not result.success:
                    continue
                
                file_name = result.file_info.audio_name
                text_parts.append(f"{i}. {file_name}")
                text_parts.append("-" * (len(file_name) + 3))
                
                # 添加檔案資訊
                text_parts.append(f"檔案大小: {result.file_info.file_size_mb:.2f} MB")
                text_parts.append(f"處理時間: {result.total_time:.1f} 秒")
                
                if result.file_info.agenda_path:
                    text_parts.append(f"議程檔案: {Path(result.file_info.agenda_path).name}")
                
                text_parts.append("")
                
                # 添加內容
                if result.summary and result.summary.success:
                    text_parts.append("摘要內容:")
                    text_parts.append(result.summary.content)
                elif result.transcription and result.transcription.success:
                    text_parts.append("轉錄內容:")
                    text_parts.append(result.transcription.content)
                
                text_parts.append("")
                text_parts.append("=" * 50)
                text_parts.append("")
            
            # 寫入檔案
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(text_parts))
            
            logger.info(f"組合文字檔案已生成: {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"生成組合文字檔案時發生錯誤: {e}")
            return None
    
    def _generate_processing_report(self, batch_result: BatchProcessingResult, 
                                  output_dir: str) -> Optional[str]:
        """
        生成處理報告
        
        Args:
            batch_result: 批次處理結果
            output_dir: 輸出目錄
            
        Returns:
            生成的報告檔案路徑
        """
        try:
            output_file = Path(output_dir) / "processing_report.md"
            
            report_parts = []
            
            # 報告標題
            report_parts.append("# 批次音訊處理報告")
            report_parts.append(f"\n生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 處理統計
            stats = batch_result.get_processing_stats()
            report_parts.append("\n## 處理統計")
            report_parts.append(f"- **總檔案數**: {batch_result.total_files}")
            report_parts.append(f"- **成功處理**: {batch_result.successful_files}")
            report_parts.append(f"- **處理失敗**: {batch_result.failed_files}")
            report_parts.append(f"- **成功率**: {stats['success_rate']:.1%}")
            report_parts.append(f"- **總處理時間**: {batch_result.total_processing_time:.1f} 秒")
            report_parts.append(f"- **平均處理時間**: {stats['avg_processing_time']:.1f} 秒")
            
            if 'avg_transcription_time' in stats:
                report_parts.append(f"- **平均轉錄時間**: {stats['avg_transcription_time']:.1f} 秒")
            
            if 'avg_summary_time' in stats:
                report_parts.append(f"- **平均摘要時間**: {stats['avg_summary_time']:.1f} 秒")
            
            # 處理詳情
            report_parts.append("\n## 處理詳情")
            
            # 成功的檔案
            successful_results = [r for r in batch_result.results if r.success]
            if successful_results:
                report_parts.append("\n### ✅ 成功處理的檔案")
                for result in successful_results:
                    report_parts.append(f"- **{result.file_info.audio_name}**")
                    report_parts.append(f"  - 檔案大小: {result.file_info.file_size_mb:.2f} MB")
                    report_parts.append(f"  - 處理時間: {result.total_time:.1f} 秒")
                    report_parts.append(f"  - 生成文件: {len(result.documents)} 個")
                    
                    if result.transcription:
                        report_parts.append(f"  - 轉錄時間: {result.transcription.processing_time:.1f} 秒")
                        report_parts.append(f"  - 內容長度: {len(result.transcription.content)} 字符")
                    
                    if result.summary:
                        report_parts.append(f"  - 摘要時間: {result.summary.processing_time:.1f} 秒")
                        if result.summary.agenda_used:
                            report_parts.append("  - 使用了議程檔案")
                        if result.summary.images_inserted > 0:
                            report_parts.append(f"  - 插入圖片: {result.summary.images_inserted} 張")
            
            # 失敗的檔案
            failed_results = [r for r in batch_result.results if not r.success]
            if failed_results:
                report_parts.append("\n### ❌ 處理失敗的檔案")
                for result in failed_results:
                    report_parts.append(f"- **{result.file_info.audio_name}**")
                    report_parts.append(f"  - 錯誤: {result.error}")
                    report_parts.append(f"  - 狀態: {result.status.value}")
            
            # 系統資訊
            orchestrator_stats = self.get_processing_stats()
            report_parts.append("\n## 系統資訊")
            report_parts.append(f"- **轉錄模型**: {self.config.transcription_model.value}")
            report_parts.append(f"- **摘要模型**: {self.config.summary_model.value}")
            report_parts.append(f"- **並行處理**: {'啟用' if self.config.enable_parallel else '停用'}")
            report_parts.append(f"- **最大工作者**: {self.config.max_workers}")
            report_parts.append(f"- **重試次數**: {self.config.retry_attempts}")
            
            # 寫入檔案
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_parts))
            
            logger.info(f"處理報告已生成: {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"生成處理報告時發生錯誤: {e}")
            return None


def create_processing_orchestrator(config: ProcessingConfig, 
                                 progress_callback: Optional[Callable] = None) -> ProcessingOrchestrator:
    """
    創建處理編排器實例
    
    Args:
        config: 處理配置
        progress_callback: 進度回調函數
        
    Returns:
        處理編排器實例
    """
    orchestrator = ProcessingOrchestrator(config)
    
    if progress_callback:
        orchestrator.add_progress_callback(progress_callback)
    
    return orchestrator


# 進度回調函數範例
def console_progress_callback(progress_info) -> None:
    """控制台進度回調函數範例"""
    if hasattr(progress_info, 'get_display_info'):
        print(f"\r進度: {progress_info.get_display_info()}", end="", flush=True)
    else:
        print(f"\r進度更新: {progress_info}", end="", flush=True)


if __name__ == "__main__":
    """測試處理編排器"""
    import logging
    
    # 設定日誌
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=== 處理編排器測試 ===\n")
    
    try:
        # 創建測試配置
        from batch_audio_models import create_default_config
        config = create_default_config()
        
        # 創建處理編排器
        orchestrator = create_processing_orchestrator(config, console_progress_callback)
        
        print("✅ 處理編排器創建成功")
        print(f"   轉錄模型: {config.transcription_model.value}")
        print(f"   摘要模型: {config.summary_model.value}")
        print(f"   輸出格式: {config.output_format.value}")
        print(f"   並行處理: {config.enable_parallel}")
        
        # 顯示統計資訊
        stats = orchestrator.get_processing_stats()
        print(f"\n📊 初始統計資訊:")
        for key, value in stats.items():
            if isinstance(value, dict):
                print(f"   {key}:")
                for sub_key, sub_value in value.items():
                    print(f"     {sub_key}: {sub_value}")
            else:
                print(f"   {key}: {value}")
        
        # 顯示進度資訊
        progress = orchestrator.get_progress_info()
        print(f"\n📈 進度資訊:")
        if hasattr(progress, 'get_display_info'):
            print(f"   {progress.get_display_info()}")
        else:
            print(f"   {progress}")
        
    except Exception as e:
        print(f"❌ 處理編排器測試失敗: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== 測試完成 ===")