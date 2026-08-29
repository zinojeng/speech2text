"""
批次音訊處理系統 - 轉錄服務包裝器
Transcription Service Wrapper for Batch Audio Processing

此模組提供轉錄服務的統一介面，整合現有的 audio2text/gpt4o_stt.py 功能，
支援多種轉錄模型、錯誤處理和重試機制。

Requirements: 2.1, 2.2, 8.1, 8.2
"""

import os
import time
import logging
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
import tempfile
from dataclasses import dataclass
from datetime import datetime
import json

from ..core.models import (
    ProcessingConfig, 
    TranscriptionResult, 
    FileInfo,
    TranscriptionModel,
    APIConfig
)
import sys
from pathlib import Path as _Path

# utils 在專案根目錄，套件深處要先把根目錄放進 path
sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from utils import check_file_size, split_large_audio, calculate_tokens_and_cost
from audio2text.gpt4o_stt import transcribe_audio_gpt4o

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """重試配置"""
    max_attempts: int = 3
    base_delay: float = 2.0
    exponential_backoff: bool = True
    max_delay: float = 60.0


@dataclass
class ProgressInfo:
    """進度資訊"""
    current_step: str = ""
    current_file: str = ""
    files_completed: int = 0
    total_files: int = 0
    segments_completed: int = 0
    total_segments: int = 0
    start_time: Optional[datetime] = None
    
    def get_progress_percentage(self) -> float:
        """取得整體進度百分比"""
        if self.total_files == 0:
            return 0.0
        return (self.files_completed / self.total_files) * 100.0
    
    def get_segment_progress_percentage(self) -> float:
        """取得當前檔案的片段進度百分比"""
        if self.total_segments == 0:
            return 0.0
        return (self.segments_completed / self.total_segments) * 100.0
    
    def get_elapsed_time(self) -> float:
        """取得已經過時間（秒）"""
        if not self.start_time:
            return 0.0
        return (datetime.now() - self.start_time).total_seconds()
    
    def get_display_info(self) -> str:
        """取得用於顯示的進度資訊"""
        parts = []
        
        if self.current_step:
            parts.append(f"步驟: {self.current_step}")
        
        if self.current_file:
            parts.append(f"檔案: {self.current_file}")
        
        if self.total_files > 0:
            parts.append(f"檔案進度: {self.files_completed}/{self.total_files} ({self.get_progress_percentage():.1f}%)")
        
        if self.total_segments > 0:
            parts.append(f"片段進度: {self.segments_completed}/{self.total_segments} ({self.get_segment_progress_percentage():.1f}%)")
        
        elapsed = self.get_elapsed_time()
        if elapsed > 0:
            parts.append(f"已用時間: {elapsed:.1f}秒")
        
        return " | ".join(parts)


class ProgressTracker:
    """
    進度追蹤器
    
    建立轉錄進度回報機制，整合現有的日誌系統，實作處理時間統計
    Requirements: 2.3, 6.1, 6.2
    """
    
    def __init__(self, enable_detailed_logging: bool = True):
        """初始化進度追蹤器"""
        self.enable_detailed_logging = enable_detailed_logging
        self.progress_info = ProgressInfo()
        self.progress_callbacks: List[Callable[[ProgressInfo], None]] = []
        self.processing_log: List[Dict[str, Any]] = []
        
        # 統計資訊
        self.stats = {
            'total_processing_time': 0.0,
            'files_processed': 0,
            'segments_processed': 0,
            'errors_encountered': 0,
            'retries_attempted': 0
        }
        
        logger.info("進度追蹤器初始化完成")
    
    def add_progress_callback(self, callback: Callable[[ProgressInfo], None]) -> None:
        """添加進度回調函數"""
        self.progress_callbacks.append(callback)
    
    def start_processing(self, total_files: int) -> None:
        """開始處理"""
        self.progress_info = ProgressInfo(
            current_step="開始處理",
            total_files=total_files,
            start_time=datetime.now()
        )
        self._notify_progress_update()
        logger.info(f"開始處理 {total_files} 個檔案")
    
    def start_file_processing(self, file_info: FileInfo, estimated_segments: int = 1) -> None:
        """開始處理檔案"""
        self.progress_info.current_step = "轉錄檔案"
        self.progress_info.current_file = file_info.audio_name
        self.progress_info.segments_completed = 0
        self.progress_info.total_segments = estimated_segments
        
        self._notify_progress_update()
        
        if self.enable_detailed_logging:
            logger.info(f"開始處理檔案: {file_info.audio_name} ({file_info.file_size_mb:.1f}MB)")
    
    def update_segment_progress(self, completed_segments: int, total_segments: int) -> None:
        """更新片段進度"""
        self.progress_info.segments_completed = completed_segments
        self.progress_info.total_segments = total_segments
        self._notify_progress_update()
    
    def complete_file_processing(self, file_info: FileInfo, result: TranscriptionResult) -> None:
        """完成檔案處理"""
        self.progress_info.files_completed += 1
        self.progress_info.segments_completed = self.progress_info.total_segments
        
        # 更新統計資訊
        self.stats['files_processed'] += 1
        self.stats['total_processing_time'] += result.processing_time
        self.stats['segments_processed'] += result.segments_processed
        
        if not result.success:
            self.stats['errors_encountered'] += 1
        
        self._notify_progress_update()
        
        status_icon = "✅" if result.success else "❌"
        logger.info(f"{status_icon} 檔案處理完成: {file_info.audio_name} ({result.processing_time:.1f}秒)")
    
    def record_retry_attempt(self, file_name: str, attempt: int, error: str) -> None:
        """記錄重試嘗試"""
        self.stats['retries_attempted'] += 1
        logger.warning(f"重試處理 {file_name} (第 {attempt} 次): {error}")
    
    def complete_processing(self) -> None:
        """完成所有處理"""
        self.progress_info.current_step = "處理完成"
        total_time = self.progress_info.get_elapsed_time()
        self._notify_progress_update()
        logger.info(f"所有處理完成: {self.progress_info.files_completed}/{self.progress_info.total_files} 檔案 ({total_time:.1f}秒)")
    
    def _notify_progress_update(self) -> None:
        """通知進度更新"""
        for callback in self.progress_callbacks:
            try:
                callback(self.progress_info)
            except Exception as e:
                logger.warning(f"進度回調函數執行失敗: {e}")
    
    def get_progress_info(self) -> ProgressInfo:
        """取得當前進度資訊"""
        return self.progress_info
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """取得處理統計資訊"""
        stats = self.stats.copy()
        
        # 計算平均處理時間
        if stats['files_processed'] > 0:
            stats['avg_processing_time'] = stats['total_processing_time'] / stats['files_processed']
        else:
            stats['avg_processing_time'] = 0.0
        
        # 計算成功率
        if stats['files_processed'] > 0:
            success_rate = (stats['files_processed'] - stats['errors_encountered']) / stats['files_processed']
            stats['success_rate'] = success_rate
        else:
            stats['success_rate'] = 0.0
        
        return stats


class TranscriptionError(Exception):
    """轉錄相關錯誤"""
    def __init__(self, message: str, error_type: str = "unknown", retryable: bool = False):
        super().__init__(message)
        self.error_type = error_type
        self.retryable = retryable


class TranscriptionService:
    """
    轉錄服務包裝器
    
    整合現有的 gpt4o_stt.py 功能，提供統一的轉錄介面，
    支援錯誤處理、重試機制和進度追蹤。
    
    Requirements: 2.1, 2.2, 8.1, 8.2
    """
    
    def __init__(self, config: ProcessingConfig, api_config: Optional[APIConfig] = None, 
                 progress_tracker: Optional[ProgressTracker] = None):
        """初始化轉錄服務"""
        self.config = config
        self.api_config = api_config or APIConfig()
        # 使用內部的 ProgressTracker 類別
        if progress_tracker is None:
            self.progress_tracker = ProgressTracker(config.enable_detailed_logging)
        else:
            # 如果傳入了外部的 progress_tracker，我們需要適配
            self.progress_tracker = ProgressTracker(config.enable_detailed_logging)
        self.retry_config = RetryConfig(
            max_attempts=config.retry_attempts,
            base_delay=config.retry_delay,
            exponential_backoff=config.exponential_backoff
        )
        
        # 驗證 API 金鑰
        self._validate_api_keys()
        
        # 統計資訊
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retry_attempts': 0,
            'total_processing_time': 0.0
        }
        
        logger.info(f"轉錄服務初始化完成，模型: {config.transcription_model.value}")
    
    def _validate_api_keys(self) -> None:
        """驗證 API 金鑰"""
        validation_results = self.api_config.validate_api_keys()
        
        if not validation_results['openai']:
            raise TranscriptionError(
                "OpenAI API 金鑰無效或缺失",
                error_type="api_key_error",
                retryable=False
            )
        
        logger.info("API 金鑰驗證通過")
    
    def transcribe_audio(self, file_info: FileInfo) -> TranscriptionResult:
        """轉錄音訊檔案"""
        start_time = time.time()
        self.stats['total_requests'] += 1
        
        try:
            # 估算片段數量
            estimated_segments = 1
            if file_info.is_large_file(self.config.max_file_size_mb):
                estimated_segments = max(1, int(file_info.file_size_mb / self.config.max_file_size_mb))
            
            # 開始檔案處理進度追蹤
            self.progress_tracker.start_file_processing(file_info, estimated_segments)
            
            logger.info(f"開始轉錄: {file_info.audio_name}")
            
            # 驗證檔案
            is_valid, error_msg = self.validate_file_for_transcription(file_info)
            if not is_valid:
                raise TranscriptionError(error_msg, error_type="file_validation_error", retryable=False)
            
            # 檢查檔案大小，決定是否需要分割
            if file_info.is_large_file(self.config.max_file_size_mb):
                logger.info(f"檔案過大 ({file_info.file_size_mb:.1f}MB)，將進行分割處理")
                result = self._transcribe_large_file(file_info)
            else:
                result = self._transcribe_single_file(file_info)
            
            # 更新統計資訊
            processing_time = time.time() - start_time
            result.processing_time = processing_time
            self.stats['total_processing_time'] += processing_time
            
            if result.success:
                self.stats['successful_requests'] += 1
                logger.info(f"轉錄成功: {file_info.audio_name} ({processing_time:.1f}秒)")
            else:
                self.stats['failed_requests'] += 1
                logger.error(f"轉錄失敗: {file_info.audio_name} - {result.error}")
            
            # 完成檔案處理進度追蹤
            self.progress_tracker.complete_file_processing(file_info, result)
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.stats['failed_requests'] += 1
            self.stats['total_processing_time'] += processing_time
            
            logger.error(f"轉錄過程發生錯誤: {e}")
            
            result = TranscriptionResult(
                success=False,
                error=str(e),
                processing_time=processing_time,
                model_used=self.config.transcription_model.value
            )
            
            # 完成檔案處理進度追蹤（即使失敗）
            self.progress_tracker.complete_file_processing(file_info, result)
            
            return result
    
    def _transcribe_single_file(self, file_info: FileInfo) -> TranscriptionResult:
        """轉錄單一檔案（帶重試機制）"""
        last_error = None
        
        for attempt in range(self.retry_config.max_attempts):
            try:
                if attempt > 0:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"重試轉錄 (第 {attempt + 1} 次): {file_info.audio_name}，等待 {delay:.1f} 秒")
                    
                    # 記錄重試嘗試
                    self.progress_tracker.record_retry_attempt(
                        file_info.audio_name, 
                        attempt + 1, 
                        str(last_error) if last_error else "未知錯誤"
                    )
                    
                    time.sleep(delay)
                    self.stats['retry_attempts'] += 1
                
                # 呼叫現有的轉錄函數
                content = transcribe_audio_gpt4o(
                    file_path=file_info.audio_path,
                    api_key=self.api_config.openai_api_key,
                    model=self.config.transcription_model.value,
                    language=self.config.transcription_language,
                    output_format="text"
                )
                
                return TranscriptionResult(
                    success=True,
                    content=content,
                    model_used=self.config.transcription_model.value,
                    language_detected=self.config.transcription_language,
                    segments_processed=1
                )
                
            except Exception as e:
                last_error = e
                error_type = self._classify_error(e)
                
                logger.warning(f"轉錄嘗試 {attempt + 1} 失敗: {e}")
                
                # 如果是不可重試的錯誤，直接失敗
                if not self._is_retryable_error(error_type):
                    logger.error(f"遇到不可重試錯誤: {error_type}")
                    break
                
                # 如果是最後一次嘗試，不再重試
                if attempt == self.retry_config.max_attempts - 1:
                    logger.error(f"已達到最大重試次數 ({self.retry_config.max_attempts})")
                    break
        
        # 所有重試都失敗
        return TranscriptionResult(
            success=False,
            error=f"轉錄失敗 (重試 {self.retry_config.max_attempts} 次): {str(last_error)}",
            model_used=self.config.transcription_model.value
        )
    
    def _transcribe_large_file(self, file_info: FileInfo) -> TranscriptionResult:
        """轉錄大型檔案（分割處理）"""
        temp_files = []
        temp_dir = None
        
        try:
            logger.info(f"開始處理大型檔案: {file_info.audio_name} ({file_info.file_size_mb:.1f}MB)")
            
            # 創建臨時目錄
            temp_dir = tempfile.mkdtemp(prefix=f"transcription_{file_info.audio_name}_")
            logger.debug(f"創建臨時目錄: {temp_dir}")
            
            # 分割音訊檔案
            segment_paths = split_large_audio(
                file_info.audio_path,
                max_duration_seconds=self.config.segment_duration_seconds
            )
            
            if not segment_paths:
                raise TranscriptionError(
                    "音訊檔案分割失敗，可能是格式不支援或檔案損壞",
                    error_type="file_processing_error",
                    retryable=False
                )
            
            # 如果分割後只有一個檔案，說明原檔案不需要分割
            if len(segment_paths) == 1 and segment_paths[0] == file_info.audio_path:
                logger.info("檔案無需分割，直接轉錄")
                return self._transcribe_single_file(file_info)
            
            temp_files = segment_paths
            logger.info(f"檔案已分割為 {len(segment_paths)} 個片段")
            
            # 轉錄每個片段
            all_transcripts = []
            total_tokens = 0
            successful_segments = 0
            
            for i, segment_path in enumerate(segment_paths):
                segment_name = Path(segment_path).name
                logger.info(f"轉錄片段 {i + 1}/{len(segment_paths)}: {segment_name}")
                
                # 更新片段進度
                self.progress_tracker.update_segment_progress(i, len(segment_paths))
                
                # 創建片段的 FileInfo
                segment_info = FileInfo(
                    audio_path=segment_path,
                    audio_name=f"{file_info.audio_name}_segment_{i + 1:03d}"
                )
                
                # 轉錄片段
                segment_result = self._transcribe_single_file(segment_info)
                
                if segment_result.success:
                    successful_segments += 1
                    all_transcripts.append(segment_result.content)
                    if segment_result.token_count:
                        total_tokens += segment_result.token_count
                    logger.debug(f"片段 {i + 1} 轉錄成功，內容長度: {len(segment_result.content)}")
                else:
                    logger.error(f"片段 {i + 1} 轉錄失敗: {segment_result.error}")
                    all_transcripts.append(f"\n[--- 片段 {i + 1} 轉錄失敗: {segment_result.error} ---]\n")
                
                # 更新完成的片段進度
                self.progress_tracker.update_segment_progress(i + 1, len(segment_paths))
                
                # 添加 API 速率限制延遲
                if i < len(segment_paths) - 1:
                    delay = self.config.api_rate_limit_delay
                    if delay > 0:
                        logger.debug(f"API 速率限制延遲: {delay} 秒")
                        time.sleep(delay)
            
            # 合併所有轉錄結果
            combined_content = self._merge_segment_transcripts(all_transcripts, file_info.audio_name)
            
            # 計算整體成功率
            success_rate = successful_segments / len(segment_paths) if segment_paths else 0
            
            # 判斷整體是否成功（至少 50% 的片段成功）
            overall_success = success_rate >= 0.5
            
            if not overall_success:
                error_msg = f"大部分片段轉錄失敗 (成功: {successful_segments}/{len(segment_paths)})"
                logger.error(error_msg)
                return TranscriptionResult(
                    success=False,
                    error=error_msg,
                    content=combined_content,
                    model_used=self.config.transcription_model.value,
                    segments_processed=len(segment_paths)
                )
            
            logger.info(f"大型檔案轉錄完成: 成功 {successful_segments}/{len(segment_paths)} 片段")
            
            return TranscriptionResult(
                success=True,
                content=combined_content,
                model_used=self.config.transcription_model.value,
                language_detected=self.config.transcription_language,
                token_count=total_tokens if total_tokens > 0 else None,
                segments_processed=len(segment_paths)
            )
            
        except Exception as e:
            logger.error(f"大型檔案轉錄失敗: {e}")
            return TranscriptionResult(
                success=False,
                error=f"大型檔案處理失敗: {str(e)}",
                model_used=self.config.transcription_model.value
            )
        
        finally:
            # 清理臨時檔案和目錄
            self._cleanup_temp_files(temp_files)
            if temp_dir and Path(temp_dir).exists():
                self._cleanup_temp_directory(temp_dir)
    
    def _merge_segment_transcripts(self, transcripts: List[str], audio_name: str) -> str:
        """合併分段轉錄結果"""
        if not transcripts:
            return ""
        
        # 添加檔案標題
        header = f"# {audio_name} - 語音轉錄結果\n\n"
        
        # 合併內容，為每個片段添加分隔符
        merged_parts = [header]
        
        for i, transcript in enumerate(transcripts):
            if transcript.strip():
                # 添加片段標記
                segment_header = f"## 片段 {i + 1}\n\n"
                merged_parts.append(segment_header)
                merged_parts.append(transcript.strip())
                merged_parts.append("\n\n")
        
        return "".join(merged_parts).strip()
    
    def _cleanup_temp_files(self, temp_files: List[str]) -> None:
        """清理臨時檔案"""
        if not temp_files:
            return
        
        cleaned_count = 0
        failed_count = 0
        
        for temp_file in temp_files:
            try:
                temp_path = Path(temp_file)
                if temp_path.exists():
                    if self._is_temp_file(temp_file):
                        temp_path.unlink()
                        cleaned_count += 1
                        logger.debug(f"已清理臨時檔案: {temp_file}")
                    else:
                        logger.warning(f"跳過非臨時檔案: {temp_file}")
                else:
                    logger.debug(f"臨時檔案已不存在: {temp_file}")
            except Exception as e:
                failed_count += 1
                logger.warning(f"清理臨時檔案失敗 {temp_file}: {e}")
        
        if cleaned_count > 0 or failed_count > 0:
            logger.info(f"臨時檔案清理完成: 成功 {cleaned_count} 個，失敗 {failed_count} 個")
    
    def _cleanup_temp_directory(self, temp_dir: str) -> None:
        """清理臨時目錄"""
        try:
            import shutil
            if Path(temp_dir).exists():
                shutil.rmtree(temp_dir)
                logger.debug(f"已清理臨時目錄: {temp_dir}")
        except Exception as e:
            logger.warning(f"清理臨時目錄失敗 {temp_dir}: {e}")
    
    def _is_temp_file(self, file_path: str) -> bool:
        """檢查是否為臨時檔案"""
        file_name = Path(file_path).name.lower()
        temp_patterns = [
            "temp_segment_",
            "transcription_",
            ".tmp",
            "segment_"
        ]
        
        return any(pattern in file_name for pattern in temp_patterns)
    
    def validate_file_for_transcription(self, file_info: FileInfo) -> tuple[bool, str]:
        """驗證檔案是否適合轉錄"""
        try:
            # 檢查檔案是否存在
            if not Path(file_info.audio_path).exists():
                return False, f"音訊檔案不存在: {file_info.audio_path}"
            
            # 檢查檔案是否可讀
            if not os.access(file_info.audio_path, os.R_OK):
                return False, f"無法讀取音訊檔案: {file_info.audio_path}"
            
            # 檢查檔案格式
            supported_formats = {
                '.mp3', '.wav', '.m4a', '.aac', '.flac', 
                '.ogg', '.wma', '.mp4', '.mov', '.avi', 
                '.mkv', '.webm'
            }
            
            file_ext = Path(file_info.audio_path).suffix.lower()
            if file_ext not in supported_formats:
                return False, f"不支援的音訊格式: {file_ext}"
            
            # 檢查檔案大小
            if file_info.file_size_mb <= 0:
                return False, "檔案大小無效"
            
            # 檢查是否超過系統限制（例如 100MB）
            max_system_limit = 100  # MB
            if file_info.file_size_mb > max_system_limit:
                return False, f"檔案過大，超過系統限制 {max_system_limit}MB: {file_info.file_size_mb:.1f}MB"
            
            return True, "檔案驗證通過"
            
        except Exception as e:
            return False, f"檔案驗證時發生錯誤: {str(e)}"
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """計算重試延遲時間"""
        if not self.retry_config.exponential_backoff:
            return self.retry_config.base_delay
        
        # 指數退避算法
        delay = self.retry_config.base_delay * (2 ** (attempt - 1))
        return min(delay, self.retry_config.max_delay)
    
    def _classify_error(self, error: Exception) -> str:
        """分類錯誤類型"""
        error_str = str(error).lower()
        
        if "api key" in error_str or "unauthorized" in error_str:
            return "api_key_error"
        elif "rate limit" in error_str or "quota" in error_str:
            return "rate_limit_error"
        elif "network" in error_str or "connection" in error_str or "timeout" in error_str:
            return "network_error"
        elif "file not found" in error_str or "no such file" in error_str:
            return "file_not_found"
        elif "permission" in error_str:
            return "permission_error"
        elif "format" in error_str or "codec" in error_str:
            return "format_error"
        else:
            return "unknown_error"
    
    def _is_retryable_error(self, error_type: str) -> bool:
        """判斷錯誤是否可重試"""
        retryable_errors = {
            "rate_limit_error",
            "network_error",
            "unknown_error"
        }
        
        non_retryable_errors = {
            "api_key_error",
            "file_not_found",
            "permission_error",
            "format_error"
        }
        
        if error_type in non_retryable_errors:
            return False
        elif error_type in retryable_errors:
            return True
        else:
            # 預設為可重試
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """取得轉錄服務統計資訊"""
        stats = self.stats.copy()
        
        # 計算成功率
        if stats['total_requests'] > 0:
            stats['success_rate'] = stats['successful_requests'] / stats['total_requests']
        else:
            stats['success_rate'] = 0.0
        
        # 計算平均處理時間
        if stats['successful_requests'] > 0:
            stats['avg_processing_time'] = stats['total_processing_time'] / stats['successful_requests']
        else:
            stats['avg_processing_time'] = 0.0
        
        return stats
    
    def get_progress_info(self) -> ProgressInfo:
        """取得當前進度資訊"""
        return self.progress_tracker.get_progress_info()
    
    def add_progress_callback(self, callback: Callable[[ProgressInfo], None]) -> None:
        """添加進度回調函數"""
        self.progress_tracker.add_progress_callback(callback)
    
    def transcribe_batch(self, file_infos: List[FileInfo]) -> List[TranscriptionResult]:
        """批次轉錄多個檔案"""
        if not file_infos:
            logger.warning("沒有檔案需要轉錄")
            return []
        
        # 開始批次處理
        self.progress_tracker.start_processing(len(file_infos))
        
        results = []
        start_time = time.time()
        
        try:
            logger.info(f"開始批次轉錄 {len(file_infos)} 個檔案")
            
            for i, file_info in enumerate(file_infos):
                logger.info(f"批次處理 ({i + 1}/{len(file_infos)}): {file_info.audio_name}")
                
                # 轉錄檔案
                result = self.transcribe_audio(file_info)
                results.append(result)
                
                # 記錄處理結果
                if result.success:
                    logger.info(f"✅ 檔案 {i + 1} 處理成功: {file_info.audio_name}")
                else:
                    logger.error(f"❌ 檔案 {i + 1} 處理失敗: {file_info.audio_name} - {result.error}")
            
            # 完成批次處理
            self.progress_tracker.complete_processing()
            
            # 統計結果
            total_time = time.time() - start_time
            successful_count = sum(1 for r in results if r.success)
            failed_count = len(results) - successful_count
            
            logger.info(f"批次轉錄完成: 成功 {successful_count}/{len(results)} 個檔案 ({total_time:.1f} 秒)")
            
            if failed_count > 0:
                logger.warning(f"有 {failed_count} 個檔案處理失敗")
            
            return results
            
        except Exception as e:
            logger.error(f"批次處理過程發生錯誤: {e}")
            self.progress_tracker.complete_processing()
            return results


def create_transcription_service(config: ProcessingConfig, 
                               progress_callback: Optional[Callable[[ProgressInfo], None]] = None) -> TranscriptionService:
    """創建轉錄服務實例"""
    service = TranscriptionService(config)
    
    if progress_callback:
        service.add_progress_callback(progress_callback)
    
    return service


# 進度回調函數範例
def console_progress_callback(progress_info: ProgressInfo) -> None:
    """控制台進度回調函數範例"""
    print(f"\r進度: {progress_info.get_display_info()}", end="", flush=True)


if __name__ == "__main__":
    """測試轉錄服務"""
    import logging
    
    # 設定日誌
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=== 轉錄服務測試 ===\n")
    
    try:
        # 創建測試配置
        from batch_audio_models import create_default_config
        config = create_default_config()
        
        # 創建轉錄服務（帶進度回調）
        service = create_transcription_service(config, console_progress_callback)
        
        print("✅ 轉錄服務創建成功")
        print(f"   模型: {config.transcription_model.value}")
        print(f"   語言: {config.transcription_language}")
        print(f"   重試次數: {config.retry_attempts}")
        print(f"   詳細日誌: {config.enable_detailed_logging}")
        
        # 顯示統計資訊
        stats = service.get_stats()
        print(f"\n📊 初始統計資訊:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # 顯示進度資訊
        progress = service.get_progress_info()
        print(f"\n📈 進度資訊:")
        print(f"   {progress.get_display_info()}")
        
    except Exception as e:
        print(f"❌ 轉錄服務測試失敗: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== 測試完成 ===")