#!/bin/bash

# 簡單的批次處理執行腳本
# 直接使用 venv_app 環境

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 腳本目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 顯示標題
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        智慧批次音訊處理系統 v2.0                          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 檢查參數
if [ -z "$1" ]; then
    echo -e "${YELLOW}使用方法:${NC}"
    echo "  $0 <資料夾路徑> [選項]"
    echo ""
    echo "選項:"
    echo "  --model MODEL      (預設: gpt-transcribe)"
    echo "  --format FORMAT    (預設: text, 可選: srt, markdown)"
    echo "  --force           強制重新處理"
    echo "  --docx            產生 Word 文件"
    echo "  --combined        合併輸出"
    exit 1
fi

# 啟動虛擬環境並執行
echo -e "${GREEN}啟動虛擬環境...${NC}"
source "$SCRIPT_DIR/venv_app/bin/activate"

echo -e "${GREEN}開始處理...${NC}"
python "$SCRIPT_DIR/batch_audio_smart.py" "$@"