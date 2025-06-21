---
title: 音訊轉文字與優化系統
emoji: 🎙️
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.19.2
app_file: app.py
pinned: false
---

# Speech2Text 應用程式

一個功能強大的音訊轉文字和文件處理系統，提供語音轉錄、文字優化和文件轉換功能。

## 快速啟動

使用以下指令快速啟動應用程式：

```bash
./start_app.sh
```

這個腳本會自動：
1. 檢查並創建虛擬環境（如果不存在）
2. 啟動虛擬環境
3. 安裝所需依賴
4. 檢查 ffmpeg 是否已安裝
5. 啟動應用程式

## 故障排除

### 修復 magika 套件問題

如果遇到 PDF 轉換失敗，錯誤信息包含 "JSONDecodeError"，請執行：

```bash
python fix_magika.py
```

### 音訊處理問題

如果遇到音訊處理問題，請確保已安裝 ffmpeg：

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows (使用 Chocolatey)
choco install ffmpeg
```

## 系統需求

- Python 3.8 或更高版本
- 網絡連接（用於 API 調用）
- ffmpeg（用於音訊處理，可選但推薦）

## 主要功能

1. **文件轉換與關鍵詞**：將各種格式文件轉為 Markdown
2. **語音轉文字**：將音訊檔案轉換為文字
3. **文字優化**：優化轉錄文字，製作會議記錄或講稿

## API 設定

應用程式使用以下 API 服務：
- OpenAI API（用於語音轉錄和文字優化）
- Google Gemini API（用於文字優化，可選）
- ElevenLabs API（用於高級語音轉錄，可選）

請在應用程式側邊欄設定相應的 API 金鑰。

## 作者

**Tseng Yao Hsien**  
Endocrinologist  
Tungs' Taichung MetroHarbor Hospital 