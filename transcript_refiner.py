from openai import OpenAI
from typing import Optional, Dict


def refine_transcript(
    raw_text: str,
    api_key: str,
    model: str = "gpt-4o",
    temperature: float = 0.5
) -> Optional[Dict[str, str]]:
    """
    使用 OpenAI 優化轉錄文字
    
    Args:
        raw_text: 原始文字
        api_key: OpenAI API 金鑰
        model: 使用的模型名稱
        temperature: 創意程度 (0.0-1.0)
    """
    client = OpenAI(api_key=api_key)
    
    try:
        # 第一步：修正並轉換為繁體中文
        correction_response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一個專業的文字編輯，負責將文字轉換成正確的繁體中文並修正語法錯誤。"
                        "請保持原意，但確保輸出是優美的繁體中文。"
                    )
                },
                {
                    "role": "user",
                    "content": f"請將以下文字轉換成繁體中文，並修正語法和標點符號：\n\n{raw_text}"
                }
            ]
        )
        
        corrected_text = correction_response.choices[0].message.content
        
        # 第二步：結構化整理
        summary_response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一個專業的文字編輯，負責整理和結構化文字內容。"
                        "請以繁體中文輸出，並確保格式清晰易讀。"
                    )
                },
                {
                    "role": "user",
                    "content": (
                        "請幫我整理以下文字，並提供：\n"
                        "1. 重點摘要\n"
                        "2. 關鍵字列表\n"
                        "3. 主要論點或重要資訊\n\n"
                        f"{corrected_text}"
                    )
                }
            ]
        )
        
        summary_text = summary_response.choices[0].message.content
        
        return {
            "corrected": corrected_text,
            "summary": summary_text
        }
        
    except Exception as e:
        print(f"文字優化失敗：{str(e)}")
        return None


def convert_to_traditional_chinese(
    text: str,
    api_key: str,
    model: str = "o3-mini"
) -> str:
    """將文字轉換為繁體中文"""
    client = OpenAI(api_key=api_key)
    
    response = client.chat.completions.create(
        model=model,
        temperature=0.1,  # 使用較低的溫度以確保準確轉換
        messages=[
            {
                "role": "system",
                "content": "你是一個專業的繁簡轉換工具，請將輸入文字轉換成繁體中文，保持原意不變。"
            },
            {
                "role": "user",
                "content": text
            }
        ]
    )
    
    return response.choices[0].message.content

# Example usage with elevenlabs_stt:
# raw_transcript = transcribe_audio(...)['text']
# refined = refine_transcript(
#     raw_text=raw_transcript,
#     api_key="OPENAI_API_KEY",
#     temperature=0.5
# ) 