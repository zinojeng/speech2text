"""
配置載入器 - 批次音訊處理系統
Configuration Loader for Batch Audio Processing System

此模組提供配置載入和驗證的實用工具，包括：
- 從檔案載入配置
- 從命令列參數載入配置
- 配置合併和覆蓋
- 配置驗證和錯誤處理

Requirements: 7.1, 7.2, 7.5
"""

import os
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import asdict

from ..core.models import (
    ProcessingConfig, APIConfig, TranscriptionModel, 
    OutputFormat, SummaryModel, validate_system_requirements
)

logger = logging.getLogger(__name__)


class ConfigLoader:
    """配置載入器類別"""
    
    def __init__(self):
        self.config_file_paths = [
            Path.cwd() / "batch_config.json",
            Path.home() / ".batch_audio_config.json",
            Path("/etc/batch_audio/config.json")
        ]
    
    def load_from_file(self, config_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        從 JSON 檔案載入配置
        
        Args:
            config_path: 配置檔案路徑，如果未提供則搜索預設位置
            
        Returns:
            配置字典，如果載入失敗則返回 None
        """
        search_paths = [Path(config_path)] if config_path else self.config_file_paths
        
        for config_file in search_paths:
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    
                    logger.info(f"從檔案載入配置: {config_file}")
                    return config_data
                    
                except (json.JSONDecodeError, IOError) as e:
                    logger.error(f"載入配置檔案失敗 {config_file}: {e}")
                    continue
        
        logger.info("未找到配置檔案，使用預設配置")
        return None
    
    def save_to_file(self, config: ProcessingConfig, config_path: str) -> bool:
        """
        將配置儲存到 JSON 檔案
        
        Args:
            config: 要儲存的配置
            config_path: 儲存路徑
            
        Returns:
            儲存是否成功
        """
        try:
            config_dict = asdict(config)
            
            # 轉換 Enum 為字串值
            config_dict['transcription_model'] = config.transcription_model.value
            config_dict['output_format'] = config.output_format.value
            config_dict['summary_model'] = config.summary_model.value
            
            config_file = Path(config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"配置已儲存到: {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"儲存配置檔案失敗: {e}")
            return False
    
    def load_from_args(self, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        從命令列參數載入配置
        
        Args:
            args: 命令列參數列表，如果未提供則使用 sys.argv
            
        Returns:
            從命令列參數解析的配置字典
        """
        parser = argparse.ArgumentParser(
            description="批次音訊處理系統",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # 基本參數
        parser.add_argument(
            'folder_path',
            nargs='?',
            help='要處理的資料夾路徑'
        )
        
        parser.add_argument(
            '--config',
            type=str,
            help='配置檔案路徑'
        )
        
        # 轉錄設定
        parser.add_argument(
            '--model',
            type=str,
            choices=[model.value for model in TranscriptionModel],
            help='轉錄模型選擇'
        )
        
        parser.add_argument(
            '--language',
            type=str,
            default='zh',
            help='轉錄語言代碼 (預設: zh)'
        )
        
        # 輸出設定
        parser.add_argument(
            '--format',
            type=str,
            choices=[fmt.value for fmt in OutputFormat],
            help='輸出格式選擇'
        )
        
        parser.add_argument(
            '--combined',
            action='store_true',
            help='啟用組合輸出模式'
        )
        
        # 處理設定
        parser.add_argument(
            '--workers',
            type=int,
            help='並行工作者數量'
        )
        
        parser.add_argument(
            '--no-parallel',
            action='store_true',
            help='停用並行處理'
        )
        
        parser.add_argument(
            '--retry',
            type=int,
            help='重試次數'
        )
        
        parser.add_argument(
            '--max-size',
            type=int,
            help='最大檔案大小限制 (MB)'
        )
        
        # 日誌設定
        parser.add_argument(
            '--log-level',
            type=str,
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            help='日誌級別'
        )
        
        parser.add_argument(
            '--no-report',
            action='store_true',
            help='停用處理報告生成'
        )
        
        # 解析參數
        parsed_args = parser.parse_args(args)
        
        # 轉換為配置字典
        config_dict = {}
        
        if parsed_args.model:
            config_dict['transcription_model'] = parsed_args.model
        
        if parsed_args.language:
            config_dict['transcription_language'] = parsed_args.language
        
        if parsed_args.format:
            config_dict['output_format'] = parsed_args.format
        
        if parsed_args.combined:
            config_dict['enable_combined_output'] = True
        
        if parsed_args.workers:
            config_dict['max_workers'] = parsed_args.workers
        
        if parsed_args.no_parallel:
            config_dict['enable_parallel'] = False
        
        if parsed_args.retry:
            config_dict['retry_attempts'] = parsed_args.retry
        
        if parsed_args.max_size:
            config_dict['max_file_size_mb'] = parsed_args.max_size
        
        if parsed_args.log_level:
            config_dict['log_level'] = parsed_args.log_level
        
        if parsed_args.no_report:
            config_dict['generate_processing_report'] = False
        
        # 儲存額外資訊
        config_dict['_folder_path'] = parsed_args.folder_path
        config_dict['_config_file'] = parsed_args.config
        
        return config_dict
    
    def merge_configs(self, *config_dicts: Dict[str, Any]) -> Dict[str, Any]:
        """
        合併多個配置字典，後面的配置會覆蓋前面的配置
        
        Args:
            *config_dicts: 要合併的配置字典
            
        Returns:
            合併後的配置字典
        """
        merged_config = {}
        
        for config_dict in config_dicts:
            if config_dict:
                merged_config.update(config_dict)
        
        return merged_config
    
    def create_config_from_dict(self, config_dict: Dict[str, Any]) -> ProcessingConfig:
        """
        從字典創建 ProcessingConfig 實例
        
        Args:
            config_dict: 配置字典
            
        Returns:
            ProcessingConfig 實例
        """
        # 過濾掉不屬於 ProcessingConfig 的鍵
        valid_keys = set(ProcessingConfig.__dataclass_fields__.keys())
        filtered_dict = {k: v for k, v in config_dict.items() if k in valid_keys}
        
        # 轉換 Enum 字串為 Enum 實例
        if 'transcription_model' in filtered_dict:
            filtered_dict['transcription_model'] = TranscriptionModel(
                filtered_dict['transcription_model']
            )
        
        if 'output_format' in filtered_dict:
            filtered_dict['output_format'] = OutputFormat(
                filtered_dict['output_format']
            )
        
        if 'summary_model' in filtered_dict:
            filtered_dict['summary_model'] = SummaryModel(
                filtered_dict['summary_model']
            )
        
        return ProcessingConfig(**filtered_dict)
    
    def load_complete_config(self, args: Optional[List[str]] = None) -> tuple[ProcessingConfig, APIConfig, str]:
        """
        載入完整的配置，包括處理配置、API 配置和資料夾路徑
        
        Args:
            args: 命令列參數列表
            
        Returns:
            (ProcessingConfig, APIConfig, folder_path) 的元組
        """
        # 1. 載入命令列參數
        args_config = self.load_from_args(args)
        folder_path = args_config.pop('_folder_path', None)
        config_file = args_config.pop('_config_file', None)
        
        # 2. 載入檔案配置
        file_config = self.load_from_file(config_file)
        
        # 3. 載入環境變數配置
        env_config = self._load_from_env()
        
        # 4. 合併配置（優先順序：命令列 > 檔案 > 環境變數 > 預設值）
        merged_config = self.merge_configs(env_config, file_config, args_config)
        
        # 5. 創建配置實例
        processing_config = self.create_config_from_dict(merged_config)
        api_config = APIConfig()
        
        # 6. 如果沒有提供資料夾路徑，則互動式詢問
        if not folder_path:
            folder_path = self._get_interactive_folder_path()
        
        return processing_config, api_config, folder_path
    
    def _load_from_env(self) -> Dict[str, Any]:
        """從環境變數載入配置"""
        env_config = {}
        
        env_mappings = {
            'TRANSCRIPTION_MODEL': 'transcription_model',
            'TRANSCRIPTION_LANGUAGE': 'transcription_language',
            'OUTPUT_FORMAT': 'output_format',
            'MAX_WORKERS': ('max_workers', int),
            'RETRY_ATTEMPTS': ('retry_attempts', int),
            'MAX_FILE_SIZE_MB': ('max_file_size_mb', int),
            'LOG_LEVEL': 'log_level',
            'ENABLE_PARALLEL': ('enable_parallel', lambda x: x.lower() == 'true'),
            'ENABLE_COMBINED_OUTPUT': ('enable_combined_output', lambda x: x.lower() == 'true'),
        }
        
        for env_key, config_mapping in env_mappings.items():
            env_value = os.getenv(env_key)
            if env_value:
                if isinstance(config_mapping, tuple):
                    config_key, converter = config_mapping
                    try:
                        env_config[config_key] = converter(env_value)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"無效的環境變數值 {env_key}={env_value}: {e}")
                else:
                    env_config[config_mapping] = env_value
        
        return env_config
    
    def _get_interactive_folder_path(self) -> str:
        """互動式取得資料夾路徑"""
        print("=== 批次音訊處理系統 ===")
        print("請輸入要處理的資料夾路徑:")
        
        while True:
            folder_path = input("> ").strip().strip('"\'')
            
            if not folder_path:
                print("請輸入有效的資料夾路徑")
                continue
            
            if Path(folder_path).exists():
                return folder_path
            else:
                print(f"資料夾不存在: {folder_path}")
                print("請重新輸入:")


def setup_logging(config: ProcessingConfig) -> None:
    """
    根據配置設定日誌系統
    
    Args:
        config: 處理配置
    """
    log_level = getattr(logging, config.log_level.upper())
    
    # 設定日誌格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 設定日誌處理器
    handlers = [logging.StreamHandler()]
    
    if config.enable_detailed_logging:
        # 添加檔案日誌處理器
        log_file = Path.cwd() / "batch_processor.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)
    
    # 配置根日誌記錄器
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers,
        force=True  # 覆蓋現有配置
    )
    
    logger.info(f"日誌系統已設定，級別: {config.log_level}")


def validate_configuration(config: ProcessingConfig, api_config: APIConfig) -> List[str]:
    """
    驗證完整配置的有效性
    
    Args:
        config: 處理配置
        api_config: API 配置
        
    Returns:
        驗證錯誤訊息列表，如果為空則表示驗證通過
    """
    errors = []
    
    try:
        # 驗證處理配置
        config.validate()
    except ValueError as e:
        errors.append(f"處理配置錯誤: {e}")
    
    # 驗證 API 配置
    missing_keys = api_config.get_missing_keys()
    if missing_keys:
        errors.append(f"缺少 API 金鑰: {', '.join(missing_keys)}")
    
    # 驗證系統需求
    requirements = validate_system_requirements()
    if not requirements['dependencies']:
        errors.append("缺少必要的依賴套件")
    
    if not requirements['file_permissions']:
        errors.append("檔案權限不足")
    
    return errors


if __name__ == "__main__":
    """測試配置載入器功能"""
    # 設定基本日誌
    logging.basicConfig(level=logging.INFO)
    
    print("=== 配置載入器測試 ===\n")
    
    # 測試配置載入
    loader = ConfigLoader()
    
    try:
        # 測試從命令列參數載入
        print("1. 測試命令列參數載入...")
        test_args = ['test_folder', '--model', 'gpt-transcribe', '--format', 'srt', '--workers', '4']
        args_config = loader.load_from_args(test_args)
        print(f"✅ 命令列參數載入成功: {len(args_config)} 個參數")
        
        # 測試配置合併
        print("\n2. 測試配置合併...")
        env_config = {'max_workers': 2, 'log_level': 'DEBUG'}
        merged = loader.merge_configs(env_config, args_config)
        print(f"✅ 配置合併成功: {len(merged)} 個參數")
        
        # 測試創建配置實例
        print("\n3. 測試配置實例創建...")
        processing_config = loader.create_config_from_dict(merged)
        print(f"✅ 配置實例創建成功")
        print(f"   轉錄模型: {processing_config.transcription_model.value}")
        print(f"   輸出格式: {processing_config.output_format.value}")
        print(f"   工作者數量: {processing_config.max_workers}")
        
        # 測試配置驗證
        print("\n4. 測試配置驗證...")
        api_config = APIConfig()
        errors = validate_configuration(processing_config, api_config)
        if errors:
            print("⚠️  配置驗證發現問題:")
            for error in errors:
                print(f"   - {error}")
        else:
            print("✅ 配置驗證通過")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
    
    print("\n=== 測試完成 ===")