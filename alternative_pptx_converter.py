"""
替代的 PPTX 轉換方案，使用 LibreOffice 將 PPTX 轉為圖片再用 Vision API 分析
"""

import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional, List, Tuple
import base64
from openai import OpenAI

logger = logging.getLogger(__name__)

def check_libreoffice_installed() -> bool:
    """檢查系統是否安裝了 LibreOffice"""
    try:
        # 嘗試使用 soffice 命令
        result = subprocess.run(['soffice', '--version'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        try:
            # 備用：嘗試 libreoffice 命令
            result = subprocess.run(['libreoffice', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # 在雲端環境中可能沒有 LibreOffice
            logger.warning("LibreOffice 未安裝，Vision API 功能將不可用")
            return False

def convert_pptx_to_images(pptx_path: str, output_dir: str) -> List[str]:
    """
    使用 LibreOffice 將 PPTX 轉換為圖片
    
    Args:
        pptx_path: PPTX 檔案路徑
        output_dir: 輸出目錄
        
    Returns:
        List[str]: 生成的圖片檔案路徑列表
    """
    try:
        if not check_libreoffice_installed():
            logger.warning("LibreOffice 未安裝，無法轉換 PPTX 為圖片")
            return []
        
        # 使用 LibreOffice 將 PPTX 轉為 PDF
        cmd = [
            'soffice', '--headless', '--convert-to', 'pdf',
            '--outdir', output_dir, pptx_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            logger.error(f"LibreOffice 轉換失敗: {result.stderr}")
            return []
        
        # 找到生成的 PDF 檔案
        pdf_name = Path(pptx_path).stem + '.pdf'
        pdf_path = os.path.join(output_dir, pdf_name)
        
        if not os.path.exists(pdf_path):
            logger.error(f"找不到生成的 PDF 檔案: {pdf_path}")
            return []
        
        # 使用 pdftoppm 將 PDF 轉為圖片 (需要安裝 poppler-utils)
        image_prefix = os.path.join(output_dir, Path(pptx_path).stem)
        cmd = ['pdftoppm', '-png', pdf_path, image_prefix]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            logger.warning(f"pdftoppm 轉換失敗: {result.stderr}")
            # 如果 pdftoppm 失敗，嘗試其他方法或返回空列表
            return []
        
        # 找到生成的圖片檔案
        image_files = []
        for file in os.listdir(output_dir):
            if file.startswith(Path(pptx_path).stem) and file.endswith('.png'):
                image_files.append(os.path.join(output_dir, file))
        
        image_files.sort()  # 確保順序正確
        logger.info(f"成功轉換 PPTX 為 {len(image_files)} 張圖片")
        
        return image_files
        
    except subprocess.TimeoutExpired:
        logger.error("轉換 PPTX 為圖片時逾時")
        return []
    except Exception as e:
        logger.error(f"轉換 PPTX 為圖片時發生錯誤: {e}")
        return []

def analyze_pptx_with_vision(pptx_path: str, api_key: str, model: str = "gpt-4o") -> Tuple[bool, str, dict]:
    """
    使用 Vision API 分析 PPTX 檔案
    
    Args:
        pptx_path: PPTX 檔案路徑
        api_key: OpenAI API Key
        model: 使用的模型
        
    Returns:
        Tuple[bool, str, dict]: (是否成功, Markdown 內容, 資訊)
    """
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # 轉換 PPTX 為圖片
            image_files = convert_pptx_to_images(pptx_path, temp_dir)
            
            if not image_files:
                return False, "", {"error": "無法將 PPTX 轉換為圖片"}
            
            # 使用 OpenAI Vision 分析每張圖片
            try:
                client = OpenAI(api_key=api_key)
            except Exception as e:
                logger.error(f"初始化 OpenAI 客戶端失敗: {e}")
                return False, "", {"error": f"初始化 OpenAI 客戶端失敗: {e}"}
            
            markdown_content = []
            
            for i, image_path in enumerate(image_files, 1):
                try:
                    # 讀取並編碼圖片
                    with open(image_path, "rb") as image_file:
                        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                    
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": f"這是 PowerPoint 投影片第 {i} 頁的圖片。請仔細分析內容，包括：1) 提取所有可見的文字內容 2) 描述圖表、圖像、圖形等視覺元素 3) 解釋投影片的主要訊息和重點。請用繁體中文回應，並以 Markdown 格式整理。"
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=1000,
                        temperature=0.3
                    )
                    
                    result = response.choices[0].message.content
                    
                    if result:
                        markdown_content.append(f"## 投影片 {i}\n\n{result}\n\n---\n")
                        logger.info(f"成功分析投影片 {i}")
                    else:
                        markdown_content.append(f"## 投影片 {i}\n\n*無法分析此投影片內容*\n\n---\n")
                        logger.warning(f"投影片 {i} 分析結果為空")
                        
                except Exception as e:
                    logger.error(f"分析投影片 {i} 時出錯: {e}")
                    markdown_content.append(f"## 投影片 {i}\n\n*分析此投影片時發生錯誤: {str(e)}*\n\n---\n")
            
            final_content = "\n".join(markdown_content)
            
            info = {
                "method": "vision_api",
                "total_slides": len(image_files),
                "content_length": len(final_content)
            }
            
            return True, final_content, info
            
    except Exception as e:
        logger.error(f"使用 Vision API 分析 PPTX 時發生錯誤: {e}")
        return False, "", {"error": str(e)}

def install_dependencies():
    """安裝必要的系統依賴"""
    import platform
    
    system = platform.system().lower()
    
    if system == "darwin":  # macOS
        print("在 macOS 上安裝依賴：")
        print("1. 安裝 LibreOffice: brew install --cask libreoffice")
        print("2. 安裝 poppler: brew install poppler")
    elif system == "linux":
        print("在 Linux 上安裝依賴：")
        print("1. 安裝 LibreOffice: sudo apt install libreoffice")
        print("2. 安裝 poppler: sudo apt install poppler-utils")
    else:
        print(f"不支援的系統: {system}")

if __name__ == "__main__":
    # 檢查系統依賴
    if not check_libreoffice_installed():
        print("LibreOffice 未安裝")
        install_dependencies()
    else:
        print("LibreOffice 已安裝，可以使用 Vision API 分析 PPTX")