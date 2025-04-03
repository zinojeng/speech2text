import gradio as gr
import os
from elevenlabs_stt import transcribe_audio_elevenlabs
from whisper_stt import transcribe_audio_whisper
from transcript_refiner import refine_transcript
from utils import calculate_tokens_and_cost, OPENAI_MODELS, MODEL_PRICES

def process_audio(
    audio_file,
    openai_api_key,
    elevenlabs_api_key,
    service_choice,
    openai_model,
    language,
    speaker_detection=False,
    creativity=0.5
):
    try:
        if not openai_api_key or len(openai_api_key) < 20:
            return "請輸入有效的 OpenAI API 金鑰", "", "", ""
        
        if service_choice == "ElevenLabs" and (not elevenlabs_api_key or len(elevenlabs_api_key) < 20):
            return "請輸入有效的 ElevenLabs API 金鑰", "", "", ""

        # 音訊轉文字
        if service_choice == "ElevenLabs":
            transcript = transcribe_audio_elevenlabs(
                api_key=elevenlabs_api_key,
                file_path=audio_file,
                language_code=language,
                diarize=speaker_detection
            )
        else:  # Whisper
            transcript = transcribe_audio_whisper(
                audio_file,
                language=language
            )

        # 優化文字
        refined_text = refine_transcript(
            transcript,
            openai_api_key,
            openai_model,
            creativity
        )

        # 計算 token 和費用
        tokens_info, cost_info = calculate_tokens_and_cost(
            transcript,
            refined_text,
            openai_model
        )

        return transcript, refined_text, tokens_info, cost_info

    except Exception as e:
        return f"錯誤：{str(e)}", "", "", ""
    
    finally:
        # 清除敏感資訊
        if 'openai_api_key' in locals():
            del openai_api_key
        if 'elevenlabs_api_key' in locals():
            del elevenlabs_api_key

# 創建 Gradio 介面
with gr.Blocks() as demo:
    gr.Markdown("# 音訊轉文字與優化系統")
    
    with gr.Row():
        with gr.Column():
            audio_input = gr.Audio(
                label="上傳音訊檔案",
                type="filepath"
            )
            
            with gr.Row():
                openai_key = gr.Textbox(
                    label="OpenAI API 金鑰",
                    placeholder="輸入您的 OpenAI API 金鑰",
                    type="password",
                    value="",
                    every=None
                )
                elevenlabs_key = gr.Textbox(
                    label="ElevenLabs API 金鑰",
                    placeholder="輸入您的 ElevenLabs API 金鑰（如果使用 ElevenLabs）",
                    type="password",
                    value="",
                    every=None
                )
            
            service = gr.Radio(
                choices=["Whisper", "ElevenLabs"],
                label="選擇轉錄服務",
                value="Whisper"
            )
            
            model = gr.Dropdown(
                choices=list(OPENAI_MODELS.keys()),
                label="選擇 OpenAI 模型",
                value="gpt-3.5-turbo"
            )
            
            language = gr.Textbox(
                label="語言（可選）",
                placeholder="輸入語言代碼，例如：zh-TW、en、ja",
                value=""
            )
            
            speaker = gr.Checkbox(
                label="啟用說話者辨識（僅限 ElevenLabs）",
                value=False
            )
            
            creativity = gr.Slider(
                minimum=0,
                maximum=1,
                value=0.5,
                label="創意程度"
            )
            
            process_btn = gr.Button("處理音訊")
        
        with gr.Column():
            original_output = gr.Textbox(
                label="原始轉錄文字",
                lines=10
            )
            refined_output = gr.Textbox(
                label="優化後文字",
                lines=10
            )
            token_info = gr.Textbox(
                label="Token 使用資訊",
                lines=3
            )
            cost_info = gr.Textbox(
                label="費用資訊",
                lines=3
            )
    
    gr.Markdown("""
    ### 安全性說明
    - API 金鑰僅在當前處理中使用
    - 不會儲存任何敏感資訊
    - 每次使用需重新輸入 API 金鑰
    """)
    
    # 設定處理函數
    process_btn.click(
        fn=process_audio,
        inputs=[
            audio_input,
            openai_key,
            elevenlabs_key,
            service,
            model,
            language,
            speaker,
            creativity
        ],
        outputs=[
            original_output,
            refined_output,
            token_info,
            cost_info
        ]
    )

# 啟動應用程式
demo.launch() 