# 音訊與文字處理程式使用指南

本文件說明三個專為 ADA 2025 年會內容處理所開發的程式工具。

## 📋 程式總覽

這三個程式形成完整的會議內容處理工作流程：

```
音訊檔案 → [batch_audio_processor.py] → 轉錄文字
                        ↓
              [process_transcription.py] → 智能摘要
                        ↓
         [merge_transcript_slides.py] → 完整會議筆記
```

---

## 1. 🎙️ batch_audio_processor.py - 批次音訊轉錄處理器

### 主要功能
- 自動搜索並處理資料夾中的所有音訊檔案
- 使用 OpenAI GPT-4o 進行高品質語音轉錄
- 自動分割大型音訊檔案（>25MB 或 >5分鐘）
- 使用 Gemini-2.5-pro 進行內容摘要
- 批次生成 Word 文件報告

### 支援格式
音訊：`mp3, wav, m4a, aac, flac, ogg, wma, mp4, mov, avi, mkv, webm`
文字：`txt, md, rtf, doc, docx, pdf, html, htm, xml, json, csv`

### 使用方式
```bash
# 基本使用（預設使用 gpt-4o-mini-transcribe）
python batch_audio_processor.py

# 指定資料夾
python batch_audio_processor.py "/path/to/audio/folder"

# 指定模型
python batch_audio_processor.py "/path/to/folder" gpt-4o-transcribe
```

### 特殊功能
- **議程檔案配對**：自動尋找與音訊同名的文字檔案作為議程
- **大檔案處理**：自動分割成 5 分鐘片段
- **批次報告**：生成 `processing_report.docx` 統計處理結果

### 注意事項
- 需要設定 `OPENAI_API_KEY` 和 `GOOGLE_API_KEY`
- 已修改為使用 Gemini-2.5-pro（API key 已內建）

---

## 2. 📝 process_transcription.py - 轉錄文字智能摘要處理器

### 主要功能
- 處理已轉錄的文字檔案
- 使用 Gemini-2.5-pro 生成學術論文風格的會議筆記
- 保留完整內容並進行專業潤稿
- 生成結構化的 Markdown 和 Word 文件

### 使用方式
```bash
python process_transcription.py <transcription_file.txt>

# 範例
python process_transcription.py transcription-34.txt
```

### 輸出格式
- **Markdown 檔案**：`[原檔名]_summary.md`
- **Word 檔案**：`[原檔名]_summary.docx`

### 格式特點
- **段落式寫作**：流暢的學術風格敘述
- **重點標記**：
  - **粗體**：關鍵概念、藥物名稱、重要數據
  - __底線__：最重要的研究發現或結論
- **適度列表**：複雜資訊時使用項目符號增加可讀性

### 適用場景
- 處理已經轉錄完成的會議錄音文字
- 需要生成專業學術風格的會議筆記
- 單一檔案的深度處理

---

## 3. 🔄 merge_transcript_slides.py - 演講稿與投影片整合器

### 主要功能
- 智能合併演講稿與投影片內容
- 以演講者內容為主軸，投影片作為補充
- 使用 Gemini-2.5-pro 進行內容整合
- 生成完整、流暢的會議筆記

### 使用方式
```bash
# 基本使用
python merge_transcript_slides.py <transcript_file> <slides_file>

# 指定輸出名稱
python merge_transcript_slides.py transcript.txt slides.md lecture_notes

# 包含圖片嵌入（新功能）
python merge_transcript_slides.py transcript.txt slides.md output_name --images "./slides/folder"

# 範例
python merge_transcript_slides.py transcription-34.txt "AID and GLP-1.md"
python merge_transcript_slides.py transcription-34.txt slides.md output --images "./Slides/folder"
```

### 整合原則
1. **演講者優先**：保留完整演講內容，進行適度潤稿
2. **投影片補充**：
   - 添加具體數據、圖表說明
   - 填補演講未提及的重要資訊
   - 避免重複內容
3. **格式標記**：
   - __底線__：標記來自投影片的補充和延伸解讀
4. **圖片整合**（新功能）：
   - 支援 `--images` 參數載入投影片圖片
   - 自動解析圖片時間戳記（如 slide_009_t1m4.7s.jpg）
   - 在 Word 文件中嵌入實際圖片
   - Markdown 文件使用圖片連結格式

### 輸出檔案
- **Markdown**：`[指定名稱]_merged.md`（含圖片連結）
- **Word**：`[指定名稱]_merged.docx`（含嵌入圖片）

---

## 🔧 環境設定

### API 金鑰配置
```bash
# 在 .env 檔案中設定
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_key

# 或使用內建的 Google API Key（已在程式中設定）
GOOGLE_API_KEY=AIzaSyBUNvJo_D2KZV3UVVgQxvFlZC1aFfXIw9k
```

### 依賴套件
```bash
pip install openai google-generativeai python-docx python-dotenv pydub
```

---

## 📊 建議工作流程

### 完整會議處理流程
1. **錄音轉文字**：使用 `batch_audio_processor.py` 批次處理音訊
2. **深度摘要**：使用 `process_transcription.py` 生成學術筆記
3. **內容整合**：使用 `merge_transcript_slides.py` 合併演講與投影片

### 快速處理單一檔案
- 已有轉錄文字 → 直接使用 `process_transcription.py`
- 需要合併投影片 → 使用 `merge_transcript_slides.py`

---

## ❓ 常見問題

### Q1: 檔案路徑有空格怎麼辦？
使用引號包圍路徑：
```bash
python process_transcription.py "/path with spaces/file.txt"
```

### Q2: 如何處理超大檔案？
- `batch_audio_processor.py` 會自動分割大檔案
- 如果 API 超時，可以分批處理或使用較小的模型

### Q3: 輸出檔案在哪裡？
所有輸出檔案都保存在原始檔案的同一目錄中

### Q4: 如何更改輸出語言？
程式預設使用繁體中文（zh-tw），可在程式碼中的 SYSTEM_PROMPT 修改

---

## 📌 快速參考

| 程式 | 輸入 | 輸出 | 主要用途 |
|------|------|------|----------|
| batch_audio_processor.py | 音訊資料夾 | 轉錄文字 + Word | 批次音訊轉錄 |
| process_transcription.py | 轉錄文字 | 摘要 MD + Word | 智能摘要生成 |
| merge_transcript_slides.py | 演講稿 + 投影片 | 整合 MD + Word | 內容整合 |

---

最後更新：2024年1月15日