#!/bin/bash
# 啟動語音轉文字應用程式

echo "🚀 啟動語音轉文字應用程式..."

# 激活虛擬環境
source venv_app/bin/activate

# 安裝相依套件
echo "📦 安裝相依套件 (這可能需要幾分鐘時間)..."
pip install -r requirements.txt --verbose

# 檢查安裝狀態
echo "✅ 相依套件安裝完成"

# 啟動 Streamlit 應用
echo "🌐 正在啟動 Streamlit 應用..."
echo ""
echo "📌 請使用以下網址訪問："
echo "   推薦: http://127.0.0.1:8501"
echo "   備選: http://[::1]:8501 (IPv6)"
echo ""
echo "⚠️  Safari 使用者注意事項："
echo "   - 請使用 http://127.0.0.1:8501 而非 localhost"
echo "   - 確保輸入完整的 http:// 前綴"
echo "   - 如仍有問題，建議使用 Chrome 或 Firefox"
echo ""

# 使用 --server.address 0.0.0.0 確保所有網路介面都可訪問
streamlit run main_app.py --server.address 0.0.0.0 --server.port 8501 --server.headless false

echo "👋 應用程式已關閉"