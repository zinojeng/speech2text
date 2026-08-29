# 摘要服務包裝器 (Summary Service Wrapper)

## 概述

本模組實作了批次音訊處理系統的摘要服務包裝器，整合現有的 `gemini_utils.py`，提供 ADA 2025 會議專用的智能摘要功能。

## 主要功能

### 4.1 SummaryService 基礎類別 ✅

- **整合 Gemini API**: 使用 `gemini-2.5-pro-preview-06-05` 模型
- **ADA 2025 專用提示詞**: 針對美國糖尿病學會年會內容優化
- **中文輸出**: 專業的中文醫學摘要格式
- **配置驅動**: 支援靈活的配置選項

### 4.2 議程內容整合 ✅

- **多格式支援**: 支援 txt, md, rtf, doc, docx, pdf, html, xml, json, csv 等格式
- **智能合併**: 根據議程結構智能合併轉錄文字和議程內容
- **結構分析**: 自動分析議程的時間結構和主題結構
- **中文格式化**: 優化中英文混排和標點符號

### 4.3 圖片標記處理 ✅

- **圖片檔案搜尋**: 遞歸搜尋資料夾中的圖片檔案
- **存在性檢查**: 驗證圖片檔案的存在性和可讀性
- **Markdown 連結**: 生成標準的 Markdown 格式圖片連結
- **智能插入**: 在適當位置插入圖片標記

### 4.4 錯誤處理和重試機制 ✅

- **分類錯誤處理**: 區分不同類型的 API 錯誤
- **重試策略**: 支援指數退避和固定延遲重試
- **備用策略**: 多層次的備用處理機制
- **品質驗證**: 全面的摘要品質評估

## 核心類別

### SummaryService

主要的摘要服務類別，提供完整的摘要生成功能。

```python
from batch_summary_service import SummaryService, SummaryRequest
from batch_audio_models import ProcessingConfig

# 創建配置
config = ProcessingConfig()

# 初始化服務
service = SummaryService(config)

# 創建請求
request = SummaryRequest(
    transcript="會議轉錄內容",
    agenda_content="議程內容",
    audio_folder="/path/to/images",
    file_name="meeting_001"
)

# 生成摘要
result = service.generate_summary(request)
```

### SummaryRequest

摘要請求資料類別，包含所有必要的輸入資訊。

```python
@dataclass
class SummaryRequest:
    transcript: str                    # 轉錄文字
    agenda_content: Optional[str]      # 議程內容
    agenda_path: Optional[str]         # 議程檔案路徑
    audio_folder: Optional[str]        # 音訊資料夾（用於圖片搜尋）
    file_name: str                     # 檔案名稱
    language: str                      # 語言設定
```

## 主要方法

### 摘要生成
- `generate_summary()`: 主要的摘要生成方法
- `_build_prompt()`: 構建 ADA 2025 專用提示詞
- `format_chinese_output()`: 格式化中文輸出

### 議程處理
- `process_agenda_file()`: 處理各種格式的議程檔案
- `merge_transcript_and_agenda()`: 智能合併轉錄和議程內容
- `_analyze_agenda_structure()`: 分析議程結構

### 圖片處理
- `_insert_image_markers()`: 插入圖片標記
- `_find_image_files()`: 搜尋圖片檔案
- `validate_image_files()`: 驗證圖片檔案
- `generate_image_gallery_markdown()`: 生成圖片畫廊

### 錯誤處理
- `handle_api_failure()`: 處理 API 失敗
- `apply_fallback_strategy()`: 應用備用策略
- `validate_summary_quality()`: 驗證摘要品質
- `_attempt_error_recovery()`: 嘗試錯誤恢復

## 錯誤處理策略

### 1. API 錯誤分類
- **AuthenticationError**: API 金鑰錯誤
- **QuotaError**: 配額超限
- **NetworkError**: 網路連線問題
- **ContentPolicyError**: 內容政策違規
- **ModelError**: 模型相關錯誤

### 2. 備用策略
- **備用模型**: 使用 Gemini 2.0 Flash
- **內容修改**: 清理敏感內容
- **簡單摘要**: 基於關鍵詞的基本摘要

### 3. 品質驗證
- 內容完整性檢查
- 結構清晰度評估
- 醫學術語覆蓋度
- 中文格式化品質
- 總體品質評分

## 配置選項

```python
# 在 ProcessingConfig 中的相關設定
summary_model: SummaryModel = SummaryModel.GEMINI_2_5_PRO
retry_attempts: int = 3
retry_delay: float = 2.0
exponential_backoff: bool = True
```

## 需求覆蓋

- ✅ **Requirements 3.1**: Gemini API 整合和 ADA 2025 提示詞
- ✅ **Requirements 3.2**: 議程內容整合和智能摘要
- ✅ **Requirements 3.3**: 中文輸出格式化
- ✅ **Requirements 3.4**: API 錯誤處理和重試機制
- ✅ **Requirements 3.5**: 圖片標記處理
- ✅ **Requirements 4.4**: 議程檔案處理
- ✅ **Requirements 8.2**: 重試機制和指數退避
- ✅ **Requirements 8.3**: 備用策略和錯誤恢復

## 測試

執行測試腳本來驗證實作：

```bash
python test_summary_service.py
```

測試涵蓋：
- 模組導入測試
- 服務結構測試  
- 需求覆蓋度測試

## 使用範例

### 基本使用

```python
# 基本摘要生成
service = SummaryService(config)
request = SummaryRequest(transcript="轉錄內容", file_name="test")
result = service.generate_summary(request)

if result.success:
    print(f"摘要生成成功: {len(result.content)} 字符")
    print(f"處理時間: {result.processing_time:.2f} 秒")
else:
    print(f"摘要生成失敗: {result.error}")
```

### 包含議程的摘要

```python
# 包含議程內容的摘要
request = SummaryRequest(
    transcript="轉錄內容",
    agenda_path="/path/to/agenda.txt",
    file_name="meeting_with_agenda"
)
result = service.generate_summary(request)
```

### 包含圖片的摘要

```python
# 包含圖片標記的摘要
request = SummaryRequest(
    transcript="轉錄內容",
    audio_folder="/path/to/images",
    file_name="meeting_with_images"
)
result = service.generate_summary(request)
print(f"插入了 {result.images_inserted} 個圖片標記")
```

## 注意事項

1. **API 金鑰**: 需要設定 `GOOGLE_API_KEY` 環境變數
2. **依賴套件**: 需要安裝 `google-generativeai` 和 `markitdown`
3. **檔案權限**: 確保有讀取議程檔案和圖片檔案的權限
4. **網路連線**: API 呼叫需要穩定的網路連線

## 未來擴展

- 支援更多摘要模型
- 增加更多語言支援
- 優化圖片分析功能
- 增強錯誤恢復機制