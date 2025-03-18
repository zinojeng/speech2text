import streamlit as st
from dotenv import load_dotenv
import os
from elevenlabs_stt import transcribe_audio as transcribe_audio_elevenlabs
from whisper_stt import transcribe_audio_whisper, get_available_models, get_model_description
from transcript_refiner import refine_transcript, OPENAI_MODELS
from utils import check_file_size, split_large_audio
import logging

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定義可用的 OpenAI 模型
OPENAI_MODELS = {
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "o3-mini": "o3-mini",
    "o1-mini": "o1-mini"
}

# 模型設定和價格（USD per 1M tokens）
MODEL_CONFIG = {
    "gpt-4o": {
        "display_name": "gpt-4o",
        "input": 2.50,        # $2.50 per 1M tokens
        "cached_input": 1.25, # $1.25 per 1M tokens
        "output": 10.00       # $10.00 per 1M tokens
    },
    "gpt-4o-mini": {
        "display_name": "gpt-4o-mini",
        "input": 0.15,        # $0.15 per 1M tokens
        "cached_input": 0.075,# $0.075 per 1M tokens
        "output": 0.60        # $0.60 per 1M tokens
    },
    "o1-mini": {
        "display_name": "o1-mini",
        "input": 1.10,        # $1.10 per 1M tokens
        "cached_input": 0.55, # $0.55 per 1M tokens
        "output": 4.40        # $4.40 per 1M tokens
    },
    "o3-mini": {
        "display_name": "o3-mini",
        "input": 1.10,        # $1.10 per 1M tokens
        "cached_input": 0.55, # $0.55 per 1M tokens
        "output": 4.40        # $4.40 per 1M tokens
    }
}

# 匯率設定
USD_TO_NTD = 31.5

def calculate_cost(input_tokens, output_tokens, model_name, is_cached=False):
    """計算 API 使用成本
    
    Args:
        input_tokens (int): 輸入 tokens 數量
        output_tokens (int): 輸出 tokens 數量
        model_name (str): 模型名稱 (gpt-4o, gpt-4o-mini, o1-mini, o3-mini)
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

# 在 Streamlit 介面中顯示成本
def display_cost_info(input_tokens, output_tokens, model_name, is_cached=False):
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
    st.title("音訊轉文字與優化系統")
    
    # 初始化 token 計數
    if "input_tokens" not in st.session_state:
        st.session_state.input_tokens = 0
    if "output_tokens" not in st.session_state:
        st.session_state.output_tokens = 0
    if "total_tokens" not in st.session_state:
        st.session_state.total_tokens = 0

    # 檢查 session_state 中的 openai_model 是否有效，不是則重設為預設值 o3-mini
    valid_openai_models = ["o3-mini", "o1-mini"]
    if "openai_model" not in st.session_state or st.session_state["openai_model"] not in valid_openai_models:
        st.session_state["openai_model"] = "o3-mini"
    if "whisper_model" not in st.session_state:
        st.session_state["whisper_model"] = "small"

    with st.sidebar:
        st.header("設定")
        
        # 選擇轉錄服務
        transcription_service = st.selectbox(
            "選擇轉錄服務",
            ["Whisper", "ElevenLabs"],
            index=0,
            help="選擇要使用的語音轉文字服務"
        )
        
        # Whisper 相關設定
        if transcription_service == "Whisper":
            whisper_model = st.selectbox(
                "選擇 Whisper 模型",
                options=["tiny", "base", "small", "medium", "large"],
                index=2  # 預設是 small (第三個選項)
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
        
        # OpenAI API 金鑰和模型選擇
        openai_api_key = st.text_input(
            "OpenAI API 金鑰",
            type="password"
        )
        
        model_choice = st.selectbox(
            "選擇 OpenAI 模型",
            options=["gpt-4o", "gpt-4o-mini", "o1-mini", "o3-mini"],
            index=3,  # 預設選擇 o3-mini
            help="選擇要使用的 OpenAI 模型"
        )
        st.session_state["openai_model"] = model_choice
        
        # 其他設定
        enable_diarization = st.checkbox("啟用說話者辨識", value=False)
        temperature = st.slider("創意程度", 0.0, 1.0, 0.5)
        
        # 作者資訊
        st.markdown("---")
        st.markdown("""
        ### Created by
        **Tseng Yao Hsien**  
        Endocrinologist  
        Tungs' Taichung MetroHarbor Hospital
        """)

        # 顯示價格說明
        with st.sidebar.expander("💡 模型價格說明（USD per 1M tokens）"):
            st.write("""
            ### gpt-4o
            - 輸入：$2.50 / 1M tokens
            - 快取輸入：$1.25 / 1M tokens
            - 輸出：$10.00 / 1M tokens
            
            ### gpt-4o-mini
            - 輸入：$0.15 / 1M tokens
            - 快取輸入：$0.075 / 1M tokens
            - 輸出：$0.60 / 1M tokens
            
            ### o1-mini & o3-mini
            - 輸入：$1.10 / 1M tokens
            - 快取輸入：$0.55 / 1M tokens
            - 輸出：$4.40 / 1M tokens
            
            ### 匯率
            - 1 USD = 31.5 NTD
            """)

    # 提示詞設定
    with st.expander("提示詞設定（選填）", expanded=False):
        context_prompt = st.text_area(
            "請輸入相關提示詞",
            placeholder="例如：\n- 這是一段醫學演講\n- 包含專有名詞：糖尿病、胰島素\n- 主要討論糖尿病的治療方法",
            help="提供音訊內容的相關資訊，可以幫助 AI 更準確地理解和轉錄內容"
        )
    
    # 上傳檔案
    uploaded_file = st.file_uploader("上傳音訊檔案", type=["mp3", "wav", "ogg", "m4a"])
    
    if uploaded_file and st.button("處理音訊"):
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
                
                # 檢查檔案大小
                temp_path = f"temp_{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
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
                        else:
                            result = transcribe_audio_elevenlabs(
                                api_key=elevenlabs_api_key,
                                file_path=segment_path,
                                diarize=enable_diarization
                            )
                        
                        if result:
                            full_transcript += result["text"] + "\n"
                        progress_bar.progress((i + 1) / len(audio_segments))
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
                    else:
                        result = transcribe_audio_elevenlabs(
                            api_key=elevenlabs_api_key,
                            file_path=temp_path,
                            diarize=enable_diarization
                        )
                    
                    if result:
                        full_transcript = result["text"]
                
                # 清理原始暫存檔
                os.remove(temp_path)
                
                # 處理轉錄結果
                if full_transcript:
                    st.subheader("原始轉錄文字")
                    st.text_area("原始文字", full_transcript, height=200)
                    
                    # 優化文字
                    refined = refine_transcript(
                        raw_text=full_transcript,
                        api_key=openai_api_key,
                        model=model_choice,
                        temperature=temperature,
                        context=context_prompt
                    )
                    
                    if refined:
                        st.subheader("優化後的文字")
                        st.text_area("修正後的文字", refined["corrected"], height=200)
                        st.subheader("文字摘要")
                        st.text_area("摘要", refined["summary"], height=200)
                        
                        # 更新 token 使用統計（包含兩次 API 呼叫的總和）
                        current_usage = refined.get("usage", {})
                        st.session_state.input_tokens = current_usage.get("total_input_tokens", 0)
                        st.session_state.output_tokens = current_usage.get("total_output_tokens", 0)
                        st.session_state.total_tokens = st.session_state.input_tokens + st.session_state.output_tokens
                        
                        # 顯示費用統計
                        st.markdown("---")
                        st.markdown("### 💰 費用統計")
                        st.markdown("#### 總計")
                        st.markdown(f"總 Tokens: **{st.session_state.total_tokens:,}**")
                        
                        # 計算費用
                        total_cost_usd, total_cost_ntd, details = calculate_cost(
                            st.session_state.input_tokens,
                            st.session_state.output_tokens,
                            model_choice,
                            is_cached=False
                        )
                        
                        st.markdown(f"總費用: **NT$ {total_cost_ntd:.2f}**")
                        
                        # 顯示詳細成本資訊
                        display_cost_info(
                            st.session_state.input_tokens,
                            st.session_state.output_tokens,
                            model_choice,
                            is_cached=False
                        )
                    else:
                        st.error("文字優化失敗")
                else:
                    st.error("轉錄失敗")
                    
        except Exception as e:
            st.error(f"處理失敗：{str(e)}")
            logger.error(f"處理失敗：{str(e)}")

if __name__ == "__main__":
    main() 