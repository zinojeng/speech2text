# 圖片解析模組 - 使用 OpenAI 模型解析圖片內容
import os
import logging
import base64
from PIL import Image
import io
from openai import OpenAI
import re
from typing import List, Dict, Tuple, Optional, Union

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def encode_image_to_base64(image_path: str) -> Optional[str]:
    """
    將圖片編碼為 base64 字串，以便傳送給 OpenAI API
    
    Args:
        image_path (str): 圖片檔案路徑
        
    Returns:
        Optional[str]: base64 編碼的圖片字串，如果失敗則返回 None
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"圖片編碼失敗: {str(e)}")
        return None

def analyze_image(
    image_path: str, 
    api_key: str, 
    model: str = "o4-mini"
) -> Dict:
    """
    使用 OpenAI API 解析圖片內容
    
    Args:
        image_path (str): 圖片檔案路徑
        api_key (str): OpenAI API 金鑰
        model (str, optional): 使用的模型名稱. 預設為 "o4-mini"
        
    Returns:
        Dict: 解析結果，包含描述和相關資訊
    """
    try:
        # 檢查檔案是否存在
        if not os.path.exists(image_path):
            return {"success": False, "error": f"圖片檔案不存在: {image_path}"}
        
        # 編碼圖片
        base64_image = encode_image_to_base64(image_path)
        if not base64_image:
            return {"success": False, "error": "圖片編碼失敗"}
        
        # 初始化 OpenAI 客戶端
        client = OpenAI(api_key=api_key)
        
        # 準備提示詞
        prompt = """
        請以繁體中文詳細分析這張圖片，並提供以下資訊：
        
        1. 圖片類型（照片、圖表、示意圖等）
        2. 主要內容描述
        3. 如果是數據圖表，請詳細描述圖表類型和呈現的數據趨勢
        4. 如果有文字內容，請列出重要文字
        5. 對於醫學或科學圖片，請提供專業的解釋
        
        請以結構化的方式回答，使用繁體中文。
        """
        
        # 呼叫 OpenAI API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一個專業的圖片分析助手，專長於醫學和科學圖片的分析。"},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}
            ],
            max_completion_tokens=500
        )
        
        # 處理回應
        description = response.choices[0].message.content
        tokens_used = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        
        return {
            "success": True,
            "description": description,
            "tokens": tokens_used
        }
    
    except Exception as e:
        logger.error(f"圖片解析失敗: {str(e)}")
        return {"success": False, "error": str(e)}

def enhance_markdown_with_image_analysis(
    markdown_text: str, 
    base_dir: str, 
    api_key: str,
    model: str = "o4-mini"
) -> Tuple[str, Dict]:
    """
    增強 Markdown 文本，為圖片添加解析描述
    
    Args:
        markdown_text (str): 原始 Markdown 文本
        base_dir (str): 圖片基礎目錄路徑
        api_key (str): OpenAI API 金鑰
        model (str, optional): 使用的模型名稱. 預設為 "o4-mini"
        
    Returns:
        Tuple[str, Dict]: 增強後的 Markdown 文本和解析統計資訊
    """
    # 初始化統計資訊
    stats = {
        "images_processed": 0,
        "images_analyzed": 0,
        "images_failed": 0,
        "total_tokens": 0
    }
    
    # 查找所有圖片標記
    img_pattern = r"!\[(.*?)\]\((.*?)\)"
    
    def replace_image(match):
        alt_text = match.group(1)
        img_path = match.group(2)
        stats["images_processed"] += 1
        
        # 跳過已經有詳細描述的圖片
        if len(alt_text) > 20:  # 假設詳細描述至少有20個字元
            return match.group(0)
            
        # 構建完整圖片路徑
        full_img_path = os.path.join(base_dir, img_path)
        
        # 檢查文件是否存在
        if not os.path.exists(full_img_path):
            logger.warning(f"圖片不存在: {full_img_path}")
            stats["images_failed"] += 1
            return match.group(0)
        
        # 分析圖片
        analysis = analyze_image(full_img_path, api_key, model)
        
        if analysis["success"]:
            stats["images_analyzed"] += 1
            stats["total_tokens"] += analysis["tokens"]["total_tokens"]
            
            # 提取簡短描述作為 alt 文本
            short_desc = analysis["description"].split("\n")[0]
            if len(short_desc) > 100:
                short_desc = short_desc[:97] + "..."
                
            # 創建新的圖片標記，帶有描述
            new_img = f'![{short_desc}]({img_path})\n\n<details>\n<summary>圖片詳細描述</summary>\n\n{analysis["description"]}\n</details>'
            return new_img
        else:
            stats["images_failed"] += 1
            return match.group(0)
    
    # 替換圖片標記
    enhanced_markdown = re.sub(img_pattern, replace_image, markdown_text)
    
    return enhanced_markdown, stats

def enhance_slides(
    markdown_text: str,
    api_key: str,
    model: str = "o4-mini"
) -> Dict:
    """
    增強幻燈片內容，識別幻燈片中的圖片並添加描述
    
    Args:
        markdown_text (str): 幻燈片的 Markdown 文本
        api_key (str): OpenAI API 金鑰
        model (str, optional): 使用的模型名稱. 預設為 "o4-mini"
        
    Returns:
        Dict: 增強結果，包含增強後的文本和統計資訊
    """
    # 將幻燈片文本按幻燈片分隔
    slide_pattern = r"<!-- Slide number: \d+ -->"
    slides = re.split(slide_pattern, markdown_text)
    
    # 如果沒有符合的分隔符，則將整個文本作為一個幻燈片處理
    if len(slides) == 1 and slides[0] == markdown_text:
        slides = [markdown_text]
    
    # 初始化統計資訊
    stats = {
        "slides_processed": len(slides),
        "images_processed": 0,
        "images_analyzed": 0,
        "images_failed": 0,
        "total_tokens": 0
    }
    
    # 處理每個幻燈片
    enhanced_slides = []
    for i, slide in enumerate(slides):
        if not slide.strip():
            enhanced_slides.append(slide)
            continue
            
        # 識別幻燈片中的圖片
        logger.info(f"處理幻燈片 {i+1}/{len(slides)}")
        
        # 使用當前目錄作為基礎目錄
        base_dir = "."
        enhanced_slide, slide_stats = enhance_markdown_with_image_analysis(
            slide, base_dir, api_key, model
        )
        
        # 更新統計資訊
        stats["images_processed"] += slide_stats["images_processed"]
        stats["images_analyzed"] += slide_stats["images_analyzed"]
        stats["images_failed"] += slide_stats["images_failed"]
        stats["total_tokens"] += slide_stats["total_tokens"]
        
        # 添加幻燈片編號
        if i > 0:  # 第一個可能是空白或前言
            enhanced_slide = f"<!-- Slide number: {i} -->\n{enhanced_slide}"
            
        enhanced_slides.append(enhanced_slide)
    
    # 合併增強後的幻燈片
    enhanced_text = "".join(enhanced_slides)
    
    return {
        "enhanced_text": enhanced_text,
        "stats": stats
    }

def batch_process_images(
    image_paths: List[str], 
    api_key: str, 
    model: str = "o4-mini"
) -> Dict:
    """
    批次處理多張圖片
    
    Args:
        image_paths (List[str]): 圖片路徑列表
        api_key (str): OpenAI API 金鑰
        model (str, optional): 使用的模型名稱. 預設為 "o4-mini"
        
    Returns:
        Dict: 批次處理結果
    """
    results = {}
    total_tokens = 0
    
    for img_path in image_paths:
        logger.info(f"處理圖片: {img_path}")
        result = analyze_image(img_path, api_key, model)
        
        if result["success"]:
            results[img_path] = result["description"]
            total_tokens += result["tokens"]["total_tokens"]
        else:
            results[img_path] = f"分析失敗: {result.get('error', '未知錯誤')}"
    
    return {
        "results": results,
        "total_tokens": total_tokens,
        "images_processed": len(image_paths)
    }

# 測試函數
def test_image_analyzer(image_path: str, api_key: str):
    """
    測試圖片解析功能
    
    Args:
        image_path (str): 測試圖片路徑
        api_key (str): OpenAI API 金鑰
    """
    print(f"測試圖片解析: {image_path}")
    result = analyze_image(image_path, api_key)
    
    if result["success"]:
        print("\n===== 圖片解析結果 =====")
        print(result["description"])
        print(f"\n使用 tokens: {result['tokens']['total_tokens']}")
    else:
        print(f"解析失敗: {result.get('error', '未知錯誤')}")

if __name__ == "__main__":
    # 這裡可以放置測試代碼
    pass 