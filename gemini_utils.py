"""
Gemini API utilities
"""

import os
from typing import Optional

try:
    import google.generativeai as genai
except ImportError:
    genai = None

def call_gemini_api(prompt: str, model: str = "gemini-2.0-flash-exp", api_key: Optional[str] = None) -> Optional[str]:
    """
    Call Gemini API for text generation
    
    Args:
        prompt: The prompt text
        model: Model name (default: gemini-2.0-flash-exp)
        api_key: API key (if not provided, uses environment variable)
    
    Returns:
        Generated text or None if failed
    """
    try:
        if genai is None:
            print("Google Generative AI not installed. Skipping summary generation.")
            return None
            
        # Use provided API key or get from environment
        if not api_key:
            api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            raise ValueError("No Google API key provided")
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Create the model
        generation_config = {
            "temperature": 0.5,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
        
        model_obj = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
        )
        
        # Generate content
        response = model_obj.generate_content(prompt)
        
        return response.text
        
    except Exception as e:
        print(f"Gemini API error: {str(e)}")
        return None