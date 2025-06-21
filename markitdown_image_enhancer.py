#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MarkItDown 圖片增強工具

此工具用於增強 MarkItDown 功能，為 Markdown 文件中的圖片添加 AI 生成的解析描述。
它會尋找 Markdown 文件中所有圖片標記，使用 OpenAI API 解析圖片內容，
然後在 Markdown 中為圖片添加詳細描述。
"""

import os
import sys
import argparse
import logging
import json
from typing import Dict, Optional, Tuple
import time
from pathlib import Path

# 導入 image_analyzer 模組
try:
    from image_analyzer import enhance_markdown_with_image_analysis
except ImportError:
    print("錯誤：找不到 image_analyzer 模組，請確保該檔案在正確路徑")
    sys.exit(1)

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_markdown_file(
    input_file: str,
    output_file: Optional[str] = None,
    api_key: Optional[str] = None,
    model: str = "o4-mini",
    image_base_dir: Optional[str] = None
) -> Dict:
    """
    處理 Markdown 檔案，為其中的圖片添加 AI 解析描述
    
    Args:
        input_file (str): 輸入 Markdown 檔案路徑
        output_file (Optional[str]): 輸出 Markdown 檔案路徑，如果為 None 則替換原檔案
        api_key (Optional[str]): OpenAI API 金鑰，如果為 None 則嘗試從環境變數獲取
        model (str): 使用的 OpenAI 模型，預設為 "o4-mini"
        image_base_dir (Optional[str]): 圖片基礎目錄，如果為 None 則使用輸入檔案的目錄
        
    Returns:
        Dict: 處理結果統計資訊
    """
    logger.info(f"開始處理 Markdown 檔案: {input_file}")
    
    # 檢查檔案是否存在
    if not os.path.exists(input_file):
        logger.error(f"檔案不存在: {input_file}")
        return {"success": False, "error": f"檔案不存在: {input_file}"}
    
    # 取得 API 金鑰
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("找不到 OpenAI API 金鑰")
            return {"success": False, "error": "找不到 OpenAI API 金鑰"}
    
    # 確定圖片基礎目錄
    if not image_base_dir:
        image_base_dir = os.path.dirname(os.path.abspath(input_file))
    
    # 確定輸出檔案路徑
    if not output_file:
        input_path = Path(input_file)
        output_file = str(input_path.parent / 
                         f"{input_path.stem}_enhanced{input_path.suffix}")
    
    try:
        # 讀取輸入檔案
        with open(input_file, 'r', encoding='utf-8') as f:
            markdown_text = f.read()
        
        # 增強 Markdown
        logger.info("開始增強 Markdown 內容，為圖片添加描述...")
        enhanced_markdown, stats = enhance_markdown_with_image_analysis(
            markdown_text=markdown_text,
            base_dir=image_base_dir,
            api_key=api_key,
            model=model
        )
        
        # 寫入輸出檔案
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(enhanced_markdown)
        
        # 記錄結果
        logger.info(f"處理完成，已寫入檔案: {output_file}")
        logger.info(
            f"處理統計: 共處理 {stats['images_processed']} 張圖片，"
            f"成功解析 {stats['images_analyzed']} 張，"
            f"失敗 {stats['images_failed']} 張"
        )
        
        return {
            "success": True,
            "stats": stats,
            "input_file": input_file,
            "output_file": output_file
        }
    
    except Exception as e:
        logger.error(f"處理出錯: {str(e)}")
        return {"success": False, "error": str(e)}


def batch_process_directory(
    directory: str,
    output_directory: Optional[str] = None,
    api_key: Optional[str] = None,
    model: str = "o4-mini",
    file_extension: str = ".md"
) -> Dict:
    """
    批次處理目錄下所有 Markdown 檔案
    
    Args:
        directory (str): 輸入目錄路徑
        output_directory (Optional[str]): 輸出目錄路徑，如果為 None 則在輸入檔案旁邊建立新檔案
        api_key (Optional[str]): OpenAI API 金鑰
        model (str): 使用的 OpenAI 模型，預設為 "o4-mini"
        file_extension (str): 要處理的檔案副檔名，預設為 ".md"
        
    Returns:
        Dict: 批次處理結果
    """
    logger.info(f"開始批次處理目錄: {directory}")
    
    # 檢查目錄是否存在
    if not os.path.isdir(directory):
        logger.error(f"目錄不存在: {directory}")
        return {"success": False, "error": f"目錄不存在: {directory}"}
    
    # 如果指定了輸出目錄，確保其存在
    if output_directory and not os.path.exists(output_directory):
        logger.info(f"創建輸出目錄: {output_directory}")
        os.makedirs(output_directory, exist_ok=True)
    
    # 取得 API 金鑰
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("找不到 OpenAI API 金鑰")
            return {"success": False, "error": "找不到 OpenAI API 金鑰"}
    
    # 收集所有檔案
    files_to_process = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(file_extension):
                files_to_process.append(os.path.join(root, file))
    
    if not files_to_process:
        logger.warning(f"在目錄 {directory} 中找不到 {file_extension} 檔案")
        return {"success": True, "files_processed": 0, "message": "沒有找到檔案"}
    
    # 批次處理檔案
    results = []
    total_processed = 0
    total_images = 0
    start_time = time.time()
    
    for file_path in files_to_process:
        # 決定輸出檔案路徑
        if output_directory:
            # 取得相對路徑
            rel_path = os.path.relpath(file_path, directory)
            output_file = os.path.join(output_directory, rel_path)
            
            # 確保輸出目錄存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
        else:
            output_file = None  # 使用預設行為，在原始檔案旁創建新檔案
        
        # 處理檔案
        result = process_markdown_file(
            input_file=file_path,
            output_file=output_file,
            api_key=api_key,
            model=model,
            image_base_dir=os.path.dirname(file_path)
        )
        
        # 更新統計資訊
        results.append(result)
        if result["success"]:
            total_processed += 1
            total_images += result["stats"]["images_processed"]
    
    # 計算處理時間
    elapsed_time = time.time() - start_time
    
    # 返回結果
    return {
        "success": True,
        "files_total": len(files_to_process),
        "files_processed": total_processed,
        "total_images": total_images,
        "elapsed_time": elapsed_time,
        "results": results
    }


def save_report(report: Dict, output_file: str) -> None:
    """
    將處理報告儲存為 JSON 檔案
    
    Args:
        report (Dict): 處理報告
        output_file (str): 輸出檔案路徑
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info(f"報告已儲存至 {output_file}")


def main():
    """主函數，處理命令列引數並執行檔案處理"""
    parser = argparse.ArgumentParser(
        description="MarkItDown 圖片增強工具 - 為 Markdown 文件中的圖片添加 AI 生成的解析描述"
    )
    
    # 必要引數
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--file", "-f",
        help="要處理的 Markdown 檔案路徑"
    )
    input_group.add_argument(
        "--directory", "-d",
        help="要批次處理的目錄路徑"
    )
    
    # 可選引數
    parser.add_argument(
        "--output", "-o",
        help="輸出檔案或目錄路徑，如果未指定則在原始檔案旁創建新檔案"
    )
    parser.add_argument(
        "--api-key", "-k",
        help="OpenAI API 金鑰，如果未指定則嘗試從環境變數獲取"
    )
    parser.add_argument(
        "--model", "-m",
        default="o4-mini",
        help="使用的 OpenAI 模型，預設為 o4-mini"
    )
    parser.add_argument(
        "--image-dir", "-i",
        help="圖片基礎目錄，如果未指定則使用輸入檔案的目錄"
    )
    parser.add_argument(
        "--report", "-r",
        help="處理報告輸出檔案路徑"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="顯示詳細資訊"
    )
    
    args = parser.parse_args()
    
    # 設定日誌級別
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 執行處理
    if args.file:
        # 處理單一檔案
        result = process_markdown_file(
            input_file=args.file,
            output_file=args.output,
            api_key=args.api_key,
            model=args.model,
            image_base_dir=args.image_dir
        )
    else:
        # 批次處理目錄
        result = batch_process_directory(
            directory=args.directory,
            output_directory=args.output,
            api_key=args.api_key,
            model=args.model
        )
    
    # 如果需要，儲存報告
    if args.report and result:
        save_report(result, args.report)
    
    # 顯示結果
    if result["success"]:
        if args.file:
            logger.info("檔案處理完成!")
        else:
            logger.info(f"批次處理完成! 成功處理 {result['files_processed']} 個檔案")
    else:
        logger.error(f"處理失敗: {result.get('error', '未知錯誤')}")
        sys.exit(1)


if __name__ == "__main__":
    main() 