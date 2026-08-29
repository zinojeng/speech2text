import streamlit as st
import os
import tempfile
from openai import OpenAI
import time

def transcribe_audio(audio_file, api_key, model, language, output_format):
    """使用 GPT-4o 模型轉錄音頻"""
    client = OpenAI(api_key=api_key)
    
    try:
        # 根據格式設定 response_format
        response_format = "text"
        if output_format == "SRT (含時間戳)":
            response_format = "srt"
        elif output_format == "Markdown":
            response_format = "text"  # 先取得文字再轉換為 markdown
        
        with st.spinner("正在轉錄音頻..."):
            transcript = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                language=language if language != "自動偵測" else None,
                response_format=response_format
            )
        
        if output_format == "Markdown":
            # 將文字轉換為 markdown 格式
            result = f"# 語音轉錄結果\n\n{transcript.text}\n"
        elif output_format == "SRT (含時間戳)":
            # SRT 格式直接回傳字串，不需要 .text 屬性
            result = transcript
        else:
            # 純文字格式
            result = transcript.text
            
        return result, None
        
    except Exception as e:
        return None, str(e)

def main():
    st.set_page_config(
        page_title="GPT-4o 語音轉文字",
        page_icon="🎤",
        layout="wide"
    )
    
    st.title("🎤 GPT-4o 語音轉文字")
    st.markdown("使用最新的 GPT-4o 語音模型將音頻轉換為文字")
    
    # 側邊欄設定
    with st.sidebar:
        st.header("⚙️ 設定")
        
        # API Key 輸入
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            help="請輸入您的 OpenAI API 金鑰"
        )
        
        # 模型選擇
        model = st.selectbox(
            "選擇模型",
            options=["gpt-transcribe", "gemini-3.5-transcribe"],
            index=0,
            help="選擇要使用的 GPT-4o 語音模型"
        )
        
        # 語言選擇
        language = st.selectbox(
            "語言設定",
            options=[
                "自動偵測",
                "zh (中文)",
                "en (英文)",
                "ja (日文)",
                "ko (韓文)",
                "es (西班牙文)",
                "fr (法文)",
                "de (德文)",
                "it (義大利文)",
                "pt (葡萄牙文)",
                "ru (俄文)"
            ],
            index=0,
            help="選擇音頻的語言，或使用自動偵測"
        )
        
        # 輸出格式選擇
        output_format = st.selectbox(
            "輸出格式",
            options=["純文字", "Markdown", "SRT (含時間戳)"],
            index=0,
            help="選擇轉錄結果的輸出格式"
        )
        
        st.markdown("---")
        st.markdown("### 💡 使用說明")
        st.markdown("""
        1. 輸入 OpenAI API 金鑰
        2. 選擇適合的模型和語言
        3. 上傳音頻檔案
        4. 點擊「開始轉錄」
        """)
    
    # 主要內容區域
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📁 音頻上傳")
        
        # 檔案上傳
        uploaded_file = st.file_uploader(
            "選擇音頻檔案",
            type=['mp3', 'wav', 'flac', 'm4a', 'ogg', 'webm'],
            help="支援格式: MP3, WAV, FLAC, M4A, OGG, WebM"
        )
        
        if uploaded_file is not None:
            st.success(f"已上傳檔案: {uploaded_file.name}")
            st.info(f"檔案大小: {uploaded_file.size / 1024 / 1024:.2f} MB")
            
            # 音頻播放器
            st.audio(uploaded_file, format=uploaded_file.type)
    
    with col2:
        st.header("📝 轉錄結果")
        
        # 轉錄按鈕
        if st.button("🚀 開始轉錄", type="primary", use_container_width=True):
            if not api_key:
                st.error("❌ 請先輸入 OpenAI API 金鑰")
            elif not uploaded_file:
                st.error("❌ 請先上傳音頻檔案")
            else:
                # 處理語言代碼
                lang_code = None if language == "自動偵測" else language.split(" ")[0]
                
                # 建立臨時檔案
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                try:
                    # 開始轉錄
                    start_time = time.time()
                    
                    with open(tmp_file_path, "rb") as audio_file:
                        result, error = transcribe_audio(
                            audio_file, api_key, model, lang_code, output_format
                        )
                    
                    end_time = time.time()
                    
                    if error:
                        st.error(f"❌ 轉錄失敗: {error}")
                    else:
                        st.success(f"✅ 轉錄完成！耗時: {end_time - start_time:.2f} 秒")
                        
                        # 顯示結果
                        if output_format == "Markdown":
                            st.markdown(result)
                        elif output_format == "SRT (含時間戳)":
                            st.code(result, language="srt")
                        else:
                            st.text_area("轉錄結果", result, height=400)
                        
                        # 下載按鈕
                        file_extension = {
                            "純文字": "txt",
                            "Markdown": "md", 
                            "SRT (含時間戳)": "srt"
                        }[output_format]
                        
                        st.download_button(
                            label=f"📥 下載 {output_format} 檔案",
                            data=result,
                            file_name=f"transcript.{file_extension}",
                            mime=f"text/{file_extension}"
                        )
                        
                finally:
                    # 清除臨時檔案
                    if os.path.exists(tmp_file_path):
                        os.unlink(tmp_file_path)
    
    # 頁腳資訊
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>🤖 使用 GPT-4o 語音模型 | 🔐 API 金鑰不會被儲存</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()