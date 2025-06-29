"""
GPT-4o Speech-to-Text 模組
使用 OpenAI GPT-4o 語音轉文字模型
"""

from openai import OpenAI

def transcribe_audio_gpt4o(file_path, api_key, model="gpt-4o-transcribe", language=None, output_format="text"):
    """
    使用 GPT-4o 模型轉錄音頻
    
    Args:
        file_path: 音頻檔案路徑
        api_key: OpenAI API 金鑰
        model: 模型名稱 (gpt-4o-transcribe 或 gpt-4o-mini-transcribe)
        language: 語言代碼 (如 'zh', 'en', 'ja' 等)
        output_format: 輸出格式 ('text', 'srt', 'markdown')
    
    Returns:
        轉錄結果文字
    """
    try:
        client = OpenAI(api_key=api_key)
        
        # 根據格式設定 response_format
        response_format = "text"
        if output_format == "srt":
            response_format = "srt"
        elif output_format == "markdown":
            response_format = "text"  # 先取得文字再轉換為 markdown
        
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                language=language,
                response_format=response_format
            )
        
        if output_format == "markdown":
            # 將文字轉換為 markdown 格式
            result = f"# 語音轉錄結果\n\n{transcript.text}\n"
        elif output_format == "srt":
            # SRT 格式直接回傳字串
            result = transcript
        else:
            # 純文字格式
            result = transcript.text
            
        return result
        
    except Exception as e:
        raise Exception(f"GPT-4o 轉錄失敗: {str(e)}")