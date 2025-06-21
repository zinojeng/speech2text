#!/usr/bin/env python3
"""
主應用程式入口點 - 適用於 Zeabur 部署
"""

import os
import sys
import warnings

# 抑制警告信息
warnings.filterwarnings("ignore")

# 設置環境變數
os.environ["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))

# 導入主應用
try:
    from main_app import main
    
    if __name__ == "__main__":
        # 設置 Streamlit 配置
        import streamlit as st
        st.set_page_config(
            page_title="語音轉文字與文件處理系統",
            page_icon="🎙️",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # 運行主應用
        main()
        
except ImportError as e:
    print(f"導入錯誤：{e}")
    print("請確保所有依賴都已正確安裝")
    sys.exit(1)
except Exception as e:
    print(f"應用程式啟動錯誤：{e}")
    sys.exit(1) 