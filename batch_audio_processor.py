#!/usr/bin/env python3
"""
批次音訊處理自動化程式
Batch Audio Processor for ADA 2025 Conference

此程式用於自動化處理音訊檔案，包含：
1. 搜索指定資料夾中的所有音訊檔案和格式化文字文件
2. 使用 GPT-4o 進行語音轉錄
3. 使用 Gemini 2.5 Pro 進行摘要處理
4. 將結果轉換為 Word 文件

使用方法:
    python batch_audio_processor.py
    或
    python batch_audio_processor.py <資料夾路徑>

環境需求:
- .env 檔案中需包含 OPENAI_API_KEY 和 GOOGLE_API_KEY
- 音訊檔案需有同名的文字檔案作為 agenda 內容
"""

import os
import sys
import glob
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
from openai import OpenAI
import google.generativeai as genai
from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import re
import time

# 導入現有的工具函數
from utils import split_large_audio, check_file_size
from audio2text.gpt4o_stt import transcribe_audio_gpt4o
from pydub import AudioSegment

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_processor.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 支援的音訊格式
SUPPORTED_AUDIO_FORMATS = [
    '*.mp3', '*.wav', '*.m4a', '*.aac', '*.flac', '*.ogg',
    '*.wma', '*.mp4', '*.mov', '*.avi', '*.mkv', '*.webm'
]

# 支援的文字文件格式
SUPPORTED_TEXT_FORMATS = [
    '*.txt', '*.md', '*.rtf', '*.doc', '*.docx', '*.pdf',
    '*.html', '*.htm', '*.xml', '*.json', '*.csv'
]

# 系統提示詞
SYSTEM_PROMPT = """This is American Diabetes Association 2025年會，聚焦在糖尿病，代謝，肥胖等等主題。優化演講者 transcribe content 成完整的筆記.

rewrite or 順暢演講者內容，並儘可能完整呈現，加入一些粗體或底線來呈現重點，或加入小結來總結或延伸您的想法。 並依使用者提供的 agenda 整理。as detail , professional and comprehensive as you can in zh-tw

依以下的 agenda 來分主要段落。"""


class BatchAudioProcessor:
    """批次音訊處理器"""
    
    def __init__(self, model="gpt-4o-mini-transcribe", output_format="text"):
        """
        初始化處理器
        
        Args:
            model: 使用的轉錄模型 (gpt-4o-transcribe 或 gpt-4o-mini-transcribe)
            output_format: 輸出格式 (text, markdown, srt)
        """
        self.openai_client = None
        self.transcribe_model = model
        self.output_format = output_format
        self.setup_apis()
    
    def setup_apis(self):
        """設定 API 客戶端"""
        # 設定 OpenAI API
        openai_key = os.getenv('OPENAI_API_KEY')
        if not openai_key:
            raise ValueError("請在 .env 檔案中設定 OPENAI_API_KEY")

        self.openai_client = OpenAI(api_key=openai_key)
        logger.info("OpenAI API 設定完成")

        # 設定 Google Gemini API
        google_key = 'AIzaSyBUNvJo_D2KZV3UVVgQxvFlZC1aFfXIw9k'  # 使用提供的 API key
        if not google_key:
            google_key = os.getenv('GOOGLE_API_KEY')
            if not google_key:
                raise ValueError("請在 .env 檔案中設定 GOOGLE_API_KEY")

        genai.configure(api_key=google_key)
        logger.info("Google Gemini API 設定完成")
    
    def get_folder_path(self) -> str:
        """
        取得使用者輸入的資料夾路徑

        Returns:
            資料夾路徑字串
        """
        if len(sys.argv) > 1:
            folder_path = sys.argv[1]
        else:
            print("=== 批次音訊處理自動化程式 ===")
            print("請輸入要處理的資料夾路徑:")
            folder_path = input("> ").strip()

        # 移除路徑兩端的引號
        folder_path = folder_path.strip('"\'')

        # 驗證路徑是否存在
        if not Path(folder_path).exists():
            raise ValueError(f"資料夾不存在: {folder_path}")

        return folder_path

    def find_files(self, folder_path: str) -> Dict[str, List[str]]:
        """
        在指定資料夾中遞歸搜索音訊檔案和文字文件

        Args:
            folder_path: 要搜索的資料夾路徑

        Returns:
            包含音訊檔案和文字文件的字典
        """
        folder_path = Path(folder_path)

        if not folder_path.exists():
            logger.error(f"資料夾不存在: {folder_path}")
            return {'audio': [], 'text': []}

        logger.info(f"搜索資料夾: {folder_path}")

        # 搜索音訊檔案
        audio_files = []
        for pattern in SUPPORTED_AUDIO_FORMATS:
            files = glob.glob(str(folder_path / "**" / pattern),
                              recursive=True)
            audio_files.extend(files)

        # 搜索文字文件
        text_files = []
        for pattern in SUPPORTED_TEXT_FORMATS:
            files = glob.glob(str(folder_path / "**" / pattern),
                              recursive=True)
            text_files.extend(files)

        # 去重並排序
        audio_files = sorted(list(set(audio_files)))
        text_files = sorted(list(set(text_files)))

        logger.info(f"找到 {len(audio_files)} 個音訊檔案")
        for file in audio_files:
            logger.info(f"  - {file}")

        logger.info(f"找到 {len(text_files)} 個文字文件")
        for file in text_files:
            logger.info(f"  - {file}")

        return {'audio': audio_files, 'text': text_files}
    
    def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """
        使用 GPT-4o 轉錄音訊檔案，支援大檔案分割

        Args:
            audio_path: 音訊檔案路徑

        Returns:
            轉錄文字，失敗時返回 None
        """
        try:
            logger.info(f"開始轉錄音訊: {audio_path}")
            
            # 檢查檔案大小，如果太大則分割
            if check_file_size(audio_path):
                logger.info(f"檔案較大，進行分割處理: {audio_path}")
                segments = split_large_audio(audio_path)
                
                if not segments:
                    logger.error("音訊分割失敗")
                    return None
                
                # 分別轉錄每個片段
                full_transcript = ""
                for i, segment_path in enumerate(segments):
                    logger.info(f"轉錄片段 {i+1}/{len(segments)}: {segment_path}")
                    
                    try:
                        with open(segment_path, "rb") as audio_file:
                            transcript = self.openai_client.audio.transcriptions.create(
                                model=self.transcribe_model,
                                file=audio_file,
                                language="zh",
                                response_format="text"
                            )
                        
                        full_transcript += transcript.text + " "
                        logger.info(f"片段 {i+1} 轉錄完成")
                        
                        # 清理臨時檔案
                        if os.path.exists(segment_path):
                            os.remove(segment_path)
                            
                    except Exception as e:
                        logger.error(f"片段 {i+1} 轉錄失敗: {e}")
                        # 清理臨時檔案
                        if os.path.exists(segment_path):
                            os.remove(segment_path)
                        continue
                    
                    # 避免 API 限制，加入延遲
                    time.sleep(2)
                
                if full_transcript.strip():
                    logger.info(f"所有片段轉錄完成，總長度: {len(full_transcript)}")
                    return full_transcript.strip()
                else:
                    logger.error("所有片段轉錄都失敗")
                    return None
            
            else:
                # 檔案大小正常，直接轉錄
                with open(audio_path, "rb") as audio_file:
                    transcript = self.openai_client.audio.transcriptions.create(
                        model=self.transcribe_model,
                        file=audio_file,
                        language="zh",
                        response_format="text"
                    )

                logger.info(f"轉錄完成，文字長度: {len(transcript.text)}")
                return transcript.text

        except Exception as e:
            logger.error(f"轉錄失敗: {e}")
            return None
    
    def read_agenda_file(self, audio_path: str,
                         text_files: List[str]) -> Optional[str]:
        """
        讀取與音訊檔案同名的議程文字檔案

        Args:
            audio_path: 音訊檔案路徑
            text_files: 可用的文字檔案列表

        Returns:
            議程內容，找不到時返回 None
        """
        audio_path = Path(audio_path)
        audio_stem = audio_path.stem

        # 尋找同名的文字檔案
        for text_file in text_files:
            text_path = Path(text_file)
            if text_path.stem == audio_stem:
                try:
                    with open(text_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    if content:
                        logger.info(f"找到議程檔案: {text_path}")
                        return content
                except Exception as e:
                    logger.warning(f"讀取議程檔案失敗 {text_path}: {e}")

        # 如果沒有找到同名檔案，嘗試常見的議程檔案名
        agenda_names = ['agenda', 'schedule', 'program', '議程']
        for text_file in text_files:
            text_path = Path(text_file)
            if any(name in text_path.stem.lower() for name in agenda_names):
                try:
                    with open(text_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    if content:
                        logger.info(f"找到議程檔案: {text_path}")
                        return content
                except Exception as e:
                    logger.warning(f"讀取議程檔案失敗 {text_path}: {e}")

        logger.warning(f"未找到議程檔案: {audio_stem}")
        return None
    
    def summarize_with_gemini(self, transcript: str,
                              agenda: Optional[str] = None) -> Optional[str]:
        """
        使用 Gemini 2.5 Pro 進行摘要處理

        Args:
            transcript: 轉錄文字
            agenda: 議程內容

        Returns:
            摘要文字，失敗時返回 None
        """
        try:
            logger.info("開始使用 Gemini 2.5 Pro 進行摘要處理")

            # 建立模型 - 使用最新的 Gemini 2.5 Pro
            model = genai.GenerativeModel('gemini-2.5-pro')

            # 構建提示詞
            user_prompt = f"""請根據以下轉錄內容進行摘要處理：

轉錄內容：
{transcript}
"""

            if agenda:
                user_prompt += f"""

議程內容：
{agenda}
"""

            # 生成摘要
            response = model.generate_content([
                {"role": "user", "parts": [{"text": SYSTEM_PROMPT}]},
                {"role": "user", "parts": [{"text": user_prompt}]}
            ])

            summary = response.text
            logger.info(f"摘要完成，長度: {len(summary)}")
            return summary

        except Exception as e:
            logger.error(f"摘要處理失敗: {e}")
            return None
    
    def markdown_to_docx(self, markdown_text: str, output_path: str) -> bool:
        """
        將 Markdown 文字轉換為 Word 文件

        Args:
            markdown_text: Markdown 格式文字
            output_path: 輸出檔案路徑

        Returns:
            轉換是否成功
        """
        try:
            logger.info(f"開始轉換為 Word 文件: {output_path}")

            doc = Document()

            # 分行處理
            lines = markdown_text.split('\n')

            for line in lines:
                line = line.strip()
                if not line:
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

                # 處理普通段落
                paragraph = doc.add_paragraph()

                # 處理粗體和底線
                parts = re.split(r'(\*\*.*?\*\*|__.*?__|\*.*?\*|_.*?_)', line)

                for part in parts:
                    if part.startswith('**') and part.endswith('**'):
                        # 粗體
                        run = paragraph.add_run(part[2:-2])
                        run.bold = True
                    elif part.startswith('__') and part.endswith('__'):
                        # 底線
                        run = paragraph.add_run(part[2:-2])
                        run.underline = True
                    elif part.startswith('*') and part.endswith('*'):
                        # 斜體
                        run = paragraph.add_run(part[1:-1])
                        run.italic = True
                    elif part.startswith('_') and part.endswith('_'):
                        # 底線
                        run = paragraph.add_run(part[1:-1])
                        run.underline = True
                    else:
                        # 普通文字
                        paragraph.add_run(part)

            # 儲存文件
            doc.save(output_path)
            logger.info(f"Word 文件已儲存: {output_path}")
            return True

        except Exception as e:
            logger.error(f"轉換為 Word 文件失敗: {e}")
            return False
    
    def process_single_file(self, audio_path: str,
                            text_files: List[str]) -> Dict:
        """
        處理單一音訊檔案

        Args:
            audio_path: 音訊檔案路徑
            text_files: 可用的文字檔案列表

        Returns:
            處理結果字典
        """
        result = {
            'file': audio_path,
            'success': False,
            'transcript': None,
            'summary': None,
            'docx_path': None,
            'error': None
        }

        try:
            # 1. 轉錄音訊
            transcript = self.transcribe_audio(audio_path)
            if not transcript:
                result['error'] = "轉錄失敗"
                return result

            result['transcript'] = transcript

            # 2. 讀取議程檔案
            agenda = self.read_agenda_file(audio_path, text_files)

            # 3. 生成摘要
            summary = self.summarize_with_gemini(transcript, agenda)
            if not summary:
                result['error'] = "摘要處理失敗"
                return result

            result['summary'] = summary

            # 4. 轉換為 Word 文件
            audio_path_obj = Path(audio_path)
            docx_path = audio_path_obj.with_suffix('.docx')

            if self.markdown_to_docx(summary, str(docx_path)):
                result['docx_path'] = str(docx_path)
                result['success'] = True
            else:
                result['error'] = "Word 文件轉換失敗"

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"處理檔案時發生錯誤: {e}")

        return result
    
    def process_folder(self, folder_path: str) -> List[Dict]:
        """
        處理整個資料夾中的音訊檔案

        Args:
            folder_path: 資料夾路徑

        Returns:
            處理結果列表
        """
        logger.info(f"開始處理資料夾: {folder_path}")

        # 找到所有檔案
        files = self.find_files(folder_path)
        audio_files = files['audio']
        text_files = files['text']

        if not audio_files:
            logger.warning("未找到任何音訊檔案")
            return []

        results = []

        for i, audio_file in enumerate(audio_files, 1):
            logger.info(f"處理檔案 {i}/{len(audio_files)}: {audio_file}")

            result = self.process_single_file(audio_file, text_files)
            results.append(result)

            if result['success']:
                logger.info(f"✅ 成功處理: {audio_file}")
            else:
                logger.error(f"❌ 處理失敗: {audio_file} - {result['error']}")

            # 避免 API 限制，加入延遲
            time.sleep(1)

        return results
    
    def generate_report(self, results: List[Dict], output_path: str):
        """
        生成處理結果報告

        Args:
            results: 處理結果列表
            output_path: 報告輸出路徑
        """
        try:
            doc = Document()

            # 標題
            title = doc.add_heading('批次音訊處理報告', level=1)
            title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

            # 統計資訊
            total_files = len(results)
            success_files = sum(1 for r in results if r['success'])
            failed_files = total_files - success_files

            stats = doc.add_paragraph()
            stats.add_run(f"總檔案數: {total_files}\n").bold = True
            stats.add_run(f"成功處理: {success_files}\n").bold = True
            stats.add_run(f"處理失敗: {failed_files}\n").bold = True

            # 詳細結果
            doc.add_heading('處理結果詳細', level=2)

            for result in results:
                file_name = Path(result['file']).name

                if result['success']:
                    status = "✅ 成功"
                    doc.add_paragraph(f"{file_name}: {status}")
                    doc.add_paragraph(f"  輸出文件: {result['docx_path']}")
                else:
                    status = "❌ 失敗"
                    doc.add_paragraph(f"{file_name}: {status}")
                    doc.add_paragraph(f"  錯誤: {result['error']}")

                doc.add_paragraph()  # 空行

            doc.save(output_path)
            logger.info(f"報告已儲存: {output_path}")

        except Exception as e:
            logger.error(f"生成報告失敗: {e}")


def main():
    """主函數"""
    try:
        # 檢查命令行參數中是否指定模型
        model = "gpt-4o-mini-transcribe"  # 預設使用 mini 版本
        if len(sys.argv) > 2 and sys.argv[2] in ["gpt-4o-transcribe", "gpt-4o-mini-transcribe"]:
            model = sys.argv[2]
        
        print(f"🤖 使用轉錄模型: {model}")
        processor = BatchAudioProcessor(model=model)
        folder_path = processor.get_folder_path()
        results = processor.process_folder(folder_path)

        # 生成報告
        report_path = Path(folder_path) / "processing_report.docx"
        processor.generate_report(results, str(report_path))

        # 顯示結果統計
        total_files = len(results)
        success_files = sum(1 for r in results if r['success'])

        print("\n=== 處理完成 ===")
        print(f"總檔案數: {total_files}")
        print(f"成功處理: {success_files}")
        print(f"處理失敗: {total_files - success_files}")
        print(f"報告位置: {report_path}")

    except Exception as e:
        logger.error(f"程式執行失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
