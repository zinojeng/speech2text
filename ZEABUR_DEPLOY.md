# Zeabur 部署指南

## 📋 部署準備

### 必要文件
- ✅ `Dockerfile` - Docker 配置文件
- ✅ `requirements.txt` - Python 依賴項
- ✅ `main_app.py` - 主應用程式
- ✅ `.streamlit/config.toml` - Streamlit 配置
- ✅ `zeabur.json` - Zeabur 配置文件

### 環境變數設定
在 Zeabur 控制台中設定以下環境變數：

```bash
# Streamlit 配置
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_SERVER_PORT=8080
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# 可選：預設 API 金鑰（生產環境中建議使用 Zeabur 的加密環境變數）
# OPENAI_API_KEY=your_openai_api_key
# ELEVENLABS_API_KEY=your_elevenlabs_api_key
```

## 🚀 部署步驟

### 1. 推送到 GitHub
```bash
git add .
git commit -m "Prepare for Zeabur deployment"
git push origin main
```

### 2. 在 Zeabur 控制台部署
1. 登入 [Zeabur](https://zeabur.com)
2. 選擇 "New Project"
3. 連接你的 GitHub 倉庫 `speech2text`
4. Zeabur 會自動偵測 Dockerfile 並開始構建
5. 設定環境變數（如需要）
6. 部署完成後會獲得一個公開 URL

### 3. 驗證部署
- 訪問分配的 URL
- 測試語音轉文字功能
- 確認 GPT-4o 和 SRT 格式正常工作

## 🔧 配置說明

### Dockerfile 重點
- 使用 Python 3.11-slim 基礎映像
- 安裝 ffmpeg 和 poppler-utils 系統依賴
- 端口設定為 8080（Zeabur 標準）
- 完整的 Streamlit 環境配置

### Streamlit 配置
- Headless 模式運行
- CORS 和 XSRF 保護已停用（適合容器環境）
- 錯誤詳細資訊已隱藏（生產環境安全）

## 📋 功能清單

部署後可用功能：
- 🎤 GPT-4o 語音轉文字
- 🎬 SRT 字幕格式輸出（含時間戳）
- 📝 Markdown 格式輸出
- 📄 純文字格式輸出
- 📁 文件轉換功能
- ✨ AI 文字優化

## 🛠️ 故障排除

### 常見問題
1. **端口問題**: 確保使用 8080 端口
2. **依賴安裝失敗**: 檢查 requirements.txt 版本兼容性
3. **ffmpeg 錯誤**: Dockerfile 已包含 ffmpeg 安裝
4. **API 金鑰**: 在 Zeabur 環境變數中正確設定

### 日誌檢查
- 在 Zeabur 控制台查看構建和運行日誌
- 注意任何 Python 錯誤或依賴問題

## 🔐 安全注意事項

- 不要在代碼中硬編碼 API 金鑰
- 使用 Zeabur 的環境變數功能
- 定期更新依賴項以修復安全漏洞