#!/bin/bash
# 啟動語音轉文字應用程式

echo "🚀 啟動語音轉文字應用程式..."

# 激活虛擬環境
source venv_app/bin/activate

# 檢查相依套件
echo "📦 檢查相依套件..."
python -c "
try:
    import streamlit
    import openai
    import google.generativeai
    from pydub import AudioSegment
    from dotenv import load_dotenv
    print('✅ 所有相依套件正常')
except ImportError as e:
    print('❌ 套件導入失敗:', e)
    exit(1)
"

# 啟動 Streamlit 應用
echo "🌐 啟動 Streamlit 應用 (http://localhost:8501)..."
streamlit run main_app.py --server.headless false

echo "👋 應用程式已關閉"