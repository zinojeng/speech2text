"""
提供 MarkItDown 相關功能的實用函數
"""

import os
import tempfile
from pathlib import Path
import logging
from markitdown import MarkItDown
from openai import OpenAI, AuthenticationError
from typing import Dict, Any, Optional, List, Tuple

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("markitdown-utils")

def convert_file_to_markdown(input_path: str, 
                            use_llm: bool = False, 
                            api_key: Optional[str] = None, 
                            model: str = "gpt-4o") -> Tuple[bool, str, Dict[str, Any]]:
    """
    將檔案轉換為 Markdown 格式，可選用 LLM 處理圖片
    
    Args:
        input_path (str): 輸入檔案路徑
        use_llm (bool): 是否使用 LLM 處理圖片
        api_key (str, optional): OpenAI API Key
        model (str): OpenAI 模型名稱
    
    Returns:
        Tuple[bool, str, Dict]: (是否成功, Markdown 文字, 轉換資訊)
    """
    try:
        input_path = Path(input_path).resolve()
        
        if not input_path.exists():
            logger.error(f"找不到檔案: {input_path}")
            return False, "", {"error": f"找不到檔案: {input_path}"}
            
        logger.info(f"正在轉換: {input_path}")
        
        # 建立 MarkItDown 實例
        md_kwargs = {"enable_plugins": True}
        llm_client = None
        llm_info = {}
        
        if use_llm:
            logger.info(f"嘗試啟用 LLM ({model}) 進行處理...")
            current_api_key = api_key or os.environ.get("OPENAI_API_KEY")
            if not current_api_key:
                logger.warning("未提供 OpenAI API Key，無法使用 LLM 處理圖片。")
                llm_info["status"] = "未提供 API Key"
            else:
                try:
                    llm_client = OpenAI(api_key=current_api_key)
                    # 執行一個簡單的測試呼叫來驗證金鑰
                    llm_client.models.list() 
                    logger.info("OpenAI API Key 驗證成功。")
                    md_kwargs["llm_client"] = llm_client
                    md_kwargs["llm_model"] = model
                    llm_info["status"] = "啟用成功"
                    llm_info["model"] = model
                except AuthenticationError:
                    logger.error("OpenAI API Key 無效或錯誤，無法使用 LLM。")
                    llm_info["status"] = "API Key 無效"
                except Exception as e:
                    logger.error(f"初始化 OpenAI client 時發生錯誤: {e}")
                    llm_info["status"] = f"初始化錯誤: {str(e)}"

        md = MarkItDown(**md_kwargs)
        
        # 轉換檔案
        result = md.convert(str(input_path))
        
        # 準備轉換資訊
        conversion_info = {
            "llm": llm_info,
            "file_name": input_path.name,
            "file_size": input_path.stat().st_size
        }
        
        if result and result.text_content:
            # 檢查 converter_used 屬性是否存在
            if hasattr(result, 'converter_used'):
                conversion_info["converter"] = result.converter_used
            conversion_info["content_length"] = len(result.text_content)
            
            return True, result.text_content, conversion_info
        else:
            logger.error("轉換失敗，未獲得有效結果")
            return False, "", {"error": "轉換失敗，未獲得有效結果"}
            
    except Exception as e:
        logger.error(f"轉換過程中發生錯誤: {e}")
        import traceback
        error_details = traceback.format_exc()
        logger.error(error_details)
        return False, "", {"error": str(e), "details": error_details}

def convert_url_to_markdown(url: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    將 URL 轉換為 Markdown 格式
    
    Args:
        url (str): 輸入 URL
    
    Returns:
        Tuple[bool, str, Dict]: (是否成功, Markdown 文字, 轉換資訊)
    """
    try:
        logger.info(f"正在轉換 URL: {url}")
        
        # 建立 MarkItDown 實例
        md = MarkItDown(enable_plugins=True)
        
        # 轉換 URL
        result = md.convert(url)
        
        # 準備轉換資訊
        conversion_info = {
            "url": url
        }
        
        if result and result.text_content:
            # 檢查 converter_used 屬性是否存在
            if hasattr(result, 'converter_used'):
                conversion_info["converter"] = result.converter_used
            conversion_info["content_length"] = len(result.text_content)
            
            return True, result.text_content, conversion_info
        else:
            logger.error("轉換失敗，未獲得有效結果")
            return False, "", {"error": "轉換失敗，未獲得有效結果"}
            
    except Exception as e:
        logger.error(f"轉換過程中發生錯誤: {e}")
        import traceback
        error_details = traceback.format_exc()
        logger.error(error_details)
        return False, "", {"error": str(e), "details": error_details}

def extract_keywords(markdown_text: str, api_key: str, model: str = "gpt-4o-mini", count: int = 10) -> List[str]:
    """
    從 Markdown 文字中提取關鍵詞
    
    Args:
        markdown_text (str): Markdown 格式的文字
        api_key (str): OpenAI API Key
        model (str): 模型名稱
        count (int): 要提取的關鍵詞數量
    
    Returns:
        List[str]: 關鍵詞列表
    """
    try:
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system", 
                    "content": f"你是一個專業的關鍵詞提取工具。請從提供的文本中提取最重要的 {count} 個關鍵詞或短語，這些詞語能夠反映文本的核心主題、概念和專業術語。關鍵詞應以繁體中文提供，並按重要性排序。請僅返回關鍵詞列表，一行一個關鍵詞，不要加編號或任何其他說明。"
                },
                {
                    "role": "user",
                    "content": markdown_text
                }
            ],
            temperature=0.3
        )
        
        keywords_text = response.choices[0].message.content
        
        # 處理回應，將文字分割成列表
        keywords = [kw.strip() for kw in keywords_text.strip().split('\n') if kw.strip()]
        
        return keywords
        
    except Exception as e:
        logger.error(f"提取關鍵詞失敗: {e}")
        return []

def save_uploaded_file(uploaded_file) -> Tuple[bool, str]:
    """
    將上傳的檔案保存到臨時目錄
    
    Args:
        uploaded_file: Streamlit 上傳的檔案物件
        
    Returns:
        Tuple[bool, str]: (是否成功, 臨時檔案路徑)
    """
    try:
        # 取得檔案後綴
        file_extension = os.path.splitext(uploaded_file.name)[1]
        
        # 創建臨時檔案
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp:
            temp.write(uploaded_file.getbuffer())
            return True, temp.name
    except Exception as e:
        logger.error(f"保存上傳檔案失敗: {e}")
        return False, str(e) 