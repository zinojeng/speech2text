#!/bin/bash

# 互動式演講稿與投影片合併工具
# Interactive Merge Tool for Transcripts and Slides
# 支援單一或多個投影片，可選擇性加入圖片

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 清屏並顯示標題
clear
echo -e "${CYAN}=================================================${NC}"
echo -e "${CYAN}     演講稿與投影片智能合併工具 v1.0            ${NC}"
echo -e "${CYAN}     ADA 2025 Conference Content Merger          ${NC}"
echo -e "${CYAN}=================================================${NC}"
echo ""

# 檢查是否在正確的目錄
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 檢查必要的 Python 腳本是否存在
if [ ! -f "merge_transcript_slides.py" ] || [ ! -f "merge_transcript_multi_slides.py" ]; then
    echo -e "${RED}錯誤：找不到必要的 Python 腳本！${NC}"
    echo "請確保以下檔案存在於同一目錄："
    echo "- merge_transcript_slides.py"
    echo "- merge_transcript_multi_slides.py"
    exit 1
fi

# 檢查 Python 環境
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}錯誤：找不到 Python！請先安裝 Python 3${NC}"
    exit 1
fi

# 使用 python3 或 python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

# 初始化變數
TRANSCRIPT_FILE=""
SLIDES_FILES=()
SLIDES_WITH_IMAGES=()
OUTPUT_NAME=""

# 函數：檢查檔案是否存在
check_file() {
    if [ ! -f "$1" ]; then
        echo -e "${RED}錯誤：檔案不存在 - $1${NC}"
        return 1
    fi
    return 0
}

# 函數：檢查目錄是否存在
check_directory() {
    if [ ! -d "$1" ]; then
        echo -e "${RED}錯誤：目錄不存在 - $1${NC}"
        return 1
    fi
    return 0
}

# 步驟 1：選擇演講稿檔案
echo -e "${YELLOW}步驟 1/4：選擇演講稿檔案${NC}"
echo "請輸入演講稿檔案路徑（支援拖放檔案）："
read -r transcript_input

# 移除可能的引號
transcript_input="${transcript_input%\"}"
transcript_input="${transcript_input#\"}"
transcript_input="${transcript_input%\'}"
transcript_input="${transcript_input#\'}"

# 展開波浪號
transcript_input="${transcript_input/#\~/$HOME}"

if check_file "$transcript_input"; then
    TRANSCRIPT_FILE="$transcript_input"
    echo -e "${GREEN}✓ 演講稿檔案：$(basename "$TRANSCRIPT_FILE")${NC}"
else
    echo -e "${RED}程式終止${NC}"
    exit 1
fi

echo ""

# 步驟 2：選擇投影片數量
echo -e "${YELLOW}步驟 2/4：選擇投影片數量${NC}"
echo "您要處理幾個投影片檔案？"
echo "1) 單一投影片"
echo "2) 多個投影片"
read -r slide_choice

case $slide_choice in
    1)
        MULTI_SLIDES=false
        echo -e "${GREEN}✓ 選擇：單一投影片模式${NC}"
        ;;
    2)
        MULTI_SLIDES=true
        echo -e "${GREEN}✓ 選擇：多投影片模式${NC}"
        ;;
    *)
        echo -e "${RED}無效選擇，預設使用單一投影片模式${NC}"
        MULTI_SLIDES=false
        ;;
esac

echo ""

# 步驟 3：輸入投影片檔案
if [ "$MULTI_SLIDES" = false ]; then
    # 單一投影片模式
    echo -e "${YELLOW}步驟 3/4：輸入投影片檔案${NC}"
    echo "請輸入投影片檔案路徑（.md 檔案）："
    read -r slide_input
    
    # 清理輸入
    slide_input="${slide_input%\"}"
    slide_input="${slide_input#\"}"
    slide_input="${slide_input%\'}"
    slide_input="${slide_input#\'}"
    slide_input="${slide_input/#\~/$HOME}"
    
    if check_file "$slide_input"; then
        SLIDES_FILES+=("$slide_input")
        echo -e "${GREEN}✓ 投影片檔案：$(basename "$slide_input")${NC}"
        
        # 詢問是否有對應的圖片資料夾
        echo ""
        echo "這個投影片是否有對應的圖片資料夾？(y/n)"
        read -r has_images
        
        if [[ "$has_images" =~ ^[Yy]$ ]]; then
            echo "請輸入圖片資料夾路徑："
            read -r images_input
            
            # 清理輸入
            images_input="${images_input%\"}"
            images_input="${images_input#\"}"
            images_input="${images_input%\'}"
            images_input="${images_input#\'}"
            images_input="${images_input/#\~/$HOME}"
            
            if check_directory "$images_input"; then
                SLIDES_WITH_IMAGES+=("$slide_input:$images_input")
                echo -e "${GREEN}✓ 圖片資料夾：$(basename "$images_input")${NC}"
                # 顯示找到的圖片數量
                img_count=$(find "$images_input" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.JPG" -o -name "*.JPEG" -o -name "*.PNG" \) | wc -l)
                echo -e "${CYAN}  找到 $img_count 張圖片${NC}"
            else
                echo -e "${YELLOW}警告：將不包含圖片${NC}"
                SLIDES_WITH_IMAGES+=("$slide_input")
            fi
        else
            SLIDES_WITH_IMAGES+=("$slide_input")
        fi
    else
        echo -e "${RED}程式終止${NC}"
        exit 1
    fi
else
    # 多投影片模式
    echo -e "${YELLOW}步驟 3/4：輸入投影片檔案${NC}"
    slide_count=1
    
    while true; do
        echo ""
        echo "請輸入第 $slide_count 個投影片檔案路徑（輸入 'done' 完成）："
        read -r slide_input
        
        if [ "$slide_input" = "done" ] || [ "$slide_input" = "DONE" ]; then
            if [ ${#SLIDES_FILES[@]} -eq 0 ]; then
                echo -e "${RED}至少需要一個投影片檔案！${NC}"
                continue
            else
                break
            fi
        fi
        
        # 清理輸入
        slide_input="${slide_input%\"}"
        slide_input="${slide_input#\"}"
        slide_input="${slide_input%\'}"
        slide_input="${slide_input#\'}"
        slide_input="${slide_input/#\~/$HOME}"
        
        if check_file "$slide_input"; then
            SLIDES_FILES+=("$slide_input")
            echo -e "${GREEN}✓ 投影片 $slide_count：$(basename "$slide_input")${NC}"
            
            # 詢問是否有對應的圖片資料夾
            echo "這個投影片是否有對應的圖片資料夾？(y/n)"
            read -r has_images
            
            if [[ "$has_images" =~ ^[Yy]$ ]]; then
                echo "請輸入圖片資料夾路徑："
                read -r images_input
                
                # 清理輸入
                images_input="${images_input%\"}"
                images_input="${images_input#\"}"
                images_input="${images_input%\'}"
                images_input="${images_input#\'}"
                images_input="${images_input/#\~/$HOME}"
                
                if check_directory "$images_input"; then
                    SLIDES_WITH_IMAGES+=("$slide_input:$images_input")
                    echo -e "${GREEN}✓ 圖片資料夾：$(basename "$images_input")${NC}"
                    # 顯示找到的圖片數量
                    img_count=$(find "$images_input" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.JPG" -o -name "*.JPEG" -o -name "*.PNG" \) | wc -l)
                    echo -e "${CYAN}  找到 $img_count 張圖片${NC}"
                else
                    echo -e "${YELLOW}警告：將不包含圖片${NC}"
                    SLIDES_WITH_IMAGES+=("$slide_input")
                fi
            else
                SLIDES_WITH_IMAGES+=("$slide_input")
            fi
            
            ((slide_count++))
        else
            echo -e "${YELLOW}跳過無效檔案${NC}"
        fi
    done
fi

echo ""

# 步驟 4：輸出檔案名稱
echo -e "${YELLOW}步驟 4/4：設定輸出檔案名稱${NC}"
echo "請輸入輸出檔案基礎名稱（選填，按 Enter 使用預設）："
read -r output_input

if [ -n "$output_input" ]; then
    OUTPUT_NAME="$output_input"
    echo -e "${GREEN}✓ 輸出名稱：$OUTPUT_NAME${NC}"
else
    echo -e "${CYAN}將使用預設名稱（基於演講稿檔名）${NC}"
fi

echo ""
echo -e "${PURPLE}=================================================${NC}"
echo -e "${PURPLE}準備執行合併...${NC}"
echo -e "${PURPLE}=================================================${NC}"
echo ""

# 顯示摘要
echo -e "${CYAN}執行摘要：${NC}"
echo -e "演講稿：$(basename "$TRANSCRIPT_FILE")"
echo -e "投影片數量：${#SLIDES_FILES[@]}"
for i in "${!SLIDES_FILES[@]}"; do
    echo -e "  - 投影片 $((i+1))：$(basename "${SLIDES_FILES[$i]}")"
done

# 計算總圖片數
total_images=0
for item in "${SLIDES_WITH_IMAGES[@]}"; do
    if [[ "$item" == *":"* ]]; then
        img_folder="${item#*:}"
        img_count=$(find "$img_folder" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.JPG" -o -name "*.JPEG" -o -name "*.PNG" \) 2>/dev/null | wc -l)
        total_images=$((total_images + img_count))
    fi
done

if [ $total_images -gt 0 ]; then
    echo -e "${CYAN}總圖片數：$total_images${NC}"
fi

echo ""
echo -e "${YELLOW}確定要執行嗎？(y/n)${NC}"
read -r confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo -e "${RED}已取消${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}開始執行...${NC}"
echo ""

# 執行對應的 Python 腳本
if [ "$MULTI_SLIDES" = false ]; then
    # 單一投影片模式
    if [ -n "$OUTPUT_NAME" ]; then
        if [[ "${SLIDES_WITH_IMAGES[0]}" == *":"* ]]; then
            # 有圖片
            slide_file="${SLIDES_WITH_IMAGES[0]%%:*}"
            img_folder="${SLIDES_WITH_IMAGES[0]#*:}"
            $PYTHON_CMD merge_transcript_slides.py "$TRANSCRIPT_FILE" "$slide_file" "$OUTPUT_NAME" --images "$img_folder"
        else
            # 無圖片
            $PYTHON_CMD merge_transcript_slides.py "$TRANSCRIPT_FILE" "${SLIDES_WITH_IMAGES[0]}" "$OUTPUT_NAME"
        fi
    else
        if [[ "${SLIDES_WITH_IMAGES[0]}" == *":"* ]]; then
            # 有圖片
            slide_file="${SLIDES_WITH_IMAGES[0]%%:*}"
            img_folder="${SLIDES_WITH_IMAGES[0]#*:}"
            $PYTHON_CMD merge_transcript_slides.py "$TRANSCRIPT_FILE" "$slide_file" --images "$img_folder"
        else
            # 無圖片
            $PYTHON_CMD merge_transcript_slides.py "$TRANSCRIPT_FILE" "${SLIDES_WITH_IMAGES[0]}"
        fi
    fi
else
    # 多投影片模式
    cmd="$PYTHON_CMD merge_transcript_multi_slides.py \"$TRANSCRIPT_FILE\""
    
    # 添加所有投影片參數
    for item in "${SLIDES_WITH_IMAGES[@]}"; do
        cmd="$cmd \"$item\""
    done
    
    # 添加輸出名稱（如果有）
    if [ -n "$OUTPUT_NAME" ]; then
        cmd="$cmd --output \"$OUTPUT_NAME\""
    fi
    
    # 執行命令
    eval $cmd
fi

# 檢查執行結果
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=================================================${NC}"
    echo -e "${GREEN}✓ 合併完成！${NC}"
    echo -e "${GREEN}=================================================${NC}"
    echo ""
    echo -e "${CYAN}提示：請檢查輸出的 .md 和 .docx 檔案${NC}"
else
    echo ""
    echo -e "${RED}=================================================${NC}"
    echo -e "${RED}✗ 合併失敗！${NC}"
    echo -e "${RED}=================================================${NC}"
    echo ""
    echo -e "${YELLOW}請檢查錯誤訊息並重試${NC}"
fi

# 詢問是否要再次執行
echo ""
echo -e "${YELLOW}要再處理其他檔案嗎？(y/n)${NC}"
read -r again

if [[ "$again" =~ ^[Yy]$ ]]; then
    exec "$0"
fi

echo ""
echo -e "${CYAN}感謝使用！${NC}"