# 音訊與文字處理程式使用指南

本文件說明專為 ADA 2025 年會內容處理所開發的程式工具。

## 📋 程式總覽

這些程式形成完整的會議內容處理工作流程：

```
音訊檔案 → [batch_audio_processor.py] → 轉錄文字
                        ↓
              [process_transcription.py] → 智能摘要
                        ↓
         [merge_transcript_slides.py] → 完整會議筆記
                        ↓
    [merge_transcript_multi_slides.py] → 多投影片整合筆記
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

## 4. 🔄🔄 merge_transcript_multi_slides.py - 多投影片整合器（新）

### 主要功能
- 支援同時整合多個投影片檔案與演講稿
- 每個投影片可以有對應的圖片資料夾
- 智能合併多份內容，避免重複
- 使用 Gemini-2.5-pro 進行整合
- 生成包含所有內容的完整筆記

### 使用方式
```bash
# 基本使用（多個投影片，無圖片）
python merge_transcript_multi_slides.py transcript.txt slides1.md slides2.md

# 指定輸出名稱
python merge_transcript_multi_slides.py transcript.txt slides1.md slides2.md --output merged_notes

# 單一投影片與圖片
python merge_transcript_multi_slides.py transcript.txt slides1.md:images1/

# 多個投影片與對應圖片
python merge_transcript_multi_slides.py transcript.txt slides1.md:images1/ slides2.md:images2/ --output final

# 混合使用（部分有圖片）
python merge_transcript_multi_slides.py transcript.txt slides1.md slides2.md:images2/ slides3.md
```

### 特殊功能
- **彈性輸入格式**：使用 `slides.md:images/` 格式指定圖片
- **智能時間戳記處理**：自動避免多個投影片圖片的時間衝突
- **流暢內容銜接**：確保多個投影片內容的自然過渡
- **批次圖片處理**：支援處理總計數十張圖片

### 輸出檔案
- **Markdown**：`[名稱]_multi_merged.md`（含圖片連結）
- **Word**：`[名稱]_multi_merged.docx`（含嵌入圖片）

### 適用場景
- 多位講者的聯合演講
- 分段式的長時間演講
- 需要整合多份相關投影片的會議
- 工作坊或教學課程的完整記錄

---

## 5. 🎯 互動式合併工具（Shell Scripts）

### interactive_merge.sh - 互動式引導工具

提供友善的互動式介面，一步步引導使用者完成合併流程。

**功能特點：**
- 🎨 彩色介面，清晰的步驟指引
- 📁 支援檔案拖放
- 🖼️ 自動偵測圖片數量
- ✅ 輸入驗證和錯誤處理
- 🔄 可重複執行

**使用方式：**
```bash
./interactive_merge.sh
```

**互動流程：**
1. 選擇演講稿檔案（支援拖放）
2. 選擇單一或多個投影片模式
3. 逐一輸入投影片檔案和圖片資料夾
4. 設定輸出名稱（可選）
5. 確認並執行

### quick_merge.sh - 快速命令列工具

適合熟悉命令列的使用者，快速執行合併。

**使用方式：**
```bash
# 單一投影片
./quick_merge.sh transcript.txt slides.md

# 多個投影片
./quick_merge.sh transcript.txt slides1.md slides2.md slides3.md
```

**特點：**
- 自動判斷單一或多投影片模式
- 簡潔的執行過程
- 適合批次處理或腳本整合

---

## 🔧 環境設定

### API 金鑰配置

⚠️ **重要安全提醒**：絕對不要將 API 金鑰硬編碼在程式中或提交到版本控制系統！

1. **複製範例檔案**：
```bash
cp .env.example .env
```

2. **編輯 .env 檔案，填入您的 API 金鑰**：
```bash
# 必需的 API Keys
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here

# 選用
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

3. **確保 .env 在 .gitignore 中**（已設定）

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

### Python 程式

| 程式 | 輸入 | 輸出 | 主要用途 |
|------|------|------|----------|
| batch_audio_processor.py | 音訊資料夾 | 轉錄文字 + Word | 批次音訊轉錄 |
| process_transcription.py | 轉錄文字 | 摘要 MD + Word | 智能摘要生成 |
| merge_transcript_slides.py | 演講稿 + 投影片 | 整合 MD + Word | 內容整合 |
| merge_transcript_multi_slides.py | 演講稿 + 多投影片 | 整合 MD + Word | 多投影片整合 |

### Shell 腳本

| 腳本 | 用途 | 特點 |
|------|------|------|
| interactive_merge.sh | 互動式合併引導 | 友善介面、步驟引導 |
| quick_merge.sh | 快速命令列合併 | 簡潔快速、適合批次 |
| audio_auto.sh | 音訊批次處理 | 自動分割、格式選擇 |
| start_app.sh | 啟動主程式 | Streamlit 介面 |

---

最後更新：2025年1月15日

## 🐛 已知問題與解決方案

### 圖片未顯示在 Markdown/Word 中
**問題**：Gemini 生成的內容使用 `> 🖼️ **投影片圖表說明**（[3m34.7s]）：` 格式，或 `[IMAGE: t1m4.7s]` 格式，而非程式原本期待的 `[IMAGE: 214.7]` 格式。

**解決方案**：
- 程式已更新以支援多種格式
- 支援時間格式：`3m34.7s`、`214.7`、`214.7s`、`t1m4.7s`
- 自動移除 't' 前綴並正確解析時間
- 如果圖片仍未顯示，請檢查：
  1. 圖片路徑是否正確
  2. 圖片檔名是否包含時間戳記（如 `slide_009_t1m4.7s.jpg`）
  3. 時間容差設定（預設 30 秒）