# 標準庫導入
import os
import logging
import tempfile
import time
import base64
import glob
from pathlib import Path

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
- 可提取關鍵詞
"""

# 圖片分析服務說明
IMAGE_ANALYSIS_SERVICE_INFO = """
### 圖片分析功能
- 使用 OpenAI o4-mini 模型分析圖片內容
- 可辨識圖片文字內容和視覺元素
- 支援各種圖片格式（PNG、JPG 等）
"""

# 支援的檔案類型
SUPPORTED_FILE_TYPES = [
    "pdf", "docx", "doc", "pptx", "ppt", 
    "xlsx", "xls", "csv", "txt", "rtf", 
    "html", "htm", "md", "markdown"
]

# 支援的圖片類型
SUPPORTED_IMAGE_TYPES = ["png", "jpg", "jpeg", "webp"]

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

def render_markitdown_tab_with_image_analysis():
    """渲染整合了圖片分析功能的 MarkItDown 標籤頁"""
    st.header("Step 1: 文件轉換與圖片分析")
    
    # 整合的服務說明
    combined_info = """
    ### 文件與圖片分析工具
    - 將各種格式的文件轉換為 Markdown
    - 支援 PDF、DOCX、PowerPoint、Excel 等格式
    - 使用 OpenAI o4-mini 模型分析文件中的圖片
    - 提取文字與圖片內容作為關鍵詞和上下文
    """
    st.markdown(combined_info)
    
    # 初始化 session state
    if "markdown_text" not in st.session_state:
        st.session_state.markdown_text = None
    if "markdown_keywords" not in st.session_state:
        st.session_state.markdown_keywords = None
    if "analyzed_images" not in st.session_state:
        st.session_state.analyzed_images = {}
    if "combined_context" not in st.session_state:
        st.session_state.combined_context = None
    if "openai_api_key_checked" not in st.session_state:
        st.session_state.openai_api_key_checked = False

    # 從側邊欄獲取 API 金鑰
    openai_api_key = st.session_state.get("openai_api_key", "")
    
    # 若有 API 金鑰，設置標記以避免重複檢查
    if openai_api_key and not st.session_state.openai_api_key_checked:
        st.session_state.openai_api_key_checked = True

    # 創建兩個標籤頁：文件或圖片上傳和使用者自行輸入
    tab1, tab2 = st.tabs(["📄 文件或圖片上傳", "✏️ 使用者自行輸入"])
    
    # 文件或圖片上傳標籤頁
    with tab1:
        # 合併支援的檔案類型
        combined_file_types = SUPPORTED_FILE_TYPES + SUPPORTED_IMAGE_TYPES
        
        uploaded_files = st.file_uploader(
            "上傳文件或圖片",
            type=combined_file_types,
            accept_multiple_files=True,
            help="支援多個檔案上傳，包含文件及圖片格式"
            )
            
        # 增加圖片處理選項
        enable_image_analysis = st.checkbox(
            "啟用圖片分析",
            value=True,
            help="使用 OpenAI o4-mini 模型自動分析文件中的圖片內容或分析上傳的圖片"
        )
        
        # 檢查 API 金鑰，只有在未檢查過且沒有 API 金鑰時顯示警告
        if enable_image_analysis and not openai_api_key and not st.session_state.openai_api_key_checked:
            st.warning("請在側邊欄填入 OpenAI API 金鑰以啟用圖片分析功能")
        
        if uploaded_files:
            # 顯示上傳的檔案數量
            st.info(f"已上傳 {len(uploaded_files)} 個檔案")
            
            # 創建一個展開區顯示所有上傳的檔案
            with st.expander("查看上傳的檔案清單", expanded=False):
                for i, file in enumerate(uploaded_files):
                    st.write(f"{i+1}. {file.name} ({file.size/1024:.1f} KB)")
            
            # 處理按鈕
            process_btn = st.button(
                f"🔄 處理所有檔案" + (" 並分析圖片" if enable_image_analysis and openai_api_key else ""),
                use_container_width=True
            )
            
            if process_btn:
                # 初始化 OpenAI 客戶端（如果啟用了圖片分析）
                if enable_image_analysis and openai_api_key:
                    client = OpenAI(api_key=openai_api_key)
                
                # 處理每個檔案
                total_files = len(uploaded_files)
                progress_text = "正在處理檔案..."
                progress_bar = st.progress(0, text=progress_text)
                
                combined_markdown = ""
                all_image_analysis_results = []
                total_input_tokens = 0
                total_output_tokens = 0
                
                for i, uploaded_file in enumerate(uploaded_files):
                    # 更新進度
                    progress = (i + 1) / total_files
                    progress_bar.progress(
                        progress,
                        text=f"{progress_text} ({i + 1}/{total_files}): {uploaded_file.name}"
                    )
                    
                    # 判斷檔案類型
                    file_extension = uploaded_file.name.split('.')[-1].lower()
                    is_image = file_extension in SUPPORTED_IMAGE_TYPES
                    
                    # 保存上傳的檔案
                    with tempfile.NamedTemporaryFile(
                        delete=False, 
                        suffix=f".{file_extension}"
                    ) as temp_file:
                        temp_file.write(uploaded_file.getvalue())
                        temp_path = temp_file.name
                    
                    # 根據檔案類型進行處理
                    if is_image and enable_image_analysis and openai_api_key:
                        # 處理圖片文件
                        with st.spinner(f"分析圖片 {i + 1}/{total_files}: {uploaded_file.name}"):
                            try:
                                # 分析圖片
                                result = analyze_image(client, temp_path)
                                
                                if result["success"]:
                                    image_name = uploaded_file.name
                                    st.session_state.analyzed_images[image_name] = {
                                        "path": temp_path,
                                        "result": result["result"],
                                        "usage": result["usage"]
                                    }
                                    
                                    # 更新 token 使用量
                                    if "usage" in result:
                                        total_input_tokens += result["usage"].get(
                                            "input_tokens", 0
                                        )
                                        total_output_tokens += result["usage"].get(
                                            "output_tokens", 0
                                        )
                                    
                                    # 將圖片分析結果添加到合併的 Markdown 中
                                    image_markdown = f"""
# 圖片分析結果: {image_name}

![{image_name}]({temp_path})

## 分析內容
{result["result"]}

---

"""
                                    combined_markdown += image_markdown
                                    all_image_analysis_results.append(result["result"])
                                else:
                                    st.error(f"圖片 {uploaded_file.name} 分析失敗: {result.get('error', '未知錯誤')}")
                            except Exception as e:
                                st.error(f"處理圖片 {uploaded_file.name} 時發生錯誤: {str(e)}")
                    elif not is_image:
                        # 處理文件
                        with st.spinner(f"轉換文件 {i + 1}/{total_files}: {uploaded_file.name}"):
                            try:
                                success, md_text, info = convert_file_to_markdown(
                                    input_path=temp_path,
                                    use_llm=False,
                                    api_key=openai_api_key,
                                    model="o4-mini"
                                )
                                
                                if success:
                                    # 如果啟用了圖片分析，則分析文件中的圖片
                                    if enable_image_analysis and openai_api_key:
                                        # 從 md_text 中提取圖片路徑
                                        image_paths = extract_image_paths_from_markdown(
                                            md_text, 
                                            os.path.dirname(temp_path)
                                        )
                                        
                                        if image_paths:
                                            st.info(
                                                f"從文件 {uploaded_file.name} 中找到 {len(image_paths)} 張圖片，開始分析..."
                                            )
                                            
                                            # 分析每張圖片
                                            file_image_results = []
                                            
                                            for img_path in image_paths:
                                                try:
                                                    img_result = analyze_image(client, img_path)
                                                    if img_result["success"]:
                                                        image_name = os.path.basename(img_path)
                                                        st.session_state.analyzed_images[image_name] = {
                                                            "path": img_path,
                                                            "result": img_result["result"],
                                                            "usage": img_result["usage"]
                                                        }
                                                        # 更新 token 使用量
                                                        if "usage" in img_result:
                                                            total_input_tokens += img_result["usage"].get(
                                                                "input_tokens", 0
                                                            )
                                                            total_output_tokens += img_result["usage"].get(
                                                                "output_tokens", 0
                                                            )
                                                        file_image_results.append(img_result["result"])
                                                        all_image_analysis_results.append(img_result["result"])
                                                except Exception as e:
                                                    st.error(f"圖片分析失敗: {str(e)}")
                    
                                            # 將圖片分析結果添加到 Markdown 中
                                            if file_image_results:
                                                md_text = add_image_analysis_to_markdown(
                                                    md_text, 
                                                    image_paths, 
                                                    file_image_results
                                                )
                                    
                                    # 添加文件標題和分隔線
                                    file_markdown = f"""
# 文件: {uploaded_file.name}

{md_text}

---

"""
                                    combined_markdown += file_markdown
                            else:
                                st.error(f"文件 {uploaded_file.name} 轉換失敗: {info.get('error', '未知錯誤')}")
                            except Exception as e:
                                st.error(f"處理文件 {uploaded_file.name} 時發生錯誤: {str(e)}")
                    
                    # 清理臨時檔案（除非是圖片，圖片保留以便顯示）
                    if not is_image:
                        try:
                            os.remove(temp_path)
                        except Exception as e:
                            logger.error(f"清理臨時檔案失敗: {str(e)}")
        
                # 完成處理所有檔案
                progress_bar.empty()
                
                if combined_markdown:
                    st.success(f"已完成 {total_files} 個檔案的處理")
        
                    # 儲存結果到 session state
                    st.session_state.markdown_text = combined_markdown
                    
                    # 建立合併的上下文
                    if all_image_analysis_results:
                        st.session_state.combined_context = f"""
文件文字內容：
{combined_markdown}

圖片分析結果：
{' '.join(all_image_analysis_results)}
"""
                                else:
                        st.session_state.combined_context = combined_markdown
                    
                    # 顯示 token 使用量
                    if total_input_tokens > 0 or total_output_tokens > 0:
                        with st.expander("Token 使用量", expanded=True):
                            st.write(f"輸入 Tokens: {total_input_tokens:,}")
                            st.write(f"輸出 Tokens: {total_output_tokens:,}")
                            st.write(
                                f"總計 Tokens: {total_input_tokens + total_output_tokens:,}"
                            )
                            
                            # 計算費用
                            cost_usd, cost_ntd, _ = calculate_cost(
                                total_input_tokens,
                                total_output_tokens,
                                "o4-mini",
                                is_cached=False
                            )
                            st.write(
                                f"估計費用: USD ${cost_usd:.4f} (NTD ${cost_ntd:.2f})"
                            )
                    
                    # 自動提取關鍵詞
                    if openai_api_key:
                        with st.spinner("正在提取關鍵詞..."):
                            keywords = extract_keywords(
                                markdown_text=st.session_state.combined_context,
                                api_key=openai_api_key,
                                model="o4-mini",
                                count=15
                            )
                            
                            if keywords:
                                st.session_state.markdown_keywords = keywords
                                st.success(f"已自動提取 {len(keywords)} 個關鍵詞")
        
                                # 顯示關鍵詞
                                with st.expander("提取的關鍵詞", expanded=True):
                                    st.write(", ".join(keywords))
                    
                    # 顯示 Markdown 內容
                    with st.expander("合併的 Markdown 內容", expanded=True):
                st.text_area(
                            "處理結果",
                            st.session_state.markdown_text,
                            height=300
                )
                
                        # 下載按鈕
                    st.download_button(
                            label="📥 下載 Markdown 檔案",
                            data=st.session_state.markdown_text,
                            file_name="combined.md",
                        mime="text/markdown",
                            help="下載合併後的 Markdown 文件"
                    )
                
                    # 自動傳入下一步驟
                    st.session_state.transcribed_text = st.session_state.markdown_text
                    
                    # 顯示已自動傳入訊息
                    st.success("✅ 處理結果已自動傳入 Step 3: 文字優化")
                else:
                    st.warning("所有檔案處理完成，但未生成有效的 Markdown 內容")
                    
                # 清理上傳檔案記錄，讓使用者可以上傳新檔案
                st.rerun()

    # 使用者自行輸入標籤頁
    with tab2:
        user_text = st.text_area(
            "直接輸入文字",
            placeholder="在此輸入您的文字內容...",
            help="直接輸入要處理的文字內容",
                    height=300
                )
                
        if user_text:
            # 處理按鈕
            process_text_btn = st.button(
                "✅ 處理文字內容",
                use_container_width=True
            )
            
            if process_text_btn:
                # 儲存用戶輸入的文字
                st.session_state.markdown_text = user_text
                
                # 自動提取關鍵詞
                if openai_api_key:
                    with st.spinner("正在提取關鍵詞..."):
                        keywords = extract_keywords(
                            markdown_text=user_text,
                                    api_key=openai_api_key,
                            model="o4-mini",
                            count=15
                        )
                        
                        if keywords:
                            st.session_state.markdown_keywords = keywords
                            st.success(f"已自動提取 {len(keywords)} 個關鍵詞")
                            
                            # 顯示關鍵詞
                            with st.expander("提取的關鍵詞", expanded=True):
                                st.write(", ".join(keywords))
                
                st.success(
                    f"文字內容已處理！長度: {len(user_text)} 字元"
                )
                
                # 自動傳入下一步驟
                st.session_state.transcribed_text = user_text
                
                # 顯示已自動傳入訊息
                st.success("✅ 處理結果已自動傳入 Step 3: 文字優化")
                
                # 清理輸入框
                                st.rerun()

    # 移除獨立的圖片分析標籤頁代碼
    # with main_tabs[3]:
    #     render_image_analysis_tab()

    # 移除關於標籤頁的內容，改為在側邊欄顯示
    with st.sidebar:
        # 分隔線
        st.markdown("---")
        
        # 關於資訊
        with st.expander("ℹ️ 關於", expanded=False):
            st.markdown("""
            ### 音訊轉文字與文件處理系統
            
            本系統提供以下功能：
            
            1. **文件轉換與關鍵詞**：將各種格式文件轉為 Markdown
            2. **語音轉文字**：將音訊檔案轉換為文字
            3. **文字優化**：優化轉錄文字，製作會議記錄或講稿
            
            ### 技術支援
            * 音訊轉文字：OpenAI 模型、Whisper 模型
            * 文字優化：GPT-4o 系列模型、Gemini 2.5 Pro
            * 文件轉換：MarkItDown 套件
            
            ### 版本資訊
            * 版本：1.1.0
            * 更新日期：2025-04-20
            * 新增功能：文件轉換與關鍵詞提取
            """)


if __name__ == "__main__":
    main() 