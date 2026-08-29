#!/bin/bash

# ==============================================================================
# 智慧批次音訊處理腳本
# Smart Batch Audio Processing Script with Skip Functionality
# 
# 此腳本提供友善的介面來使用 batch_audio_smart.py
# 自動跳過已處理的檔案，支援遞歸掃描子資料夾
# ==============================================================================

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# 腳本所在目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 啟動虛擬環境
if [ -d "$SCRIPT_DIR/venv_app" ]; then
    source "$SCRIPT_DIR/venv_app/bin/activate"
elif [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
fi

# 預設值
DEFAULT_MODEL="gpt-transcribe"
DEFAULT_FORMAT="text"

# 顯示標題
show_banner() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║        ${BLUE}智慧批次音訊處理系統 v2.0${CYAN}                         ║${NC}"
    echo -e "${CYAN}║        ${BLUE}Smart Batch Audio Processor${CYAN}                       ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# 顯示使用說明
show_usage() {
    echo -e "${GREEN}使用方法:${NC}"
    echo -e "  $0 <資料夾路徑> [選項]"
    echo ""
    echo -e "${GREEN}選項:${NC}"
    echo -e "  ${YELLOW}--model${NC} MODEL      轉錄模型 (預設: gpt-transcribe)"
    echo -e "                     可選: gpt-transcribe, gemini-3.5-transcribe"
    echo -e "  ${YELLOW}--format${NC} FORMAT   輸出格式 (預設: text)"
    echo -e "                     可選: text, srt, markdown"
    echo -e "  ${YELLOW}--force${NC}           強制重新處理所有檔案（忽略已存在的轉錄）"
    echo -e "  ${YELLOW}--docx${NC}            同時產生 Word 文件"
    echo -e "  ${YELLOW}--combined${NC}        合併所有轉錄到單一檔案"
    echo -e "  ${YELLOW}--help${NC}            顯示此說明"
    echo ""
    echo -e "${GREEN}範例:${NC}"
    echo -e "  ${CYAN}# 基本使用（自動跳過已處理檔案）${NC}"
    echo -e "  $0 /path/to/audio/folder"
    echo ""
    echo -e "  ${CYAN}# 使用 SRT 格式輸出${NC}"
    echo -e "  $0 /path/to/audio/folder --format srt"
    echo ""
    echo -e "  ${CYAN}# 強制重新處理所有檔案${NC}"
    echo -e "  $0 /path/to/audio/folder --force"
    echo ""
    echo -e "  ${CYAN}# 合併所有輸出並產生 Word 文件${NC}"
    echo -e "  $0 /path/to/audio/folder --combined --docx"
    echo ""
}

# 檢查必要檔案
check_requirements() {
    local has_error=0
    
    echo -e "${BLUE}📋 檢查系統需求...${NC}"
    
    # 檢查 Python
    if ! command -v python &> /dev/null; then
        echo -e "${RED}❌ 找不到 Python${NC}"
        has_error=1
    else
        python_version=$(python --version 2>&1 | awk '{print $2}')
        echo -e "${GREEN}✅ Python $python_version${NC}"
    fi
    
    # 檢查主程式
    if [ ! -f "$SCRIPT_DIR/batch_audio_smart.py" ]; then
        echo -e "${RED}❌ 找不到 batch_audio_smart.py${NC}"
        has_error=1
    else
        echo -e "${GREEN}✅ 主程式檔案存在${NC}"
    fi
    
    # 檢查 .env 檔案
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        echo -e "${RED}❌ 找不到 .env 檔案${NC}"
        echo -e "${YELLOW}💡 請建立 .env 檔案並設定以下內容:${NC}"
        echo -e "${CYAN}OPENAI_API_KEY=your_openai_api_key${NC}"
        has_error=1
    else
        # 檢查 OpenAI API Key
        if grep -q "OPENAI_API_KEY=" "$SCRIPT_DIR/.env"; then
            echo -e "${GREEN}✅ OpenAI API Key 已設定${NC}"
        else
            echo -e "${RED}❌ 請在 .env 檔案中設定 OPENAI_API_KEY${NC}"
            has_error=1
        fi
    fi
    
    # 檢查必要的 Python 套件（使用虛擬環境時簡化檢查）
    echo -e "${BLUE}📦 檢查 Python 套件...${NC}"
    
    # 快速檢查關鍵套件
    if python -c "import openai" 2>/dev/null; then
        echo -e "${GREEN}✅ openai 套件已安裝${NC}"
    else
        echo -e "${RED}❌ 缺少 openai 套件${NC}"
        echo -e "${YELLOW}請在虛擬環境中安裝: pip install openai${NC}"
        has_error=1
    fi
    
    if python -c "import pydub" 2>/dev/null; then
        echo -e "${GREEN}✅ pydub 套件已安裝${NC}"
    else
        echo -e "${RED}❌ 缺少 pydub 套件${NC}"
        echo -e "${YELLOW}請在虛擬環境中安裝: pip install pydub${NC}"
        has_error=1
    fi
    
    # 檢查 ffmpeg
    if command -v ffmpeg &> /dev/null; then
        echo -e "${GREEN}✅ ffmpeg 已安裝${NC}"
    else
        echo -e "${YELLOW}⚠️  建議安裝 ffmpeg 以支援更多音訊格式${NC}"
        echo -e "${CYAN}   macOS: brew install ffmpeg${NC}"
        echo -e "${CYAN}   Ubuntu: sudo apt-get install ffmpeg${NC}"
    fi
    
    echo ""
    
    if [ $has_error -eq 1 ]; then
        echo -e "${RED}❌ 請先解決上述問題再執行腳本${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ 所有需求檢查通過${NC}"
    echo ""
}

# 檢查資料夾
check_folder() {
    local folder="$1"
    
    if [ -z "$folder" ]; then
        echo -e "${RED}❌ 請提供資料夾路徑${NC}"
        echo ""
        show_usage
        exit 1
    fi
    
    if [ ! -d "$folder" ]; then
        echo -e "${RED}❌ 資料夾不存在: $folder${NC}"
        exit 1
    fi
    
    # 檢查是否有音訊檔案
    local audio_count=0
    for ext in mp3 wav m4a mp4 mov avi mkv; do
        count=$(find "$folder" -type f -name "*.$ext" 2>/dev/null | wc -l)
        audio_count=$((audio_count + count))
    done
    
    if [ $audio_count -eq 0 ]; then
        echo -e "${YELLOW}⚠️  在 $folder 中未找到音訊檔案${NC}"
        echo -e "${CYAN}支援的格式: mp3, wav, m4a, mp4, mov, avi, mkv 等${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ 找到 $audio_count 個音訊檔案${NC}"
}

# 預覽處理
preview_processing() {
    local folder="$1"
    shift
    local args="$@"
    
    echo -e "${BLUE}📊 處理預覽${NC}"
    echo -e "${CYAN}資料夾: $folder${NC}"
    
    # 顯示將要使用的參數
    if [[ " $args " =~ " --force " ]]; then
        echo -e "${YELLOW}模式: 強制重新處理所有檔案${NC}"
    else
        echo -e "${GREEN}模式: 智慧跳過已處理檔案${NC}"
    fi
    
    if [[ " $args " =~ " --combined " ]]; then
        echo -e "${MAGENTA}輸出: 合併到單一檔案${NC}"
    else
        echo -e "${MAGENTA}輸出: 個別檔案${NC}"
    fi
    
    echo ""
}

# 執行處理
run_processing() {
    local folder="$1"
    shift
    local args="$@"
    
    echo -e "${BLUE}🚀 開始處理...${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════${NC}"
    
    # 建立日誌目錄
    mkdir -p "$SCRIPT_DIR/logs"
    
    # 執行 Python 腳本
    python "$SCRIPT_DIR/batch_audio_smart.py" "$folder" $args
    
    local exit_code=$?
    
    echo -e "${CYAN}═══════════════════════════════════════════${NC}"
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ 處理完成！${NC}"
        
        # 顯示輸出位置
        echo -e "${BLUE}📁 輸出檔案位置:${NC}"
        echo -e "${CYAN}   $folder${NC}"
        
        # 檢查是否有處理報告
        report_file=$(ls -t "$folder"/processing_report_*.json 2>/dev/null | head -1)
        if [ -n "$report_file" ]; then
            echo -e "${BLUE}📊 處理報告:${NC}"
            echo -e "${CYAN}   $report_file${NC}"
        fi
    else
        echo -e "${RED}❌ 處理過程中發生錯誤${NC}"
        echo -e "${YELLOW}請檢查日誌檔案以獲取詳細資訊${NC}"
    fi
}

# 主程式
main() {
    show_banner
    
    # 檢查是否需要顯示說明
    if [ "$1" == "--help" ] || [ "$1" == "-h" ] || [ -z "$1" ]; then
        show_usage
        exit 0
    fi
    
    # 取得資料夾路徑
    FOLDER_PATH="$1"
    shift
    
    # 檢查系統需求
    check_requirements
    
    # 檢查資料夾
    check_folder "$FOLDER_PATH"
    
    # 預覽處理
    preview_processing "$FOLDER_PATH" "$@"
    
    # 確認執行
    echo -e "${YELLOW}準備開始處理，是否繼續？ (y/n)${NC}"
    read -p "> " confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo -e "${YELLOW}已取消處理${NC}"
        exit 0
    fi
    
    # 執行處理
    run_processing "$FOLDER_PATH" "$@"
}

# 執行主程式
main "$@"