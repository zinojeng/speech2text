#!/bin/bash

# 簡單批次音訊處理腳本
# 使用現有的 gpt4o_transcribe.py

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 腳本目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 顯示說明
if [ -z "$1" ]; then
    echo -e "${BLUE}批次音訊轉文字處理${NC}"
    echo ""
    echo "使用方法:"
    echo "  $0 <資料夾路徑> [model]"
    echo ""
    echo "模型選項:"
    echo "  gpt-transcribe (預設)"
    echo "  gpt-transcribe"
    echo ""
    echo "範例:"
    echo "  $0 /path/to/audio/folder"
    echo "  $0 /path/to/audio/folder gpt-transcribe"
    exit 1
fi

FOLDER="$1"
MODEL="${2:-gpt-transcribe}"

# 檢查資料夾
if [ ! -d "$FOLDER" ]; then
    echo -e "${RED}錯誤: 資料夾不存在 - $FOLDER${NC}"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}批次音訊轉文字處理${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}資料夾: $FOLDER${NC}"
echo -e "${GREEN}模型: $MODEL${NC}"
echo ""

# 啟動虛擬環境
echo -e "${YELLOW}啟動虛擬環境...${NC}"
source "$SCRIPT_DIR/venv_app/bin/activate"

# 統計
TOTAL=0
PROCESSED=0
SKIPPED=0

# 找出所有音訊檔案
echo -e "${YELLOW}掃描音訊檔案...${NC}"
audio_files=$(find "$FOLDER" -type f \( -name "*.mp3" -o -name "*.wav" -o -name "*.m4a" -o -name "*.mp4" -o -name "*.mov" \) 2>/dev/null)

# 計算總數
for file in $audio_files; do
    ((TOTAL++))
done

echo -e "${GREEN}找到 $TOTAL 個音訊檔案${NC}"
echo ""

# 處理每個檔案
for audio_file in $audio_files; do
    # 取得檔案基本名稱和路徑
    base_name="${audio_file%.*}"
    file_name=$(basename "$audio_file")
    
    # 檢查是否已有轉錄檔案
    if [ -f "${base_name}.txt" ] || [ -f "${base_name}.srt" ] || [ -f "${base_name}.md" ]; then
        echo -e "${YELLOW}[跳過] $file_name - 已有轉錄檔案${NC}"
        ((SKIPPED++))
        continue
    fi
    
    # 轉錄檔案
    echo -e "${BLUE}[處理 $((PROCESSED+1))/$((TOTAL-SKIPPED))] $file_name${NC}"
    
    # 執行轉錄
    python "$SCRIPT_DIR/gpt4o_transcribe.py" "$audio_file" --model "$MODEL"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 完成${NC}"
        ((PROCESSED++))
    else
        echo -e "${RED}✗ 失敗${NC}"
    fi
    
    echo ""
done

# 顯示統計
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}處理完成${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "總檔案數: $TOTAL"
echo -e "已處理: ${GREEN}$PROCESSED${NC}"
echo -e "已跳過: ${YELLOW}$SKIPPED${NC}"
echo -e "失敗: ${RED}$((TOTAL - PROCESSED - SKIPPED))${NC}"