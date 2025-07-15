#!/bin/bash

# API 金鑰設定助手
# API Key Setup Helper

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}===================================${NC}"
echo -e "${BLUE}      API 金鑰設定助手${NC}"
echo -e "${BLUE}    API Key Setup Helper${NC}"
echo -e "${BLUE}===================================${NC}"
echo ""

# 檢查 .env 檔案是否存在
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ 找不到 .env 檔案${NC}"
    echo -e "${BLUE}🔧 正在建立 .env 檔案...${NC}"
    cat > .env << EOF
# OpenAI API 設定
OPENAI_API_KEY=

# Google Gemini API 設定
GOOGLE_API_KEY=

# 可選的其他設定
# OPENAI_ORG_ID=your_org_id_here
EOF
    echo -e "${GREEN}✅ .env 檔案已建立${NC}"
fi

# 顯示目前設定
echo -e "${BLUE}📋 目前 API 金鑰設定:${NC}"
echo ""

# 檢查 OpenAI API Key
OPENAI_KEY=$(grep "OPENAI_API_KEY=" .env | cut -d'=' -f2 | tr -d ' ')
if [ -z "$OPENAI_KEY" ] || [ "$OPENAI_KEY" = "your_openai_api_key_here" ]; then
    echo -e "${RED}❌ OpenAI API Key: 未設定${NC}"
    OPENAI_STATUS="missing"
else
    echo -e "${GREEN}✅ OpenAI API Key: ${OPENAI_KEY:0:20}...${NC}"
    OPENAI_STATUS="ok"
fi

# 檢查 Google API Key
GOOGLE_KEY=$(grep "GOOGLE_API_KEY=" .env | cut -d'=' -f2 | tr -d ' ')
if [ -z "$GOOGLE_KEY" ] || [ "$GOOGLE_KEY" = "your_google_api_key_here" ]; then
    echo -e "${RED}❌ Google API Key: 未設定${NC}"
    GOOGLE_STATUS="missing"
else
    echo -e "${GREEN}✅ Google API Key: ${GOOGLE_KEY:0:20}...${NC}"
    GOOGLE_STATUS="ok"
fi

echo ""

# 設定 Google API Key
if [ "$GOOGLE_STATUS" = "missing" ]; then
    echo -e "${BLUE}🔑 請設定 Google Gemini API 金鑰:${NC}"
    echo -e "${YELLOW}💡 取得方式: https://aistudio.google.com/app/apikey${NC}"
    echo -e "${YELLOW}💡 格式通常為: AIzaSy...${NC}"
    echo ""
    read -p "請輸入您的 Google Gemini API 金鑰: " NEW_GOOGLE_KEY
    
    if [ ! -z "$NEW_GOOGLE_KEY" ]; then
        # 更新 .env 檔案
        if grep -q "GOOGLE_API_KEY=" .env; then
            # 替換現有的行
            sed -i.bak "s/GOOGLE_API_KEY=.*/GOOGLE_API_KEY=$NEW_GOOGLE_KEY/" .env
        else
            # 新增行
            echo "GOOGLE_API_KEY=$NEW_GOOGLE_KEY" >> .env
        fi
        echo -e "${GREEN}✅ Google API Key 已設定${NC}"
    else
        echo -e "${YELLOW}⚠️  跳過 Google API Key 設定${NC}"
    fi
fi

# 設定 OpenAI API Key
if [ "$OPENAI_STATUS" = "missing" ]; then
    echo ""
    echo -e "${BLUE}🔑 請設定 OpenAI API 金鑰:${NC}"
    echo -e "${YELLOW}💡 取得方式: https://platform.openai.com/api-keys${NC}"
    echo -e "${YELLOW}💡 格式通常為: sk-proj-...${NC}"
    echo ""
    read -p "請輸入您的 OpenAI API 金鑰: " NEW_OPENAI_KEY
    
    if [ ! -z "$NEW_OPENAI_KEY" ]; then
        # 更新 .env 檔案
        if grep -q "OPENAI_API_KEY=" .env; then
            # 替換現有的行
            sed -i.bak "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$NEW_OPENAI_KEY/" .env
        else
            # 新增行
            echo "OPENAI_API_KEY=$NEW_OPENAI_KEY" >> .env
        fi
        echo -e "${GREEN}✅ OpenAI API Key 已設定${NC}"
    else
        echo -e "${YELLOW}⚠️  跳過 OpenAI API Key 設定${NC}"
    fi
fi

echo ""
echo -e "${BLUE}📋 最終設定結果:${NC}"

# 重新檢查
OPENAI_KEY=$(grep "OPENAI_API_KEY=" .env | cut -d'=' -f2 | tr -d ' ')
GOOGLE_KEY=$(grep "GOOGLE_API_KEY=" .env | cut -d'=' -f2 | tr -d ' ')

if [ ! -z "$OPENAI_KEY" ] && [ "$OPENAI_KEY" != "your_openai_api_key_here" ]; then
    echo -e "${GREEN}✅ OpenAI API Key: 已設定${NC}"
else
    echo -e "${RED}❌ OpenAI API Key: 未設定${NC}"
fi

if [ ! -z "$GOOGLE_KEY" ] && [ "$GOOGLE_KEY" != "your_google_api_key_here" ]; then
    echo -e "${GREEN}✅ Google API Key: 已設定${NC}"
else
    echo -e "${RED}❌ Google API Key: 未設定${NC}"
fi

echo ""
echo -e "${BLUE}🚀 設定完成！現在可以執行: ./audio_auto.sh${NC}"