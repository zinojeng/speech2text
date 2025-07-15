#!/bin/bash
# 啟動語音轉文字應用程式

echo "🚀 啟動語音轉文字應用程式..."

# 激活虛擬環境
source venv_app/bin/activate

# 啟動 Streamlit 應用
echo "🌐 正在啟動 Streamlit 應用..."
echo ""
echo "📌 請使用以下網址訪問："
echo "   http://127.0.0.1:8501"
echo ""

# 使用最簡單的啟動方式
streamlit run main_app.py

echo "👋 應用程式已關閉"