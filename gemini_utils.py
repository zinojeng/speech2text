"""
Gemini API utilities
"""

import os
from typing import Optional
from llm_provider_kit import GeminiTextModel
from llm_provider_kit import GEMINI_REFINE_CHEAP

def call_gemini_api(prompt: str, model: str = GEMINI_REFINE_CHEAP, api_key: Optional[str] = None) -> Optional[str]:
    """
    Call Gemini API for text generation
    
    Args:
        prompt: The prompt text
        model: Model name (預設見 model_config.GEMINI_REFINE_CHEAP)
        api_key: API key (if not provided, uses environment variable)
    
    Returns:
        Generated text or None if failed
    """
    try:
        # 金鑰解析交給共用邏輯（GEMINI_API_KEY 或 GOOGLE_API_KEY 皆可）
        
        # Gemini 3.x 不接受 temperature / top_p / top_k（會回 400），
        # 所以這裡只保留 max_output_tokens。
        model_obj = GeminiTextModel(
            model,
            api_key=api_key,
            max_output_tokens=8192,
        )

        response = model_obj.generate_content(prompt)

        return response.text
        
    except Exception as e:
        print(f"Gemini API error: {str(e)}")
        return None