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
import subprocess
import sys
import base64
from io import BytesIO

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("markitdown-utils")


def reinstall_magika():
    """重新安裝 magika 套件以修復損壞的模型檔案"""
    try:
        logger.info("嘗試重新安裝 magika 套件...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "uninstall", "magika", "-y"
        ])
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "magika"
        ])
        logger.info("magika 套件重新安裝完成")
        return True
    except Exception as e:
        logger.error(f"重新安裝 magika 失敗: {e}")
        return False


def convert_file_to_markdown(input_path: str,
                             use_llm: bool = False,
                             api_key: Optional[str] = None,
                             model: str = "gpt-4o") -> Tuple[bool, str,
                                                             Dict[str, Any]]:
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
        
        # 檢查是否為 PPTX 檔案，如果啟用了 Vision API 則使用替代方法
        if str(input_path).lower().endswith('.pptx') and use_llm and api_key:
            logger.info("偵測到 PPTX 檔案且啟用 Vision API，使用 Vision API 分析...")
            
            try:
                from alternative_pptx_converter import analyze_pptx_with_vision
                logger.info("嘗試使用 Vision API 分析 PPTX...")
                
                success, result_text, vision_info = analyze_pptx_with_vision(
                    str(input_path), api_key, model
                )
                
                if success and result_text:
                    conversion_info = {
                        "method": "vision_api",
                        "file_name": input_path.name,
                        "file_size": input_path.stat().st_size,
                        **vision_info
                    }
                    logger.info(f"成功使用 Vision API 分析 PPTX，內容長度: {len(result_text)}")
                    return True, result_text, conversion_info
                else:
                    logger.warning("Vision API 分析失敗，回退到 MarkItDown 方法")
                    
            except ImportError:
                logger.warning("找不到 alternative_pptx_converter 模組，使用 MarkItDown 方法")
            except Exception as e:
                logger.warning(f"Vision API 分析出錯: {e}，使用 MarkItDown 方法")
        
        # 使用原始 MarkItDown 進行轉換（適用於所有檔案類型）
        
        # 建立 MarkItDown 實例
        # 對於 PPTX 檔案，啟用所有插件以獲得最佳效果
        md_kwargs = {}
        if str(input_path).lower().endswith('.pptx'):
            md_kwargs["enable_plugins"] = True
        
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

        # 嘗試建立 MarkItDown 實例，如果失敗則嘗試修復
        max_retries = 2
        md = None
        
        for attempt in range(max_retries):
            try:
                md = MarkItDown(**md_kwargs)
                break
            except Exception as e:
                error_msg = str(e)
                logger.error(f"建立 MarkItDown 實例失敗 "
                           f"(嘗試 {attempt + 1}/{max_retries}): {error_msg}")
                
                # 檢查是否為 magika 相關錯誤
                if ("magika" in error_msg.lower() and 
                    "json" in error_msg.lower()):
                    if attempt == 0:  # 第一次嘗試修復
                        logger.info("偵測到 magika 套件問題，嘗試修復...")
                        if reinstall_magika():
                            continue
                    
                    # 如果修復失敗或是第二次嘗試，使用不依賴 magika 的方式
                    logger.warning("使用簡化模式，不使用檔案類型偵測")
                    try:
                        # 嘗試不使用 magika 的方式
                        md_kwargs_simple = {}
                        if llm_client:
                            md_kwargs_simple["llm_client"] = llm_client
                            md_kwargs_simple["llm_model"] = model
                        md = MarkItDown(**md_kwargs_simple)
                        break
                    except Exception as e2:
                        logger.error(f"簡化模式也失敗: {e2}")
                        if attempt == max_retries - 1:
                            raise e
                else:
                    if attempt == max_retries - 1:
                        raise e
        
        if md is None:
            raise Exception("無法建立 MarkItDown 實例")
        
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
            
            # 對於 PPTX 檔案，如果只有圖片引用而沒有實際文字內容，提供更好的說明
            if str(input_path).lower().endswith('.pptx'):
                text_content = result.text_content
                
                # 檢查是否主要是圖片內容
                lines = text_content.split('\n')
                image_lines = [line for line in lines if line.strip().startswith('![') or 'Picture' in line]
                text_lines = [line for line in lines if line.strip() and not line.strip().startswith('<!--') and not line.strip().startswith('![')]
                
                if len(image_lines) > len(text_lines) and len(text_lines) < 5:
                    # 主要是圖片內容，增加說明
                    slide_count = len([line for line in lines if 'Slide number:' in line])
                    enhanced_content = f"""# PPTX 檔案內容

**檔案說明：** 此 PowerPoint 檔案主要包含圖片內容。

**投影片數量：** {slide_count} 張

**內容類型：** 圖片為主的簡報

## 原始 MarkItDown 輸出

{text_content}

---

**提示：** 如需分析圖片內容，請啟用「🔍 Vision API 分析」選項。
"""
                    conversion_info["content_length"] = len(enhanced_content)
                    return True, enhanced_content, conversion_info
            
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

def convert_images_to_markdown(
    image_paths: List[str],
    output_file: str,
    title: str = "圖片集合",
    use_llm: bool = True,
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini"
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    將多個圖片檔案轉換為單一 Markdown 檔案
    
    Args:
        image_paths (List[str]): 圖片檔案路徑列表
        output_file (str): 輸出 Markdown 檔案路徑
        title (str): Markdown 文件標題
        use_llm (bool): 是否使用 LLM 處理圖片
        api_key (Optional[str]): OpenAI API Key
        model (str): 使用的 OpenAI 模型
        
    Returns:
        Tuple[bool, str, Dict]: (是否成功, 輸出檔案路徑, 處理資訊)
    """
    try:
        logger.info(f"將 {len(image_paths)} 張圖片轉換為 Markdown")
        
        # 檢查圖片列表
        if not image_paths:
            logger.error("圖片列表為空")
            return False, "", {"error": "圖片列表為空"}
            
        # 過濾有效的圖片檔案
        valid_images = []
        for img_path in image_paths:
            if os.path.exists(img_path):
                valid_images.append(img_path)
            else:
                logger.warning(f"找不到圖片: {img_path}")
                
        if not valid_images:
            logger.error("沒有有效的圖片檔案")
            return False, "", {"error": "沒有有效的圖片檔案"}
        
        # 生成初始 Markdown 文本
        md_content = f"# {title}\n\n"
        
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
                use_llm = False
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
                    use_llm = False
                except Exception as e:
                    logger.error(f"初始化 OpenAI client 時發生錯誤: {e}")
                    llm_info["status"] = f"初始化錯誤: {str(e)}"
                    use_llm = False
                    
        md = MarkItDown(**md_kwargs)
        
        # 處理每個圖片
        successful_conversions = 0
        for img_path in valid_images:
            try:
                img_relpath = os.path.basename(img_path)
                logger.info(f"處理圖片: {img_relpath}")
                
                # 轉換圖片
                result = md.convert(img_path)
                
                if result and result.text_content:
                    md_content += f"## 圖片：{img_relpath}\n\n"
                    md_content += result.text_content + "\n\n"
                    successful_conversions += 1
                else:
                    logger.warning(f"無法轉換圖片: {img_relpath}")
                    # 添加簡單的圖片標記
                    md_content += f"## 圖片：{img_relpath}\n\n"
                    md_content += f"![{img_relpath}]({img_path})\n\n"
            except Exception as e:
                logger.warning(f"處理圖片 {img_path} 時出錯: {e}")
                # 添加簡單的圖片標記
                md_content += f"## 圖片：{img_relpath}\n\n"
                md_content += f"![{img_relpath}]({img_path})\n\n"
                
        # 寫入輸出檔案
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(md_content)
            logger.info(f"已將 {successful_conversions} 張圖片轉換並寫入 {output_file}")
            
            # 嘗試使用 image_analyzer 增強圖片描述
            if use_llm and os.path.exists(output_file):
                try:
                    from image_analyzer import enhance_markdown_with_image_analysis
                    
                    # 讀取剛生成的 Markdown 檔案
                    with open(output_file, 'r', encoding='utf-8') as f:
                        original_md = f.read()
                    
                    # 增強 Markdown 內容
                    enhanced_md, stats = enhance_markdown_with_image_analysis(
                        markdown_text=original_md,
                        base_dir=os.path.dirname(output_file),
                        api_key=current_api_key,
                        model=model
                    )
                    
                    # 寫入增強後的內容
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(enhanced_md)
                    
                    logger.info(f"已增強 {stats['images_processed']} 張圖片的描述")
                    
                except ImportError:
                    logger.warning("找不到 image_analyzer 模組，無法增強圖片描述")
                except Exception as e:
                    logger.warning(f"增強圖片描述時出錯: {e}")
            
            result_info = {
                "success": True,
                "total_images": len(valid_images),
                "converted_images": successful_conversions,
                "output_file": output_file,
                "llm": llm_info
            }
            
            return True, output_file, result_info
            
        except Exception as e:
            logger.error(f"寫入輸出檔案時發生錯誤: {e}")
            return False, "", {"error": f"寫入輸出檔案時發生錯誤: {e}"}
        
    except Exception as e:
        logger.error(f"轉換圖片集合時發生錯誤: {e}")
        import traceback
        error_details = traceback.format_exc()
        logger.error(error_details)
        return False, "", {"error": str(e), "details": error_details}


# Vision API 相關函數已移至 alternative_pptx_converter.py 