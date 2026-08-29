from openai import OpenAI
from typing import Optional, Dict, Any
import streamlit as st

# 定義可用的 OpenAI 模型
OPENAI_MODELS = {
    "gpt-5.6-terra": "GPT-5.6 Terra（品質優先）",
    "gpt-5.6-luna": "GPT-5.6 Luna（省錢／量大）",
}

def refine_transcript(
    raw_text: str,
    api_key: str,
    model: str = "gpt-5.6-luna",
    temperature: float = 0.5,
    context: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    使用 OpenAI 優化轉錄文字
    
    Args:
        raw_text: 原始文字
        api_key: OpenAI API 金鑰
        model: 使用的模型名稱
        temperature: 創意程度 (0.0-1.0)
        context: 背景資訊
    """
    client = OpenAI(api_key=api_key)
    
    try:
        # 準備 API 參數
        system_prompt = (
            "你是一個專業的文字編輯，負責將文字轉換成正確的繁體中文並修正語法錯誤。"
            "請保持原意，但確保輸出是優美的繁體中文。"
        )
        if context:
            system_prompt += f"\n\n背景資訊：{context}"
        
        params = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": f"請將以下文字轉換成繁體中文，並修正語法和標點符號：\n\n{raw_text}"
                }
            ]
        }
        
        # GPT-5.x 只接受預設的 temperature（送 0.5 會回 400），所以不傳。
        # 參數保留在簽章中以維持呼叫端相容。
        _ = temperature
        
        # 第一步：修正並轉換為繁體中文
        correction_response = client.chat.completions.create(**params)
        
        corrected_text = correction_response.choices[0].message.content
        
        # 第二步：結構化整理（使用相同的參數設定）
        params["messages"] = [
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
        
        summary_response = client.chat.completions.create(**params)
        summary_text = summary_response.choices[0].message.content
        
        # 計算總 token 使用量
        total_input_tokens = (
            correction_response.usage.prompt_tokens +
            summary_response.usage.prompt_tokens
        )
        total_output_tokens = (
            correction_response.usage.completion_tokens +
            summary_response.usage.completion_tokens
        )
        
        return {
            "corrected": corrected_text,
            "summary": summary_text,
            "usage": {
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "model": model
            }
        }
        
    except Exception as e:
        print(f"文字優化失敗：{str(e)}")
        return None


def convert_to_traditional_chinese(
    text: str,
    api_key: str,
    model: str = "gpt-5.6-luna"
) -> str:
    """將文字轉換為繁體中文"""
    client = OpenAI(api_key=api_key)
    
    # GPT-5.x 只接受預設 temperature，送 0.1 會回 400
    response = client.chat.completions.create(
        model=model,
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