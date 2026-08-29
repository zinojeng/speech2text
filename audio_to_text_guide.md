# Audio to Text 執行指南

本指南說明如何使用此專案執行音訊轉文字功能。

## 快速開始

### 方法一：Shell 腳本批次處理（推薦）

最簡單的方式是使用 `audio_auto.sh` 腳本：

```bash
# 基本用法
./audio_auto.sh [資料夾路徑] [模型] [格式] [--combined]

# 範例：處理資料夾中所有音檔
./audio_auto.sh /path/to/audio/folder gpt-4o-mini-transcribe text

# 生成 SRT 字幕檔
./audio_auto.sh /path/to/audio/folder gpt-4o-mini-transcribe srt

# 合併所有轉錄結果為單一檔案
./audio_auto.sh /path/to/audio/folder gpt-4o-mini-transcribe text --combined
```

### 方法二：Streamlit UI 介面

使用圖形化介面操作：

```bash
./start_app.sh
```

然後在瀏覽器開啟：http://127.0.0.1:8501

### 方法三：Python 命令列

#### 單一檔案轉錄
```bash
python gpt4o_transcribe.py audio.mp3 --model gpt-4o-mini-transcribe --format text
```

#### 批次處理多個檔案
```bash
python batch_audio_processor.py /path/to/folder [model]
```

## 前置需求

### 1. 設定 API Keys

在專案根目錄建立 `.env` 檔案：

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
GOOGLE_API_KEY=your_google_api_key_here
# 選擇性：
# ELEVENLABS_API_KEY=your_elevenlabs_key
```

### 2. 啟動虛擬環境

```bash
# 主應用程式環境
source venv_app/bin/activate

# 或開發環境
source venv/bin/activate
```

### 3. 安裝依賴

```bash
pip install -r requirements.txt
```

## 支援的模型

### GPT-4o 模型
- `gpt-4o-mini-transcribe` - 預設選項，較經濟實惠
- `gpt-4o-transcribe` - 更高品質，但較昂貴

### 其他後端
- Whisper (本地處理)
- ElevenLabs (支援說話者辨識)

## 支援的格式

### 音訊格式
- mp3, wav, m4a, aac, flac, ogg, wma
- mp4, mov, avi, mkv, webm (影片檔案的音訊)

### 輸出格式
- `text` - 純文字檔案 (.txt)
- `markdown` - Markdown 格式 (.md)
- `srt` - 字幕檔案 (.srt)

## 常用範例

### 1. 處理單一音檔
```bash
python gpt4o_transcribe.py interview.mp3 --language zh --format text
```

### 2. 批次處理整個資料夾
```bash
./audio_auto.sh ~/Desktop/recordings gpt-4o-mini-transcribe text
```

### 3. 生成字幕檔
```bash
./audio_auto.sh ./videos gpt-4o-mini-transcribe srt
```

### 4. 合併多個音檔轉錄結果
```bash
./audio_auto.sh ./meeting_recordings gpt-4o-mini-transcribe text --combined
```

### 5. 使用較高品質模型
```bash
./audio_auto.sh ./important_audio gpt-4o-transcribe markdown
```

## 進階功能

### 自動檔案分割
- 大於 25MB 的檔案會自動分割成 5 分鐘的片段
- 分割後的檔案會自動合併轉錄結果

### 合併輸出模式
使用 `--combined` 參數時：
- **SRT 格式**：自動調整時間軸，連續播放
- **文字格式**：添加檔案標題分隔

### 遞迴資料夾處理
- 自動搜尋子資料夾中的所有音檔
- 保持原始資料夾結構輸出

### 議程檔案配對
- 可自動尋找同名的文字檔案作為議程
- 支援 txt, md, docx 等格式

## 疑難排解

### API Key 錯誤
確認 `.env` 檔案中的 API Key 格式正確：
```bash
# 檢查 .env 檔案
cat .env | grep API_KEY
```

### 檔案太大錯誤
檔案會自動分割，但如果仍有問題：
```bash
# 手動分割音檔
python -c "from utils import split_large_audio; split_large_audio('large_file.mp3')"
```

### 虛擬環境問題
```bash
# 重新建立虛擬環境
python3 -m venv venv_app
source venv_app/bin/activate
pip install -r requirements.txt
```

## 批次處理流程

1. **準備音檔資料夾**
   - 將所有音檔放在同一資料夾（可包含子資料夾）
   - 可選：準備同名的議程檔案

2. **執行批次處理**
   ```bash
   ./audio_auto.sh /path/to/folder
   ```

3. **檢查輸出**
   - 個別模式：每個音檔會有對應的輸出檔案
   - 合併模式：在資料夾根目錄生成 `combined_transcription.*`

## 成本估算

- **gpt-4o-mini-transcribe**：約 $0.10 / 小時
- **gpt-4o-transcribe**：約 $0.30 / 小時
- 本地 Whisper：免費但較慢

## 最佳實踐

1. **一般用途**：使用 `gpt-4o-mini-transcribe`
2. **重要內容**：使用 `gpt-4o-transcribe`
3. **大量檔案**：使用批次處理並啟用合併模式
4. **字幕製作**：使用 SRT 格式輸出
5. **檔案整理**：先整理好資料夾結構再批次處理

## 相關檔案

- `audio_auto.sh` - 批次處理腳本
- `gpt4o_transcribe.py` - 單檔轉錄程式
- `batch_audio_processor.py` - Python 批次處理器
- `main_app.py` - Streamlit 主介面
- `utils.py` - 工具函數（檔案分割等）