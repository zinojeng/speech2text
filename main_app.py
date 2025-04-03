import streamlit as st
from dotenv import load_dotenv
import os
from elevenlabs_stt import transcribe_audio_elevenlabs
from whisper_stt import (
    transcribe_audio_whisper,
    get_model_description
)
from transcript_refiner import refine_transcript
from utils import check_file_size, split_large_audio
import logging
import tempfile
from openai import OpenAI
import google.generativeai as genai

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
        請協助優化以下文字的格式和內容。需要：
        1. 修正標點符號和格式
        2. 保持原意的情況下讓文字更通順
        3. 製作重點摘要
        
        上下文資訊：
        {context if context else "無特定上下文"}
        
        原始文字：
        {text}
        
        請提供：
        1. 優化後的完整文字
        2. 300字以內的重點摘要
        """
        
        response = model.generate_content(
            prompt,
            generation_config={
                'temperature': temperature
            }
        )
        
        # 解析回應
        response_text = response.text
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


def main():
    """主程式函數"""
    st.title("音訊轉文字與優化系統")
    
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

            # 其他設定
            enable_diarization = st.checkbox("啟用說話者辨識", value=False)
        
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
                    if check_file_size(temp_path):
                        # 檔案需要分割
                        audio_segments = split_large_audio(temp_path)
                        if not audio_segments:
                            st.error("檔案分割失敗")
                            return
                        
                        progress_bar = st.progress(0)
                        for i, segment_path in enumerate(audio_segments):
                            if transcription_service == "Whisper":
                                result = transcribe_audio_whisper(
                                    segment_path,
                                    model_name=whisper_model,
                                    language=language_code,
                                    initial_prompt=context_prompt
                                )
                            elif transcription_service == "ElevenLabs":
                                result = transcribe_audio_elevenlabs(
                                    api_key=elevenlabs_api_key,
                                    file_path=segment_path,
                                    language_code="zh-TW",  # 指定繁體中文
                                    diarize=enable_diarization
                                )
                            elif transcription_service == "OpenAI 2025 New":
                                with open(segment_path, "rb") as audio_file:
                                    response = (
                                        openai_client.audio
                                        .transcriptions
                                        .create(
                                            model=openai_model,
                                            file=audio_file,
                                            language=language_code
                                        )
                                    )
                                    result = {"text": response.text}
                            
                            if result:
                                full_transcript += result["text"] + "\n"
                            
                            # 更新進度
                            progress = (i + 1) / len(audio_segments)
                            progress_bar.progress(progress)
                            
                            os.remove(segment_path)
                    else:
                        # 直接轉錄
                        if transcription_service == "Whisper":
                            result = transcribe_audio_whisper(
                                temp_path,
                                model_name=whisper_model,
                                language=language_code,
                                initial_prompt=context_prompt
                            )
                        elif transcription_service == "ElevenLabs":
                            result = transcribe_audio_elevenlabs(
                                api_key=elevenlabs_api_key,
                                file_path=temp_path,
                                language_code="zh-TW",  # 指定繁體中文
                                diarize=enable_diarization
                            )
                        elif transcription_service == "OpenAI 2025 New":
                            with open(temp_path, "rb") as audio_file:
                                response = (
                                    openai_client.audio
                                    .transcriptions
                                    .create(
                                        model=openai_model,
                                        file=audio_file,
                                        language=language_code
                                    )
                                )
                                result = {"text": response.text}
                        
                        if result:
                            full_transcript = result["text"]
                finally:
                    # 確保清理臨時檔案
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                
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
                    
                    # 組合完整結果文字（純文字格式）
                    st.session_state.full_result = f"""優化後文字：
{refined["corrected"]}

重點摘要：
{refined["summary"]}"""

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
    if hasattr(st.session_state, 'optimized_text') and st.session_state.optimized_text:
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


if __name__ == "__main__":
    main() 