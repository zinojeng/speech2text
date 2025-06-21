# Zeabur 部署指南

## 🚀 快速部署

### 方法 1：GitHub 自動部署

1. **連接 GitHub 倉庫**
   - 登入 [Zeabur Dashboard](https://zeabur.com)
   - 點擊 "New Project"
   - 選擇 "Deploy from GitHub"
   - 選擇此倉庫：`zinojeng/speech2text`

2. **配置部署設定**
   - Framework: **Streamlit**
   - Entry Point: `main_app.py` 或 `app.py`
   - Build Command: 自動檢測
   - Port: 8501 (Streamlit 默認)

3. **設置環境變數**
   ```
   STREAMLIT_SERVER_PORT=8501
   STREAMLIT_SERVER_HEADLESS=true
   ```

### 方法 2：手動配置

1. **確認檔案結構**
   ```
   ├── main_app.py          # 主應用程式
   ├── app.py               # 部署入口點
   ├── requirements.txt     # Python 依賴
   ├── packages.txt         # 系統依賴
   ├── .streamlit/
   │   └── config.toml      # Streamlit 配置
   └── 其他模組檔案...
   ```

2. **推送到 GitHub**
   ```bash
   git add .
   git commit -m "Prepare for Zeabur deployment"
   git push origin main
   ```

3. **在 Zeabur 中部署**
   - 選擇倉庫
   - 確認配置
   - 點擊部署

## ⚙️ 配置說明

### 必要檔案

1. **requirements.txt** - Python 依賴 ✅
2. **packages.txt** - 系統依賴 ✅
3. **.streamlit/config.toml** - Streamlit 配置 ✅
4. **app.py** - 部署入口點 ✅

### 環境變數設定

在 Zeabur Dashboard 中設置以下環境變數：

```env
# Streamlit 配置
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# API 金鑰 (可選，用戶可在界面中輸入)
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
```

## 🔧 功能限制

### 雲端環境限制

1. **Vision API 功能**
   - ❌ LibreOffice 無法在 Zeabur 上安裝
   - ✅ MarkItDown 內建圖片處理仍可使用
   - ✅ 基本文件轉換功能正常

2. **檔案處理**
   - ✅ PDF、DOCX、XLSX 等基本格式
   - ✅ 音訊轉文字功能
   - ✅ 文字優化功能
   - ⚠️ 進階 PPTX 圖片分析受限

3. **系統資源**
   - 記憶體限制：512MB - 1GB
   - 暫存檔案會自動清理
   - 長時間處理可能超時

## 🐛 故障排除

### 常見問題

1. **模組導入錯誤**
   ```
   ImportError: No module named 'xxx'
   ```
   **解決方案：** 檢查 `requirements.txt` 是否包含所有依賴

2. **Port 綁定問題**
   ```
   OSError: [Errno 48] Address already in use
   ```
   **解決方案：** 確認 Streamlit 配置正確

3. **API 金鑰問題**
   ```
   AuthenticationError: Invalid API key
   ```
   **解決方案：** 在環境變數或界面中正確設置 API 金鑰

### 調試步驟

1. **檢查部署日誌**
   - 在 Zeabur Dashboard 查看建置和運行日誌
   - 尋找錯誤訊息和警告

2. **本地測試**
   ```bash
   streamlit run main_app.py
   ```

3. **依賴檢查**
   ```bash
   pip install -r requirements.txt
   python -c "import main_app"
   ```

## 📊 監控與維護

### 健康檢查

應用程式會在以下端點提供健康檢查：
- Health Check: `https://your-app.zeabur.app/_stcore/health`

### 日誌監控

在 Zeabur Dashboard 中可以查看：
- 建置日誌
- 運行日誌
- 錯誤報告

### 更新部署

每次推送到 `main` 分支都會觸發自動重新部署。

## 🔗 相關連結

- [Zeabur 官方文檔](https://zeabur.com/docs)
- [Streamlit 部署指南](https://docs.streamlit.io/streamlit-cloud)
- [GitHub 倉庫](https://github.com/zinojeng/speech2text)