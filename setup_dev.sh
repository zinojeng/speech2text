#!/bin/bash

echo "設置 Speech2Text 開發環境..."

# 檢測作業系統
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "檢測到 macOS 系統"
    
    # 檢查 Homebrew 是否已安裝
    if ! command -v brew &> /dev/null; then
        echo "安裝 Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    # 安裝 ffmpeg
    echo "安裝 ffmpeg..."
    brew install ffmpeg
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    echo "檢測到 Linux 系統"
    
    # 檢查包管理器
    if command -v apt-get &> /dev/null; then
        # Debian/Ubuntu
        echo "使用 apt 安裝必要工具..."
        sudo apt-get update
        sudo apt-get install -y ffmpeg
    elif command -v dnf &> /dev/null; then
        # Fedora
        echo "使用 dnf 安裝必要工具..."
        sudo dnf install -y ffmpeg
    else
        echo "無法識別的 Linux 發行版，請手動安裝 ffmpeg"
    fi
    
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    echo "檢測到 Windows 系統"
    echo "請確保已安裝 ffmpeg 並添加到系統路徑"
    echo "建議使用 Chocolatey 安裝："
    echo "choco install ffmpeg"
fi

# 建立捷徑命令
echo "建立啟動捷徑..."

# 建立別名設定 (針對 zsh/bash)
if [[ -f "$HOME/.zshrc" ]]; then
    SHELL_RC="$HOME/.zshrc"
elif [[ -f "$HOME/.bashrc" ]]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [[ -n "$SHELL_RC" ]]; then
    echo "# Speech2Text 啟動別名" >> "$SHELL_RC"
    echo "alias speech2text='cd $(pwd) && ./start_app.sh'" >> "$SHELL_RC"
    echo "已新增別名 'speech2text' 到 $SHELL_RC"
    echo "請重新載入設定檔或重啟終端機以啟用別名"
    echo "  source $SHELL_RC"
fi

echo "設置完成！"
echo "現在可以使用以下方式啟動應用程式："
echo "1. 執行 ./start_app.sh"
echo "2. 使用別名 'speech2text' (需重新載入設定檔)" 