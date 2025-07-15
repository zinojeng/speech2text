#!/usr/bin/env python3
"""
合併演講稿與投影片內容處理程式
Merge Transcript and Slides Script for ADA 2025 Conference

此程式用於智能合併演講稿與投影片內容：
1. 以演講者內容為主軸，保留完整演講內容
2. 將投影片內容作為補充說明
3. 使用 Gemini-2.5-pro 進行內容整合與潤稿
4. 生成結構化的 Markdown 和 Word 文件

使用方法:
    python merge_transcript_slides.py <transcript_file> <slides_file>
"""

import os
import sys
import re
import logging
from pathlib import Path
from typing import Optional, Tuple
import google.generativeai as genai
from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from datetime import datetime

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('merge_transcript_slides.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# API 配置
GOOGLE_API_KEY = 'AIzaSyBUNvJo_D2KZV3UVVgQxvFlZC1aFfXIw9k'

# 系統提示詞
SYSTEM_PROMPT = """你是一位專業的醫學會議內容編輯，專精於整合演講稿與投影片內容。這是American Diabetes Association 2025年會的內容。

你的任務是智能合併演講稿與投影片內容，創建一份完整、流暢的會議筆記。

**整合原則：**

1. **以演講者內容為主軸**：
   - 保留演講者的完整論述，包含口語表達的生動性
   - 對演講內容進行適度潤稿，使其更加流暢專業
   - 保持演講者的觀點和強調重點

2. **投影片內容的運用**：
   - 作為補充說明，豐富演講內容
   - 填補演講中未提及但重要的資訊
   - 提供具體數據、圖表說明或參考文獻
   - 不要重複已在演講中詳細說明的內容

3. **內容組織方式**：
   - 按照演講的邏輯順序組織內容
   - 在適當位置插入投影片的補充資訊
   - 使用 __底線__ 標記延伸解讀或重要補充說明
   - 保持段落之間的流暢過渡

4. **格式要求**：
   - 使用 # ## ### 組織章節
   - **粗體**標記重要概念、藥物名稱、關鍵數據
   - __底線__用於標記：
     * 來自投影片的重要補充
     * 延伸解讀和深入說明
     * 關鍵研究發現或結論
   - 適度使用項目列表呈現並列資訊

5. **寫作風格**：
   - 保持學術專業性，但不失演講的生動性
   - 確保內容完整、詳細、易讀
   - 使用繁體中文

**範例整合方式：**
演講者說：「這個研究顯示了顯著的改善效果...」
投影片補充：具體數據為改善率達到78.5% (p<0.001)
整合後：「這個研究顯示了顯著的改善效果，__根據投影片數據，具體改善率達到78.5% (p<0.001)，這個結果在統計學上具有高度顯著性__。」

請確保輸出是一份完整、專業、資訊豐富的會議筆記。"""


class TranscriptSlidesProcessor:
    """處理演講稿與投影片合併的處理器"""
    
    def __init__(self):
        """初始化處理器"""
        self.setup_api()
    
    def setup_api(self):
        """設定 Google Gemini API"""
        try:
            genai.configure(api_key=GOOGLE_API_KEY)
            logger.info("Google Gemini API 設定完成")
        except Exception as e:
            logger.error(f"API 設定失敗: {e}")
            raise
    
    def read_file(self, file_path: str, file_type: str) -> str:
        """
        讀取檔案內容
        
        Args:
            file_path: 檔案路徑
            file_type: 檔案類型描述（用於日誌）
            
        Returns:
            檔案內容
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"{file_type}檔案不存在: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                raise ValueError(f"{file_type}檔案內容為空")
            
            logger.info(f"成功讀取{file_type}檔案: {file_path}")
            logger.info(f"檔案大小: {len(content)} 字元")
            return content
            
        except Exception as e:
            logger.error(f"讀取{file_type}檔案失敗: {e}")
            raise
    
    def merge_with_gemini(self, transcript: str, slides: str) -> str:
        """
        使用 Gemini-2.5-pro 進行內容合併與整合
        
        Args:
            transcript: 演講稿內容
            slides: 投影片內容
            
        Returns:
            整合後的 Markdown 內容
        """
        try:
            logger.info("開始使用 Gemini-2.5-pro 進行內容整合")
            
            # 建立模型
            model = genai.GenerativeModel('gemini-2.5-pro')
            
            # 構建提示詞
            user_prompt = f"""請根據以下演講稿和投影片內容，創建一份整合的會議筆記：

=== 演講稿內容 ===
{transcript}

=== 投影片內容 ===
{slides}

請按照指示整合這兩份內容，生成完整的 Markdown 格式會議筆記。"""
            
            # 生成整合內容
            response = model.generate_content([
                {"role": "user", "parts": [{"text": SYSTEM_PROMPT}]},
                {"role": "user", "parts": [{"text": user_prompt}]}
            ])
            
            merged_content = response.text
            logger.info(f"內容整合完成，長度: {len(merged_content)} 字元")
            return merged_content
            
        except Exception as e:
            logger.error(f"內容整合失敗: {e}")
            raise
    
    def save_markdown(self, content: str, output_path: str) -> str:
        """
        保存 Markdown 檔案
        
        Args:
            content: Markdown 內容
            output_path: 輸出路徑
            
        Returns:
            保存的檔案路徑
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Markdown 檔案已保存: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"保存 Markdown 失敗: {e}")
            raise
    
    def markdown_to_docx(self, markdown_text: str, output_path: str) -> bool:
        """
        將 Markdown 文字轉換為保留格式的 Word 文件
        
        Args:
            markdown_text: Markdown 格式文字
            output_path: 輸出檔案路徑
            
        Returns:
            轉換是否成功
        """
        try:
            logger.info(f"開始轉換為 Word 文件: {output_path}")
            
            doc = Document()
            
            # 添加標題
            title = doc.add_heading('ADA 2025 會議筆記 - 演講與投影片整合版', level=0)
            title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            
            # 添加日期
            date_para = doc.add_paragraph()
            date_para.add_run(f"整合日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            date_para.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
            
            doc.add_paragraph()  # 空行
            
            # 分行處理 Markdown 內容
            lines = markdown_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    doc.add_paragraph()  # 空行
                    continue
                
                # 處理標題
                if line.startswith('#'):
                    level = len(line) - len(line.lstrip('#'))
                    title_text = line.lstrip('#').strip()
                    
                    if level == 1:
                        doc.add_heading(title_text, level=1)
                    elif level == 2:
                        doc.add_heading(title_text, level=2)
                    elif level == 3:
                        doc.add_heading(title_text, level=3)
                    else:
                        doc.add_heading(title_text, level=4)
                    
                    continue
                
                # 處理列表項目
                if line.startswith(('- ', '* ', '+ ')):
                    list_text = line[2:].strip()
                    paragraph = doc.add_paragraph(style='List Bullet')
                    self._add_formatted_text(paragraph, list_text)
                elif re.match(r'^\d+\.\s', line):
                    list_text = re.sub(r'^\d+\.\s', '', line).strip()
                    paragraph = doc.add_paragraph(style='List Number')
                    self._add_formatted_text(paragraph, list_text)
                else:
                    # 處理普通段落
                    paragraph = doc.add_paragraph()
                    self._add_formatted_text(paragraph, line)
            
            # 儲存文件
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path))
            
            logger.info(f"Word 文件已儲存: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"轉換為 Word 文件失敗: {e}")
            return False
    
    def _add_formatted_text(self, paragraph, text):
        """
        處理文字格式並添加到段落
        
        Args:
            paragraph: Word 段落對象
            text: 要處理的文字
        """
        # 使用更精確的正則表達式來處理格式
        # 先處理雙底線（必須在單底線之前）
        parts = re.split(r'(__[^_]+__|_[^_]+_|\*\*[^*]+\*\*|\*[^*]+\*)', text)
        
        for part in parts:
            if not part:
                continue
            
            if part.startswith('**') and part.endswith('**') and len(part) > 4:
                # 粗體
                run = paragraph.add_run(part[2:-2])
                run.bold = True
            elif part.startswith('__') and part.endswith('__') and len(part) > 4:
                # 底線（雙底線）
                run = paragraph.add_run(part[2:-2])
                run.underline = True
            elif part.startswith('_') and part.endswith('_') and len(part) > 2:
                # 底線（單底線）
                run = paragraph.add_run(part[1:-1])
                run.underline = True
            elif part.startswith('*') and part.endswith('*') and len(part) > 2:
                # 斜體
                run = paragraph.add_run(part[1:-1])
                run.italic = True
            else:
                # 普通文字
                paragraph.add_run(part)
    
    def process_files(self, transcript_file: str, slides_file: str, output_base: str = None) -> dict:
        """
        處理演講稿與投影片檔案
        
        Args:
            transcript_file: 演講稿檔案路徑
            slides_file: 投影片檔案路徑
            output_base: 輸出檔案基礎名稱（可選）
            
        Returns:
            處理結果
        """
        result = {
            'success': False,
            'transcript_file': transcript_file,
            'slides_file': slides_file,
            'markdown_file': None,
            'docx_file': None,
            'error': None
        }
        
        try:
            # 讀取檔案
            transcript = self.read_file(transcript_file, "演講稿")
            slides = self.read_file(slides_file, "投影片")
            
            # 使用 Gemini 進行內容整合
            merged_content = self.merge_with_gemini(transcript, slides)
            
            # 準備輸出路徑
            if not output_base:
                # 使用演講稿檔案名作為基礎
                transcript_path = Path(transcript_file)
                output_base = transcript_path.stem
            
            output_dir = Path(transcript_file).parent
            
            # 保存 Markdown
            markdown_path = output_dir / f"{output_base}_merged.md"
            self.save_markdown(merged_content, str(markdown_path))
            result['markdown_file'] = str(markdown_path)
            
            # 轉換為 Word
            docx_path = output_dir / f"{output_base}_merged.docx"
            if self.markdown_to_docx(merged_content, str(docx_path)):
                result['docx_file'] = str(docx_path)
                result['success'] = True
            else:
                result['error'] = "Word 轉換失敗"
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"處理檔案失敗: {e}")
        
        return result


def main():
    """主函數"""
    if len(sys.argv) < 3:
        print("使用方法: python merge_transcript_slides.py <transcript_file> <slides_file> [output_base_name]")
        print("範例: python merge_transcript_slides.py transcript.txt slides.txt lecture_notes")
        sys.exit(1)
    
    transcript_file = sys.argv[1]
    slides_file = sys.argv[2]
    output_base = sys.argv[3] if len(sys.argv) > 3 else None
    
    print(f"\n=== 演講稿與投影片整合程式 ===")
    print(f"演講稿檔案: {transcript_file}")
    print(f"投影片檔案: {slides_file}")
    print(f"使用模型: Gemini-2.5-pro")
    print("處理中...\n")
    
    try:
        processor = TranscriptSlidesProcessor()
        result = processor.process_files(transcript_file, slides_file, output_base)
        
        if result['success']:
            print("\n✅ 處理成功！")
            print(f"Markdown 檔案: {result['markdown_file']}")
            print(f"Word 檔案: {result['docx_file']}")
        else:
            print(f"\n❌ 處理失敗: {result['error']}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ 程式執行失敗: {e}")
        logger.error(f"程式執行失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()