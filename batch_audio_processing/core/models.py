"""
批次音訊處理系統 - 核心資料模型和配置系統
Core Data Models and Configuration System for Batch Audio Processing

此模組定義了批次音訊處理系統的核心資料結構，包括：
- 處理配置 (ProcessingConfig)
- 檔案資訊 (FileInfo)
- 轉錄結果 (TranscriptionResult)
- 摘要結果 (SummaryResult)
- API 配置和驗證機制

Requirements: 1.1, 7.1, 7.2, 7.5
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from pathlib import Path
from enum import Enum
import sys

from llm_provider_kit import (
    GEMINI_REFINE,
    GEMINI_REFINE_CHEAP,
    GEMINI_TRANSCRIBE,
    OPENAI_TRANSCRIBE,
)

# 設定日誌
logger = logging.getLogger(__name__)


class TranscriptionModel(Enum):
    """支援的轉錄模型（實際 id 見 model_config.py）"""
    OPENAI = OPENAI_TRANSCRIBE
    GEMINI = GEMINI_TRANSCRIBE


class OutputFormat(Enum):
    """支援的輸出格式"""
    TEXT = "text"
    MARKDOWN = "markdown"
    SRT = "srt"
    DOCX = "docx"


class SummaryModel(Enum):
    """支援的摘要模型（實際 id 見 model_config.py）"""
    GEMINI_FLASH = GEMINI_REFINE
    GEMINI_FLASH_LITE = GEMINI_REFINE_CHEAP


@dataclass
class ProcessingConfig:
    """
    處理配置類別
    
    包含所有處理參數和設定選項
    Requirements: 7.1, 7.2, 7.5
    """
    # 轉錄設定
    transcription_model: TranscriptionModel = TranscriptionModel.OPENAI
    transcription_language: str = "zh"
    
    # 摘要設定
    summary_model: SummaryModel = SummaryModel.GEMINI_FLASH
    
    # 輸出設定
    output_format: OutputFormat = OutputFormat.MARKDOWN
    enable_combined_output: bool = False
    enable_srt_support: bool = True
    
    # 並行處理設定
    max_workers: int = 2
    enable_parallel: bool = True
    
    # 錯誤處理和重試設定
    retry_attempts: int = 3
    retry_delay: float = 2.0
    exponential_backoff: bool = True
    
    # 檔案處理設定
    max_file_size_mb: int = 25
    segment_duration_seconds: int = 300  # 5 分鐘
    auto_split_large_files: bool = True
    
    # API 設定
    api_rate_limit_delay: float = 1.0
    api_timeout_seconds: int = 300
    
    # 日誌和報告設定
    enable_detailed_logging: bool = True
    log_level: str = "INFO"
    generate_processing_report: bool = True
    
    def __post_init__(self):
        """初始化後驗證配置"""
        self.validate()
    
    def validate(self) -> None:
        """
        驗證配置參數的有效性
        
        Raises:
            ValueError: 當配置參數無效時
        """
        # 驗證數值範圍
        if self.max_workers < 1:
            raise ValueError("max_workers 必須大於 0")
        
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts 不能為負數")
        
        if self.retry_delay < 0:
            raise ValueError("retry_delay 不能為負數")
        
        if self.max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb 必須大於 0")
        
        if self.segment_duration_seconds <= 0:
            raise ValueError("segment_duration_seconds 必須大於 0")
        
        if self.api_rate_limit_delay < 0:
            raise ValueError("api_rate_limit_delay 不能為負數")
        
        if self.api_timeout_seconds <= 0:
            raise ValueError("api_timeout_seconds 必須大於 0")
        
        # 驗證語言代碼
        valid_languages = ["zh", "en", "ja", "ko", "es", "fr", "de", "it", "pt", "ru"]
        if self.transcription_language not in valid_languages:
            logger.warning(f"語言代碼 '{self.transcription_language}' 可能不被支援")
        
        # 驗證日誌級別
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_log_levels:
            raise ValueError(f"log_level 必須是以下之一: {valid_log_levels}")
        
        logger.info("配置驗證通過")


@dataclass
class APIConfig:
    """
    API 配置和金鑰管理
    
    Requirements: 7.1, 7.2
    """
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    
    def __post_init__(self):
        """初始化後載入環境變數中的 API 金鑰"""
        if not self.openai_api_key:
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if not self.google_api_key:
            self.google_api_key = os.getenv('GOOGLE_API_KEY')
    
    def validate_api_keys(self) -> Dict[str, bool]:
        """
        驗證 API 金鑰是否存在和有效
        
        Returns:
            包含各 API 金鑰驗證狀態的字典
        """
        validation_results = {
            'openai': False,
            'google': False
        }
        
        # 檢查 OpenAI API 金鑰
        if self.openai_api_key and self.openai_api_key.strip():
            if self.openai_api_key.startswith('sk-'):
                validation_results['openai'] = True
                logger.info("OpenAI API 金鑰格式驗證通過")
            else:
                logger.warning("OpenAI API 金鑰格式可能不正確")
        else:
            logger.error("未找到 OpenAI API 金鑰")
        
        # 檢查 Google API 金鑰
        if self.google_api_key and self.google_api_key.strip():
            validation_results['google'] = True
            logger.info("Google API 金鑰存在")
        else:
            logger.error("未找到 Google API 金鑰")
        
        return validation_results
    
    def get_missing_keys(self) -> List[str]:
        """
        取得缺失的 API 金鑰列表
        
        Returns:
            缺失的 API 金鑰名稱列表
        """
        missing_keys = []
        
        if not self.openai_api_key or not self.openai_api_key.strip():
            missing_keys.append('OPENAI_API_KEY')
        
        if not self.google_api_key or not self.google_api_key.strip():
            missing_keys.append('GOOGLE_API_KEY')
        
        return missing_keys


@dataclass
class FileInfo:
    """
    檔案資訊類別
    
    包含音訊檔案和相關議程檔案的資訊
    Requirements: 1.1, 4.1, 4.2
    """
    audio_path: str
    audio_name: str
    agenda_path: Optional[str] = None
    agenda_content: Optional[str] = None
    file_size_mb: float = 0.0
    estimated_duration: Optional[float] = None
    file_format: Optional[str] = None
    
    def __post_init__(self):
        """初始化後計算檔案資訊"""
        self._calculate_file_info()
    
    def _calculate_file_info(self) -> None:
        """計算檔案大小和格式資訊"""
        try:
            audio_path = Path(self.audio_path)
            
            if audio_path.exists():
                # 計算檔案大小
                file_size_bytes = audio_path.stat().st_size
                self.file_size_mb = file_size_bytes / (1024 * 1024)
                
                # 取得檔案格式
                self.file_format = audio_path.suffix.lower().lstrip('.')
                
                # 設定檔案名稱（如果未提供）
                if not self.audio_name:
                    self.audio_name = audio_path.stem
                
                logger.debug(f"檔案資訊計算完成: {self.audio_name} ({self.file_size_mb:.2f}MB)")
            else:
                logger.warning(f"音訊檔案不存在: {self.audio_path}")
                
        except Exception as e:
            logger.error(f"計算檔案資訊時發生錯誤: {e}")
    
    def is_large_file(self, max_size_mb: int = 25) -> bool:
        """
        檢查是否為大型檔案
        
        Args:
            max_size_mb: 最大檔案大小限制（MB）
            
        Returns:
            如果檔案超過大小限制則返回 True
        """
        return self.file_size_mb > max_size_mb
    
    def get_display_info(self) -> str:
        """
        取得用於顯示的檔案資訊字串
        
        Returns:
            格式化的檔案資訊字串
        """
        info_parts = [
            f"檔案: {self.audio_name}",
            f"大小: {self.file_size_mb:.2f}MB"
        ]
        
        if self.file_format:
            info_parts.append(f"格式: {self.file_format}")
        
        if self.estimated_duration:
            info_parts.append(f"時長: {self.estimated_duration:.1f}秒")
        
        if self.agenda_path:
            info_parts.append("有議程檔案")
        
        return " | ".join(info_parts)


@dataclass
class TranscriptionResult:
    """
    轉錄結果類別
    
    包含語音轉錄的結果和相關資訊
    Requirements: 2.1, 2.2, 2.3
    """
    success: bool
    content: str = ""
    error: Optional[str] = None
    processing_time: float = 0.0
    token_count: Optional[int] = None
    model_used: Optional[str] = None
    language_detected: Optional[str] = None
    confidence_score: Optional[float] = None
    segments_processed: int = 1
    
    def __post_init__(self):
        """初始化後驗證結果"""
        self._validate_result()
    
    def _validate_result(self) -> None:
        """驗證轉錄結果的一致性"""
        if self.success and not self.content.strip():
            logger.warning("轉錄標記為成功但內容為空")
        
        if not self.success and not self.error:
            logger.warning("轉錄標記為失敗但未提供錯誤訊息")
        
        if self.processing_time < 0:
            logger.warning("處理時間不能為負數")
            self.processing_time = 0.0
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        取得轉錄結果的統計資訊
        
        Returns:
            包含統計資訊的字典
        """
        stats = {
            'success': self.success,
            'content_length': len(self.content) if self.content else 0,
            'processing_time': self.processing_time,
            'segments_processed': self.segments_processed
        }
        
        if self.token_count:
            stats['token_count'] = self.token_count
        
        if self.model_used:
            stats['model_used'] = self.model_used
        
        if self.confidence_score:
            stats['confidence_score'] = self.confidence_score
        
        return stats
    
    def get_display_summary(self) -> str:
        """
        取得用於顯示的轉錄結果摘要
        
        Returns:
            格式化的結果摘要字串
        """
        if self.success:
            summary_parts = [
                f"✅ 轉錄成功",
                f"內容長度: {len(self.content)}字符",
                f"處理時間: {self.processing_time:.1f}秒"
            ]
            
            if self.segments_processed > 1:
                summary_parts.append(f"分段處理: {self.segments_processed}段")
            
            if self.model_used:
                summary_parts.append(f"模型: {self.model_used}")
            
            return " | ".join(summary_parts)
        else:
            return f"❌ 轉錄失敗: {self.error or '未知錯誤'}"


@dataclass
class SummaryResult:
    """
    摘要結果類別
    
    包含智能摘要的結果和相關資訊
    Requirements: 3.1, 3.2, 3.3, 3.4
    """
    success: bool
    content: str = ""
    error: Optional[str] = None
    processing_time: float = 0.0
    token_count: Optional[int] = None
    model_used: Optional[str] = None
    agenda_used: bool = False
    images_inserted: int = 0
    
    def __post_init__(self):
        """初始化後驗證結果"""
        self._validate_result()
    
    def _validate_result(self) -> None:
        """驗證摘要結果的一致性"""
        if self.success and not self.content.strip():
            logger.warning("摘要標記為成功但內容為空")
        
        if not self.success and not self.error:
            logger.warning("摘要標記為失敗但未提供錯誤訊息")
        
        if self.processing_time < 0:
            logger.warning("處理時間不能為負數")
            self.processing_time = 0.0
        
        if self.images_inserted < 0:
            logger.warning("插入圖片數量不能為負數")
            self.images_inserted = 0
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        取得摘要結果的統計資訊
        
        Returns:
            包含統計資訊的字典
        """
        stats = {
            'success': self.success,
            'content_length': len(self.content) if self.content else 0,
            'processing_time': self.processing_time,
            'agenda_used': self.agenda_used,
            'images_inserted': self.images_inserted
        }
        
        if self.token_count:
            stats['token_count'] = self.token_count
        
        if self.model_used:
            stats['model_used'] = self.model_used
        
        return stats
    
    def get_display_summary(self) -> str:
        """
        取得用於顯示的摘要結果摘要
        
        Returns:
            格式化的結果摘要字串
        """
        if self.success:
            summary_parts = [
                f"✅ 摘要成功",
                f"內容長度: {len(self.content)}字符",
                f"處理時間: {self.processing_time:.1f}秒"
            ]
            
            if self.agenda_used:
                summary_parts.append("使用議程")
            
            if self.images_inserted > 0:
                summary_parts.append(f"插入圖片: {self.images_inserted}張")
            
            if self.model_used:
                summary_parts.append(f"模型: {self.model_used}")
            
            return " | ".join(summary_parts)
        else:
            return f"❌ 摘要失敗: {self.error or '未知錯誤'}"


@dataclass
class DiscoveryResult:
    """
    檔案發現結果類別
    
    包含檔案搜索和匹配的結果
    Requirements: 1.1, 4.1, 4.5
    """
    audio_files: List[str] = field(default_factory=list)
    text_files: List[str] = field(default_factory=list)
    matched_pairs: Dict[str, str] = field(default_factory=dict)
    unmatched_audio: List[str] = field(default_factory=list)
    skipped_files: List[str] = field(default_factory=list)  # 被跳過的檔案（已有轉錄）
    total_size_mb: float = 0.0
    
    def __post_init__(self):
        """初始化後計算統計資訊"""
        self._calculate_stats()
    
    def _calculate_stats(self) -> None:
        """計算檔案發現的統計資訊"""
        try:
            total_size = 0.0
            for audio_file in self.audio_files:
                if Path(audio_file).exists():
                    file_size = Path(audio_file).stat().st_size
                    total_size += file_size / (1024 * 1024)  # 轉換為 MB
            
            self.total_size_mb = total_size
            
            # 計算未匹配的音訊檔案
            matched_audio_files = set(self.matched_pairs.keys())
            all_audio_files = set(self.audio_files)
            self.unmatched_audio = list(all_audio_files - matched_audio_files)
            
        except Exception as e:
            logger.error(f"計算檔案發現統計時發生錯誤: {e}")
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        取得檔案發現的統計資訊
        
        Returns:
            包含統計資訊的字典
        """
        return {
            'total_audio_files': len(self.audio_files),
            'total_text_files': len(self.text_files),
            'matched_pairs': len(self.matched_pairs),
            'unmatched_audio': len(self.unmatched_audio),
            'skipped_files': len(self.skipped_files),
            'total_size_mb': self.total_size_mb
        }
    
    def get_display_summary(self) -> str:
        """
        取得用於顯示的檔案發現摘要
        
        Returns:
            格式化的發現結果摘要字串
        """
        summary_parts = [
            f"音訊檔案: {len(self.audio_files)}個",
            f"文字檔案: {len(self.text_files)}個",
            f"配對成功: {len(self.matched_pairs)}對",
            f"總大小: {self.total_size_mb:.1f}MB"
        ]
        
        if self.unmatched_audio:
            summary_parts.append(f"未配對: {len(self.unmatched_audio)}個")
        
        if self.skipped_files:
            summary_parts.append(f"已轉錄跳過: {len(self.skipped_files)}個")
        
        return " | ".join(summary_parts)


def create_default_config() -> ProcessingConfig:
    """
    創建預設的處理配置
    
    Returns:
        預設的 ProcessingConfig 實例
    """
    return ProcessingConfig()


def load_config_from_env() -> ProcessingConfig:
    """
    從環境變數載入配置
    
    Returns:
        從環境變數載入的 ProcessingConfig 實例
    """
    config = ProcessingConfig()
    
    # 從環境變數載入配置（如果存在）
    if os.getenv('TRANSCRIPTION_MODEL'):
        try:
            config.transcription_model = TranscriptionModel(os.getenv('TRANSCRIPTION_MODEL'))
        except ValueError:
            logger.warning(f"無效的轉錄模型: {os.getenv('TRANSCRIPTION_MODEL')}")
    
    if os.getenv('OUTPUT_FORMAT'):
        try:
            config.output_format = OutputFormat(os.getenv('OUTPUT_FORMAT'))
        except ValueError:
            logger.warning(f"無效的輸出格式: {os.getenv('OUTPUT_FORMAT')}")
    
    if os.getenv('MAX_WORKERS'):
        try:
            config.max_workers = int(os.getenv('MAX_WORKERS'))
        except ValueError:
            logger.warning(f"無效的 MAX_WORKERS 值: {os.getenv('MAX_WORKERS')}")
    
    if os.getenv('RETRY_ATTEMPTS'):
        try:
            config.retry_attempts = int(os.getenv('RETRY_ATTEMPTS'))
        except ValueError:
            logger.warning(f"無效的 RETRY_ATTEMPTS 值: {os.getenv('RETRY_ATTEMPTS')}")
    
    return config


def validate_system_requirements() -> Dict[str, bool]:
    """
    驗證系統需求和依賴
    
    Returns:
        包含各項需求驗證狀態的字典
    """
    requirements = {
        'api_keys': False,
        'dependencies': False,
        'file_permissions': False
    }
    
    try:
        # 檢查 API 金鑰
        api_config = APIConfig()
        api_validation = api_config.validate_api_keys()
        requirements['api_keys'] = all(api_validation.values())
        
        # 檢查必要的依賴套件
        try:
            import openai
            import google.genai
            from pydub import AudioSegment
            from docx import Document
            requirements['dependencies'] = True
            logger.info("所有必要依賴套件已安裝")
        except ImportError as e:
            logger.error(f"缺少必要依賴套件: {e}")
            requirements['dependencies'] = False
        
        # 檢查檔案權限（創建臨時檔案測試）
        try:
            test_file = Path("temp_permission_test.txt")
            test_file.write_text("test")
            test_file.unlink()
            requirements['file_permissions'] = True
            logger.info("檔案權限檢查通過")
        except Exception as e:
            logger.error(f"檔案權限檢查失敗: {e}")
            requirements['file_permissions'] = False
        
    except Exception as e:
        logger.error(f"系統需求驗證時發生錯誤: {e}")
    
    return requirements


if __name__ == "__main__":
    """測試模組功能"""
    # 設定日誌
    logging.basicConfig(level=logging.INFO)
    
    print("=== 批次音訊處理系統 - 核心資料模型測試 ===\n")
    
    # 測試配置系統
    print("1. 測試配置系統...")
    try:
        config = create_default_config()
        print(f"✅ 預設配置創建成功")
        print(f"   轉錄模型: {config.transcription_model.value}")
        print(f"   輸出格式: {config.output_format.value}")
        print(f"   最大工作者: {config.max_workers}")
    except Exception as e:
        print(f"❌ 配置系統測試失敗: {e}")
    
    # 測試 API 配置
    print("\n2. 測試 API 配置...")
    try:
        api_config = APIConfig()
        validation_results = api_config.validate_api_keys()
        missing_keys = api_config.get_missing_keys()
        
        print(f"   OpenAI API: {'✅' if validation_results['openai'] else '❌'}")
        print(f"   Google API: {'✅' if validation_results['google'] else '❌'}")
        
        if missing_keys:
            print(f"   缺少的 API 金鑰: {', '.join(missing_keys)}")
    except Exception as e:
        print(f"❌ API 配置測試失敗: {e}")
    
    # 測試系統需求
    print("\n3. 測試系統需求...")
    try:
        requirements = validate_system_requirements()
        for req_name, status in requirements.items():
            print(f"   {req_name}: {'✅' if status else '❌'}")
    except Exception as e:
        print(f"❌ 系統需求測試失敗: {e}")
    
    print("\n=== 測試完成 ===")