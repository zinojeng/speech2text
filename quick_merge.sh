#!/bin/bash

# 快速合併工具 - 簡化版本
# Quick Merge Tool for common use cases

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# 顯示標題
echo -e "${CYAN}=== 快速合併工具 ===${NC}"
echo ""

# 檢查參數
if [ $# -eq 0 ]; then
    echo "使用方法："
    echo "  $0 <演講稿> <投影片1> [投影片2] ..."
    echo ""
    echo "範例："
    echo "  $0 transcript.txt slides.md"
    echo "  $0 transcript.txt slides1.md slides2.md"
    echo ""
    echo "如需互動式介面，請使用 ./interactive_merge.sh"
    exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 使用 python3 或 python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

# 取得參數
TRANSCRIPT="$1"
shift

# 檢查演講稿是否存在
if [ ! -f "$TRANSCRIPT" ]; then
    echo -e "${YELLOW}錯誤：找不到演講稿檔案 - $TRANSCRIPT${NC}"
    exit 1
fi

echo -e "${GREEN}演講稿：$(basename "$TRANSCRIPT")${NC}"

# 處理投影片
SLIDES=("$@")
SLIDE_COUNT=${#SLIDES[@]}

if [ $SLIDE_COUNT -eq 0 ]; then
    echo -e "${YELLOW}錯誤：至少需要一個投影片檔案${NC}"
    exit 1
fi

echo -e "${GREEN}投影片數量：$SLIDE_COUNT${NC}"

# 顯示投影片列表
for slide in "${SLIDES[@]}"; do
    if [ -f "$slide" ]; then
        echo -e "  ✓ $(basename "$slide")"
    else
        echo -e "  ✗ $(basename "$slide") - 檔案不存在"
    fi
done

echo ""
echo -e "${CYAN}開始處理...${NC}"
echo ""

# 根據投影片數量選擇腳本
if [ $SLIDE_COUNT -eq 1 ]; then
    # 單一投影片
    $PYTHON_CMD merge_transcript_slides.py "$TRANSCRIPT" "${SLIDES[0]}"
else
    # 多個投影片
    $PYTHON_CMD merge_transcript_multi_slides.py "$TRANSCRIPT" "${SLIDES[@]}"
fi

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ 處理完成！${NC}"
else
    echo ""
    echo -e "${YELLOW}✗ 處理失敗${NC}"
fi