# 音訊轉文字與優化系統 (Speech-to-Text System)

這是一個整合了 ElevenLabs 語音轉文字和 OpenAI 文字優化功能的應用程式。系統能夠將音訊檔案轉換成文字，並提供文字優化和摘要整理功能。

## 功能特點

- 支援多種音訊格式（MP3、WAV、OGG、M4A）
- 多語言轉錄支援
- 說話者辨識功能（可選）
- 自動將文字轉換為繁體中文
- 提供文字摘要和重點整理
- 支援下載原始及優化後的文字

## 系統需求

- Python 3.8 或更高版本
- FFmpeg（用於音訊處理）

## 安裝步驟

1. 克隆專案：
```bash
git clone https://github.com/zinojeng/speech2text.git
cd speech2text
```

2. 安裝相依套件：
```bash
pip install -r requirements.txt
```

3. 設定環境變數：
   - 建立 `.env` 檔案
   - 加入以下內容：
   ```
   OPENAI_API_KEY=your_openai_api_key
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   ```

## 使用方法

1. 啟動應用程式：
```bash
streamlit run main_app.py
```

2. 在網頁界面中：
   - 輸入 API 金鑰
   - 選擇音訊語言
   - 上傳音訊檔案
   - 設定所需選項（如說話者辨識）
   - 點擊「處理音訊」開始轉換

## 支援的語言

- 中文（普通話）
- 中文（粵語）
- 英文
- 日文
- 韓文
- 法文
- 德文
- 西班牙文
- 義大利文
- 俄文
- 越南文
- 泰文
- 印尼文
- 馬來文

## 注意事項

- 音訊檔案大小限制：25MB
- 建議使用高品質的音訊檔案以獲得更好的轉錄效果
- 確保網路連線穩定

## 授權

本專案採用 MIT 授權條款。詳見 [LICENSE](LICENSE) 檔案。

## 貢獻

歡迎提交 Issue 或 Pull Request 來改善專案。

## 作者

Zino Jeng 