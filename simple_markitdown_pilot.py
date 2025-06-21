#!/usr/bin/env python
"""
Simple Markitdown Pilot - 將檔案或 URL 轉換為 Markdown
使用 Microsoft 的 markitdown 套件，可選用 OpenAI 處理圖片描述
"""

import argparse
import sys
import os
from pathlib import Path
import logging
from markitdown import MarkItDown
from openai import OpenAI, AuthenticationError

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("markitdown-pilot")

def convert_file_to_markdown(input_path, output_path=None, verbose=False, use_llm=False, api_key=None, model="gpt-4o"):
    """
    將檔案轉換為 Markdown 格式，可選用 LLM 處理圖片
    
    Args:
        input_path (str): 輸入檔案路徑
        output_path (str, optional): 輸出檔案路徑，若未指定則輸出到標準輸出
        verbose (bool): 是否顯示詳細訊息
        use_llm (bool): 是否使用 LLM 處理圖片
        api_key (str, optional): OpenAI API Key
        model (str): OpenAI 模型名稱
    
    Returns:
        bool: 是否成功轉換
    """
    try:
        input_path = Path(input_path).resolve()
        
        if not input_path.exists():
            logger.error(f"找不到檔案: {input_path}")
            return False
            
        logger.info(f"正在轉換: {input_path}")
        
        # 建立 MarkItDown 實例
        md_kwargs = {"enable_plugins": True}
        llm_client = None
        
        if use_llm:
            logger.info(f"嘗試啟用 LLM ({model}) 進行處理...")
            current_api_key = api_key or os.environ.get("OPENAI_API_KEY")
            if not current_api_key:
                logger.warning("未提供 OpenAI API Key，無法使用 LLM 處理圖片。")
            else:
                try:
                    llm_client = OpenAI(api_key=current_api_key)
                    # 執行一個簡單的測試呼叫來驗證金鑰
                    llm_client.models.list() 
                    logger.info("OpenAI API Key 驗證成功。")
                    md_kwargs["llm_client"] = llm_client
                    md_kwargs["llm_model"] = model
                except AuthenticationError:
                    logger.error("OpenAI API Key 無效或錯誤，無法使用 LLM。")
                except Exception as e:
                    logger.error(f"初始化 OpenAI client 時發生錯誤: {e}")

        md = MarkItDown(**md_kwargs)
        
        # 轉換檔案
        result = md.convert(str(input_path))
        
        if result and result.text_content:
            # 如果有指定輸出檔案，寫入檔案
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result.text_content)
                logger.info(f"已將轉換結果儲存至: {output_path}")
            else:
                # 輸出到標準輸出
                print(result.text_content)
                
            if verbose:
                # 檢查 converter_used 屬性是否存在
                if hasattr(result, 'converter_used'):
                    logger.info(f"使用的轉換器: {result.converter_used}")
                logger.info(f"內容長度: {len(result.text_content)} 字符")
                
            return True
        else:
            logger.error("轉換失敗，未獲得有效結果")
            return False
            
    except Exception as e:
        logger.error(f"轉換過程中發生錯誤: {e}")
        if verbose:
            import traceback
            logger.error(traceback.format_exc())
        return False

def convert_url_to_markdown(url, output_path=None, verbose=False):
    """
    將 URL 轉換為 Markdown 格式
    
    Args:
        url (str): 輸入 URL
        output_path (str, optional): 輸出檔案路徑，若未指定則輸出到標準輸出
        verbose (bool): 是否顯示詳細訊息
    
    Returns:
        bool: 是否成功轉換
    """
    try:
        logger.info(f"正在轉換 URL: {url}")
        
        # 建立 MarkItDown 實例
        md = MarkItDown(enable_plugins=True)
        
        # 轉換 URL
        result = md.convert(url)
        
        if result and result.text_content:
            # 如果有指定輸出檔案，寫入檔案
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result.text_content)
                logger.info(f"已將轉換結果儲存至: {output_path}")
            else:
                # 輸出到標準輸出
                print(result.text_content)
                
            if verbose:
                # 檢查 converter_used 屬性是否存在
                if hasattr(result, 'converter_used'):
                    logger.info(f"使用的轉換器: {result.converter_used}")
                logger.info(f"內容長度: {len(result.text_content)} 字符")
                
            return True
        else:
            logger.error("轉換失敗，未獲得有效結果")
            return False
            
    except Exception as e:
        logger.error(f"轉換過程中發生錯誤: {e}")
        if verbose:
            import traceback
            logger.error(traceback.format_exc())
        return False

def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description="MarkItDown Pilot - 將檔案或網址轉換為 Markdown，可選用 LLM 處理圖片"
    )
    parser.add_argument(
        "input",
        help="要轉換的檔案路徑或 URL"
    )
    parser.add_argument(
        "-o", "--output",
        help="輸出檔案路徑 (不指定則輸出到標準輸出)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="顯示詳細訊息"
    )
    parser.add_argument(
        "--is-url",
        action="store_true",
        help="強制將輸入視為 URL"
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="啟用 LLM (OpenAI) 處理圖片描述"
    )
    parser.add_argument(
        "--api-key",
        help="OpenAI API Key (優先於環境變數 OPENAI_API_KEY)"
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="OpenAI 模型名稱 (默認: gpt-4o)"
    )
    
    args = parser.parse_args()
    
    # 判斷輸入是 URL 還是檔案路徑
    is_url = args.is_url or args.input.startswith(('http://', 'https://'))
    
    if is_url:
        success = convert_url_to_markdown(args.input, args.output, args.verbose)
    else:
        success = convert_file_to_markdown(
            args.input, 
            args.output, 
            args.verbose,
            args.use_llm,
            args.api_key,
            args.model
        )
    
    # 返回對應的退出碼
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 