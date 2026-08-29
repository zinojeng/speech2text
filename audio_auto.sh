#!/bin/bash

# ==============================================================================
# 批次音訊處理自動化腳本
# Batch Audio Processing Automation Script
# 
# 此腳本用於簡化批次音訊處理程式的使用
# ==============================================================================

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 腳本所在目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 確保 temp 資料夾存在
TEMP_DIR="$SCRIPT_DIR/temp"
mkdir -p "$TEMP_DIR"

# 顯示標題
echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}       批次音訊處理自動化腳本 v1.0${NC}"
echo -e "${BLUE}   Batch Audio Processing Automation Script${NC}"
echo -e "${BLUE}===================================================${NC}"
echo ""

# 檢查必要檔案
check_requirements() {
    echo -e "${BLUE}📋 檢查必要檔案...${NC}"
    
    # 檢查 Python 腳本
    if [ ! -f "batch_audio_processor.py" ]; then
        echo -e "${RED}❌ 找不到 batch_audio_processor.py${NC}"
        exit 1
    fi
    
    # 檢查 .env 檔案
    if [ ! -f ".env" ]; then
        echo -e "${RED}❌ 找不到 .env 檔案${NC}"
        echo -e "${YELLOW}💡 請先建立 .env 檔案並設定 API 金鑰${NC}"
        exit 1
    fi
    
    # 檢查 API 金鑰是否已設定
    if ! grep -q "OPENAI_API_KEY=sk-" .env; then
        echo -e "${RED}❌ 請在 .env 檔案中設定有效的 OPENAI_API_KEY${NC}"
        exit 1
    fi
    
    # 檢查 Google API Key - 改進版本，支援引號
    echo -e "${BLUE}🔍 調試信息:${NC}"
    echo -e "${BLUE}   當前目錄: $(pwd)${NC}"
    echo -e "${BLUE}   .env 檔案存在: $(test -f .env && echo '是' || echo '否')${NC}"
    echo -e "${BLUE}   .env 檔案內容 (Google):${NC}"
    grep "GOOGLE_API_KEY" .env || echo "   未找到 GOOGLE_API_KEY"
    echo ""
    
    GOOGLE_KEY_RAW=$(grep "GOOGLE_API_KEY=" .env | cut -d'=' -f2-)
    # 移除前後的空格和引號
    GOOGLE_KEY=$(echo "$GOOGLE_KEY_RAW" | sed 's/^[ \t]*//; s/[ \t]*$//; s/^["'\'']\|["'\'']$//g')
    
    echo -e "${BLUE}   原始值: '$GOOGLE_KEY_RAW'${NC}"
    echo -e "${BLUE}   處理後: '$GOOGLE_KEY'${NC}"
    echo -e "${BLUE}   長度: ${#GOOGLE_KEY}${NC}"
    echo ""
    
    if [ -z "$GOOGLE_KEY" ] || [ "$GOOGLE_KEY" = "your_google_api_key_here" ]; then
        echo -e "${RED}❌ 請在 .env 檔案中設定有效的 GOOGLE_API_KEY${NC}"
        echo -e "${YELLOW}💡 請將 GOOGLE_API_KEY= 後面加上您的 Google Gemini API 金鑰${NC}"
        echo -e "${YELLOW}💡 取得方式: https://aistudio.google.com/app/apikey${NC}"
        echo -e "${YELLOW}💡 支援格式: GOOGLE_API_KEY=your_key 或 GOOGLE_API_KEY='your_key'${NC}"
        echo ""
        echo -e "${BLUE}📝 請手動編輯 .env 檔案，或按 Enter 繼續編輯:${NC}"
        read -p "按 Enter 繼續..."
        if command -v open > /dev/null; then
            open .env
        else
            echo -e "${YELLOW}請手動打開 .env 檔案進行編輯${NC}"
        fi
        exit 1
    fi
    
    echo -e "${GREEN}✅ 所有必要檔案檢查通過${NC}"
}

# 檢查虛擬環境
check_virtual_env() {
    echo -e "${BLUE}🐍 檢查 Python 環境...${NC}"
    
    # 檢查是否在虛擬環境中
    if [ "$VIRTUAL_ENV" != "" ]; then
        echo -e "${GREEN}✅ 虛擬環境已啟動: $VIRTUAL_ENV${NC}"
    else
        echo -e "${YELLOW}⚠️  未偵測到虛擬環境${NC}"
        
        # 檢查是否有 venv 資料夾
        if [ -d "venv" ]; then
            echo -e "${BLUE}🔧 嘗試啟動虛擬環境...${NC}"
            source venv/bin/activate
            if [ "$?" -eq 0 ]; then
                echo -e "${GREEN}✅ 虛擬環境啟動成功${NC}"
            else
                echo -e "${RED}❌ 虛擬環境啟動失敗${NC}"
            fi
        else
            echo -e "${YELLOW}💡 建議使用虛擬環境運行程式${NC}"
        fi
    fi
}

# 檢查依賴項目
check_dependencies() {
    echo -e "${BLUE}📦 檢查依賴項目...${NC}"
    
    # 檢查 requirements.txt
    if [ ! -f "requirements.txt" ]; then
        echo -e "${RED}❌ 找不到 requirements.txt${NC}"
        exit 1
    fi
    
    # 檢查關鍵依賴
    echo -e "${BLUE}🔍 檢查 Python 套件...${NC}"
    
    # 逐個檢查關鍵套件
    missing_packages=()
    
    echo -n "  - openai: "
    if python -c "import openai" 2>/dev/null; then
        echo -e "${GREEN}✅${NC}"
    else
        echo -e "${RED}❌${NC}"
        missing_packages+=("openai")
    fi
    
    echo -n "  - google.generativeai: "
    if python -c "import google.generativeai" 2>/dev/null; then
        echo -e "${GREEN}✅${NC}"
    else
        echo -e "${RED}❌${NC}"
        missing_packages+=("google-generativeai")
    fi
    
    echo -n "  - docx: "
    if python -c "import docx" 2>/dev/null; then
        echo -e "${GREEN}✅${NC}"
    else
        echo -e "${RED}❌${NC}"
        missing_packages+=("python-docx")
    fi
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠️  缺少必要的依賴項目: ${missing_packages[*]}${NC}"
        echo -e "${BLUE}🔧 正在安裝依賴項目...${NC}"
        pip install -r requirements.txt
        if [ "$?" -eq 0 ]; then
            echo -e "${GREEN}✅ 依賴項目安裝成功${NC}"
        else
            echo -e "${RED}❌ 依賴項目安裝失敗${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✅ 所有依賴項目已就緒${NC}"
    fi
}

# 顯示使用說明
show_usage() {
    echo -e "${BLUE}📖 使用方法:${NC}"
    echo "  ./audio_auto.sh [資料夾路徑] [模型] [輸出格式] [--combined]"
    echo ""
    echo -e "${BLUE}🤖 支援的轉錄模型:${NC}"
    echo "  gpt-transcribe (預設，更經濟)"
    echo "  gpt-transcribe (更高品質，較昂貴)"
    echo ""
    echo -e "${BLUE}📝 支援的輸出格式:${NC}"
    echo "  text (純文字 .txt)"
    echo "  markdown (Markdown .md)"
    echo "  srt (字幕檔 .srt)"
    echo ""
    echo -e "${BLUE}🎵 支援的音訊格式:${NC}"
    echo "  mp3, wav, m4a, aac, flac, ogg, wma"
    echo ""
    echo -e "${BLUE}💡 功能特色:${NC}"
    echo "  - 自動搜索多層目錄中的所有音訊檔案"
    echo "  - 使用與 main_app.py 相同的轉錄方法"
    echo "  - 支援多種輸出格式選擇"
    echo "  - 轉錄結果保存在與原檔案相同目錄"
    echo "  - 支援合併輸出模式 (--combined)"
    echo ""
    echo -e "${BLUE}🔄 合併輸出模式:${NC}"
    echo "  --combined: 將所有轉錄結果合併為單一檔案"
    echo "  - SRT 格式: 自動調整時間軸"
    echo "  - 其他格式: 添加檔案標題分隔"
    echo ""
}

# 取得資料夾路徑和模型
get_folder_path() {
    if [ "$1" != "" ]; then
        FOLDER_PATH="$1"
    else
        echo -e "${BLUE}📁 請輸入要處理的資料夾路徑:${NC}"
        read -p "> " FOLDER_PATH
    fi
    
    # 移除引號
    FOLDER_PATH=$(echo "$FOLDER_PATH" | sed 's/^["'\'']\|["'\'']$//g')
    
    # 檢查路徑是否存在
    if [ ! -d "$FOLDER_PATH" ]; then
        echo -e "${RED}❌ 資料夾不存在: $FOLDER_PATH${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ 資料夾路徑: $FOLDER_PATH${NC}"
}

# 取得轉錄模型
get_transcribe_model() {
    if [ "$1" != "" ]; then
        MODEL="$1"
        if [ "$MODEL" != "gpt-transcribe" ] && [ "$MODEL" != "gemini-3.5-transcribe" ]; then
            echo -e "${YELLOW}⚠️  無效的模型名稱，使用預設模型: gpt-transcribe${NC}"
            MODEL="gpt-transcribe"
        fi
    else
        echo -e "${BLUE}🤖 選擇轉錄模型:${NC}"
        echo "  1) gpt-transcribe (預設，文字準確度最好)"
        echo "  2) gemini-3.5-transcribe (真實詞級時間戳＋講者標記)"
        read -p "請選擇 (1-2，預設為1): " choice
        
        case $choice in
            2)
                MODEL="gemini-3.5-transcribe"
                ;;
            *)
                MODEL="gpt-transcribe"
                ;;
        esac
    fi
    
    echo -e "${GREEN}✅ 使用模型: $MODEL${NC}"
}

# 取得輸出格式
get_output_format() {
    if [ "$2" != "" ]; then
        OUTPUT_FORMAT="$2"
        if [ "$OUTPUT_FORMAT" != "text" ] && [ "$OUTPUT_FORMAT" != "markdown" ] && [ "$OUTPUT_FORMAT" != "srt" ]; then
            echo -e "${YELLOW}⚠️  無效的輸出格式，使用預設格式: text${NC}"
            OUTPUT_FORMAT="text"
        fi
    else
        echo -e "${BLUE}📝 選擇輸出格式:${NC}"
        echo "  1) text (純文字 .txt)"
        echo "  2) markdown (Markdown .md)"
        echo "  3) srt (字幕檔 .srt)"
        read -p "請選擇 (1-3，預設為1): " choice
        
        case $choice in
            2)
                OUTPUT_FORMAT="markdown"
                ;;
            3)
                OUTPUT_FORMAT="srt"
                ;;
            *)
                OUTPUT_FORMAT="text"
                ;;
        esac
    fi
    
    echo -e "${GREEN}✅ 輸出格式: $OUTPUT_FORMAT${NC}"
}

# 檢查是否為合併模式
check_combined_mode() {
    COMBINED_MODE="false"
    for arg in "$@"; do
        if [ "$arg" = "--combined" ]; then
            COMBINED_MODE="true"
            echo -e "${GREEN}✅ 合併輸出模式: 已啟用${NC}"
            break
        fi
    done
    
    if [ "$COMBINED_MODE" = "false" ]; then
        echo -e "${BLUE}📝 合併輸出模式: 未啟用${NC}"
        echo -e "${BLUE}💡 提示: 添加 --combined 參數可將所有轉錄結果合併為單一檔案${NC}"
    fi
}

# 預覽要處理的檔案
preview_files() {
    echo -e "${BLUE}🔍 預覽要處理的檔案...${NC}"
    
    # 計算音訊檔案數量（排除 ._ 開頭的隱藏檔案，只處理純音訊格式）
    AUDIO_COUNT=$(find "$FOLDER_PATH" -type f \( -name "*.mp3" -o -name "*.wav" -o -name "*.m4a" -o -name "*.aac" -o -name "*.flac" -o -name "*.ogg" -o -name "*.wma" \) ! -name "._*" | wc -l)
    
    # 計算文字檔案數量
    TEXT_COUNT=$(find "$FOLDER_PATH" -type f \( -name "*.txt" -o -name "*.md" -o -name "*.rtf" -o -name "*.doc" -o -name "*.docx" -o -name "*.pdf" -o -name "*.html" -o -name "*.htm" -o -name "*.xml" -o -name "*.json" -o -name "*.csv" \) | wc -l)
    
    echo -e "${GREEN}📊 找到 $AUDIO_COUNT 個音訊檔案和 $TEXT_COUNT 個文字檔案${NC}"
    
    if [ "$AUDIO_COUNT" -eq 0 ]; then
        echo -e "${RED}❌ 未找到任何音訊檔案${NC}"
        exit 1
    fi
    
    # 顯示前 5 個音訊檔案（排除 ._ 開頭的隱藏檔案，只處理純音訊格式）
    echo -e "${BLUE}🎵 音訊檔案範例:${NC}"
    find "$FOLDER_PATH" -type f \( -name "*.mp3" -o -name "*.wav" -o -name "*.m4a" -o -name "*.aac" -o -name "*.flac" -o -name "*.ogg" -o -name "*.wma" \) ! -name "._*" | head -5 | while IFS= read -r file; do
        echo "  - $(basename "$file")"
    done
    
    if [ "$AUDIO_COUNT" -gt 5 ]; then
        echo "  ... 還有 $((AUDIO_COUNT - 5)) 個檔案"
    fi
}

# 確認執行
confirm_execution() {
    echo ""
    echo -e "${YELLOW}❓ 確定要開始處理嗎? (y/N)${NC}"
    read -p "> " CONFIRM
    
    if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
        echo -e "${YELLOW}⏹️  使用者取消操作${NC}"
        exit 0
    fi
}

# 執行處理
run_processing() {
    echo -e "${BLUE}🚀 開始批次處理...${NC}"
    echo ""
    
    # 記錄開始時間
    START_TIME=$(date +%s)
    
    # 找到所有音訊檔案
    echo -e "${BLUE}🔍 搜索音訊檔案...${NC}"
    
    # 使用 while 迴圈正確處理包含空格的檔案名稱（排除 ._ 開頭的隱藏檔案，只處理純音訊格式）
    AUDIO_FILES=()
    while IFS= read -r -d '' file; do
        AUDIO_FILES+=("$file")
    done < <(find "$FOLDER_PATH" -type f \( -name "*.mp3" -o -name "*.wav" -o -name "*.m4a" -o -name "*.aac" -o -name "*.flac" -o -name "*.ogg" -o -name "*.wma" \) ! -name "._*" -print0)
    
    TOTAL_FILES=${#AUDIO_FILES[@]}
    
    if [ $TOTAL_FILES -eq 0 ]; then
        echo -e "${RED}❌ 未找到任何音訊檔案${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ 找到 $TOTAL_FILES 個音訊檔案${NC}"
    
    # 設定輸出副檔名
    case $OUTPUT_FORMAT in
        "markdown")
            OUTPUT_EXT=".md"
            ;;
        "srt")
            OUTPUT_EXT=".srt"
            ;;
        *)
            OUTPUT_EXT=".txt"
            ;;
    esac
    
    if [ "$COMBINED_MODE" = "true" ]; then
        run_combined_processing
    else
        run_individual_processing
    fi
}

# 個別檔案處理
run_individual_processing() {
    # 處理每個檔案
    SUCCESS_COUNT=0
    FAILED_COUNT=0
    
    for i in "${!AUDIO_FILES[@]}"; do
        AUDIO_FILE="${AUDIO_FILES[$i]}"
        FILE_NUM=$((i + 1))
        
        echo -e "${BLUE}📁 處理檔案 $FILE_NUM/$TOTAL_FILES: $(basename "$AUDIO_FILE")${NC}"
        
        # 生成輸出檔案路徑
        DIR_PATH=$(dirname "$AUDIO_FILE")
        BASE_NAME=$(basename "$AUDIO_FILE" | sed 's/\.[^.]*$//')
        OUTPUT_FILE="$DIR_PATH/$BASE_NAME$OUTPUT_EXT"
        
        # 執行轉錄
        if python gpt4o_transcribe.py "$AUDIO_FILE" --model "$MODEL" --format "$OUTPUT_FORMAT" > "$OUTPUT_FILE" 2>&1; then
            echo -e "${GREEN}✅ 成功: $OUTPUT_FILE${NC}"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            echo -e "${RED}❌ 失敗: $(basename "$AUDIO_FILE")${NC}"
            FAILED_COUNT=$((FAILED_COUNT + 1))
            # 如果失敗，刪除可能生成的空檔案
            [ -f "$OUTPUT_FILE" ] && rm "$OUTPUT_FILE"
        fi
        
        # 顯示進度
        PROGRESS=$((FILE_NUM * 100 / TOTAL_FILES))
        echo -e "${BLUE}📊 進度: $PROGRESS% ($FILE_NUM/$TOTAL_FILES)${NC}"
        echo ""
        
        # 避免 API 限制，加入延遲
        if [ $FILE_NUM -lt $TOTAL_FILES ]; then
            sleep 2
        fi
    done
    
    show_final_results
}

# 合併處理
run_combined_processing() {
    echo -e "${BLUE}🔄 合併模式: 正在處理所有檔案...${NC}"
    
    # 建立合併輸出檔案
    COMBINED_OUTPUT="$FOLDER_PATH/combined_transcription$OUTPUT_EXT"
    
    # 建立 temp 資料夾在專案根目錄
    TEMP_DIR="$SCRIPT_DIR/temp"
    mkdir -p "$TEMP_DIR"
    echo -e "${BLUE}📁 臨時檔案資料夾: $TEMP_DIR${NC}"
    
    # 處理每個檔案
    SUCCESS_COUNT=0
    FAILED_COUNT=0
    CURRENT_TIMESTAMP=0
    
    # 初始化合併檔案
    if [ "$OUTPUT_FORMAT" = "markdown" ]; then
        echo "# 合併轉錄結果" > "$COMBINED_OUTPUT"
        echo "" >> "$COMBINED_OUTPUT"
        echo "生成時間: $(date)" >> "$COMBINED_OUTPUT"
        echo "" >> "$COMBINED_OUTPUT"
    elif [ "$OUTPUT_FORMAT" = "text" ]; then
        echo "合併轉錄結果" > "$COMBINED_OUTPUT"
        echo "===============" >> "$COMBINED_OUTPUT"
        echo "" >> "$COMBINED_OUTPUT"
        echo "生成時間: $(date)" >> "$COMBINED_OUTPUT"
        echo "" >> "$COMBINED_OUTPUT"
    fi
    
    for i in "${!AUDIO_FILES[@]}"; do
        AUDIO_FILE="${AUDIO_FILES[$i]}"
        FILE_NUM=$((i + 1))
        
        echo -e "${BLUE}📁 處理檔案 $FILE_NUM/$TOTAL_FILES: $(basename "$AUDIO_FILE")${NC}"
        
        # 生成暫存檔案路徑
        TEMP_FILE="$TEMP_DIR/temp_$i$OUTPUT_EXT"
        
        # 執行轉錄
        if python gpt4o_transcribe.py "$AUDIO_FILE" --model "$MODEL" --format "$OUTPUT_FORMAT" > "$TEMP_FILE" 2>&1; then
            echo -e "${GREEN}✅ 成功: $(basename "$AUDIO_FILE")${NC}"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            
            # 添加到合併檔案
            if [ "$OUTPUT_FORMAT" = "srt" ]; then
                add_srt_to_combined "$TEMP_FILE" "$AUDIO_FILE"
            else
                add_text_to_combined "$TEMP_FILE" "$AUDIO_FILE"
            fi
        else
            echo -e "${RED}❌ 失敗: $(basename "$AUDIO_FILE")${NC}"
            FAILED_COUNT=$((FAILED_COUNT + 1))
        fi
        
        # 顯示進度
        PROGRESS=$((FILE_NUM * 100 / TOTAL_FILES))
        echo -e "${BLUE}📊 進度: $PROGRESS% ($FILE_NUM/$TOTAL_FILES)${NC}"
        echo ""
        
        # 避免 API 限制，加入延遲
        if [ $FILE_NUM -lt $TOTAL_FILES ]; then
            sleep 2
        fi
    done
    
    # 清理暫存檔案（只刪除檔案，保留資料夾）
    rm -f "$TEMP_DIR"/*.txt "$TEMP_DIR"/*.md "$TEMP_DIR"/*.srt 2>/dev/null
    echo -e "${BLUE}🗑️  已清理臨時檔案${NC}"
    
    show_final_results
    
    if [ $SUCCESS_COUNT -gt 0 ]; then
        echo -e "${GREEN}📄 合併檔案: $COMBINED_OUTPUT${NC}"
    fi
}

# 添加 SRT 內容到合併檔案
add_srt_to_combined() {
    local TEMP_FILE="$1"
    local AUDIO_FILE="$2"
    
    if [ -f "$TEMP_FILE" ] && [ -s "$TEMP_FILE" ]; then
        # 添加檔案標題註解
        echo "" >> "$COMBINED_OUTPUT"
        echo "# 檔案: $(basename "$AUDIO_FILE")" >> "$COMBINED_OUTPUT"
        echo "" >> "$COMBINED_OUTPUT"
        
        # 處理 SRT 內容並調整時間戳
        while IFS= read -r line; do
            if [[ "$line" =~ ^[0-9]+$ ]]; then
                # 字幕序號，需要累加
                echo $((line + CURRENT_TIMESTAMP / 1000)) >> "$COMBINED_OUTPUT"
            elif [[ "$line" =~ ^[0-9]{2}:[0-9]{2}:[0-9]{2},[0-9]{3}\ --\>\ [0-9]{2}:[0-9]{2}:[0-9]{2},[0-9]{3}$ ]]; then
                # 時間戳行，需要調整
                START_TIME=$(echo "$line" | cut -d' ' -f1)
                END_TIME=$(echo "$line" | cut -d' ' -f3)
                
                # 轉換時間戳為毫秒並加上偏移
                START_MS=$(time_to_ms "$START_TIME")
                END_MS=$(time_to_ms "$END_TIME")
                
                NEW_START_MS=$((START_MS + CURRENT_TIMESTAMP))
                NEW_END_MS=$((END_MS + CURRENT_TIMESTAMP))
                
                NEW_START=$(ms_to_time "$NEW_START_MS")
                NEW_END=$(ms_to_time "$NEW_END_MS")
                
                echo "$NEW_START --> $NEW_END" >> "$COMBINED_OUTPUT"
            else
                # 普通文字行
                echo "$line" >> "$COMBINED_OUTPUT"
            fi
        done < "$TEMP_FILE"
        
        # 取得音訊檔案長度並更新時間戳偏移
        AUDIO_DURATION=$(python -c "
import subprocess
import sys
try:
    result = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', '$AUDIO_FILE'], capture_output=True, text=True)
    duration = float(result.stdout.strip()) * 1000  # 轉換為毫秒
    print(int(duration))
except:
    print(300000)  # 預設 5 分鐘
")
        CURRENT_TIMESTAMP=$((CURRENT_TIMESTAMP + AUDIO_DURATION))
    fi
}

# 添加文字內容到合併檔案
add_text_to_combined() {
    local TEMP_FILE="$1"
    local AUDIO_FILE="$2"
    
    if [ -f "$TEMP_FILE" ] && [ -s "$TEMP_FILE" ]; then
        # 添加檔案分隔符
        if [ "$OUTPUT_FORMAT" = "markdown" ]; then
            echo "" >> "$COMBINED_OUTPUT"
            echo "## $(basename "$AUDIO_FILE")" >> "$COMBINED_OUTPUT"
            echo "" >> "$COMBINED_OUTPUT"
        else
            echo "" >> "$COMBINED_OUTPUT"
            echo "檔案: $(basename "$AUDIO_FILE")" >> "$COMBINED_OUTPUT"
            echo "=================" >> "$COMBINED_OUTPUT"
            echo "" >> "$COMBINED_OUTPUT"
        fi
        
        # 添加內容
        cat "$TEMP_FILE" >> "$COMBINED_OUTPUT"
        echo "" >> "$COMBINED_OUTPUT"
    fi
}

# 時間戳轉換函數
time_to_ms() {
    local time_str="$1"
    local hours=$(echo "$time_str" | cut -d: -f1)
    local minutes=$(echo "$time_str" | cut -d: -f2)
    local seconds_ms=$(echo "$time_str" | cut -d: -f3)
    local seconds=$(echo "$seconds_ms" | cut -d, -f1)
    local milliseconds=$(echo "$seconds_ms" | cut -d, -f2)
    
    echo $(( (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds ))
}

ms_to_time() {
    local ms="$1"
    local hours=$((ms / 3600000))
    local minutes=$(((ms % 3600000) / 60000))
    local seconds=$(((ms % 60000) / 1000))
    local milliseconds=$((ms % 1000))
    
    printf "%02d:%02d:%02d,%03d" "$hours" "$minutes" "$seconds" "$milliseconds"
}

# 顯示最終結果
show_final_results() {
    RESULT=0
    if [ $FAILED_COUNT -gt 0 ]; then
        RESULT=1
    fi
    
    # 記錄結束時間
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo ""
    if [ $RESULT -eq 0 ]; then
        echo -e "${GREEN}✅ 批次處理完成！${NC}"
        echo -e "${BLUE}⏱️  總耗時: ${DURATION} 秒${NC}"
        echo -e "${GREEN}📊 成功處理: $SUCCESS_COUNT 個檔案${NC}"
        echo -e "${BLUE}📁 輸出格式: $OUTPUT_FORMAT${NC}"
        if [ "$COMBINED_MODE" = "true" ]; then
            echo -e "${BLUE}📂 輸出位置: 合併檔案在 $FOLDER_PATH${NC}"
        else
            echo -e "${BLUE}📂 輸出位置: 與原音訊檔案相同目錄${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  批次處理完成，但有部分失敗${NC}"
        echo -e "${BLUE}⏱️  總耗時: ${DURATION} 秒${NC}"
        echo -e "${GREEN}📊 成功處理: $SUCCESS_COUNT 個檔案${NC}"
        echo -e "${RED}📊 處理失敗: $FAILED_COUNT 個檔案${NC}"
        echo -e "${BLUE}💡 建議檢查 API 配額或網路連接${NC}"
    fi
}

# 主程式
main() {
    # 檢查參數
    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        show_usage
        exit 0
    fi
    
    # 執行檢查
    check_requirements
    check_virtual_env
    check_dependencies
    
    echo ""
    
    # 取得資料夾路徑、模型和輸出格式
    get_folder_path "$1"
    get_transcribe_model "$2"
    get_output_format "$3"
    check_combined_mode "$@"
    
    # 預覽檔案
    preview_files
    
    # 確認執行
    confirm_execution
    
    # 開始處理
    run_processing
}

# 錯誤處理
set -e
trap 'echo -e "${RED}❌ 腳本執行中發生錯誤${NC}"; exit 1' ERR

# 執行主程式
main "$@"