FROM python:3.11-slim

LABEL "language"="python"

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    ffmpeg \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# 設置工作目錄
WORKDIR /src

# 複製requirements.txt並安裝Python依賴
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY . .

# 暴露端口（Zeabur 通常使用 8080）
EXPOSE 8080

# 設置環境變數
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

# 啟動應用
CMD ["streamlit", "run", "main_app.py", "--server.port=8080", "--server.address=0.0.0.0"]