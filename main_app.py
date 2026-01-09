# 標準庫導入
import os
import logging
import tempfile
import time
import base64
import shutil
import subprocess

# 第三方庫導入
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
import google.generativeai as genai
from pydub import AudioSegment

# 本地模組導入
from whisper_stt import get_model_description, transcribe_audio_whisper
from elevenlabs_stt import transcribe_audio_elevenlabs
from transcript_refiner import refine_transcript
from markitdown_utils import (
    convert_file_to_markdown,
    extract_keywords, save_uploaded_file
)
# 導入圖像分析功能
from image_analyzer import (
    analyze_image,
    enhance_slides
)

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定義可用的 OpenAI 模型
AVAILABLE_MODELS = {
    "o4-mini": "o4-mini",  # 新模型放前面作為預設
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "o3-mini": "o3-mini",
    "o1-mini": "o1-mini"
}

# 模型設定和價格（USD per 1M tokens）
MODEL_CONFIG = {
    "o4-mini": {
        "display_name": "o4-mini",
        "input": 0.15,          # $0.15 per 1M tokens
        "cached_input": 0.075,  # $0.075 per 1M tokens
        "output": 0.60          # $0.60 per 1M tokens
    },
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
    "gemini-3-pro-preview": {
        "display_name": "Gemini 3 Pro Preview",
        "input": 0.00,          # 價格待定
        "cached_input": 0.00,   # 價格待定
        "output": 0.00          # 價格待定
    },
    "gemini-3-flash-preview": {
        "display_name": "Gemini 3 Flash Preview",
        "input": 0.00,          # 價格待定
        "cached_input": 0.00,   # 價格待定
        "output": 0.00          # 價格待定
    },
    "gemini-2.5-pro": {
        "display_name": "Gemini 2.5 Pro",
        "input": 0.00,          # 價格待定
        "cached_input": 0.00,   # 價格待定
        "output": 0.00          # 價格待定
    },
    "gemini-2.5-flash": {
        "display_name": "Gemini 2.5 Flash",
        "input": 0.00,          # 價格待定
        "cached_input": 0.00,   # 價格待定
        "output": 0.00          # 價格待定
    },
    "gemini-2.0-flash": {
        "display_name": "Gemini 2.0 Flash",
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

# 支援的檔案類型
SUPPORTED_FILE_TYPES = [
    "pdf", "docx", "doc", "pptx", "ppt", 
    "xlsx", "xls", "csv", "txt", "rtf", 
    "html", "htm", "md", "markdown"
]

# 支援的影片格式
SUPPORTED_VIDEO_FORMATS = ["mp4", "avi", "mkv", "mov", "webm", "flv", "wmv"]

def extract_audio_from_video(video_path: str, output_path: str = None, audio_format: str = "mp3") -> tuple:
    """
    從影片檔案中提取音訊
    
    Args:
        video_path: 影片檔案路徑
        output_path: 輸出音訊檔案路徑，預設為原影片名稱加上音訊格式後綴
        audio_format: 輸出音訊格式，預設為 mp3
        
    Returns:
        tuple: (success: bool, output_file_or_error: str)
    """
    moviepy_error = None
    
    # 如果未指定輸出路徑，使用預設路徑
    if not output_path:
        base_name = os.path.splitext(video_path)[0]
        output_path = f"{base_name}.{audio_format}"
    
    # 先嘗試使用 MoviePy
    try:
        from moviepy.editor import VideoFileClip
        
        with VideoFileClip(video_path) as video_clip:
            audio_clip = video_clip.audio
            if audio_clip is None:
                raise ValueError("影片不含音訊軌道")
            try:
                audio_clip.write_audiofile(output_path, logger=None)
            finally:
                audio_clip.close()
        return True, output_path
    except ImportError:
        moviepy_error = "MoviePy 未安裝"
    except Exception as exc:
        moviepy_error = str(exc)
    
    # MoviePy 失敗時，改用 ffmpeg 指令
    if moviepy_error:
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            return False, f"音訊提取失敗 (MoviePy): {moviepy_error}; 並且系統未找到 ffmpeg"
        
        # 根據格式設定編碼器
        codec_map = {
            "mp3": ["libmp3lame", "-b:a", "192k"],
            "wav": ["pcm_s16le"],
            "aac": ["aac", "-b:a", "192k"],
            "m4a": ["aac", "-b:a", "192k"],
        }
        
        codec_args = codec_map.get(audio_format, ["libmp3lame", "-b:a", "192k"])
        
        cmd = [
            ffmpeg_path,
            "-y",  # 覆蓋輸出
            "-i", video_path,
            "-vn",  # 不要視訊
            "-ac", "2",  # 雙聲道
            "-ar", "44100",  # 取樣率
            "-c:a", codec_args[0],
        ]
        
        # 添加額外的編碼器參數
        if len(codec_args) > 1:
            cmd.extend(codec_args[1:])
        
        cmd.append(output_path)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                return True, output_path
            
            error_msg = result.stderr.strip() or "未知錯誤"
            return False, f"ffmpeg 轉換失敗: {error_msg}"
        except subprocess.TimeoutExpired:
            return False, "轉換超時（超過10分鐘）"
        except Exception as e:
            return False, f"ffmpeg 執行失敗: {str(e)}"
    
    return False, "未知錯誤"


def render_video_to_audio_tab():
    """渲染影片轉音檔標籤頁"""
    st.header("🎬 影片轉音檔")
    st.markdown("""
    此功能可從影片檔案中提取音訊軌道，輸出為 MP3、WAV 或 AAC 格式。
    
    **支援的影片格式：** MP4, AVI, MKV, MOV, WebM, FLV, WMV
    """)
    
    # 提示：無縫流程
    st.info("💡 **無縫流程**：處理後的音檔可一鍵轉換至「Step 3: 語音轉文字」，無需下載後再上傳！")
    
    # 檢查是否有 moviepy 或 ffmpeg
    has_moviepy = False
    has_ffmpeg = shutil.which("ffmpeg") is not None
    
    try:
        import moviepy.editor
        has_moviepy = True
    except ImportError:
        pass
    
    if not has_moviepy and not has_ffmpeg:
        st.error("⚠️ 需要安裝 MoviePy 或系統 ffmpeg 才能使用此功能")
        st.code("pip install moviepy", language="bash")
        st.markdown("或安裝 ffmpeg：")
        st.code("# macOS\nbrew install ffmpeg\n\n# Ubuntu/Debian\nsudo apt install ffmpeg", language="bash")
        return
    
    # 顯示可用的轉換工具
    tools_available = []
    if has_moviepy:
        tools_available.append("MoviePy ✅")
    if has_ffmpeg:
        tools_available.append("ffmpeg ✅")
    st.info(f"可用工具：{', '.join(tools_available)}")
    
    # 上傳影片檔案
    uploaded_video = st.file_uploader(
        "上傳影片檔案",
        type=SUPPORTED_VIDEO_FORMATS,
        help="支援 MP4, AVI, MKV, MOV, WebM, FLV, WMV 格式"
    )
    
    # 輸出格式選擇
    col1, col2 = st.columns(2)
    with col1:
        output_format = st.selectbox(
            "輸出音訊格式",
            options=["mp3", "wav", "aac", "m4a"],
            index=0,
            help="選擇輸出的音訊格式"
        )
    
    with col2:
        st.markdown("**格式說明：**")
        format_info = {
            "mp3": "最通用的格式，檔案較小",
            "wav": "無損格式，檔案較大",
            "aac": "高品質壓縮格式",
            "m4a": "Apple 相容的 AAC 格式"
        }
        st.caption(format_info.get(output_format, ""))
    
    # 轉換按鈕
    if uploaded_video is not None:
        st.markdown(f"**檔案名稱：** {uploaded_video.name}")
        st.markdown(f"**檔案大小：** {uploaded_video.size / (1024*1024):.2f} MB")
        
        if st.button("🔄 開始轉換", type="primary", use_container_width=True):
            with st.spinner("正在轉換中..."):
                try:
                    # 儲存上傳的影片到臨時檔案
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_video.name.split('.')[-1]}") as tmp_video:
                        tmp_video.write(uploaded_video.getvalue())
                        tmp_video_path = tmp_video.name
                    
                    # 設定輸出路徑
                    output_filename = os.path.splitext(uploaded_video.name)[0] + f".{output_format}"
                    tmp_audio_path = os.path.join(tempfile.gettempdir(), output_filename)
                    
                    # 執行轉換
                    progress_bar = st.progress(0, text="正在提取音訊...")
                    success, result = extract_audio_from_video(tmp_video_path, tmp_audio_path, output_format)
                    progress_bar.progress(100, text="轉換完成！")
                    
                    if success:
                        st.success(f"✅ 轉換成功！")
                        
                        # 讀取轉換後的音訊檔案
                        with open(result, "rb") as audio_file:
                            audio_data = audio_file.read()
                        
                        # 顯示音訊檔案資訊
                        audio_size = len(audio_data) / (1024*1024)
                        st.markdown(f"**輸出檔案大小：** {audio_size:.2f} MB")
                        
                        # 提供下載按鈕
                        st.download_button(
                            label=f"⬇️ 下載 {output_filename}",
                            data=audio_data,
                            file_name=output_filename,
                            mime=f"audio/{output_format}",
                            use_container_width=True
                        )
                        
                        # 提供音訊預覽
                        st.audio(audio_data, format=f"audio/{output_format}")
                        
                        # 儲存到 session state 供後續步驟使用
                        st.session_state["converted_audio_data"] = audio_data
                        st.session_state["converted_audio_name"] = output_filename
                        st.session_state["converted_audio_format"] = output_format
                        
                        # 成功提示與一鍵跳轉
                        st.success("🎉 音檔已準備就緒！可直接在「Step 3: 語音轉文字」中使用，無需重新上傳。")
                        st.markdown("👉 請切換到 **Step 3: 語音轉文字** 標籤頁，系統會自動載入此音檔。")
                        
                    else:
                        st.error(f"❌ 轉換失敗：{result}")
                    
                    # 清理臨時檔案
                    try:
                        os.unlink(tmp_video_path)
                        if success and os.path.exists(tmp_audio_path):
                            os.unlink(tmp_audio_path)
                    except:
                        pass
                        
                except Exception as e:
                    st.error(f"❌ 處理過程發生錯誤：{str(e)}")
                    logger.error(f"影片轉音檔失敗: {str(e)}")


def encode_image_to_base64(image_path: str) -> str:
    """
    將圖片編碼為 base64 字串
    
    Args:
        image_path (str): 圖片檔案路徑
        
    Returns:
        str: base64 編碼的圖片字串
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"圖片編碼失敗: {str(e)}")
        return ""

def generate_srt_from_json(json_responses, segment_duration=600, overlap_duration=30):
    """
    從 JSON 格式的轉錄結果生成 SRT 字幕
    
    Args:
        json_responses: JSON 格式的轉錄回應列表
        segment_duration: 每段音頻長度（秒）
        overlap_duration: 重疊時長（秒）
    
    Returns:
        SRT 格式的字幕文字
    """
    srt_content = []
    subtitle_index = 1
    
    for segment_idx, response in enumerate(json_responses):
        if not response:
            continue
            
        # 計算此分段的時間偏移
        segment_offset = max(0, segment_idx * segment_duration - overlap_duration if segment_idx > 0 else 0)
        
        # 檢查 JSON 回應是否包含 words 或 segments 信息
        try:
            if hasattr(response, 'words') and response.words:
                # 如果有詳細的詞級時間戳
                for word in response.words:
                    start_time = segment_offset + word.start
                    end_time = segment_offset + word.end
                    
                    start_srt = format_srt_time(start_time)
                    end_srt = format_srt_time(end_time)
                    
                    srt_content.append(f"{subtitle_index}")
                    srt_content.append(f"{start_srt} --> {end_srt}")
                    srt_content.append(word.word.strip())
                    srt_content.append("")
                    subtitle_index += 1
            
            elif hasattr(response, 'segments') and response.segments:
                # 如果有句級時間戳
                for segment in response.segments:
                    start_time = segment_offset + segment.start
                    end_time = segment_offset + segment.end
                    
                    start_srt = format_srt_time(start_time)
                    end_srt = format_srt_time(end_time)
                    
                    srt_content.append(f"{subtitle_index}")
                    srt_content.append(f"{start_srt} --> {end_srt}")
                    srt_content.append(segment.text.strip())
                    srt_content.append("")
                    subtitle_index += 1
            
            else:
                # 如果沒有詳細時間戳，使用文字內容估算
                text = response.text if hasattr(response, 'text') else str(response)
                fallback_srt = generate_srt_format_fallback([text], segment_offset, segment_duration)
                if fallback_srt:
                    srt_content.extend(fallback_srt.split('\n'))
                    subtitle_index += text.count('.') + 1
                    
        except Exception as e:
            # 如果 JSON 解析失敗，回退到基本模式
            logger.warning(f"JSON 解析失敗，使用回退模式: {e}")
            text = response.text if hasattr(response, 'text') else str(response)
            fallback_srt = generate_srt_format_fallback([text], segment_offset, segment_duration)
            if fallback_srt:
                srt_content.extend(fallback_srt.split('\n'))
                subtitle_index += text.count('.') + 1
    
    return "\n".join(srt_content)

def generate_srt_format_fallback(text_segments, segment_offset=0, segment_duration=600):
    """
    回退模式：將文字分段轉換為 SRT 字幕格式
    """
    srt_content = []
    subtitle_index = 1
    
    for text in text_segments:
        if not text or not text.strip():
            continue
            
        # 將文字分割為句子
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        sentence_duration = segment_duration / max(len(sentences), 1)
        
        for j, sentence in enumerate(sentences):
            if not sentence:
                continue
                
            subtitle_start = segment_offset + j * sentence_duration
            subtitle_end = min(subtitle_start + sentence_duration, segment_offset + segment_duration)
            
            # 格式化時間
            start_srt = format_srt_time(subtitle_start)
            end_srt = format_srt_time(subtitle_end)
            
            # 添加 SRT 條目
            srt_content.append(f"{subtitle_index}")
            srt_content.append(f"{start_srt} --> {end_srt}")
            srt_content.append(sentence + '.')
            srt_content.append("")  # 空行分隔
            subtitle_index += 1
    
    return "\n".join(srt_content)

def format_srt_time(seconds):
    """將秒數轉換為 SRT 時間格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

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
        # 使用 session_state 中選擇的模型，如果未設置則使用預設值
        model_name = st.session_state.get("gemini_model", "gemini-2.5-pro")
        model = genai.GenerativeModel(model_name)
        
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
    st.header("Step 1: 文件與圖像處理")
    
    # MarkItDown 服務說明
    st.markdown(MARKITDOWN_SERVICE_INFO)
    
    # 初始化 session state
    if "markdown_text" not in st.session_state:
        st.session_state.markdown_text = None
    if "markdown_keywords" not in st.session_state:
        st.session_state.markdown_keywords = None
    if "analyzed_images" not in st.session_state:
        st.session_state.analyzed_images = {}
    if "enhanced_slides" not in st.session_state:
        st.session_state.enhanced_slides = None
    if "editing_keywords" not in st.session_state:
        st.session_state.editing_keywords = False
    if "transcription_prompt" not in st.session_state:
        st.session_state.transcription_prompt = ""

    # 創建兩個標籤頁：內容輸入和增強與分析
    tab1, tab2 = st.tabs(["📄 內容輸入", "✨ 增強與分析"])
    
    # 內容輸入標籤頁
    with tab1:
        st.subheader("文件及圖片上傳或直接輸入")
        
        # 選擇輸入類型
        input_type = st.radio(
            "選擇輸入方式",
            ["檔案上傳", "直接輸入"],
            horizontal=True
        )
        
        if input_type == "檔案上傳":
            # 整合文件和圖片上傳為單一上傳區域
            st.markdown("""
            支持以下檔案類型：
            - 文件：PDF, DOCX, DOC, PPTX, PPT, XLSX, XLS, CSV, TXT, RTF, HTML, 
              HTM, MD, MARKDOWN
            - 圖片：JPG, JPEG, PNG
            
            檔案大小限制：每個檔案 200MB
            """)
            
            # 合併所有支持的檔案類型
            all_supported_files = SUPPORTED_FILE_TYPES + ["jpg", "jpeg", "png"]
            
            # 單一上傳界面
            uploaded_files = st.file_uploader(
                "拖放檔案到此處上傳",
                type=all_supported_files,
                accept_multiple_files=True,
                help="支持文件和圖片同時上傳，系統會自動識別檔案類型"
            )
            
            # 檢查是否有 OpenAI API 金鑰
            openai_api_key = st.session_state.get("openai_api_key", "")
            
            # 添加 Vision API 選項
            use_vision_api = st.checkbox(
                "🔍 啟用進階 Vision API 分析 (適用於複雜 PPTX 圖片投影片)",
                value=False,
                help="使用進階 Vision API 將整個 PPTX 轉為圖片進行深度分析。即使不勾選，MarkItDown 也會自動處理文件中的圖片內容。需要 OpenAI API 金鑰。"
            )
            
            # 如果啟用了 Vision API 但沒有 API 金鑰，顯示警告
            if use_vision_api and not openai_api_key:
                st.warning("⚠️ 已啟用 Vision API，但未提供 OpenAI API 金鑰。請在側邊欄填入 API 金鑰以使用此功能。")
            
            # 處理說明
            if uploaded_files:
                # 分類上傳的檔案
                doc_files = []
                image_files = []
                
                for file in uploaded_files:
                    file_ext = file.name.split('.')[-1].lower()
                    if file_ext in ["jpg", "jpeg", "png"]:
                        image_files.append(file)
                    else:
                        doc_files.append(file)
                
                # 顯示檔案資訊
                if doc_files and image_files:
                    st.info(
                        f"已上傳 {len(doc_files)} 個文件和 {len(image_files)} 張圖片"
                    )
                    process_btn_label = "🔄 處理文件和分析圖片"
                elif doc_files:
                    st.info(f"已上傳 {len(doc_files)} 個文件")
                    process_btn_label = "🔄 轉換文件為 Markdown"
                elif image_files:
                    st.info(f"已上傳 {len(image_files)} 張圖片")
                    process_btn_label = "🔄 分析圖片"
                else:
                    st.warning("請上傳文件或圖片進行處理")
                    return
                
                # 整合處理按鈕
                if not openai_api_key:
                    st.warning("請在側邊欄提供 OpenAI API 金鑰以進行分析")
                else:
                    process_btn = st.button(
                        process_btn_label,
                        use_container_width=True
                    )
                    
                    if process_btn:
                        # 處理流程
                        with st.spinner("正在處理..."):
                            temp_markdown = ""
                            
                            # 處理文件（如果有）
                            if doc_files:
                                # 處理第一個文件（目前只支援處理一個文件）
                                uploaded_file = doc_files[0]
                                success, temp_path = save_uploaded_file(
                                    uploaded_file
                                )
                                
                                if success:
                                    # 轉換檔案
                                    st.info("正在轉換文件...")
                                    success, md_text, info = (
                                        convert_file_to_markdown(
                                            input_path=temp_path,
                                            use_llm=use_vision_api,
                                            api_key=openai_api_key,
                                            model="gpt-4o"  # Vision API 需要 gpt-4o 模型
                                        )
                                    )
                                    
                                    # 如果轉換失敗且是 magika 相關錯誤，提供修復建議
                                    if not success and "magika" in str(info.get("error", "")).lower():
                                        st.error("檔案轉換失敗：magika 套件配置問題")
                                        st.markdown("""
                                        **解決方案：**
                                        1. 在終端機執行以下命令修復 magika 套件：
                                        ```bash
                                        python fix_magika.py
                                        ```
                                        
                                        2. 或者手動執行：
                                        ```bash
                                        pip uninstall magika -y
                                        pip install magika --no-cache-dir
                                        ```
                                        
                                        3. 重新啟動應用程式
                                        """)
                                        # 跳過後續處理，直接返回
                                        return
                                    
                                    # 清理臨時檔案
                                    try:
                                        os.remove(temp_path)
                                    except Exception as e:
                                        logger.error(
                                            f"清理臨時檔案失敗: {str(e)}"
                                        )
                                        pass
                                    
                                    if success:
                                        temp_markdown = md_text
                                        st.success("文件轉換成功！")
                                    else:
                                        # 顯示錯誤資訊
                                        st.error(
                                            f"轉換失敗: {info.get('error', '未知錯誤')}"
                                        )
                                else:
                                    st.error(
                                        f"處理上傳檔案時發生錯誤: {temp_path}"
                                    )
                            
                            # 處理圖片（如果有）
                            if image_files:
                                # 如果有文件轉換內容，添加分隔線和圖片分析標題
                                if temp_markdown:
                                    temp_markdown += "\n\n## 圖片分析\n\n"
                                else:
                                    temp_markdown = "# 圖片分析結果\n\n"
                                
                                # 保存和分析圖片
                                analyzed_count = 0
                                progress_bar = st.progress(0)
                                total_images = len(image_files)
                                
                                for i, img_file in enumerate(image_files):
                                    # 保存上傳的檔案
                                    success, temp_path = save_uploaded_file(
                                        img_file
                                    )
                                    
                                    if success:
                                        # 分析圖片
                                        with st.spinner(
                                            f"分析圖片 {i+1}/{total_images}..."
                                        ):
                                            result = analyze_image(
                                                temp_path, 
                                                openai_api_key, 
                                                "o4-mini"  # 使用o4-mini模型
                                            )
                                        
                                        if result["success"]:
                                            # 儲存分析結果
                                            img_analysis = {
                                                "path": temp_path,
                                                "description": (
                                                    result["description"]
                                                ),
                                                "tokens": result["tokens"]
                                            }
                                            st.session_state.analyzed_images[
                                                img_file.name
                                            ] = img_analysis
                                            
                                            # 顯示圖片和分析結果
                                            st.image(
                                                temp_path, 
                                                caption=img_file.name
                                            )
                                            st.markdown("### 分析結果")
                                            st.markdown(result["description"])
                                            st.markdown("---")
                                            
                                            # 添加到臨時 Markdown
                                            md_title = f"### {img_file.name}\n\n"
                                            temp_markdown += md_title
                                            temp_markdown += (
                                                f"![圖片]({temp_path})\n\n"
                                            )
                                            temp_markdown += (
                                                f"{result['description']}\n\n"
                                                f"---\n\n"
                                            )
                                            
                                            # 增加處理圖片計數
                                            analyzed_count += 1
                                            
                                            # 更新進度條
                                            if progress_bar is not None:
                                                progress_percentage = (
                                                    analyzed_count / 
                                                    total_images
                                                )
                                                progress_bar.progress(
                                                    progress_percentage
                                                )
                                        else:
                                            error_msg = result.get(
                                                'error', '未知錯誤'
                                            )
                                            st.error(
                                                f"分析失敗: {error_msg}"
                                            )
                                    else:
                                        st.error(
                                            f"處理上傳檔案時發生錯誤: {temp_path}"
                                        )
                                
                                # 顯示處理完成訊息
                                if analyzed_count > 0:
                                    msg = f"已完成 {analyzed_count} 張圖片的分析"
                                    st.success(msg)
                            
                            # 將分析結果存儲到 markdown_text 中
                            if temp_markdown:
                                st.session_state.markdown_text = temp_markdown
                                st.success("所有內容處理完成，可以進行後續分析")
                                st.rerun()
        
        else:  # 直接輸入
            # 文字輸入區域
            user_text = st.text_area(
                "直接輸入文字",
                placeholder="在此輸入您的文字內容...",
                help="直接輸入要處理的文字內容",
                height=300
            )
            
            # 新增：轉錄提示設定
            st.markdown("### 轉錄提示設定")
            st.markdown("""
            提供提示可以幫助模型更準確地識別特定術語、專有名詞或領域特定詞彙。
            """)
            
            transcription_prompt = st.text_area(
                "轉錄提示 (可選)",
                value=st.session_state.get("transcription_prompt", ""),
                placeholder="例如：這是一段醫學演講，可能包含以下專業術語: 高血壓、糖尿病、心肌梗塞...",
                help="提供上下文或領域特定的詞彙，以增強轉錄準確性"
            )
            
            # 儲存到 session state
            st.session_state["transcription_prompt"] = transcription_prompt
            
            if user_text:
                # 處理按鈕
                process_text_btn = st.button(
                    "✅ 處理文字內容",
                    use_container_width=True
                )
                
                if process_text_btn:
                    # 儲存用戶輸入的文字
                    st.session_state.markdown_text = user_text
                    st.success(
                        f"文字內容已處理！長度: {len(user_text)} 字元"
                    )
                    st.rerun()
    
    # 增強與分析標籤頁
    with tab2:
        st.subheader("文本增強與分析")
        
        # 是否有內容可以進行增強與分析
        if not st.session_state.markdown_text:
            st.info("請先在「內容輸入」標籤頁上傳文件、圖片或輸入文字")
            return
        
        # 顯示 Markdown 文字
        st.text_area(
            "內容預覽",
            st.session_state.markdown_text,
            height=250
        )
        
        # 增強選項
        st.markdown("### 選擇增強操作")
        
        enhancement_type = st.radio(
            "選擇增強類型",
            ["提取關鍵詞", "幻燈片增強", "傳送至優化功能"],
            horizontal=True
        )
        
        # 檢查 API 金鑰是否存在
        openai_api_key = st.session_state.get("openai_api_key", "")
        if not openai_api_key and enhancement_type in ["提取關鍵詞", "幻燈片增強"]:
            st.warning("請在側邊欄提供 OpenAI API 金鑰以進行增強操作")
        
        # 根據增強類型顯示不同的選項
        if enhancement_type == "提取關鍵詞" and openai_api_key:
            col1, col2 = st.columns(2)
            
            with col1:
                model_for_keywords = st.selectbox(
                    "選擇模型",
                    ["gpt-4o", "gpt-4o-mini"],
                    index=1,
                    help="選擇用於提取關鍵詞的模型"
                )
            
            with col2:
                keyword_count = st.number_input(
                    "關鍵詞數量",
                    min_value=5,
                    max_value=50,
                    value=10,
                    help="要提取的關鍵詞數量"
                )
            
            # 提取關鍵詞按鈕
            if st.button("🔍 提取關鍵詞", use_container_width=True):
                # 提取關鍵詞
                keywords = process_markdown_extraction(
                    st.session_state.markdown_text,
                    openai_api_key,
                    model_for_keywords,
                    keyword_count
                )
                
                if keywords:
                    st.session_state.markdown_keywords = keywords
                    st.success(f"成功提取 {len(keywords)} 個關鍵詞")
                    st.rerun()
            
            # 顯示已提取的關鍵詞
            if st.session_state.markdown_keywords:
                # 顯示關鍵詞
                st.write("### 提取的關鍵詞")
                for i, kw in enumerate(st.session_state.markdown_keywords):
                    st.write(f"{i+1}. {kw}")
                
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
                
                # 添加編輯關鍵詞的功能
                if st.button("✏️ 編輯關鍵詞", use_container_width=True):
                    # 將關鍵詞列表顯示在文本區域中供編輯
                    st.session_state.editing_keywords = True
                    st.rerun()
                
                # 當處於編輯模式時顯示編輯界面
                if st.session_state.get("editing_keywords", False):
                    edit_keywords = st.text_area(
                        "編輯關鍵詞（每行一個）",
                        value="\n".join(st.session_state.markdown_keywords),
                        height=200
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ 確認修改", use_container_width=True):
                            # 將編輯後的文本轉換為列表
                            edited_keywords = [
                                kw.strip() 
                                for kw in edit_keywords.split("\n") 
                                if kw.strip()
                            ]
                            if edited_keywords:
                                kw_len = len(edited_keywords)
                                update_msg = (
                                    f"已更新關鍵詞列表，共 {kw_len} 個關鍵詞"
                                )
                                st.session_state.markdown_keywords = (
                                    edited_keywords
                                )
                                st.session_state.editing_keywords = False
                                st.success(update_msg)
                    
                    with col2:
                        if st.button("❌ 取消編輯", use_container_width=True):
                            st.session_state.editing_keywords = False
                            st.rerun()
        
        elif enhancement_type == "幻燈片增強" and openai_api_key:
            # 幻燈片增強說明
            st.markdown("""
            ### 幻燈片增強功能
            
            此功能會自動識別 Markdown 中的圖片，使用 AI 為圖片添加詳細的描述，
            並以折疊式描述的方式添加到幻燈片中。適合用於增強演示文稿的資訊量。
            
            **幻燈片格式範例**：
            ```markdown
            <!-- Slide number: 1 -->
            # 標題幻燈片
            
            ## 副標題
            
            * 項目一
            * 項目二
            
            ![圖片說明](images/example.jpg)
            ```
            
            > **注意**：建議使用 `<!-- Slide number: X -->` 作為幻燈片分隔符，
            > 這將幫助系統正確識別每個幻燈片區塊。
            """)
            
            # 模型選擇
            slide_model = st.selectbox(
                "選擇模型",
                ["gpt-4o", "gpt-4o-mini"],
                index=1,
                help="選擇用於幻燈片增強的模型"
            )
            
            # 增強按鈕
            if st.button("✨ 增強幻燈片", use_container_width=True):
                with st.spinner("正在增強幻燈片內容..."):
                    # 增強幻燈片
                    result = enhance_slides(
                        st.session_state.markdown_text, 
                        openai_api_key, 
                        slide_model
                    )
                    
                    # 將結果儲存到 session state
                    st.session_state.enhanced_slides = result["enhanced_text"]
                    
                    # 顯示統計資訊
                    st.markdown("### 處理統計")
                    st.write(f"處理幻燈片數量: {result['stats']['slides_processed']}")
                    st.write(f"處理圖片數量: {result['stats']['images_processed']}")
                    st.write(f"成功分析圖片: {result['stats']['images_analyzed']}")
                    st.write(f"分析失敗圖片: {result['stats']['images_failed']}")
                    st.write(f"使用 Tokens: {result['stats']['total_tokens']}")
                    
                    # 顯示增強後的內容
                    st.markdown("### 增強後的內容")
                    st.text_area(
                        "增強後的幻燈片內容",
                        result["enhanced_text"],
                        height=400
                    )
                    
                    # 下載按鈕
                    st.download_button(
                        label="📥 下載增強後的幻燈片",
                        data=result["enhanced_text"],
                        file_name="enhanced_slides.md",
                        mime="text/markdown",
                        help="下載增強後的幻燈片 Markdown 檔案",
                        use_container_width=True
                    )
            
            # 顯示已增強的幻燈片
            if st.session_state.enhanced_slides and not st.button:
                st.markdown("### 已增強的幻燈片內容")
                st.text_area(
                    "增強後的幻燈片內容",
                    st.session_state.enhanced_slides,
                    height=400
                )
                
                # 下載按鈕
                st.download_button(
                    label="📥 下載增強後的幻燈片",
                    data=st.session_state.enhanced_slides,
                    file_name="enhanced_slides.md",
                    mime="text/markdown",
                    help="下載增強後的幻燈片 Markdown 檔案",
                    use_container_width=True
                )
        
        elif enhancement_type == "傳送至優化功能":
            # 傳送至優化功能
            if st.button(
                "📤 傳送至文字優化功能 (Step 3)",
                use_container_width=True
            ):
                st.session_state.transcribed_text = st.session_state.markdown_text
                st.success("內容已傳送至文字優化功能 (Step 3)！")
                st.rerun()
        
        # 下載原始 Markdown 檔案
        st.download_button(
            label="📥 下載 Markdown 檔案",
            data=st.session_state.markdown_text,
            file_name="content.md",
            mime="text/markdown",
            help="下載當前內容的 Markdown 檔案",
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
    if "transcription_prompt" not in st.session_state:
        st.session_state.transcription_prompt = ""
    if "optimization_prompt" not in st.session_state:
        st.session_state.optimization_prompt = ""
    
    # 設定預設API金鑰
    if "openai_api_key" not in st.session_state:
        st.session_state["openai_api_key"] = ""
    if "elevenlabs_api_key" not in st.session_state:
        st.session_state["elevenlabs_api_key"] = ""
    if "gemini_api_key" not in st.session_state:
        st.session_state["gemini_api_key"] = ""
    if "use_llm" not in st.session_state:
        st.session_state["use_llm"] = False
    if "openai_model" not in st.session_state:
        st.session_state["openai_model"] = "o4-mini-transcribe"
    if "keyword_count" not in st.session_state:
        st.session_state["keyword_count"] = 10
    if "optimization_model" not in st.session_state:
        st.session_state["optimization_model"] = "o4-mini"

    # 創建主要的功能標籤頁，添加步驟編號
    tabs_titles = [
        "🎬 Step 1: 影片轉音檔",
        "📝 Step 2: 文件與圖像處理", 
        "🎙️ Step 3: 語音轉文字", 
        "✨ Step 4: 文字優化"
    ]
    main_tabs = st.tabs(tabs_titles)
    
    # 影片轉音檔標籤頁 (Step 1)
    with main_tabs[0]:
        render_video_to_audio_tab()
    
    # 文件轉換與關鍵詞標籤頁 (Step 2)
    with main_tabs[1]:
        render_markitdown_tab()
    
    # 語音轉文字標籤頁 (Step 3)
    with main_tabs[2]:
        with st.sidebar:
            st.header("設定")
            
            # 分成兩個標籤頁：轉錄設定和優化設定
            tab1, tab2 = st.tabs(["🎙️ 轉錄設定", "✨ 優化設定"])
            
            # 轉錄設定標籤頁
            with tab1:
                # 選擇轉錄服務
                transcription_service = st.selectbox(
                    "選擇轉錄服務",
                    options=["OpenAI 2025 New", "Whisper", "ElevenLabs"],
                    index=0,
                    help="選擇要使用的語音轉文字服務"
                )
                
                # 顯示服務說明
                st.markdown(TRANSCRIPTION_SERVICE_INFO[transcription_service])
                
                # 根據選擇的服務顯示對應的API金鑰輸入框
                if transcription_service == "OpenAI 2025 New":
                    # OpenAI API 金鑰
                    openai_api_key = st.text_input(
                        "OpenAI API 金鑰",
                        type="password",
                        value=st.session_state.get("openai_api_key", ""),
                        help="用於 OpenAI 的語音轉文字服務"
                    )
                    # 儲存到 session state
                    st.session_state["openai_api_key"] = openai_api_key
                    
                    # 允許用戶選擇轉錄模型
                    transcribe_model = st.radio(
                        "選擇轉錄模型",
                        options=["gpt-4o-transcribe", "gpt-4o-mini-transcribe"],
                        index=1,  # 預設使用mini版本
                        help=("gpt-4o-transcribe：高精度、多語言支援；"
                             "gpt-4o-mini-transcribe：輕量快速、性價比高")
                    )
                    st.session_state["openai_model"] = transcribe_model
                    
                    # 語言設定
                    language_mode = st.radio(
                        "語言設定",
                        options=["自動偵測", "指定語言"],
                        help="選擇音訊的語言處理模式"
                    )
                    
                    # 語言設定
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
                    
                    # 輸出格式設定
                    output_format = st.radio(
                        "輸出格式",
                        options=["純文字", "Markdown", "SRT (含時間戳)"],
                        index=0,
                        help=("純文字：標準轉錄文字；"
                             "Markdown：結構化格式；"
                             "SRT：字幕格式，含時間戳")
                    )
                    st.session_state["output_format"] = output_format
                
                elif transcription_service == "ElevenLabs":
                    # ElevenLabs API 金鑰
                    elevenlabs_api_key = st.text_input(
                        "ElevenLabs API 金鑰",
                        type="password",
                        help="用於 ElevenLabs 語音轉文字服務"
                    )
                    # 儲存到 session state
                    st.session_state["elevenlabs_api_key"] = elevenlabs_api_key
                
                # Whisper 相關設定
                elif transcription_service == "Whisper":
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
            
            # 優化設定標籤頁
            with tab2:
                # 選擇優化服務
                optimization_service = st.selectbox(
                    "選擇優化服務",
                    ["Gemini", "OpenAI"],
                    help="選擇要使用的文字優化服務"
                )
                # 將選擇存儲到 session state
                st.session_state["optimization_service"] = optimization_service
                
                # 顯示服務說明
                st.markdown(OPTIMIZATION_SERVICE_INFO[optimization_service])
                
                # 根據選擇的服務顯示對應的API金鑰輸入框
                if optimization_service == "Gemini":
                    # Gemini API 金鑰
                    gemini_api_key = st.text_input(
                        "Google API 金鑰",
                        type="password",
                        value=st.session_state.get("gemini_api_key", ""),
                        help="用於 Gemini 模型優化文字"
                    )
                    # 儲存到 session state
                    st.session_state["gemini_api_key"] = gemini_api_key
                    
                    # 添加模型選擇選項
                    gemini_model = st.radio(
                        "選擇 Gemini 模型",
                        options=[
                            "gemini-3-pro-preview",
                            "gemini-3-flash-preview",
                            "gemini-2.5-pro", 
                            "gemini-2.5-flash",
                            "gemini-2.0-flash"
                        ],
                        index=0,
                        help="Gemini 3 系列最強大，2.5 系列穩定，Flash 版本速度更快"
                    )
                    st.session_state["gemini_model"] = gemini_model
                    
                    # 顯示 Gemini 模型資訊
                    st.info(f"使用 {gemini_model} 模型進行優化")
                else:  # OpenAI
                    # OpenAI API 金鑰
                    openai_api_key = st.text_input(
                        "OpenAI API 金鑰",
                        type="password",
                        value=st.session_state.get("openai_api_key", ""),
                        help="用於 OpenAI 模型優化文字"
                    )
                    # 儲存到 session state
                    st.session_state["openai_api_key"] = openai_api_key
                    
                    # 顯示模型資訊
                    st.info("使用 o4-mini 模型進行優化，擁有更快速度和更低成本")
                    st.session_state["optimization_model"] = "o4-mini"
                
                # 優化提示 (增加文字優化效果)
                st.markdown("### 優化提示設定")
                st.markdown("""
                提供上下文或特定指示可以使模型更好地理解內容並產生更符合需求的優化結果。
                """)
                
                optimization_prompt = st.text_area(
                    "優化提示 (可選)",
                    value=st.session_state.get("optimization_prompt", ""),
                    placeholder="例如：這是一場醫學研討會的演講稿，請特別注意醫學術語的正確性，並結構化為簡報格式...",
                    help="提供上下文或特定指示，以提升優化效果"
                )
                
                # 儲存到 session state
                st.session_state["optimization_prompt"] = optimization_prompt
                
                # 優化設定
                temperature = st.slider(
                    "創意程度",
                    0.0,
                    1.0,
                    0.5,
                    help="較高的值會產生更有創意的結果，較低的值會產生更保守的結果"
                )
                # 儲存到 session state
                st.session_state["temperature"] = temperature
            
            # 作者資訊
            st.markdown("---")
            st.markdown("""
            ### Created by
            **Tseng Yao Hsien**  
            Endocrinologist  
            Tungs' Taichung MetroHarbor Hospital
            """)

        # 語音轉文字主要內容
        st.header("Step 3: 語音轉文字")
        
        # 檢查是否有來自 Step 1 的轉換音檔
        has_converted_audio = (
            "converted_audio_data" in st.session_state and 
            st.session_state.get("converted_audio_data") is not None
        )
        
        if has_converted_audio:
            converted_name = st.session_state.get("converted_audio_name", "audio.mp3")
            st.success(f"🎉 檢測到來自 Step 1 的音檔：**{converted_name}**")
            
            # 選擇音檔來源
            audio_source = st.radio(
                "選擇音檔來源",
                options=["使用 Step 1 轉換的音檔", "上傳新的音檔"],
                index=0,
                horizontal=True
            )
            
            if audio_source == "使用 Step 1 轉換的音檔":
                # 顯示預覽
                st.audio(st.session_state["converted_audio_data"], 
                        format=f"audio/{st.session_state.get('converted_audio_format', 'mp3')}")
                uploaded_file = None  # 使用轉換的音檔，不需要上傳
                use_converted = True
            else:
                # 上傳檔案
                uploaded_file = st.file_uploader(
                    "上傳音訊檔案",
                    type=["mp3", "wav", "ogg", "m4a"]
                )
                use_converted = False
        else:
            use_converted = False
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
            
            # 根據輸出格式決定顯示方式
            output_format = st.session_state.get("output_format", "純文字")
            
            if output_format == "Markdown":
                # Markdown 格式使用 st.markdown 顯示
                st.markdown(st.session_state.transcribed_text)
                
                # 同時提供原始文字區域以便編輯
                with st.expander("📝 檢視/編輯原始 Markdown 內容"):
                    st.text_area(
                        "Markdown 內容",
                        st.session_state.transcribed_text,
                        height=200,
                        key="markdown_content"
                    )
            elif output_format == "SRT (含時間戳)":
                # SRT 格式使用 code 區塊顯示
                st.code(st.session_state.transcribed_text, language="srt")
                
                # 同時提供文字區域以便編輯
                with st.expander("📝 檢視/編輯 SRT 內容"):
                    st.text_area(
                        "SRT 內容",
                        st.session_state.transcribed_text,
                        height=200,
                        key="srt_content"
                    )
            else:
                # 純文字格式
                st.text_area(
                    "轉錄文字",
                    st.session_state.transcribed_text,
                    height=200
                )
            
            # 下載按鈕
            st.markdown("### 下載選項")
            
            # 根據格式設定檔案副檔名和 MIME 類型
            file_extensions = {
                "純文字": ("txt", "text/plain"),
                "Markdown": ("md", "text/markdown"),
                "SRT (含時間戳)": ("srt", "text/plain")
            }
            
            ext, mime_type = file_extensions.get(output_format, ("txt", "text/plain"))
            
            st.download_button(
                label=f"📥 下載 {output_format} 檔案",
                data=st.session_state.transcribed_text,
                file_name=f"transcription.{ext}",
                mime=mime_type,
                help=f"下載 {output_format} 格式的轉錄檔案",
                use_container_width=True,
                key="download_transcription_formatted"
            )
            
            # 只在有轉錄文字時顯示優化按鈕，添加 Step 3 指示
            optimize_button = st.button("✨ 進入 Step 3: 優化文字", use_container_width=True)
        else:
            optimize_button = False
        
        # 處理轉錄 - 支援上傳檔案或來自 Step 1 的轉換音檔
        should_transcribe = transcribe_button and (uploaded_file or (has_converted_audio and use_converted))
        
        if should_transcribe:
            # 從session state獲取API金鑰
            openai_api_key = st.session_state.get("openai_api_key", "")
            elevenlabs_api_key = st.session_state.get("elevenlabs_api_key", "")
            
            if transcription_service == "OpenAI 2025 New" and not openai_api_key:
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
                    
                    # 處理音檔來源
                    if has_converted_audio and use_converted:
                        # 使用來自 Step 1 的轉換音檔
                        audio_data = st.session_state["converted_audio_data"]
                        audio_name = st.session_state.get("converted_audio_name", "audio.mp3")
                        suffix = os.path.splitext(audio_name)[1]
                        
                        with tempfile.NamedTemporaryFile(
                            delete=False,
                            suffix=suffix
                        ) as temp_file:
                            temp_file.write(audio_data)
                            temp_path = temp_file.name
                        
                        st.info(f"📂 正在處理來自 Step 1 的音檔：{audio_name}")
                    else:
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
                        try:
                            audio = AudioSegment.from_file(temp_path)
                            duration_seconds = len(audio) / 1000
                        except Exception as audio_error:
                            # 如果無法使用 AudioSegment（通常是缺少 ffmpeg），直接處理整個檔案
                            logger.warning(f"無法分析音訊長度（可能缺少 ffmpeg）: {audio_error}")
                            st.warning("⚠️ 偵測到缺少 ffmpeg，將直接處理整個音訊檔案（可能較慢）")
                            audio_segments = [temp_path]
                            duration_seconds = 0  # 設為 0 以跳過分段邏輯
                        
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
                                end_time = min(
                                    start_time + MAX_SEGMENT_DURATION, 
                                    duration_seconds
                                )
                                
                                # 如果不是第一段，則從前一段結尾提前開始
                                if start_time > 0:
                                    segment_start = start_time - OVERLAP_DURATION
                                else:
                                    segment_start = start_time
                                
                                # 擷取音訊片段
                                segment = audio[
                                    int(segment_start * 1000):int(end_time * 1000)
                                ]
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
                        segment_results = []
                        
                        for i, segment_path in enumerate(audio_segments):
                            if transcription_service == "Whisper":
                                result = transcribe_audio_whisper(
                                    segment_path,
                                    model_name=whisper_model,
                                    language=language_code,
                                    initial_prompt=st.session_state["transcription_prompt"]
                                )
                            elif transcription_service == "ElevenLabs":
                                result = transcribe_audio_elevenlabs(
                                    api_key=elevenlabs_api_key,
                                    file_path=segment_path,
                                    language_code="zho",  # 指定中文
                                    diarize=False  # 取消啟用說話者辨識
                                )
                            elif transcription_service == "OpenAI 2025 New":
                                MAX_RETRIES = 3
                                retry_count = 0
                                failed = True
                                while retry_count < MAX_RETRIES:
                                    try:
                                        with open(segment_path, "rb") as audio_file:
                                            # GPT-4o 模型只支援 text 和 json 格式
                                            # 根據官方文件，gpt-4o-transcribe 只支援 json 和 text
                                            selected_format = st.session_state.get("output_format", "純文字")
                                            if selected_format == "SRT (含時間戳)":
                                                api_format = "json"  # 使用 json 嘗試獲取時間信息
                                            else:
                                                api_format = "text"
                                            
                                            # 添加詳細的調試信息
                                            logger.info(f"準備轉錄分段 {i+1}/{len(audio_segments)}")
                                            logger.info(f"使用模型: {st.session_state['openai_model']}")
                                            logger.info(f"API 格式: {api_format}")
                                            logger.info(f"語言代碼: {language_code}")
                                            
                                            response = (
                                                openai_client.audio
                                                .transcriptions
                                                .create(
                                                    model=st.session_state["openai_model"],
                                                    file=audio_file,
                                                    language=language_code,
                                                    response_format=api_format,
                                                    prompt=st.session_state["transcription_prompt"],
                                                    temperature=0.3
                                                )
                                            )
                                            # 成功則添加結果
                                            if api_format == "json":
                                                # JSON 格式，儲存完整回應以供後續處理
                                                segment_results.append(response)
                                                logger.info(f"JSON 回應長度: {len(str(response))}")
                                            else:
                                                # TEXT 格式，使用 .text 屬性
                                                text_result = response.text if hasattr(response, 'text') else str(response)
                                                segment_results.append(text_result)
                                                logger.info(f"文字結果長度: {len(text_result)}")
                                                logger.info(f"文字結果預覽: {text_result[:100]}...")
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
                                        logger.error(f"OpenAI API 錯誤詳細信息: {error_msg}")
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
                                            # 顯示錯誤給用戶
                                            st.error(f"OpenAI API 錯誤: {error_msg}")
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
                        
                        # 增加調試日誌
                        logger.info(f"共處理 {len(segment_results)} 個分段結果")
                        
                        # 合併結果
                        # 根據輸出格式處理結果
                        selected_format = st.session_state.get("output_format", "純文字")
                        
                        if selected_format == "SRT (含時間戳)":
                            # 使用 JSON 回應生成 SRT
                            full_transcript = generate_srt_from_json(
                                segment_results,
                                segment_duration=600,
                                overlap_duration=30
                            )
                        elif selected_format == "Markdown":
                            # 從結果中提取文字內容
                            text_parts = []
                            for result in segment_results:
                                if hasattr(result, 'text'):
                                    text_parts.append(result.text)
                                else:
                                    text_parts.append(str(result))
                            raw_text = " ".join(text_parts)
                            full_transcript = f"# 語音轉錄結果\n\n{raw_text}\n"
                        else:
                            # 純文字格式，從結果中提取文字內容
                            text_parts = []
                            for result in segment_results:
                                if hasattr(result, 'text'):
                                    text_parts.append(result.text)
                                else:
                                    text_parts.append(str(result))
                            full_transcript = " ".join(text_parts)
                        
                        # 添加調試日誌
                        logger.info(f"轉錄結果長度: {len(full_transcript) if full_transcript else 0}")
                        logger.info("完成所有分段的轉錄與合併")
                    
                    except Exception as e:
                        st.error(f"處理失敗：{str(e)}")
                        logger.error(f"處理失敗：{str(e)}")
                        full_transcript = ""  # 確保異常時重置變數
                    
                    # 處理轉錄結果
                    if full_transcript and full_transcript.strip():
                        st.session_state.transcribed_text = full_transcript
                        st.success("轉錄完成！")
                        logger.info("轉錄結果已儲存至 session_state")
                        st.rerun()  # 使用新的 rerun 方法
                    else:
                        st.error("轉錄失敗或結果為空")
                        logger.error("轉錄失敗：結果為空或無效")
                        
            except Exception as e:
                st.error(f"處理失敗：{str(e)}")
                logger.error(f"處理失敗：{str(e)}")
        
        # 優化標籤頁 (Step 4)
        with main_tabs[3]:
            st.header("Step 4: 文字優化")
        
            # 如果沒有待優化的文字，顯示提示
            if not st.session_state.transcribed_text:
                st.info("請先在 Step 2 轉換文件或 Step 3 轉錄音訊，然後再執行優化")
                return

            # 顯示優化結果（如果有的話）
            if st.session_state.optimized_text:
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
                optimization_service = st.session_state.get("optimization_service", "OpenAI")
                if optimization_service == "OpenAI":
                    tokens_display = st.session_state.total_tokens
                    st.markdown(f"總 Tokens: **{tokens_display:,}**")
                    
                    # 計算費用
                    cost_result = calculate_cost(
                        st.session_state.input_tokens,
                        st.session_state.output_tokens,
                        st.session_state["optimization_model"],
                        is_cached=False
                    )
                    
                    st.markdown(f"總費用: **NT$ {cost_result[1]:.2f}**")
                    
                    # 顯示詳細成本資訊
                    display_cost_info(
                        st.session_state.input_tokens,
                        st.session_state.output_tokens,
                        st.session_state["optimization_model"],
                        is_cached=False
                    )
                else:
                    st.info("Gemini API 使用量暫不計費")
            else:
                # 如果有文字但尚未優化，顯示優化按鈕
                st.text_area(
                    "待優化文字",
                    st.session_state.transcribed_text,
                    height=300
                )
                
                optimize_button = st.button("✨ 優化文字", use_container_width=True)
                
                # 處理優化
                if optimize_button:
                    try:
                        with st.spinner("優化中..."):
                            # 從 session state 獲取 API 金鑰和設定
                            openai_api_key = st.session_state.get("openai_api_key", "")
                            gemini_api_key = st.session_state.get("gemini_api_key", "")
                            optimization_service = st.session_state.get("optimization_service", "OpenAI")
                            temperature = st.session_state.get("temperature", 0.5)
                            
                            if optimization_service == "OpenAI":
                                if not openai_api_key:
                                    st.error("請在側邊欄提供 OpenAI API 金鑰")
                                    return
                                    
                                refined = refine_transcript(
                                    raw_text=st.session_state.transcribed_text,
                                    api_key=openai_api_key,
                                    model=st.session_state["optimization_model"],
                                    temperature=temperature,
                                    context=st.session_state["optimization_prompt"]
                                )
                            else:  # Gemini
                                if not gemini_api_key:
                                    st.error("請在側邊欄提供 Google API 金鑰")
                                    return
                                    
                                refined = refine_transcript_gemini(
                                    text=st.session_state.transcribed_text,
                                    api_key=gemini_api_key,
                                    temperature=temperature,
                                    context=st.session_state["optimization_prompt"]
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
                                
                                st.rerun()
                            else:
                                st.error("文字優化失敗")
                    except Exception as e:
                        st.error(f"優化失敗：{str(e)}")
                        logger.error(f"優化失敗：{str(e)}")

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