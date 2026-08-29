"""
GPT-4o Speech-to-Text 模組
使用 OpenAI GPT-4o 語音轉文字模型
"""

from openai import OpenAI

def transcribe_audio_gpt4o(file_path, api_key, model="gpt-transcribe", language=None, output_format="text"):
    """
    使用 GPT-4o 模型轉錄音頻
    
    Args:
        file_path: 音頻檔案路徑
        api_key: OpenAI API 金鑰
        model: 模型名稱 (gpt-transcribe 或 gemini-3.5-transcribe)
        language: 語言代碼 (如 'zh', 'en', 'ja' 等)
        output_format: 輸出格式 ('text', 'srt', 'markdown')
    
    Returns:
        轉錄結果文字
    """
    try:
        client = OpenAI(api_key=api_key)
        
        # OpenAI 的轉錄模型只支援 json / text，沒有可產生 srt 的模型。
        if output_format == "srt":
            raise ValueError(
                "OpenAI 轉錄模型不回傳時間戳，無法產生 SRT。"
                "請改用 gemini-3.5-transcribe（詞級時間戳＋講者標記）。"
            )

        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                language=language,
                response_format="text"
            )

        # response_format="text" 時 SDK 直接回傳字串，沒有 .text 屬性
        text = transcript if isinstance(transcript, str) else getattr(transcript, "text", str(transcript))

        if output_format == "markdown":
            return f"# 語音轉錄結果\n\n{text}\n"
        return text
        
    except Exception as e:
        raise Exception(f"GPT-4o 轉錄失敗: {str(e)}")