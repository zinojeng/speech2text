#!/bin/bash

echo "修復 macOS SSL 證書問題..."

# 檢查並安裝 certifi
echo "1. 檢查 certifi 套件..."
source venv_app/bin/activate

pip install --upgrade certifi

# 獲取 certifi 路徑
CERT_PATH=$(python -c "import certifi; print(certifi.where())")
echo "Certifi 證書位置: $CERT_PATH"

# 設置環境變數
echo ""
echo "2. 設置環境變數..."
echo "export SSL_CERT_FILE=\"$CERT_PATH\"" >> ~/.bashrc
echo "export REQUESTS_CA_BUNDLE=\"$CERT_PATH\"" >> ~/.bashrc
echo "export GRPC_DEFAULT_SSL_ROOTS_FILE_PATH=\"$CERT_PATH\"" >> ~/.bashrc

# 也設置到 .zshrc (macOS 預設 shell)
echo "export SSL_CERT_FILE=\"$CERT_PATH\"" >> ~/.zshrc
echo "export REQUESTS_CA_BUNDLE=\"$CERT_PATH\"" >> ~/.zshrc
echo "export GRPC_DEFAULT_SSL_ROOTS_FILE_PATH=\"$CERT_PATH\"" >> ~/.zshrc

# 立即生效
export SSL_CERT_FILE="$CERT_PATH"
export REQUESTS_CA_BUNDLE="$CERT_PATH"
export GRPC_DEFAULT_SSL_ROOTS_FILE_PATH="$CERT_PATH"

echo ""
echo "3. 更新 .env 檔案..."
if [ -f .env ]; then
    # 移除舊的設定
    grep -v "SSL_CERT_FILE\|REQUESTS_CA_BUNDLE\|GRPC_DEFAULT_SSL_ROOTS_FILE_PATH" .env > .env.tmp
    mv .env.tmp .env
fi

# 添加新設定
echo "SSL_CERT_FILE=\"$CERT_PATH\"" >> .env
echo "REQUESTS_CA_BUNDLE=\"$CERT_PATH\"" >> .env
echo "GRPC_DEFAULT_SSL_ROOTS_FILE_PATH=\"$CERT_PATH\"" >> .env

echo ""
echo "✅ SSL 證書設定完成！"
echo ""
echo "請執行以下命令使設定生效："
echo "  source ~/.zshrc"
echo ""
echo "或重新開啟終端機視窗。"