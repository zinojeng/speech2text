# 批次音訊處理系統
Batch Audio Processing System

一個完整的批次音訊處理解決方案，支援語音轉錄、智能摘要和文件生成。

## 功能特色

- 🎵 **批次音訊處理**: 支援多種音訊格式 (MP3, WAV, M4A, AAC 等)
- 🗣️ **語音轉錄**: 使用 OpenAI Whisper API 進行高品質轉錄
- 🤖 **智能摘要**: 使用 Google Gemini 生成結構化摘要
- 📄 **文件生成**: 支援 Markdown 和 DOCX 格式輸出
- 🔄 **錯誤恢復**: 智能重試機制和錯誤處理
- 📊 **進度追蹤**: 實時進度顯示和統計報告
- 📝 **結構化日誌**: 完整的處理日誌和監控

## 快速開始

### 安裝

```bash
# 安裝依賴
pip install -r requirements.txt

# 設定環境變數
export OPENAI_API_KEY="your-openai-api-key"
export GOOGLE_API_KEY="your-google-api-key"
```

### 基本使用

```python
from batch_audio_processing import BatchProcessor

# 創建處理器
processor = BatchProcessor()

# 處理整個資料夾
result = processor.process_folder("/path/to/audio/files")

# 處理單個檔案
result = processor.process_file("/path/to/audio.mp3")
```

### 簡化使用

```python
from batch_audio_processing import process_folder_simple, process_file_simple

# 一行處理資料夾
result = process_folder_simple("/path/to/audio/files")

# 一行處理檔案
result = process_file_simple("/path/to/audio.mp3")
```

## 進階配置

### 自訂配置

```python
from batch_audio_processing import BatchProcessor, ProcessingConfig

# 創建自訂配置
config = ProcessingConfig(
    transcription_model="gpt-4o-transcribe",
    summary_model="gemini-2.5-pro-preview-06-05",
    output_format="markdown",
    max_workers=4,
    retry_attempts=3
)

# 使用自訂配置
processor = BatchProcessor(config=config)
```

### 使用配置檔案

```python
# 從 JSON 檔案載入配置
processor = BatchProcessor(config_file="config.json")
```

配置檔案範例 (`config.json`):
```json
{
    "transcription_model": "gpt-4o-transcribe",
    "summary_model": "gemini-2.5-pro-preview-06-05",
    "output_format": "markdown",
    "max_workers": 2,
    "retry_attempts": 3,
    "enable_parallel": true,
    "enable_detailed_logging": true
}
```

## 檔案結構

```
batch_audio_processing/
├── __init__.py              # 主要 API 入口
├── batch_processor.py       # 主要處理器類別
├── README.md               # 說明文件
├── core/                   # 核心功能
│   ├── __init__.py
│   ├── models.py           # 資料模型
│   ├── error_handler.py    # 錯誤處理
│   ├── progress_tracker.py # 進度追蹤
│   └── logging_system.py   # 日誌系統
├── services/               # 處理服務
│   ├── __init__.py
│   ├── file_discovery.py   # 檔案發現
│   ├── transcription_service.py # 轉錄服務
│   ├── summary_service.py  # 摘要服務
│   ├── document_generator.py # 文件生成
│   └── processing_orchestrator.py # 處理協調
├── utils/                  # 工具模組
│   ├── __init__.py
│   └── config_loader.py    # 配置載入
└── tests/                  # 測試
    ├── __init__.py
    ├── test_error_handling_system.py
    └── test_processing_orchestrator.py
```

## API 參考

### BatchProcessor

主要的批次處理器類別。

#### 方法

- `process_folder(folder_path, output_dir=None, recursive=True)`: 處理資料夾
- `process_file(file_path, output_dir=None, agenda_file=None)`: 處理單個檔案
- `get_config()`: 取得當前配置
- `update_config(**kwargs)`: 更新配置
- `get_supported_formats()`: 取得支援的格式
- `validate_system()`: 驗證系統需求

### 便利函數

- `create_batch_processor(config_file=None)`: 創建處理器
- `process_folder_simple(folder_path, output_dir=None)`: 簡單資料夾處理
- `process_file_simple(file_path, output_dir=None)`: 簡單檔案處理

## 支援的格式

### 音訊格式
- MP3, WAV, M4A, AAC, FLAC, OGG, WMA
- MP4, MOV, AVI, MKV, WEBM (視訊檔案的音訊)

### 輸出格式
- Markdown (.md)
- Microsoft Word (.docx)
- SRT 字幕檔 (.srt)

## 錯誤處理

系統包含完整的錯誤處理機制：

- **自動重試**: 網路錯誤和 API 限制自動重試
- **錯誤分類**: 根據錯誤類型採用不同處理策略
- **恢復機制**: 嘗試自動恢復可修復的錯誤
- **詳細日誌**: 記錄所有錯誤和處理過程

## 監控和日誌

- **實時進度**: 使用 tqdm 顯示處理進度
- **結構化日誌**: JSON 和文字格式的詳細日誌
- **性能監控**: CPU、記憶體、磁碟使用監控
- **處理報告**: 自動生成詳細的處理報告

## 範例

### 處理會議錄音

```python
from batch_audio_processing import BatchProcessor

# 處理會議錄音資料夾
processor = BatchProcessor()
result = processor.process_folder("/path/to/meeting/recordings")

print(f"處理完成: {result['processed_files']}/{result['total_files']} 檔案")
print(f"成功率: {result['success_rate']:.1f}%")
```

### 自訂輸出格式

```python
from batch_audio_processing import ProcessingConfig, BatchProcessor

# 設定輸出為 DOCX 格式
config = ProcessingConfig(output_format="docx")
processor = BatchProcessor(config=config)

result = processor.process_folder("/path/to/audio", "/path/to/output")
```

## 疑難排解

### 常見問題

1. **API 金鑰錯誤**: 確保設定了正確的環境變數
2. **檔案格式不支援**: 檢查 `get_supported_formats()` 取得支援格式
3. **記憶體不足**: 減少 `max_workers` 參數
4. **網路錯誤**: 系統會自動重試，檢查網路連線

### 系統需求驗證

```python
from batch_audio_processing import BatchProcessor

processor = BatchProcessor()
requirements = processor.validate_system()

for requirement, status in requirements.items():
    print(f"{requirement}: {'✅' if status else '❌'}")
```

## 授權

MIT License

## 貢獻

歡迎提交 Issue 和 Pull Request！