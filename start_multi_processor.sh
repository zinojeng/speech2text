#!/bin/bash

# Navigate to the script's directory
cd "$(dirname "$0")"

# Activate virtual environment
source venv_app/bin/activate

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    echo "Please create a .env file with your API keys:"
    echo "  OPENAI_API_KEY=your_key_here"
    echo "  GOOGLE_API_KEY=your_key_here"
    exit 1
fi

# Start the multi-file processor
echo "Starting Multi-File Audio Processor..."
echo ""
echo "📌 請在瀏覽器中手動輸入以下網址："
echo "   http://127.0.0.1:8502"
echo ""
echo "⚠️  Safari 使用者注意："
echo "   - 請完整輸入網址，包含 http://"
echo "   - 不要只輸入 127.0.0.1:8502"
echo "   - 或使用 Chrome/Firefox 獲得更好體驗"
echo ""

# Run Streamlit without auto-opening browser
streamlit run multi_file_processor.py --server.port 8502 --server.address 127.0.0.1 --server.headless true