#!/usr/bin/env python3
"""
批次音訊處理系統 - 使用範例
Batch Audio Processing System - Usage Examples

展示如何使用批次音訊處理系統的各種功能
"""

import os
import sys
from pathlib import Path

# 添加模組路徑
sys.path.append(str(Path(__file__).parent.parent))

from batch_audio_processing import (
    BatchProcessor,
    ProcessingConfig,
    process_folder_simple,
    process_file_simple
)


def example_basic_usage():
    """基本使用範例"""
    print("=== 基本使用範例 ===")
    
    # 檢查 API 金鑰
    if not os.getenv('OPENAI_API_KEY'):
        print("警告: 未設定 OPENAI_API_KEY 環境變數")
    if not os.getenv('GOOGLE_API_KEY'):
        print("警告: 未設定 GOOGLE_API_KEY 環境變數")
    
    try:
        # 創建處理器
        processor = BatchProcessor()
        
        # 驗證系統需求
        requirements = processor.validate_system()
        print("系統需求檢查:")
        for req, status in requirements.items():
            print(f"  {req}: {'✅' if status else '❌'}")
        
        # 顯示支援的格式
        formats = processor.get_supported_formats()
        print(f"\n支援的音訊格式: {', '.join(formats)}")
        
        # 顯示當前配置
        config = processor.get_config()
        print(f"\n當前配置:")
        print(f"  轉錄模型: {config.transcription_model.value}")
        print(f"  摘要模型: {config.summary_model.value}")
        print(f"  輸出格式: {config.output_format.value}")
        print(f"  最大工作者: {config.max_workers}")
        
    except Exception as e:
        print(f"基本使用範例失敗: {e}")


def example_custom_config():
    """自訂配置範例"""
    print("\n=== 自訂配置範例 ===")
    
    try:
        # 創建自訂配置
        config = ProcessingConfig(
            transcription_model="gpt-transcribe",
            summary_model="gemini-3.7-flash",
            output_format="markdown",
            max_workers=2,
            retry_attempts=3,
            enable_parallel=True,
            enable_detailed_logging=True
        )
        
        # 使用自訂配置創建處理器
        processor = BatchProcessor(config=config)
        
        print("自訂配置創建成功:")
        print(f"  轉錄模型: {config.transcription_model.value}")
        print(f"  摘要模型: {config.summary_model.value}")
        print(f"  輸出格式: {config.output_format.value}")
        print(f"  重試次數: {config.retry_attempts}")
        
    except Exception as e:
        print(f"自訂配置範例失敗: {e}")


def example_folder_processing():
    """資料夾處理範例"""
    print("\n=== 資料夾處理範例 ===")
    
    # 測試資料夾路徑
    test_folder = "/Volumes/WD_BLACK/國際年會/ADA2025/CGM in Action—Smarter Choices, Better Balance, Lasting Impact"
    
    if not Path(test_folder).exists():
        print(f"測試資料夾不存在: {test_folder}")
        print("請修改 test_folder 變數為實際存在的音訊檔案資料夾")
        return
    
    try:
        print(f"處理資料夾: {test_folder}")
        
        # 方法 1: 使用 BatchProcessor
        processor = BatchProcessor()
        result = processor.process_folder(test_folder, recursive=False)
        
        print("處理結果:")
        print(f"  總檔案數: {result['total_files']}")
        print(f"  成功處理: {result['processed_files']}")
        print(f"  處理失敗: {result['failed_files']}")
        print(f"  成功率: {result.get('success_rate', 0):.1f}%")
        
    except Exception as e:
        print(f"資料夾處理失敗: {e}")
        
        # 方法 2: 使用簡化函數（僅作示範，不實際執行）
        print("\n也可以使用簡化函數:")
        print("result = process_folder_simple('/path/to/audio/folder')")


def example_single_file_processing():
    """單檔案處理範例"""
    print("\n=== 單檔案處理範例 ===")
    
    # 測試檔案路徑
    test_file = "/Volumes/WD_BLACK/國際年會/ADA2025/CGM in Action—Smarter Choices, Better Balance, Lasting Impact/BM-OR01-1 - CGM in Action—Smarter Choices, Better Balance, Lasting Impact.mp3"
    
    if not Path(test_file).exists():
        print(f"測試檔案不存在: {test_file}")
        print("請修改 test_file 變數為實際存在的音訊檔案")
        return
    
    try:
        print(f"處理檔案: {Path(test_file).name}")
        
        # 方法 1: 使用 BatchProcessor
        processor = BatchProcessor()
        result = processor.process_file(test_file)
        
        print("處理結果:")
        print(f"  成功: {result.get('success', False)}")
        print(f"  處理時間: {result.get('processing_time_seconds', 0):.1f} 秒")
        
    except Exception as e:
        print(f"單檔案處理失敗: {e}")
        
        # 方法 2: 使用簡化函數（僅作示範，不實際執行）
        print("\n也可以使用簡化函數:")
        print("result = process_file_simple('/path/to/audio.mp3')")


def example_error_handling():
    """錯誤處理範例"""
    print("\n=== 錯誤處理範例 ===")
    
    try:
        # 嘗試處理不存在的檔案
        processor = BatchProcessor()
        result = processor.process_file("/nonexistent/file.mp3")
        
    except FileNotFoundError as e:
        print(f"檔案不存在錯誤（預期的）: {e}")
        
    except Exception as e:
        print(f"其他錯誤: {e}")
    
    print("錯誤處理系統會自動:")
    print("  - 分類錯誤類型")
    print("  - 實施重試策略")
    print("  - 記錄詳細日誌")
    print("  - 生成錯誤報告")


def example_monitoring():
    """監控和日誌範例"""
    print("\n=== 監控和日誌範例 ===")
    
    try:
        # 啟用詳細日誌的配置
        config = ProcessingConfig(
            enable_detailed_logging=True,
            log_level="DEBUG"
        )
        
        processor = BatchProcessor(config=config)
        
        print("監控功能包括:")
        print("  - 實時進度條 (tqdm)")
        print("  - 結構化日誌記錄")
        print("  - 系統性能監控")
        print("  - 處理時間統計")
        print("  - 錯誤統計和報告")
        print("  - 自動報告生成")
        
        print("\n日誌檔案位置:")
        print("  - logs/batch_processor_structured.log (JSON 格式)")
        print("  - logs/batch_processor.log (文字格式)")
        print("  - processing_report.json (處理報告)")
        
    except Exception as e:
        print(f"監控範例失敗: {e}")


def main():
    """主函數"""
    print("批次音訊處理系統 - 使用範例")
    print("=" * 50)
    
    # 執行各種範例
    example_basic_usage()
    example_custom_config()
    example_folder_processing()
    example_single_file_processing()
    example_error_handling()
    example_monitoring()
    
    print("\n" + "=" * 50)
    print("範例執行完成！")
    print("\n更多資訊請參考:")
    print("  - README.md: 完整說明文件")
    print("  - tests/: 測試範例")
    print("  - 各模組的 docstring")


if __name__ == "__main__":
    main()