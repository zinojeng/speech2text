"""
ADA2025 批次音訊處理器
ADA2025 Batch Audio Processor

專門針對 ADA2025 會議音訊檔案的批次處理系統
"""

import os
import sys
import logging
import time
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import subprocess

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ADA2025BatchProcessor:
    """ADA2025 批次音訊處理器"""
    
    def __init__(self, base_path: str = "/Volumes/WD_BLACK/國際年會/ADA2025"):
        """
        初始化處理器
        
        Args:
            base_path: ADA2025 基礎路徑
        """
        self.base_path = Path(base_path)
        # 只處理音訊檔案，不處理影片檔案
        self.audio_extensions = {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma'}
        self.agenda_extensions = {'.txt', '.md', '.rtf', '.doc', '.docx', '.pdf', '.html', '.htm'}
        
        # 檢查必要的 API 金鑰
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.google_key = os.getenv('GOOGLE_API_KEY')
        
        if not self.openai_key:
            logger.warning("未找到 OPENAI_API_KEY，轉錄功能將不可用")
        if not self.google_key:
            logger.warning("未找到 GOOGLE_API_KEY，摘要功能將不可用")
    
    def is_folder_already_processed(self, folder_path: Path) -> tuple[bool, str]:
        """
        檢查資料夾是否已經處理過
        
        Args:
            folder_path: 資料夾路徑
            
        Returns:
            (是否已處理, 跳過原因)
        """
        try:
            # 檢查各種處理結果檔案
            transcription_files = list(folder_path.glob("transcription*.txt"))
            transcript_files = list(folder_path.glob("*轉錄*.txt"))
            docx_files = list(folder_path.glob("*.docx"))
            summary_files = list(folder_path.glob("*詳細筆記*.md"))
            
            # 過濾掉系統檔案
            transcription_files = [f for f in transcription_files if not f.name.startswith('._')]
            transcript_files = [f for f in transcript_files if not f.name.startswith('._')]
            docx_files = [f for f in docx_files if not f.name.startswith('._')]
            summary_files = [f for f in summary_files if not f.name.startswith('._')]
            
            # 檢查是否有完整的處理結果
            has_transcription = len(transcription_files) > 0 or len(transcript_files) > 0
            has_summary = len(summary_files) > 0
            has_docx = len(docx_files) > 0
            
            if has_transcription and has_summary and has_docx:
                return True, f"已有完整處理結果 (轉錄: {len(transcription_files + transcript_files)}, 摘要: {len(summary_files)}, DOCX: {len(docx_files)})"
            elif has_transcription and has_summary:
                return True, f"已有轉錄和摘要檔案 (轉錄: {len(transcription_files + transcript_files)}, 摘要: {len(summary_files)})"
            elif has_transcription:
                # 只有轉錄檔案，可能需要生成摘要
                return False, f"只有轉錄檔案，需要生成摘要"
            else:
                return False, "未找到處理結果檔案"
                
        except Exception as e:
            logger.warning(f"檢查資料夾處理狀態時發生錯誤: {e}")
            return False, "檢查處理狀態失敗"

    def find_audio_files(self, folder_path: Path) -> List[Path]:
        """
        在資料夾中尋找音訊檔案
        如果資料夾中有音訊檔案，就跳過該資料夾同一層以及所有子資料夾中的影片檔案
        
        Args:
            folder_path: 資料夾路徑
            
        Returns:
            音訊檔案路徑列表
        """
        audio_files = []
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
        
        try:
            # 首先檢查整個資料夾樹中是否有音訊檔案
            has_audio_in_tree = False
            all_audio_files = []
            all_video_files = []
            
            for file_path in folder_path.rglob('*'):
                if file_path.is_file():
                    # 排除隱藏檔案和系統檔案
                    if file_path.name.startswith('.') or file_path.name.startswith('._'):
                        continue
                    
                    if file_path.suffix.lower() in self.audio_extensions:
                        has_audio_in_tree = True
                        all_audio_files.append(file_path)
                    elif file_path.suffix.lower() in video_extensions:
                        all_video_files.append(file_path)
            
            # 應用嚴格的優先級邏輯
            if has_audio_in_tree:
                # 如果資料夾樹中有任何音訊檔案，只處理音訊檔案，跳過所有影片檔案
                audio_files.extend(all_audio_files)
                if all_video_files:
                    logger.info(f"資料夾樹 {folder_path.name} 中有音訊檔案，跳過所有 {len(all_video_files)} 個影片檔案")
                    # 記錄被跳過的影片檔案詳情
                    for video_file in all_video_files:
                        relative_path = video_file.relative_to(folder_path)
                        logger.debug(f"跳過影片檔案: {relative_path}")
            else:
                # 如果整個資料夾樹中都沒有音訊檔案，則處理影片檔案
                audio_files.extend(all_video_files)
                if all_video_files:
                    logger.info(f"資料夾樹 {folder_path.name} 中無音訊檔案，處理 {len(all_video_files)} 個影片檔案")
            
            # 按檔名排序
            audio_files.sort(key=lambda x: x.name)
            
        except Exception as e:
            logger.error(f"搜尋音訊檔案時發生錯誤: {e}")
        
        return audio_files
    
    def find_agenda_file(self, audio_file: Path) -> Optional[Path]:
        """
        尋找與音訊檔案對應的議程檔案
        
        Args:
            audio_file: 音訊檔案路徑
            
        Returns:
            議程檔案路徑，如果找不到則返回 None
        """
        folder = audio_file.parent
        base_name = audio_file.stem
        
        # 嘗試尋找同名檔案
        for ext in self.agenda_extensions:
            agenda_file = folder / f"{base_name}{ext}"
            if agenda_file.exists():
                return agenda_file
        
        # 嘗試尋找常見的議程檔案名
        common_names = ['agenda', 'schedule', 'program', '議程', 'outline']
        for name in common_names:
            for ext in self.agenda_extensions:
                agenda_file = folder / f"{name}{ext}"
                if agenda_file.exists():
                    return agenda_file
        
        return None
    
    def transcribe_audio(self, audio_file: Path, model: str = "gpt-transcribe") -> Tuple[bool, str, str]:
        """
        轉錄音訊檔案
        
        Args:
            audio_file: 音訊檔案路徑
            model: 轉錄模型
            
        Returns:
            (成功狀態, 轉錄內容, 錯誤訊息)
        """
        if not self.openai_key:
            return False, "", "未設定 OPENAI_API_KEY"
        
        try:
            # 檢查是否已存在轉錄檔案
            existing_transcript_files = list(audio_file.parent.glob(f"{audio_file.stem}_轉錄_*.txt"))
            
            if existing_transcript_files:
                # 使用最新的轉錄檔案
                latest_transcript_file = max(existing_transcript_files, key=lambda x: x.stat().st_mtime)
                logger.info(f"找到已存在的轉錄檔案: {latest_transcript_file.name}")
                
                try:
                    with open(latest_transcript_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 提取轉錄內容
                    lines = content.split('\n')
                    transcript_start = False
                    transcript_lines = []
                    
                    for line in lines:
                        if line.strip() == "轉錄內容:":
                            transcript_start = True
                            continue
                        elif transcript_start and line.strip():
                            transcript_lines.append(line)
                    
                    transcript_content = '\n'.join(transcript_lines)
                    
                    if transcript_content.strip():
                        logger.info(f"使用已存在的轉錄檔案: {len(transcript_content)} 字符")
                        return True, transcript_content, ""
                    else:
                        logger.warning(f"已存在的轉錄檔案內容為空，將重新轉錄")
                        
                except Exception as e:
                    logger.warning(f"讀取已存在的轉錄檔案失敗，將重新轉錄: {e}")
            
            logger.info(f"開始轉錄: {audio_file.name}")
            logger.info(f"檔案路徑: {audio_file}")
            
            # 呼叫增強版轉錄程式
            cmd = [
                sys.executable, "enhanced_gpt4o_transcribe.py",
                str(audio_file),
                "--model", model,
                "--format", "text"
            ]
            
            logger.info(f"執行命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 1小時超時
                cwd=os.getcwd()  # 確保在正確的工作目錄執行
            )
            
            if result.returncode == 0:
                # 尋找生成的轉錄檔案 - 使用更靈活的搜尋方式
                # 首先嘗試精確匹配
                transcript_file = audio_file.parent / f"{audio_file.stem}_轉錄_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                
                # 如果找不到預期的檔案，嘗試尋找任何相關的轉錄檔案
                if not transcript_file.exists():
                    # 搜尋所有轉錄檔案
                    transcript_files = list(audio_file.parent.glob("*轉錄*.txt"))
                    
                    if transcript_files:
                        # 按修改時間排序，取最新的
                        transcript_file = max(transcript_files, key=lambda x: x.stat().st_mtime)
                        logger.info(f"找到轉錄檔案: {transcript_file.name}")
                    else:
                        # 如果還是找不到，等待一下再搜尋
                        time.sleep(2)
                        transcript_files = list(audio_file.parent.glob("*轉錄*.txt"))
                        if transcript_files:
                            transcript_file = max(transcript_files, key=lambda x: x.stat().st_mtime)
                            logger.info(f"延遲搜尋找到轉錄檔案: {transcript_file.name}")
                
                if transcript_file and transcript_file.exists():
                    with open(transcript_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 提取轉錄內容
                    lines = content.split('\n')
                    transcript_start = False
                    transcript_lines = []
                    
                    for line in lines:
                        if line.strip() == "轉錄內容:":
                            transcript_start = True
                            continue
                        elif transcript_start and line.strip():
                            transcript_lines.append(line)
                    
                    transcript_content = '\n'.join(transcript_lines)
                    
                    if transcript_content.strip():
                        logger.info(f"轉錄成功: {len(transcript_content)} 字符")
                        return True, transcript_content, ""
                    else:
                        logger.warning(f"轉錄檔案存在但內容為空: {transcript_file}")
                        return False, "", "轉錄內容為空"
                else:
                    # 列出資料夾中的所有檔案以便除錯
                    all_files = list(audio_file.parent.glob("*"))
                    logger.error(f"找不到轉錄檔案。資料夾中的檔案:")
                    for f in all_files:
                        logger.error(f"  - {f.name}")
                    return False, "", "找不到轉錄檔案"
            else:
                error_msg = result.stderr or result.stdout or "轉錄程式執行失敗"
                logger.error(f"轉錄程式執行失敗 (返回碼: {result.returncode})")
                logger.error(f"標準輸出: {result.stdout}")
                logger.error(f"標準錯誤: {result.stderr}")
                return False, "", error_msg
                
        except subprocess.TimeoutExpired:
            return False, "", "轉錄超時"
        except Exception as e:
            logger.error(f"轉錄過程中發生錯誤: {e}")
            return False, "", str(e)
    
    def generate_summary(self, transcript: str, file_name: str, agenda_content: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        生成智能摘要
        
        Args:
            transcript: 轉錄內容
            file_name: 檔案名稱
            agenda_content: 議程內容
            
        Returns:
            (成功狀態, 摘要內容, 錯誤訊息)
        """
        if not self.google_key:
            return False, "", "未設定 GOOGLE_API_KEY"
        
        try:
            from gemini_utils import call_gemini_api
            
            # 創建增強版 prompt
            prompt = self.create_enhanced_prompt(transcript, file_name, agenda_content)
            
            logger.info(f"開始生成摘要: {file_name}")
            start_time = time.time()
            
            summary_content = call_gemini_api(
                prompt=prompt,
                model="gemini-3.7-flash",
                api_key=self.google_key
            )
            
            processing_time = time.time() - start_time
            
            if summary_content and summary_content.strip():
                logger.info(f"摘要生成成功: {processing_time:.1f}s, {len(summary_content)} 字符")
                return True, summary_content, ""
            else:
                return False, "", "摘要生成失敗：返回內容為空"
                
        except Exception as e:
            logger.error(f"摘要生成過程中發生錯誤: {e}")
            return False, "", str(e)
    
    def create_enhanced_prompt(self, transcript: str, file_name: str, agenda_content: Optional[str] = None) -> str:
        """
        創建增強版摘要 prompt
        
        Args:
            transcript: 轉錄內容
            file_name: 檔案名稱
            agenda_content: 議程內容
            
        Returns:
            增強版 prompt
        """
        prompt = f"""你是一個專業的醫學會議內容整理專家，專門處理 ADA 2025（美國糖尿病學會年會）的會議內容。

**會議資訊：**
- 會議名稱：{file_name}
- 主題：ADA 2025 年會會議內容
- 組織：美國糖尿病協會 (ADA)

🚨 **重要說明：這不是摘要工作，而是內容整理工作** 🚨

你的任務是將演講者的原始內容進行**完整保留、修飾潤稿、階層化重點標記**的專業整理。

## 核心原則：

### 1. **完整內容保留**（不是摘要）：
   - **100% 保留演講者的所有重要內容**，絕不省略任何細節
   - **完整保持演講者的原始觀點**和表達邏輯
   - **逐字逐句地整理**，而非概括或簡化
   - **保留所有數據、統計資料、研究結果**的完整性

### 2. **修飾潤稿**（提升可讀性）：
   - **改善語句流暢度**，使表達更清晰易懂
   - **修正語法錯誤**和表達不清的地方
   - **統一專業術語**的使用，確保一致性
   - **保持演講者的專業語調**和學術風格

### 3. **階層化重點標記**（格式強化）：
   - 使用 **粗體** 標記：重要概念、關鍵發現、核心結論
   - 使用 _斜體_ 標記：藥物名稱、研究名稱、技術術語
   - 使用 `代碼格式` 標記：具體數值、劑量、統計值、p值
   - 使用項目符號和編號列表組織要點
   - 使用引用格式 (>) 標記重要引言、定義或關鍵建議

### 4. **專業結構化組織**：
   - 使用清晰的 Markdown 多層次標題（##, ###, ####）
   - 按照演講邏輯順序組織內容
   - 每個主題都要有**完整詳細的內容展開**
   - 創建清晰的章節分隔和過渡

### 5. **醫學專業性強化**：
   - 保持醫學術語的**絕對準確性**（提供中英文對照）
   - **完整記錄所有臨床數據**和研究結果
   - **保留所有統計學意義**和 p 值
   - **記錄所有建議等級**（A、B、C級證據）

"""
        
        # 如果有議程內容，加入議程
        if agenda_content:
            prompt += f"""
### 6. **議程整合**：
   - **嚴格按照提供的議程內容來組織筆記結構**
   - 為每個議程項目創建對應的詳細章節
   - 確保涵蓋議程中的所有主要議題

**會議議程：**
{agenda_content}

"""
        
        prompt += f"""
**會議轉錄內容：**
{transcript}

## 整理指示：

請基於以上內容生成**詳細完整的會議筆記**（不是摘要）。筆記必須：

✅ **完整性**：儘可能保留演講者的所有內容，包括細節、例子、數據
✅ **結構化**：使用清晰的標題層次，邏輯分明
✅ **格式化**：大量使用 **粗體**、_斜體_、`數值標記` 等格式強調重點
✅ **專業性**：保持醫學術語準確，提供中英文對照
✅ **可讀性**：修飾語句使其流暢，但不改變原意
✅ **詳細度**：這是筆記整理，要比一般摘要更詳細 3-5 倍

現在開始整理詳細的會議筆記："""
        
        return prompt
    
    def save_results(self, file_name: str, transcript: str, summary: str, folder: Path) -> Dict[str, str]:
        """
        保存處理結果
        
        Args:
            file_name: 檔案名稱
            transcript: 轉錄內容
            summary: 摘要內容
            folder: 保存資料夾
            
        Returns:
            保存的檔案路徑字典
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_files = {}
        
        try:
            # 保存轉錄檔案
            transcript_file = folder / f"{file_name}_轉錄_{timestamp}.txt"
            with open(transcript_file, 'w', encoding='utf-8') as f:
                f.write(f"檔案名稱: {file_name}\n")
                f.write(f"轉錄時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"轉錄模型: gpt-transcribe\n")
                f.write("\n" + "="*50 + "\n")
                f.write("轉錄內容:\n\n")
                f.write(transcript)
            
            saved_files['transcript'] = str(transcript_file)
            
            # 保存摘要檔案 (Markdown)
            summary_file = folder / f"{file_name}_詳細筆記_{timestamp}.md"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"# {file_name} - 詳細會議筆記\n\n")
                f.write(f"**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**使用模型**: gemini-2.5-pro-preview-06-05\n")
                f.write(f"**筆記版本**: 增強版詳細筆記\n")
                f.write("\n" + "="*50 + "\n\n")
                f.write(summary)
            
            saved_files['summary_md'] = str(summary_file)
            
            # 生成 DOCX 格式
            try:
                from convert_summary_to_docx import MarkdownToDocxConverter
                
                converter = MarkdownToDocxConverter()
                converter.convert_markdown_to_docx(
                    markdown_content=summary,
                    title=f"{file_name} - 詳細會議筆記"
                )
                
                docx_file = folder / f"{file_name}_詳細筆記_{timestamp}.docx"
                converter.save_document(str(docx_file))
                
                saved_files['summary_docx'] = str(docx_file)
                
            except Exception as e:
                logger.warning(f"DOCX 生成失敗: {e}")
            
        except Exception as e:
            logger.error(f"保存結果時發生錯誤: {e}")
        
        return saved_files
    
    def process_folder(self, folder_path: Path) -> Dict[str, any]:
        """
        處理單一資料夾
        
        Args:
            folder_path: 資料夾路徑
            
        Returns:
            處理結果
        """
        result = {
            'folder_name': folder_path.name,
            'folder_path': str(folder_path),
            'audio_files_found': 0,
            'processed_files': 0,
            'failed_files': 0,
            'processing_time': 0,
            'success': False,
            'error': None,
            'processed_items': []
        }
        
        start_time = time.time()
        
        try:
            logger.info(f"處理資料夾: {folder_path.name}")
            
            # 尋找音訊檔案
            audio_files = self.find_audio_files(folder_path)
            result['audio_files_found'] = len(audio_files)
            
            if not audio_files:
                result['error'] = "未找到音訊檔案"
                return result
            
            logger.info(f"找到 {len(audio_files)} 個音訊檔案")
            
            # 處理每個音訊檔案
            for audio_file in audio_files:
                try:
                    logger.info(f"處理音訊檔案: {audio_file.name}")
                    
                    # 尋找議程檔案
                    agenda_file = self.find_agenda_file(audio_file)
                    agenda_content = None
                    
                    if agenda_file:
                        try:
                            with open(agenda_file, 'r', encoding='utf-8') as f:
                                agenda_content = f.read()
                            logger.info(f"找到議程檔案: {agenda_file.name}")
                        except Exception as e:
                            logger.warning(f"讀取議程檔案失敗: {e}")
                    
                    # 轉錄音訊
                    transcript_success, transcript_content, transcript_error = self.transcribe_audio(audio_file)
                    
                    if not transcript_success:
                        logger.error(f"轉錄失敗: {transcript_error}")
                        result['failed_files'] += 1
                        continue
                    
                    # 生成摘要
                    summary_success, summary_content, summary_error = self.generate_summary(
                        transcript_content, audio_file.stem, agenda_content
                    )
                    
                    if not summary_success:
                        logger.error(f"摘要生成失敗: {summary_error}")
                        result['failed_files'] += 1
                        continue
                    
                    # 保存結果
                    saved_files = self.save_results(
                        audio_file.stem, transcript_content, summary_content, folder_path
                    )
                    
                    result['processed_items'].append({
                        'audio_file': audio_file.name,
                        'agenda_file': agenda_file.name if agenda_file else None,
                        'saved_files': saved_files
                    })
                    
                    result['processed_files'] += 1
                    logger.info(f"✅ 成功處理: {audio_file.name}")
                    
                    # 添加延遲避免 API 限制
                    time.sleep(5)
                    
                except Exception as e:
                    logger.error(f"處理 {audio_file.name} 時發生錯誤: {e}")
                    result['failed_files'] += 1
            
            result['success'] = result['processed_files'] > 0
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"處理資料夾時發生錯誤: {e}")
        
        finally:
            result['processing_time'] = time.time() - start_time
        
        return result
    
    def batch_process_all_folders(self) -> Dict[str, any]:
        """
        批次處理所有資料夾
        
        Returns:
            批次處理結果
        """
        if not self.base_path.exists():
            return {
                'success': False,
                'error': f"基礎路徑不存在: {self.base_path}",
                'results': []
            }
        
        # 獲取所有子資料夾
        folders = []
        for item in self.base_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                folders.append(item)
        
        folders.sort(key=lambda x: x.name)
        
        logger.info(f"找到 {len(folders)} 個資料夾需要處理")
        
        # 處理統計
        total_start_time = time.time()
        results = []
        total_processed = 0
        total_failed = 0
        
        # 依序處理每個資料夾
        for i, folder in enumerate(folders, 1):
            logger.info(f"[{i}/{len(folders)}] 開始處理資料夾: {folder.name}")
            
            result = self.process_folder(folder)
            results.append(result)
            
            total_processed += result['processed_files']
            total_failed += result['failed_files']
            
            logger.info(f"資料夾處理完成: {result['processed_files']} 成功, {result['failed_files']} 失敗")
            
            # 在資料夾之間添加延遲
            if i < len(folders):
                logger.info("等待 10 秒後處理下一個資料夾...")
                time.sleep(10)
        
        # 生成總結報告
        total_time = time.time() - total_start_time
        
        batch_result = {
            'success': True,
            'total_time': total_time,
            'folders_processed': len(folders),
            'files_processed': total_processed,
            'files_failed': total_failed,
            'success_rate': (total_processed / (total_processed + total_failed) * 100) if (total_processed + total_failed) > 0 else 0,
            'results': results
        }
        
        # 保存詳細報告
        report_file = Path("temp/ada2025_batch_results") / f"batch_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(batch_result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"詳細報告已保存: {report_file}")
        
        return batch_result


def main():
    """主程式"""
    print("=== ADA2025 批次音訊處理器 ===")
    
    # 檢查必要的 API 金鑰
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ 未設定 OPENAI_API_KEY 環境變數")
        return False
    
    if not os.getenv('GOOGLE_API_KEY'):
        print("❌ 未設定 GOOGLE_API_KEY 環境變數")
        return False
    
    # 初始化處理器
    processor = ADA2025BatchProcessor()
    
    # 開始批次處理
    result = processor.batch_process_all_folders()
    
    if result['success']:
        print(f"\n{'='*80}")
        print("=== 批次處理完成 ===")
        print(f"⏱️ 總處理時間: {result['total_time']:.1f} 秒")
        print(f"📁 處理資料夾數: {result['folders_processed']}")
        print(f"✅ 成功處理檔案: {result['files_processed']}")
        print(f"❌ 失敗檔案: {result['files_failed']}")
        print(f"📊 成功率: {result['success_rate']:.1f}%")
        
        # 顯示成功處理的資料夾
        successful_folders = [r for r in result['results'] if r['success']]
        if successful_folders:
            print(f"\n✅ 成功處理的資料夾 ({len(successful_folders)}):")
            for folder_result in successful_folders:
                print(f"   - {folder_result['folder_name']}: {folder_result['processed_files']} 檔案")
        
        return True
    else:
        print(f"❌ 批次處理失敗: {result.get('error', '未知錯誤')}")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 使用者中斷處理")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 批次處理發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)