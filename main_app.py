# 標準庫導入
import os
import logging
import tempfile
import time

# 第三方庫導入
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
import google.generativeai as genai
from pydub import AudioSegment

# 本地模組導入
from whisper_stt import get_model_description
from transcript_refiner import refine_transcript
from markitdown_utils import (
    convert_file_to_markdown, convert_url_to_markdown,
    extract_keywords, save_uploaded_file
)

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定義可用的 OpenAI 模型
AVAILABLE_MODELS = {
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "o3-mini": "o3-mini",
    "o1-mini": "o1-mini"
}

# 模型設定和價格（USD per 1M tokens）
MODEL_CONFIG = {
    "gpt-4o": {
        "display_name": "gpt-4o",
        "input": 2.50,          # $2.50 per 1M tokens
        "cached_input": 1.25,   # $1.25 per 1M tokens
        "output": 10.00         # $10.00 per 1M tokens
    },
    "gpt-4o-mini": {
        "display_name": "gpt-4o-mini",
        "input": 0.15,          # $0.15 per 1M tokens
        "cached_input": 0.075,  # $0.075 per 1M tokens
        "output": 0.60          # $0.60 per 1M tokens
    },
    "o1-mini": {
        "display_name": "o1-mini",
        "input": 1.10,          # $1.10 per 1M tokens
        "cached_input": 0.55,   # $0.55 per 1M tokens
        "output": 4.40          # $4.40 per 1M tokens
    },
    "o3-mini": {
        "display_name": "o3-mini",
        "input": 1.10,          # $1.10 per 1M tokens
        "cached_input": 0.55,   # $0.55 per 1M tokens
        "output": 4.40          # $4.40 per 1M tokens
    },
    "gemini-2.5-pro-exp-03-25": {
        "display_name": "Gemini 2.5 Pro Experimental",
        "input": 0.00,          # 價格待定
        "cached_input": 0.00,   # 價格待定
        "output": 0.00          # 價格待定
    }
}

# 匯率設定
USD_TO_NTD = 31.5

# 轉錄服務說明
TRANSCRIPTION_SERVICE_INFO = {
    "Whisper": """
    ### Whisper 模型
    - 開源的語音轉文字模型
    - 支援多種語言
    - 可離線使用
    """,
    "ElevenLabs": """
    ### ElevenLabs 模型
    - 商業級語音轉文字服務
    - 支援 99 種語言
    - 提供說話者辨識功能
    """,
    "OpenAI 2025 New": """
    ### OpenAI 2025 全新模型
    - gpt-4o-transcribe：高精度、多語言支援
    - gpt-4o-mini-transcribe：輕量快速、性價比高
    - 自動語言檢測
    - 更好的中文轉錄效果
    """
}

# 優化服務說明
OPTIMIZATION_SERVICE_INFO = {
    "OpenAI": """
    ### OpenAI 優化模型
    - 專業的文字優化和校正
    - 支援多種語言
    - 可自訂優化程度
    """,
    "Gemini": """
    ### Google Gemini 2.5 Pro (實驗性)
    - 最新的 Google AI 模型
    - 更強的上下文理解能力
    - 更自然的語言處理
    - 支援多語言優化
    - 實驗性功能，持續改進中
    """
}

# MarkItDown 服務說明
MARKITDOWN_SERVICE_INFO = """
### MarkItDown 文件轉換工具
- 將各種格式的文件轉換為 Markdown
- 支援 PDF、DOCX、PowerPoint、Excel 等格式
- 支援網頁 URL 轉換
- 可選用 LLM 優化圖片描述
- 可提取關鍵詞
"""

# 支援的檔案類型
SUPPORTED_FILE_TYPES = [
    "pdf", "docx", "doc", "pptx", "ppt", 
    "xlsx", "xls", "csv", "txt", "rtf", 
    "html", "htm", "md", "markdown"
]

def calculate_cost(input_tokens, output_tokens, model_name, is_cached=False):
    """計算 API 使用成本
    
    Args:
        input_tokens (int): 輸入 tokens 數量
        output_tokens (int): 輸出 tokens 數量
        model_name (str): 模型名稱
        is_cached (bool, optional): 是否使用快取輸入價格. 預設為 False
    
    Returns:
        tuple: (USD 成本, NTD 成本, 詳細計算資訊)
    """
    if model_name not in MODEL_CONFIG:
        return 0, 0, "未支援的模型"
        
    # 取得價格設定
    model = MODEL_CONFIG[model_name]
    input_price = model["cached_input"] if is_cached else model["input"]
    output_price = model["output"]
    
    # 計算 USD 成本 (以每 1M tokens 為單位)
    input_cost = (input_tokens / 1_000_000) * input_price
    output_cost = (output_tokens / 1_000_000) * output_price
    total_cost_usd = input_cost + output_cost
    total_cost_ntd = total_cost_usd * USD_TO_NTD
    
    # 準備詳細計算資訊
    details = f"""
    計算明細 (USD):
    - 輸入: {input_tokens:,} tokens × ${input_price}/1M = ${input_cost:.4f}
    - 輸出: {output_tokens:,} tokens × ${output_price}/1M = ${output_cost:.4f}
    - 總計 (USD): ${total_cost_usd:.4f}
    - 總計 (NTD): NT${total_cost_ntd:.2f}
    """
    return total_cost_usd, total_cost_ntd, details

def refine_transcript_gemini(text, api_key, temperature=0.5, context=""):
    """使用 Gemini 模型優化文字

    Args:
        text (str): 要優化的文字
        api_key (str): Gemini API 金鑰
        temperature (float): 創意程度 (0.0-1.0)
        context (str): 上下文提示

    Returns:
        dict: 包含優化後的文字和摘要
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')
        
        # 準備提示詞
        prompt = f"""
        請將以下文字優化為一份結構完整、格式豐富的會議記錄或講稿草稿。
        無論輸入文字是簡體或繁體中文，請務必將所有輸出轉換為繁體中文。

        # 任務要求
        1. **基本要求**
           - 將所有文字轉換為繁體中文
           - 保持原意的情況下讓文字更通順、專業
           - 製作重點摘要（300字以內）

        2. **格式要求**（請參考以下範例格式）
           - 使用 `---` 作為主要分隔線
           - 使用 `# ## ###` 等標題層級區分主題
           - 使用 `**粗體**` 標示：
             * 標題（如：**標題：**）
             * 講者（如：**[講者]:**）
             * 關鍵詞或重要概念
           - 使用 `-` 或 `*` 製作項目清單，支援多層縮排
           - 使用 `>` 製作引用區塊（適用於重要引述）
           - 適當使用 `*斜體*` 強調次要重點

        # 上下文資訊
        {context if context else "無特定上下文"}

        # 原始文字
        {text}

        # 請按照以下格式回應（必須使用繁體中文）

        [優化後文字]
        ---

        **(會議記錄/講稿草稿 - 詳細版)**

        **標題：** [主要標題]

        **日期：** [日期，若有]
        **參與者：** [相關人員，若有]

        ## 1. 背景說明
        **主要議題：**
        - 重點一
          - 細節說明
          - 補充資訊
        - 重點二
          - 相關數據
          - 具體案例

        **[發言者姓名/角色]:** 「重要發言內容...」

        ## 2. 討論內容
        ### 2.1 議題探討
        **現況分析：**
        - **目前進度：** 說明...
        - **遇到挑戰：**
          - 挑戰一
          - 挑戰二

        **解決方案：**
        1. 方案一
           - 優點：...
           - 考量：...
        2. 方案二
           - 建議做法：...
           - 所需資源：...

        ### 2.2 決議事項
        **結論：**
        - 重要決定一
        - 重要決定二

        ## 3. 後續規劃
        **時程安排：**
        - 短期目標（1個月內）
        - 中期目標（3個月內）
        - 長期目標（6個月以上）

        **待辦事項：**
        1. 優先處理：...
        2. 後續追蹤：...

        ---

        [重點摘要]
        ## 會議重點摘要

        **核心議題：**
        1. 主要討論重點
           - 關鍵發現
           - 重要決議
        
        **執行方向：**
        - 近期行動項目
          - 負責單位
          - 時程規劃
        
        **注意事項：**
        - 需要特別關注的議題
        - 潛在風險與因應措施
        """
        
        response = model.generate_content(
            prompt,
            generation_config={
                'temperature': temperature
            }
        )
        
        # 解析回應
        response_text = response.text
        
        # 使用新的分隔方式解析回應
        if "[優化後文字]" in response_text and "[重點摘要]" in response_text:
            parts = response_text.split("[重點摘要]")
            corrected = parts[0].split("[優化後文字]")[1].strip()
            summary = parts[1].strip()
        else:
            # 如果找不到標記，嘗試使用舊的分隔方式
            parts = response_text.split("重點摘要：")
            if len(parts) >= 2:
                corrected = parts[0].strip()
                summary = parts[1].strip()
            else:
                corrected = response_text
                summary = "無法生成摘要"
        
        return {
            "corrected": corrected,
            "summary": summary,
            "usage": {
                "total_input_tokens": 0,  # Gemini 暫時不計算 tokens
                "total_output_tokens": 0
            }
        }
    except Exception as e:
        logger.error(f"Gemini API 錯誤：{str(e)}")
        return None

def display_cost_info(
    input_tokens,
    output_tokens,
    model_name,
    is_cached=False
):
    """在 Streamlit 介面中顯示成本資訊"""
    cost_usd, cost_ntd, details = calculate_cost(
        input_tokens,
        output_tokens,
        model_name,
        is_cached
    )
    
    with st.sidebar.expander("💰 成本計算", expanded=True):
        st.write("### Token 使用量")
        st.write(f"- 輸入: {input_tokens:,} tokens")
        st.write(f"- 輸出: {output_tokens:,} tokens")
        st.write(f"- 總計: {input_tokens + output_tokens:,} tokens")
        
        if (input_tokens + output_tokens) == 0:
            st.warning("目前 token 使用量為 0，請確認是否已正確計算 token 數量！")
        
        st.write("### 費用明細")
        st.text(details)
        
        if is_cached:
            st.info("✨ 使用快取價格計算")

def process_markdown_extraction(text, api_key, model, keyword_count):
    """
    處理 Markdown 文本提取關鍵詞
    
    Args:
        text (str): Markdown 文本
        api_key (str): OpenAI API Key
        model (str): 模型名稱
        keyword_count (int): 要提取的關鍵詞數量
        
    Returns:
        List[str]: 關鍵詞列表
    """
    try:
        with st.spinner("正在提取關鍵詞..."):
            keywords = extract_keywords(
                markdown_text=text,
                api_key=api_key,
                model=model,
                count=keyword_count
            )
            return keywords
    except Exception as e:
        st.error(f"提取關鍵詞失敗: {str(e)}")
        logger.error(f"提取關鍵詞失敗: {str(e)}")
        return []

def render_markitdown_tab():
    """渲染 MarkItDown 標籤頁"""
    st.header("文件轉換與關鍵詞提取")
    
    # MarkItDown 服務說明
    st.markdown(MARKITDOWN_SERVICE_INFO)
    
    # 初始化 session state
    if "markdown_text" not in st.session_state:
        st.session_state.markdown_text = None
    if "markdown_keywords" not in st.session_state:
        st.session_state.markdown_keywords = None
    
    # 創建兩個標籤頁：文件上傳和 URL 輸入
    tab1, tab2 = st.tabs(["📄 文件上傳", "🔗 URL 輸入"])
    
    # OpenAI API 設定
    with st.expander("OpenAI API 設定", expanded=False):
        openai_api_key = st.text_input(
            "OpenAI API 金鑰",
            type="password",
            help="用於關鍵詞提取和圖片描述優化"
        )
        
        use_llm = st.checkbox(
            "使用 LLM 處理圖片描述",
            value=False,
            help="啟用後將使用 OpenAI 模型為圖片生成更好的描述"
        )
        
        openai_model = st.selectbox(
            "選擇模型",
            ["gpt-4o-mini", "gpt-4o"],
            index=0,
            help="用於關鍵詞提取的模型"
        )
        
        keyword_count = st.number_input(
            "關鍵詞數量",
            min_value=5,
            max_value=20,
            value=10,
            step=1,
            help="要提取的關鍵詞數量"
        )
    
    # 文件上傳標籤頁
    with tab1:
        uploaded_file = st.file_uploader(
            "上傳文件",
            type=SUPPORTED_FILE_TYPES,
            help=f"支援的檔案類型: {', '.join(SUPPORTED_FILE_TYPES)}"
        )
        
        if uploaded_file:
            # 顯示檔案資訊
            st.info(
                f"已上傳: {uploaded_file.name} "
                f"({uploaded_file.size/1024:.1f} KB)"
            )
            
            # 處理按鈕
            convert_btn = st.button(
                "🔄 轉換為 Markdown",
                use_container_width=True
            )
            
            if convert_btn:
                if use_llm and not openai_api_key:
                    st.error("使用 LLM 處理圖片需要提供 OpenAI API 金鑰")
                else:
                    # 保存上傳的檔案
                    success, temp_path = save_uploaded_file(uploaded_file)
                    
                    if success:
                        # 轉換檔案
                        with st.spinner("正在轉換文件..."):
                            success, md_text, info = convert_file_to_markdown(
                                input_path=temp_path,
                                use_llm=use_llm,
                                api_key=openai_api_key,
                                model=openai_model
                            )
                            
                            # 清理臨時檔案
                            try:
                                os.remove(temp_path)
                            except Exception as e:
                                logger.error(f"清理臨時檔案失敗: {str(e)}")
                                pass
                            
                            if success:
                                st.session_state.markdown_text = md_text
                                # 顯示轉換資訊
                                st.success(f"轉換成功！內容長度: {len(md_text)} 字元")
                                
                                # 自動提取關鍵詞
                                if openai_api_key:
                                    st.session_state.markdown_keywords = (
                                        process_markdown_extraction(
                                            md_text,
                                            openai_api_key,
                                            openai_model,
                                            keyword_count
                                        )
                                    )
                                st.rerun()
                            else:
                                # 顯示錯誤資訊
                                st.error(f"轉換失敗: {info.get('error', '未知錯誤')}")
                    else:
                        st.error(f"處理上傳檔案時發生錯誤: {temp_path}")
    
    # URL 輸入標籤頁
    with tab2:
        url = st.text_input(
            "輸入網址",
            placeholder="例如: https://www.example.com",
            help="輸入要轉換為 Markdown 的網址"
        )
        
        if url:
            # 處理按鈕
            convert_url_btn = st.button(
                "🔄 轉換 URL 內容",
                use_container_width=True
            )
            
            if convert_url_btn:
                # 轉換 URL
                with st.spinner("正在轉換網頁內容..."):
                    success, md_text, info = convert_url_to_markdown(url)
                    
                    if success:
                        st.session_state.markdown_text = md_text
                        # 顯示轉換資訊
                        st.success(f"轉換成功！內容長度: {len(md_text)} 字元")
                        
                        # 自動提取關鍵詞
                        if openai_api_key:
                            st.session_state.markdown_keywords = (
                                process_markdown_extraction(
                                    md_text,
                                    openai_api_key,
                                    openai_model,
                                    keyword_count
                                )
                            )
                        st.rerun()
                    else:
                        # 顯示錯誤資訊
                        st.error(f"轉換失敗: {info.get('error', '未知錯誤')}")
    
    # 顯示轉換結果
    if st.session_state.markdown_text:
        # 創建兩個標籤頁顯示結果
        result_tab1, result_tab2 = st.tabs(["📝 Markdown 內容", "🔑 關鍵詞"])
        
        # Markdown 內容標籤頁
        with result_tab1:
            st.subheader("轉換結果")
            
            # 顯示 Markdown 文字
            st.text_area(
                "Markdown 文字",
                st.session_state.markdown_text,
                height=400
            )
            
            # 下載按鈕
            st.download_button(
                label="📥 下載 Markdown 檔案",
                data=st.session_state.markdown_text,
                file_name="converted.md",
                mime="text/markdown",
                help="下載轉換後的 Markdown 文件",
                use_container_width=True
            )
            
            # 添加按鈕，將 Markdown 文字傳送到文字優化功能
            if st.button("📤 傳送至文字優化功能", use_container_width=True):
                st.session_state.transcribed_text = (
                    st.session_state.markdown_text
                )
                st.rerun()
        
        # 關鍵詞標籤頁
        with result_tab2:
            st.subheader("關鍵詞提取")
            
            if not st.session_state.markdown_keywords and openai_api_key:
                # 手動提取關鍵詞的按鈕
                if st.button("🔍 提取關鍵詞", use_container_width=True):
                    st.session_state.markdown_keywords = (
                        process_markdown_extraction(
                            st.session_state.markdown_text,
                            openai_api_key,
                            openai_model,
                            keyword_count
                        )
                    )
                    st.rerun()
            
            if not openai_api_key:
                st.warning("請提供 OpenAI API 金鑰以啟用關鍵詞提取功能")
            
            if st.session_state.markdown_keywords:
                # 顯示關鍵詞
                st.write("### 提取的關鍵詞")
                for i, keyword in enumerate(
                    st.session_state.markdown_keywords
                ):
                    st.write(f"{i+1}. {keyword}")
                
                # 複製關鍵詞按鈕
                keywords_text = "\n".join(st.session_state.markdown_keywords)
                st.download_button(
                    label="📋 下載關鍵詞列表",
                    data=keywords_text,
                    file_name="keywords.txt",
                    mime="text/plain",
                    help="下載提取的關鍵詞列表",
                    use_container_width=True
                )

def main():
    """主程式函數"""
    st.title("音訊轉文字與文件處理系統")
    
    # 初始化 session state
    if "transcribed_text" not in st.session_state:
        st.session_state.transcribed_text = None
    if "input_tokens" not in st.session_state:
        st.session_state.input_tokens = 0
    if "output_tokens" not in st.session_state:
        st.session_state.output_tokens = 0
    if "total_tokens" not in st.session_state:
        st.session_state.total_tokens = 0
    if "optimized_text" not in st.session_state:
        st.session_state.optimized_text = None
    if "summary_text" not in st.session_state:
        st.session_state.summary_text = None
    if "markdown_text" not in st.session_state:
        st.session_state.markdown_text = None
    if "markdown_keywords" not in st.session_state:
        st.session_state.markdown_keywords = None

    # 創建主要的功能標籤頁
    main_tabs = st.tabs(["🎙️ 語音轉文字", "📝 文件轉換與關鍵詞", "ℹ️ 關於"])
    
    # 語音轉文字標籤頁
    with main_tabs[0]:
        with st.sidebar:
            st.header("設定")
            
            # 分成兩個標籤頁：轉錄設定和優化設定
            tab1, tab2 = st.tabs(["🎙️ 轉錄設定", "✨ 優化設定"])
            
            # 轉錄設定標籤頁
            with tab1:
                # 選擇轉錄服務
                transcription_service = st.selectbox(
                    "選擇轉錄服務",
                    ["OpenAI 2025 New", "Whisper", "ElevenLabs"],
                    index=0,
                    help="選擇要使用的語音轉文字服務"
                )
                
                # 顯示服務說明
                st.markdown(TRANSCRIPTION_SERVICE_INFO[transcription_service])
                
                # Whisper 相關設定
                if transcription_service == "Whisper":
                    whisper_model = st.selectbox(
                        "選擇 Whisper 模型",
                        options=["tiny", "base", "small", "medium", "large"],
                        index=2
                    )
                    st.session_state["whisper_model"] = whisper_model
                    st.caption(get_model_description(whisper_model))
                    
                    # 語言設定
                    language_mode = st.radio(
                        "語言設定",
                        options=["自動偵測", "指定語言", "混合語言"],
                        help="選擇音訊的語言處理模式"
                    )
                    
                    if language_mode == "指定語言":
                        languages = {
                            "中文 (繁體/簡體)": "zh",
                            "英文": "en",
                            "日文": "ja",
                            "韓文": "ko",
                            "其他": "custom"
                        }
                        
                        selected_lang = st.selectbox(
                            "選擇語言",
                            options=list(languages.keys())
                        )
                        
                        if selected_lang == "其他":
                            custom_lang = st.text_input(
                                "輸入語言代碼",
                                placeholder="例如：fr 代表法文",
                                help="請輸入 ISO 639-1 語言代碼"
                            )
                            language_code = custom_lang if custom_lang else None
                        else:
                            language_code = languages[selected_lang]
                    else:
                        language_code = None
                
                # ElevenLabs 相關設定
                elevenlabs_api_key = None
                if transcription_service == "ElevenLabs":
                    elevenlabs_api_key = st.text_input(
                        "ElevenLabs API 金鑰",
                        type="password"
                    )
                
                # OpenAI API 金鑰
                openai_api_key = st.text_input(
                    "OpenAI API 金鑰",
                    type="password"
                )
                
                # OpenAI 新模型相關設定
                if transcription_service == "OpenAI 2025 New":
                    openai_model = st.selectbox(
                        "選擇 OpenAI 轉錄模型",
                        ["gpt-4o-mini-transcribe", "gpt-4o-transcribe"],
                        index=0,
                        help="選擇要使用的 OpenAI 轉錄模型"
                    )
                    
                    # 語言設定
                    language_mode = st.radio(
                        "語言設定",
                        options=["自動偵測", "指定語言"],
                        help="選擇音訊的語言處理模式"
                    )
                    
                    if language_mode == "指定語言":
                        languages = {
                            "中文 (繁體/簡體)": "zh",
                            "英文": "en",
                            "日文": "ja",
                            "韓文": "ko",
                            "其他": "custom"
                        }
                        
                        selected_lang = st.selectbox(
                            "選擇語言",
                            options=list(languages.keys())
                        )
                        
                        if selected_lang == "其他":
                            custom_lang = st.text_input(
                                "輸入語言代碼",
                                placeholder="例如：fr 代表法文",
                                help="請輸入 ISO 639-1 語言代碼"
                            )
                            language_code = custom_lang if custom_lang else None
                        else:
                            language_code = languages[selected_lang]
                    else:
                        language_code = None

                # 其他設定 (已移除啟用說話者辨識設定)
            
            # 優化設定標籤頁
            with tab2:
                # 選擇優化服務
                optimization_service = st.selectbox(
                    "選擇優化服務",
                    ["Gemini", "OpenAI"],
                    help="選擇要使用的文字優化服務"
                )
                
                # 顯示服務說明
                st.markdown(OPTIMIZATION_SERVICE_INFO[optimization_service])
                
                # 顯示 Gemini 模型資訊
                if optimization_service == "Gemini":
                    st.info("使用 Gemini 2.5 Pro Experimental 模型進行優化")
                
                # Gemini API 金鑰（如果選擇 Gemini）
                gemini_api_key = None
                if optimization_service == "Gemini":
                    gemini_api_key = st.text_input(
                        "Google API 金鑰",
                        type="password"
                    )
                
                # 優化設定
                temperature = st.slider(
                    "創意程度",
                    0.0,
                    1.0,
                    0.5,
                    help="較高的值會產生更有創意的結果，較低的值會產生更保守的結果"
                )
            
            # 作者資訊
            st.markdown("---")
            st.markdown("""
            ### Created by
            **Tseng Yao Hsien**  
            Endocrinologist  
            Tungs' Taichung MetroHarbor Hospital
            """)

        # 提示詞設定
        with st.expander("提示詞設定（選填）", expanded=False):
            context_prompt = st.text_area(
                "請輸入相關提示詞",
                placeholder="例如：\n- 這是一段醫學演講\n- 包含專有名詞：糖尿病、胰島素\n- 主要討論糖尿病的治療方法",
                help="提供音訊內容的相關資訊，可以幫助 AI 更準確地理解和轉錄內容"
            )
        
        # 上傳檔案
        uploaded_file = st.file_uploader(
            "上傳音訊檔案",
            type=["mp3", "wav", "ogg", "m4a"]
        )
        
        # 只顯示轉錄按鈕
        transcribe_button = st.button("🎙️ 轉錄音訊", use_container_width=True)
        
        # 顯示轉錄結果（如果有的話）
        if st.session_state.transcribed_text:
            st.subheader("轉錄結果")
            
            # 顯示轉錄文字
            st.text_area(
                "轉錄文字",
                st.session_state.transcribed_text,
                height=200
            )
            
            # 下載按鈕
            st.markdown("### 下載選項")
            st.download_button(
                label="📥 下載轉錄文字",
                data=st.session_state.transcribed_text,
                file_name="transcription.txt",
                mime="text/plain",
                help="下載轉錄後的文字檔案",
                use_container_width=True,
                key="download_transcription"
            )
            
            # 只在有轉錄文字時顯示優化按鈕
            optimize_button = st.button("✨ 優化文字", use_container_width=True)
        else:
            optimize_button = False
        
        # 處理轉錄
        if uploaded_file and transcribe_button:
            if not openai_api_key:
                st.error("請提供 OpenAI API 金鑰")
                return
                
            if transcription_service == "ElevenLabs" and not elevenlabs_api_key:
                st.error("請提供 ElevenLabs API 金鑰")
                return
            
            try:
                with st.spinner("處理中..."):
                    # 初始化變數
                    full_transcript = ""
                    
                    # 初始化 OpenAI 客戶端（如果需要）
                    if transcription_service == "OpenAI 2025 New":
                        openai_client = OpenAI(api_key=openai_api_key)
                    
                    # 處理上傳的檔案
                    suffix = os.path.splitext(uploaded_file.name)[1]
                    with tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=suffix
                    ) as temp_file:
                        temp_file.write(uploaded_file.getvalue())
                        temp_path = temp_file.name
                    
                    try:
                        # 檢查音訊長度
                        audio = AudioSegment.from_file(temp_path)
                        duration_seconds = len(audio) / 1000
                        
                        if duration_seconds > 600:  # 如果音訊超過 10 分鐘
                            st.info("音訊較長，將採用固定時間分段處理...")
                            logger.info(
                                "音訊檔案長度: %.2f 秒，開始固定時間分段處理",
                                duration_seconds
                            )
                            
                            # 設定分段參數
                            MAX_SEGMENT_DURATION = 600  # 最大分段時長（秒）
                            OVERLAP_DURATION = 30      # 重疊時長（秒）
                            segments = []
                            start_time = 0.0
                            
                            # 進行固定時間分段
                            while start_time < duration_seconds:
                                end_time = min(start_time + MAX_SEGMENT_DURATION, duration_seconds)
                                
                                # 如果不是第一段，則從前一段結尾提前開始
                                if start_time > 0:
                                    segment_start = start_time - OVERLAP_DURATION
                                else:
                                    segment_start = start_time
                                
                                # 擷取音訊片段
                                segment = audio[int(segment_start * 1000):int(end_time * 1000)]
                                segment_path = f"{temp_path}_segment_{len(segments)}.mp3"
                                segment.export(segment_path, format="mp3")
                                logger.info(
                                    "儲存分段 %d，時間範圍：%.2f - %.2f 秒",
                                    len(segments) + 1,
                                    segment_start,
                                    end_time
                                )
                                segments.append(segment_path)
                                
                                # 更新開始時間
                                start_time = end_time
                            
                            audio_segments = segments
                            logger.info(
                                "完成分段處理，共 %d 個分段",
                                len(segments)
                            )
                        else:
                            audio_segments = [temp_path]
                            logger.info("音訊長度適中，不需分段處理")
                        
                        progress_bar = st.progress(0)
                        transcription_prompt = (
                            context_prompt if context_prompt else None
                        )
                        segment_results = []
                        
                        for i, segment_path in enumerate(audio_segments):
                            if transcription_service == "OpenAI 2025 New":
                                MAX_RETRIES = 3
                                retry_count = 0
                                failed = True
                                while retry_count < MAX_RETRIES:
                                    try:
                                        with open(segment_path, "rb") as audio_file:  # noqa: E501
                                            response = (
                                                openai_client.audio
                                                .transcriptions
                                                .create(
                                                    model=openai_model,
                                                    file=audio_file,
                                                    language=language_code,
                                                    response_format="text",
                                                    prompt=transcription_prompt,
                                                    temperature=0.3
                                                )
                                            )
                                            # 成功則添加文字結果
                                            segment_results.append(response)
                                            logger.info(
                                                "成功轉錄分段 %d/%d",
                                                i + 1,
                                                len(audio_segments)
                                            )
                                            failed = False
                                            break
                                    except Exception as e:
                                        retry_count += 1
                                        error_msg = str(e)
                                        if retry_count < MAX_RETRIES:
                                            logger.warning(
                                                "處理分段 %d 失敗 (重試 %d/%d)：%s",
                                                i + 1,
                                                retry_count,
                                                MAX_RETRIES,
                                                error_msg
                                            )
                                            time.sleep(3)
                                        else:
                                            logger.error(
                                                "處理分段 %d 最終失敗：%s",
                                                i + 1,
                                                error_msg
                                            )
                                if failed:
                                    # 若全部嘗試都失敗，附加空字串，確保完整排序
                                    segment_results.append("")
                            
                            # 更新進度
                            progress = (i + 1) / len(audio_segments)
                            progress_bar.progress(progress)
                            
                            # 清理臨時檔案
                            try:
                                if segment_path != temp_path:
                                    os.remove(segment_path)
                                    logger.info(
                                        "已清理臨時檔案：%s",
                                        segment_path
                                    )
                            except Exception as e:
                                logger.error(
                                    "清理臨時檔案失敗：%s",
                                    str(e)
                                )
                        
                        # 合併結果
                        full_transcript = " ".join(segment_results)
                        logger.info("完成所有分段的轉錄與合併")
                    
                    except Exception as e:
                        st.error(f"處理失敗：{str(e)}")
                        logger.error(f"處理失敗：{str(e)}")
                    
                    # 處理轉錄結果
                    if full_transcript:
                        st.session_state.transcribed_text = full_transcript
                        st.rerun()  # 使用新的 rerun 方法
                    else:
                        st.error("轉錄失敗")
                        
            except Exception as e:
                st.error(f"處理失敗：{str(e)}")
                logger.error(f"處理失敗：{str(e)}")
        
        # 處理優化
        if st.session_state.transcribed_text and optimize_button:
            try:
                with st.spinner("優化中..."):
                    if optimization_service == "OpenAI":
                        if not openai_api_key:
                            st.error("請提供 OpenAI API 金鑰")
                            return
                            
                        refined = refine_transcript(
                            raw_text=st.session_state.transcribed_text,
                            api_key=openai_api_key,
                            model="gpt-4o-mini",
                            temperature=temperature,
                            context=context_prompt
                        )
                    else:  # Gemini
                        if not gemini_api_key:
                            st.error("請提供 Google API 金鑰")
                            return
                            
                        refined = refine_transcript_gemini(
                            text=st.session_state.transcribed_text,
                            api_key=gemini_api_key,
                            temperature=temperature,
                            context=context_prompt
                        )
                    
                    if refined:
                        # 儲存優化結果到 session state
                        st.session_state.optimized_text = refined["corrected"]
                        st.session_state.summary_text = refined["summary"]
                        
                        # 移除 Markdown 標記的函數
                        def remove_markdown(text):
                            # 移除標題符號 (#)
                            text = text.replace('#', '')
                            # 移除粗體標記 (**)
                            text = text.replace('**', '')
                            # 移除斜體標記 (*)
                            text = text.replace('*', '')
                            # 移除分隔線 (---)
                            text = text.replace('---', '')
                            # 移除多餘的空行
                            text = "\n".join(
                                line.strip() 
                                for line in text.split("\n") 
                                if line.strip()
                            )
                            return text
                        
                        # 組合完整結果文字（純文字格式，移除所有 Markdown 標記）
                        st.session_state.full_result = f"""優化後文字：
{remove_markdown(refined["corrected"])}

重點摘要：
{remove_markdown(refined["summary"])}"""

                        # Markdown 格式的結果（保留 Markdown 標記）
                        st.session_state.markdown_result = f"""# 優化結果

## 優化後文字
{refined["corrected"]}

## 重點摘要
{refined["summary"]}"""
                        
                        # 更新 token 使用統計
                        current_usage = refined.get("usage", {})
                        st.session_state.input_tokens = current_usage.get(
                            "total_input_tokens",
                            0
                        )
                        st.session_state.output_tokens = current_usage.get(
                            "total_output_tokens",
                            0
                        )
                        st.session_state.total_tokens = (
                            st.session_state.input_tokens +
                            st.session_state.output_tokens
                        )
                    else:
                        st.error("文字優化失敗")
            except Exception as e:
                st.error(f"優化失敗：{str(e)}")
                logger.error(f"優化失敗：{str(e)}")

        # 顯示優化結果（如果有的話）
        if (hasattr(st.session_state, 'optimized_text') 
                and st.session_state.optimized_text):
            st.subheader("優化結果")
            
            # 顯示優化結果
            st.text_area(
                "完整優化結果",
                st.session_state.full_result,
                height=500
            )
            
            # 下載按鈕區域
            st.markdown("### 下載選項")
            col1, col2 = st.columns(2)
            
            with col1:
                st.download_button(
                    label="📥 下載純文字格式",
                    data=st.session_state.full_result,  # 已經是純文字格式，不需要額外處理
                    file_name="optimized_result.txt",
                    mime="text/plain",
                    help="下載純文字格式的完整結果（包含優化結果和摘要）",
                    use_container_width=True,
                    key="download_optimized_txt"
                )
            
            with col2:
                st.download_button(
                    label="📥 下載 Markdown 格式",
                    data=st.session_state.markdown_result,
                    file_name="optimized_result.md",
                    mime="text/markdown",
                    help="下載 Markdown 格式的完整結果（包含優化結果和摘要）",
                    use_container_width=True,
                    key="download_optimized_md"
                )
            
            # 顯示費用統計（如果有的話）
            if optimization_service == "OpenAI":
                tokens_display = st.session_state.total_tokens
                st.markdown(f"總 Tokens: **{tokens_display:,}**")
                
                # 計算費用
                cost_result = calculate_cost(
                    st.session_state.input_tokens,
                    st.session_state.output_tokens,
                    "gpt-4o-mini",
                    is_cached=False
                )
                
                st.markdown(f"總費用: **NT$ {cost_result[1]:.2f}**")
                
                # 顯示詳細成本資訊
                display_cost_info(
                    st.session_state.input_tokens,
                    st.session_state.output_tokens,
                    "gpt-4o-mini",
                    is_cached=False
                )
            else:
                st.info("Gemini API 使用量暫不計費")

    # 文件轉換與關鍵詞標籤頁
    with main_tabs[1]:
        render_markitdown_tab()
        
    # 關於標籤頁
    with main_tabs[2]:
        st.header("關於")
        st.markdown("""
        ### 音訊轉文字與文件處理系統
        
        本系統提供以下功能：
        
        1. **音訊轉文字**：將音訊檔案轉換為文字，支援多種轉錄引擎
        2. **文字優化**：自動優化轉錄文字，製作美觀的會議記錄或講稿
        3. **文件轉換**：將各種格式的文件轉換為 Markdown 格式
        4. **關鍵詞提取**：自動從文本中提取重要關鍵詞
        
        ### 技術支援
        * 音訊轉文字：OpenAI 模型、Whisper 模型
        * 文字優化：GPT-4o 系列模型、Gemini 2.5 Pro
        * 文件轉換：MarkItDown 套件
        
        ### 版本資訊
        * 版本：1.1.0
        * 更新日期：2025-04-20
        * 新增功能：文件轉換與關鍵詞提取
        
        ### 開發者
        **Tseng Yao Hsien**  
        Endocrinologist  
        Tungs' Taichung MetroHarbor Hospital
        """)


if __name__ == "__main__":
    main() 