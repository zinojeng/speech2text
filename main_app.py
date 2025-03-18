import streamlit as st
from elevenlabs_stt import transcribe_audio
from transcript_refiner import refine_transcript
from utils import split_large_audio
import tempfile
import os

# 定義語言對照表
LANGUAGE_MAPPING = {
    "自動偵測": None,
    "中文 (普通話)": "zho",
    "中文 (粵語)": "yue",
    "英文": "eng",
    "日文": "jpn",
    "韓文": "kor",
    "法文": "fra",
    "德文": "deu",
    "西班牙文": "spa",
    "越南文": "vie",
    "泰文": "tha",

}

# 定義 OpenAI 模型對照表
OPENAI_MODELS = {
    "o3-mini": "o3-mini",
    "o1-mini": "o1-ini",
    "gpt-4o-mini": "GPT-4o-mini",
    "gpt-4o": "GPT-4o ）"
}

st.title("音訊轉文字與優化系統")

# 側邊欄設定
with st.sidebar:
    st.header("API 設定")
    
    # API 金鑰輸入
    openai_key = st.text_input(
        "OpenAI API Key",
        type="password"
    )
    elevenlabs_key = st.text_input(
        "ElevenLabs API Key",
        type="password"
    )
    
    st.markdown("---")
    
    # OpenAI 模型選擇
    st.subheader("模型設定")
    openai_model = st.selectbox(
        "選擇 AI 模型",
        options=list(OPENAI_MODELS.keys()),
        format_func=lambda x: OPENAI_MODELS[x],
        index=0,  # 預設選擇 o3-mini
        help="選擇用於優化文字的 AI 模型"
    )
    
    # 語言選擇
    language_option = st.selectbox(
        "選擇音訊語言",
        options=list(LANGUAGE_MAPPING.keys()),
        help="選擇音訊的語言可以提高辨識準確度"
    )
    language_code = LANGUAGE_MAPPING[language_option]

    st.markdown("---")
    
    # ElevenLabs Scribe 簡介
    st.subheader("關於 ElevenLabs Scribe")
    st.markdown("""
    Scribe 是 ElevenLabs 最新的語音轉文字模型，具有：
    
    - 使用世界上最準確的 ASR 模型將語音轉錄為文字
    - 支援 99 種語言
    - 業界最高辨識準確率
    - 字詞級時間戳記
    - 說話者辨識功能
    - 非語音事件標記
    
    [了解更多](https://elevenlabs.io/blog/meet-scribe)
    """)
    
    st.markdown("---")
    
    # 作者資訊
    st.markdown("""
    ### 作者資訊
    
    **Dr. Tseng**  
    Endocrinologist  
    Tungs' Taichung MetroHarbor Hospital
    
    📧 zinojeng@gmail.com
    """)

# 主介面
uploaded_file = st.file_uploader(
    "上傳音訊檔案",
    type=["mp3", "wav", "ogg", "m4a"]
)

user_prompt = st.text_area(
    "文字優化指示",
    value="修正文法和標點符號，保持原意，不要增加新內容。",
    height=100
)

# 選項設定
col1, col2 = st.columns(2)
with col1:
    enable_diarize = st.checkbox("啟用說話者辨識")
with col2:
    temperature = st.slider("創意程度", 0.0, 1.0, 0.5)

if st.button("處理音訊"):
    if not all([openai_key, elevenlabs_key, uploaded_file]):
        st.error("請提供所有必要的輸入")
        st.stop()
    
    try:
        # 顯示進度條
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 儲存上傳的檔案
        status_text.text("儲存檔案中...")
        progress_bar.progress(10)
        
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".mp3"
        ) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        # 檢查檔案大小並分割
        status_text.text("檢查檔案中...")
        progress_bar.progress(20)
        
        # 分割大檔案
        audio_files = split_large_audio(tmp_path)
        if not audio_files:
            st.error("檔案處理失敗")
            st.stop()
        
        # 處理每個分割檔案
        all_results = []
        for i, audio_file in enumerate(audio_files):
            # 轉換音訊
            status_text.text(f"轉換音訊為文字中... ({i+1}/{len(audio_files)})")
            progress_bar.progress((i+1)/len(audio_files))
            raw_result = transcribe_audio(
                api_key=elevenlabs_key,
                file_path=audio_file,
                diarize=enable_diarize
            )
            
            if not raw_result:
                st.error("轉換失敗")
                st.stop()
            
            # 顯示原始結果
            progress_bar.progress(60)
            st.subheader(f"原始轉錄 ({i+1}/{len(audio_files)})")
            st.write(raw_result['text'])
            
            # 顯示詳細資訊
            if 'words' in raw_result:
                with st.expander("詳細時間資訊"):
                    st.json(raw_result['words'])
            
            # 優化文字
            progress_bar.progress(80)
            refined_result = refine_transcript(
                raw_text=raw_result['text'],
                api_key=openai_key,
                temperature=temperature
            )
            
            if refined_result:
                # 顯示修正後的文字
                st.subheader(f"修正後的繁體中文 ({i+1}/{len(audio_files)})")
                st.write(refined_result['corrected'])
                
                # 顯示整理結果
                st.subheader(f"重點整理 ({i+1}/{len(audio_files)})")
                st.write(refined_result['summary'])
                
                # 下載按鈕
                progress_bar.progress(100)
                status_text.text(f"處理完成！ ({i+1}/{len(audio_files)})")
                
                col_d1, col_d2, col_d3 = st.columns(3)
                with col_d1:
                    st.download_button(
                        "下載原始文字",
                        data=raw_result['text'],
                        file_name=f"原始文字_{i+1}.txt"
                    )
                with col_d2:
                    st.download_button(
                        "下載優化文字",
                        data=refined_result['corrected'],
                        file_name=f"優化文字_{i+1}.txt"
                    )
                with col_d3:
                    st.download_button(
                        "下載整理結果",
                        data=refined_result['summary'],
                        file_name=f"整理結果_{i+1}.txt"
                    )
            
            all_results.append(refined_result)
        
        # 顯示所有結果
        st.subheader("所有結果")
        for i, result in enumerate(all_results):
            st.write(f"結果 {i+1}")
            st.write(f"修正後的文字: {result['corrected']}")
            st.write(f"整理結果: {result['summary']}")
        
    except Exception as e:
        st.error(f"處理失敗：{str(e)}")
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path) 