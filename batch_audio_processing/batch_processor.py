"""
批次音訊處理器 - 主要入口點
Batch Audio Processor - Main Entry Point

提供簡單易用的 API 來處理批次音訊檔案
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from .core import (
    ProcessingConfig,
    APIConfig,
    create_default_error_handler,
    create_progress_tracker,
    create_logging_system
)

from .services import (
    FileDiscovery,
    ProcessingOrchestrator
)

from .utils import ConfigLoader

# 設定日誌
logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    批次音訊處理器
    
    提供簡單的 API 來處理批次音訊檔案，包括：
    - 自動檔案發現
    - 語音轉錄
    - 智能摘要
    - 文件生成
    - 錯誤處理和恢復
    - 進度追蹤
    """
    
    def __init__(self, config: Optional[ProcessingConfig] = None, 
                 config_file: Optional[str] = None):
        """
        初始化批次處理器
        
        Args:
            config: 處理配置物件
            config_file: 配置檔案路徑
        """
        # 載入配置
        if config:
            self.config = config
        elif config_file and Path(config_file).exists():
            config_loader = ConfigLoader()
            self.config = config_loader.load_config(config_file)
        else:
            self.config = ProcessingConfig()
        
        # 驗證 API 配置
        self.api_config = APIConfig()
        api_validation = self.api_config.validate_api_keys()
        
        if not any(api_validation.values()):
            missing_keys = self.api_config.get_missing_keys()
            raise ValueError(f"缺少必要的 API 金鑰: {', '.join(missing_keys)}")
        
        # 初始化核心系統
        self.error_handler = create_default_error_handler()
        self.progress_tracker = None  # 將在處理時初始化
        self.logging_system = create_logging_system("batch_processor")
        
        # 初始化服務
        self.file_discovery = FileDiscovery()
        self.orchestrator = ProcessingOrchestrator(
            config=self.config,
            api_config=self.api_config,
            error_handler=self.error_handler,
            logging_system=self.logging_system
        )
        
        self.logging_system.log_info("BatchProcessor 初始化完成", {
            'config': {
                'transcription_model': self.config.transcription_model.value,
                'summary_model': self.config.summary_model.value,
                'output_format': self.config.output_format.value,
                'max_workers': self.config.max_workers
            }
        })
    
    def process_folder(self, folder_path: str, output_dir: Optional[str] = None,
                      recursive: bool = True) -> Dict[str, Any]:
        """
        處理資料夾中的所有音訊檔案
        
        Args:
            folder_path: 要處理的資料夾路徑
            output_dir: 輸出目錄（可選）
            recursive: 是否遞歸搜索子資料夾
            
        Returns:
            處理結果摘要
        """
        folder_path = Path(folder_path)
        if not folder_path.exists():
            raise FileNotFoundError(f"資料夾不存在: {folder_path}")
        
        if not folder_path.is_dir():
            raise NotADirectoryError(f"路徑不是資料夾: {folder_path}")
        
        # 設定輸出目錄
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = folder_path / "output"
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # 檔案發現
            self.logging_system.log_stage_start("file_discovery", {
                'folder_path': str(folder_path),
                'recursive': recursive
            })
            
            with self.logging_system.timer("file_discovery"):
                discovery_result = self.file_discovery.discover_files(
                    str(folder_path), recursive
                )
            
            self.logging_system.log_stage_complete("file_discovery", 1.0, {
                'audio_files_found': len(discovery_result.audio_files),
                'text_files_found': len(discovery_result.text_files),
                'matched_pairs': len(discovery_result.matched_pairs),
                'total_size_mb': discovery_result.total_size_mb
            })
            
            if not discovery_result.audio_files:
                self.logging_system.log_warning("未找到音訊檔案", {
                    'folder_path': str(folder_path)
                })
                return {
                    'success': True,
                    'message': '未找到音訊檔案',
                    'processed_files': 0,
                    'failed_files': 0,
                    'total_files': 0
                }
            
            # 初始化進度追蹤
            batch_id = f"batch_{folder_path.name}_{int(os.path.getmtime(folder_path))}"
            self.progress_tracker = create_progress_tracker(batch_id)
            
            # 處理檔案
            result = self.orchestrator.process_batch(
                discovery_result,
                str(output_path),
                self.progress_tracker
            )
            
            # 生成最終報告
            final_report = self._generate_final_report(result, discovery_result)
            
            # 匯出報告
            report_file = output_path / "processing_report.json"
            self.logging_system.export_report(str(report_file))
            
            self.logging_system.log_info("批次處理完成", final_report)
            
            return final_report
            
        except Exception as e:
            error_info = self.error_handler.handle_error(e, {
                'folder_path': str(folder_path),
                'stage': 'batch_processing'
            })
            
            self.logging_system.log_error(f"批次處理失敗: {e}", {
                'folder_path': str(folder_path),
                'error_type': error_info.error_type.value
            })
            
            raise
        
        finally:
            # 清理資源
            if self.progress_tracker:
                self.progress_tracker.finish_batch()
            self.logging_system.cleanup()
    
    def process_file(self, file_path: str, output_dir: Optional[str] = None,
                    agenda_file: Optional[str] = None) -> Dict[str, Any]:
        """
        處理單個音訊檔案
        
        Args:
            file_path: 音訊檔案路徑
            output_dir: 輸出目錄（可選）
            agenda_file: 議程檔案路徑（可選）
            
        Returns:
            處理結果
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"檔案不存在: {file_path}")
        
        # 設定輸出目錄
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = file_path.parent / "output"
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # 創建檔案資訊
            from .core.models import DiscoveryResult
            
            discovery_result = DiscoveryResult(
                audio_files=[str(file_path)],
                text_files=[agenda_file] if agenda_file else [],
                matched_pairs={str(file_path): agenda_file} if agenda_file else {}
            )
            
            # 初始化進度追蹤
            batch_id = f"single_{file_path.stem}"
            self.progress_tracker = create_progress_tracker(batch_id)
            
            # 處理檔案
            result = self.orchestrator.process_batch(
                discovery_result,
                str(output_path),
                self.progress_tracker
            )
            
            return result
            
        except Exception as e:
            error_info = self.error_handler.handle_error(e, {
                'file_path': str(file_path),
                'stage': 'single_file_processing'
            })
            
            self.logging_system.log_error(f"檔案處理失敗: {e}", {
                'file_path': str(file_path),
                'error_type': error_info.error_type.value
            })
            
            raise
        
        finally:
            # 清理資源
            if self.progress_tracker:
                self.progress_tracker.finish_batch()
            self.logging_system.cleanup()
    
    def _generate_final_report(self, processing_result: Dict[str, Any],
                             discovery_result) -> Dict[str, Any]:
        """生成最終處理報告"""
        return {
            'success': True,
            'total_files': len(discovery_result.audio_files),
            'processed_files': processing_result.get('successful_files', 0),
            'failed_files': processing_result.get('failed_files', 0),
            'skipped_files': processing_result.get('skipped_files', 0),
            'total_size_mb': discovery_result.total_size_mb,
            'processing_time_seconds': processing_result.get('total_time', 0),
            'success_rate': processing_result.get('success_rate', 0),
            'error_summary': self.error_handler.get_error_summary(),
            'files_processed': processing_result.get('results', [])
        }
    
    def get_config(self) -> ProcessingConfig:
        """取得當前配置"""
        return self.config
    
    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                self.logging_system.log_warning(f"未知的配置參數: {key}")
    
    def get_supported_formats(self) -> List[str]:
        """取得支援的音訊格式"""
        from .services.file_discovery import AudioFileScanner
        return list(AudioFileScanner.SUPPORTED_AUDIO_FORMATS)
    
    def validate_system(self) -> Dict[str, bool]:
        """驗證系統需求"""
        from .core.models import validate_system_requirements
        return validate_system_requirements()


# 便利函數
def create_batch_processor(config_file: Optional[str] = None) -> BatchProcessor:
    """
    創建批次處理器的便利函數
    
    Args:
        config_file: 配置檔案路徑
        
    Returns:
        BatchProcessor 實例
    """
    return BatchProcessor(config_file=config_file)


def process_folder_simple(folder_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    簡單的資料夾處理函數
    
    Args:
        folder_path: 要處理的資料夾路徑
        output_dir: 輸出目錄
        
    Returns:
        處理結果
    """
    processor = create_batch_processor()
    return processor.process_folder(folder_path, output_dir)


def process_file_simple(file_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    簡單的檔案處理函數
    
    Args:
        file_path: 音訊檔案路徑
        output_dir: 輸出目錄
        
    Returns:
        處理結果
    """
    processor = create_batch_processor()
    return processor.process_file(file_path, output_dir)