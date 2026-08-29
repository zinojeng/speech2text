"""
批次音訊處理系統 - 摘要服務包裝器
Summary Service Wrapper for Batch Audio Processing

此模組實作摘要服務包裝器，整合現有的 gemini_utils.py，
提供 ADA 2025 會議專用的智能摘要功能。

主要功能：
- 整合 Gemini API 進行智能摘要
- 支援議程內容整合
- 圖片標記處理
- 錯誤處理和重試機制

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.4, 8.2, 8.3
"""

import os
import re
import time
import logging
from typing import Optional, Dict, List, Any
from pathlib import Path
from dataclasses import dataclass

from ..core.models import (
    ProcessingConfig, 
    SummaryResult, 
    SummaryModel
)
from gemini_utils import call_gemini_api
from markitdown_utils import convert_file_to_markdown

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class SummaryRequest:
    """摘要請求資料類別"""
    transcript: str
    agenda_content: Optional[str] = None
    agenda_path: Optional[str] = None
    audio_folder: Optional[str] = None
    file_name: str = ""
    language: str = "zh"


class SummaryService:
    """
    摘要服務基礎類別
    
    整合現有的 gemini_utils.py，使用 gemini-2.5-pro-preview-06-05 模型，
    實作 ADA 2025 會議專用系統提示詞。
    
    Requirements: 3.1, 3.2, 3.3
    """
    
    def __init__(self, config: ProcessingConfig):
        """
        初始化摘要服務
        
        Args:
            config: 處理配置
        """
        self.config = config
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.model = config.summary_model.value
        self.retry_attempts = config.retry_attempts
        self.retry_delay = config.retry_delay
        
        # 驗證 API 金鑰
        if not self.api_key:
            logger.error("未找到 Google API 金鑰")
            raise ValueError("Google API 金鑰未設定")
        
        logger.info(f"摘要服務初始化完成，使用模型: {self.model}")
    
    def process_agenda_file(self, agenda_path: str) -> Optional[str]:
        """
        處理議程檔案，支援多種格式
        
        Args:
            agenda_path: 議程檔案路徑
            
        Returns:
            議程內容文字，失敗時返回 None
        """
        try:
            if not os.path.exists(agenda_path):
                logger.warning(f"議程檔案不存在: {agenda_path}")
                return None
            
            file_path = Path(agenda_path)
            file_extension = file_path.suffix.lower()
            
            # 支援的文字檔案格式
            text_extensions = {'.txt', '.md', '.rtf'}
            
            # 直接讀取純文字檔案
            if file_extension in text_extensions:
                try:
                    with open(agenda_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    if content:
                        logger.info(f"成功讀取議程檔案: {file_path.name}")
                        return content
                except UnicodeDecodeError:
                    # 嘗試其他編碼
                    try:
                        with open(agenda_path, 'r', encoding='big5') as f:
                            content = f.read().strip()
                        if content:
                            logger.info(f"成功讀取議程檔案 (Big5 編碼): {file_path.name}")
                            return content
                    except:
                        pass
            
            # 使用 markitdown_utils 處理其他格式
            logger.info(f"使用 MarkItDown 處理議程檔案: {file_path.name}")
            success, content, info = convert_file_to_markdown(agenda_path)
            
            if success and content.strip():
                logger.info(f"成功轉換議程檔案: {file_path.name} (長度: {len(content)})")
                return content.strip()
            else:
                logger.warning(f"議程檔案轉換失敗: {info.get('error', '未知錯誤')}")
                return None
                
        except Exception as e:
            logger.error(f"處理議程檔案時發生錯誤: {e}")
            return None
    
    def merge_transcript_and_agenda(self, transcript: str, agenda_content: str) -> str:
        """
        合併轉錄文字和議程內容
        
        Args:
            transcript: 轉錄文字
            agenda_content: 議程內容
            
        Returns:
            合併後的內容
        """
        try:
            # 清理和格式化議程內容
            cleaned_agenda = self._clean_agenda_content(agenda_content)
            
            # 分析議程結構
            agenda_structure = self._analyze_agenda_structure(cleaned_agenda)
            
            # 智能合併邏輯
            merged_content = self._intelligent_merge(transcript, cleaned_agenda, agenda_structure)
            
            logger.info("成功合併轉錄文字和議程內容")
            return merged_content
            
        except Exception as e:
            logger.error(f"合併轉錄文字和議程內容時發生錯誤: {e}")
            # 如果合併失敗，返回簡單組合
            return f"議程內容：\n{agenda_content}\n\n轉錄內容：\n{transcript}"
    
    def _clean_agenda_content(self, agenda_content: str) -> str:
        """
        清理議程內容，移除不必要的格式
        
        Args:
            agenda_content: 原始議程內容
            
        Returns:
            清理後的議程內容
        """
        # 移除過多的空行
        lines = agenda_content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped_line = line.strip()
            if stripped_line:
                cleaned_lines.append(stripped_line)
            elif cleaned_lines and cleaned_lines[-1]:  # 保留單個空行作為分隔
                cleaned_lines.append('')
        
        # 移除 Markdown 格式標記（保留結構）
        cleaned_content = '\n'.join(cleaned_lines)
        
        # 移除多餘的 Markdown 標記
        cleaned_content = re.sub(r'^#+\s*', '', cleaned_content, flags=re.MULTILINE)
        cleaned_content = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned_content)
        cleaned_content = re.sub(r'\*(.*?)\*', r'\1', cleaned_content)
        
        return cleaned_content.strip()
    
    def _analyze_agenda_structure(self, agenda_content: str) -> Dict[str, Any]:
        """
        分析議程結構
        
        Args:
            agenda_content: 議程內容
            
        Returns:
            議程結構分析結果
        """
        structure = {
            'has_time_slots': False,
            'has_speakers': False,
            'has_topics': False,
            'sections': [],
            'time_pattern': None
        }
        
        lines = agenda_content.split('\n')
        
        # 檢測時間格式
        time_patterns = [
            r'\d{1,2}:\d{2}',  # 09:00
            r'\d{1,2}:\d{2}-\d{1,2}:\d{2}',  # 09:00-10:00
            r'\d{1,2}:\d{2}~\d{1,2}:\d{2}',  # 09:00~10:00
            r'\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}',  # 09:00 - 10:00
        ]
        
        for pattern in time_patterns:
            if re.search(pattern, agenda_content):
                structure['has_time_slots'] = True
                structure['time_pattern'] = pattern
                break
        
        # 檢測講者資訊
        speaker_keywords = ['講者', '主講', '演講者', '報告人', 'Speaker', 'Dr.', '教授', '醫師']
        for keyword in speaker_keywords:
            if keyword in agenda_content:
                structure['has_speakers'] = True
                break
        
        # 檢測主題結構
        topic_keywords = ['主題', '議題', '討論', '報告', 'Topic', 'Session']
        for keyword in topic_keywords:
            if keyword in agenda_content:
                structure['has_topics'] = True
                break
        
        # 分析章節
        current_section = ""
        for line in lines:
            line = line.strip()
            if line and (line.startswith('第') or line.startswith('Session') or 
                        re.match(r'^\d+\.', line)):
                if current_section:
                    structure['sections'].append(current_section)
                current_section = line
            elif line and current_section:
                current_section += f"\n{line}"
        
        if current_section:
            structure['sections'].append(current_section)
        
        return structure
    
    def _intelligent_merge(self, transcript: str, agenda: str, structure: Dict[str, Any]) -> str:
        """
        智能合併轉錄文字和議程內容
        
        Args:
            transcript: 轉錄文字
            agenda: 議程內容
            structure: 議程結構分析
            
        Returns:
            智能合併後的內容
        """
        # 如果議程有明確的時間結構，嘗試按時間對應
        if structure['has_time_slots'] and structure['sections']:
            return self._merge_with_time_structure(transcript, agenda, structure)
        
        # 如果議程有主題結構，嘗試按主題對應
        elif structure['has_topics'] and structure['sections']:
            return self._merge_with_topic_structure(transcript, agenda, structure)
        
        # 簡單合併
        else:
            return self._simple_merge(transcript, agenda)
    
    def _merge_with_time_structure(self, transcript: str, agenda: str, structure: Dict[str, Any]) -> str:
        """
        按時間結構合併內容
        """
        merged_parts = []
        merged_parts.append("# 會議內容摘要")
        merged_parts.append("\n## 會議議程")
        merged_parts.append(agenda)
        merged_parts.append("\n## 會議記錄")
        merged_parts.append("以下是根據議程時間安排的會議記錄內容：")
        merged_parts.append(transcript)
        
        return '\n\n'.join(merged_parts)
    
    def _merge_with_topic_structure(self, transcript: str, agenda: str, structure: Dict[str, Any]) -> str:
        """
        按主題結構合併內容
        """
        merged_parts = []
        merged_parts.append("# 會議內容摘要")
        merged_parts.append("\n## 會議議程")
        merged_parts.append(agenda)
        merged_parts.append("\n## 詳細內容")
        merged_parts.append("以下是根據議程主題的詳細會議內容：")
        merged_parts.append(transcript)
        
        return '\n\n'.join(merged_parts)
    
    def _simple_merge(self, transcript: str, agenda: str) -> str:
        """
        簡單合併內容
        """
        merged_parts = []
        merged_parts.append("# 會議內容")
        merged_parts.append("\n## 議程")
        merged_parts.append(agenda)
        merged_parts.append("\n## 會議記錄")
        merged_parts.append(transcript)
        
        return '\n\n'.join(merged_parts)
    
    def format_chinese_output(self, content: str) -> str:
        """
        格式化中文輸出
        
        Args:
            content: 原始內容
            
        Returns:
            格式化後的中文內容
        """
        try:
            # 修正中文標點符號
            content = self._fix_chinese_punctuation(content)
            
            # 調整中英文混排格式
            content = self._format_mixed_language(content)
            
            # 優化段落結構
            content = self._optimize_paragraph_structure(content)
            
            logger.info("中文輸出格式化完成")
            return content
            
        except Exception as e:
            logger.error(f"中文輸出格式化失敗: {e}")
            return content
    
    def _fix_chinese_punctuation(self, content: str) -> str:
        """修正中文標點符號"""
        # 替換英文標點為中文標點
        replacements = {
            ',': '，',
            ';': '；',
            ':': '：',
            '!': '！',
            '?': '？',
            '(': '（',
            ')': '）'
        }
        
        for eng, chi in replacements.items():
            # 只在中文語境中替換
            content = re.sub(f'([\\u4e00-\\u9fff]){re.escape(eng)}', f'\\1{chi}', content)
            content = re.sub(f'{re.escape(eng)}([\\u4e00-\\u9fff])', f'{chi}\\1', content)
        
        return content
    
    def _format_mixed_language(self, content: str) -> str:
        """格式化中英文混排"""
        # 在中英文之間添加適當的空格
        content = re.sub(r'([\\u4e00-\\u9fff])([a-zA-Z])', r'\\1 \\2', content)
        content = re.sub(r'([a-zA-Z])([\\u4e00-\\u9fff])', r'\\1 \\2', content)
        
        # 在中文和數字之間添加空格
        content = re.sub(r'([\\u4e00-\\u9fff])([0-9])', r'\\1 \\2', content)
        content = re.sub(r'([0-9])([\\u4e00-\\u9fff])', r'\\1 \\2', content)
        
        return content
    
    def _optimize_paragraph_structure(self, content: str) -> str:
        """優化段落結構"""
        # 移除多餘的空行
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 確保標題前後有適當的空行
        content = re.sub(r'\n(#+\s+)', r'\n\n\\1', content)
        content = re.sub(r'(#+\s+.*?)\n([^#\n])', r'\\1\n\n\\2', content)
        
        return content.strip()
    
    def generate_summary(self, request: SummaryRequest) -> SummaryResult:
        """
        生成智能摘要，整合議程內容
        
        Args:
            request: 摘要請求
            
        Returns:
            摘要結果
        """
        start_time = time.time()
        
        try:
            # 處理議程內容（如果有議程檔案路徑但沒有內容）
            agenda_content = request.agenda_content
            if not agenda_content and hasattr(request, 'agenda_path') and request.agenda_path:
                agenda_content = self.process_agenda_file(request.agenda_path)
            
            # 如果有議程內容，進行智能合併
            if agenda_content:
                merged_content = self.merge_transcript_and_agenda(
                    request.transcript, agenda_content
                )
                # 更新請求中的議程內容
                enhanced_request = SummaryRequest(
                    transcript=merged_content,
                    agenda_content=agenda_content,
                    audio_folder=request.audio_folder,
                    file_name=request.file_name,
                    language=request.language
                )
            else:
                enhanced_request = request
            
            # 構建提示詞
            prompt = self._build_prompt(enhanced_request)
            
            # 呼叫 Gemini API 進行摘要
            summary_content = self._call_gemini_with_retry(prompt)
            
            if not summary_content:
                # 嘗試備用策略
                logger.warning("主要摘要生成失敗，嘗試備用策略")
                fallback_result = self.apply_fallback_strategy(
                    enhanced_request, 
                    {'fallback_strategy': 'simple_summary'}
                )
                
                if fallback_result and fallback_result.success:
                    return fallback_result
                
                return SummaryResult(
                    success=False,
                    error="Gemini API 返回空結果，備用策略也失敗",
                    processing_time=time.time() - start_time,
                    model_used=self.model
                )
            
            # 格式化中文輸出
            summary_content = self.format_chinese_output(summary_content)
            
            # 處理圖片標記（如果有音訊資料夾）
            images_inserted = 0
            if request.audio_folder:
                summary_content, images_inserted = self._insert_image_markers(
                    summary_content, request.audio_folder
                )
            
            processing_time = time.time() - start_time
            
            return SummaryResult(
                success=True,
                content=summary_content,
                processing_time=processing_time,
                model_used=self.model,
                agenda_used=bool(agenda_content),
                images_inserted=images_inserted
            )
            
        except Exception as e:
            logger.error(f"摘要生成失敗: {e}")
            
            # 嘗試錯誤恢復
            recovery_result = self._attempt_error_recovery(enhanced_request, e, start_time)
            if recovery_result:
                return recovery_result
            
            return SummaryResult(
                success=False,
                error=str(e),
                processing_time=time.time() - start_time,
                model_used=self.model
            )
    
    def _attempt_error_recovery(self, request: SummaryRequest, error: Exception, start_time: float) -> Optional[SummaryResult]:
        """
        嘗試錯誤恢復
        
        Args:
            request: 摘要請求
            error: 發生的錯誤
            start_time: 開始時間
            
        Returns:
            恢復結果，如果無法恢復則返回 None
        """
        try:
            logger.info("嘗試錯誤恢復...")
            
            # 分析錯誤
            error_info = self.handle_api_failure(error, 1)
            
            # 嘗試備用策略
            fallback_result = self.apply_fallback_strategy(request, error_info)
            
            if fallback_result and fallback_result.success:
                # 標記為恢復結果
                fallback_result.model_used = f"{fallback_result.model_used} (錯誤恢復)"
                logger.info("錯誤恢復成功")
                return fallback_result
            
            # 如果備用策略也失敗，生成簡單摘要
            logger.info("備用策略失敗，生成簡單摘要")
            simple_result = self._generate_simple_summary(request)
            
            if simple_result.success:
                simple_result.processing_time = time.time() - start_time
                logger.info("簡單摘要生成成功")
                return simple_result
            
        except Exception as recovery_error:
            logger.error(f"錯誤恢復失敗: {recovery_error}")
        
        return None
    
    def _build_prompt(self, request: SummaryRequest) -> str:
        """
        構建 ADA 2025 會議專用系統提示詞
        
        Args:
            request: 摘要請求
            
        Returns:
            完整的提示詞
        """
        # ADA 2025 會議專用系統提示詞
        system_prompt = """你是一個專業的醫學會議摘要助手，專門處理 ADA 2025（美國糖尿病學會年會）的會議內容。

請根據以下轉錄內容生成專業的中文摘要，要求：

1. **結構化摘要**：
   - 使用清晰的標題和子標題
   - 採用 Markdown 格式
   - 保持邏輯層次分明

2. **內容要求**：
   - 重點突出糖尿病相關的臨床發現
   - 強調新藥物、新療法或新指引
   - 包含重要的統計數據和研究結果
   - 保留關鍵的醫學術語（中英文對照）

3. **格式要求**：
   - 使用 **粗體** 標記重要概念
   - 使用 _斜體_ 標記藥物名稱
   - 使用項目符號列出要點
   - 適當使用表格整理數據

4. **專業性**：
   - 保持醫學專業用語的準確性
   - 確保內容的科學性和客觀性
   - 避免過度簡化複雜的醫學概念

"""
        
        # 如果有議程內容，加入議程整合指示
        if request.agenda_content:
            system_prompt += """
5. **議程整合**：
   - 參考提供的議程內容來組織摘要結構
   - 確保摘要涵蓋議程中的主要議題
   - 將轉錄內容與議程項目對應
"""
        
        # 構建完整提示詞
        full_prompt = system_prompt + "\n\n"
        
        # 添加議程內容（如果有）
        if request.agenda_content:
            full_prompt += f"**會議議程：**\n{request.agenda_content}\n\n"
        
        # 添加轉錄內容
        full_prompt += f"**會議轉錄內容：**\n{request.transcript}\n\n"
        
        # 添加生成指示
        full_prompt += """請基於以上內容生成專業的中文摘要。摘要應該：
- 完整涵蓋重要內容
- 結構清晰易讀
- 突出臨床意義
- 保持專業水準

開始生成摘要："""
        
        return full_prompt
    
    def _call_gemini_with_retry(self, prompt: str) -> Optional[str]:
        """
        帶重試機制的 Gemini API 呼叫
        
        Args:
            prompt: 提示詞
            
        Returns:
            生成的內容，失敗時返回 None
        """
        last_error = None
        
        for attempt in range(self.retry_attempts + 1):
            try:
                if attempt > 0:
                    # 指數退避延遲
                    if self.config.exponential_backoff:
                        delay = self.retry_delay * (2 ** (attempt - 1))
                    else:
                        delay = self.retry_delay
                    
                    logger.info(f"重試第 {attempt} 次，延遲 {delay:.1f} 秒")
                    time.sleep(delay)
                
                # 呼叫 Gemini API
                result = call_gemini_api(
                    prompt=prompt,
                    model=self.model,
                    api_key=self.api_key
                )
                
                if result:
                    logger.info(f"Gemini API 呼叫成功（第 {attempt + 1} 次嘗試）")
                    return result
                else:
                    last_error = Exception("API 返回空結果")
                    logger.warning(f"Gemini API 返回空結果（第 {attempt + 1} 次嘗試）")
                
            except Exception as e:
                last_error = e
                logger.warning(f"Gemini API 呼叫失敗（第 {attempt + 1} 次嘗試）: {e}")
                
                # 分析錯誤並決定是否重試
                error_info = self.handle_api_failure(e, attempt + 1)
                
                if not error_info['is_retryable']:
                    logger.error(f"遇到不可重試的錯誤: {e}")
                    break
                
                # 根據錯誤類型調整延遲
                if error_info['suggested_delay'] != self.retry_delay:
                    self.retry_delay = error_info['suggested_delay']
        
        logger.error(f"Gemini API 呼叫最終失敗: {last_error}")
        return None
    
    def _is_non_retryable_error(self, error: Exception) -> bool:
        """
        判斷是否為不可重試的錯誤
        
        Args:
            error: 異常對象
            
        Returns:
            如果是不可重試的錯誤返回 True
        """
        error_str = str(error).lower()
        
        # API 金鑰相關錯誤
        if any(keyword in error_str for keyword in [
            'api key', 'authentication', 'unauthorized', 'invalid key'
        ]):
            return True
        
        # 配額相關錯誤（可重試，但需要更長延遲）
        if any(keyword in error_str for keyword in [
            'quota', 'rate limit', 'too many requests'
        ]):
            return False
        
        # 內容相關錯誤
        if any(keyword in error_str for keyword in [
            'content policy', 'safety', 'blocked'
        ]):
            return True
        
        # 其他錯誤預設為可重試
        return False
    
    def _insert_image_markers(self, content: str, audio_folder: str) -> tuple[str, int]:
        """
        在摘要中插入圖片標記
        
        Args:
            content: 摘要內容
            audio_folder: 音訊檔案所在資料夾
            
        Returns:
            (處理後的內容, 插入的圖片數量)
        """
        try:
            # 搜尋可能的圖片檔案
            image_files = self._find_image_files(audio_folder)
            
            if not image_files:
                logger.info("未找到圖片檔案")
                return content, 0
            
            # 在適當位置插入圖片標記
            processed_content, inserted_count = self._process_image_insertion(
                content, image_files
            )
            
            logger.info(f"成功插入 {inserted_count} 個圖片標記")
            return processed_content, inserted_count
            
        except Exception as e:
            logger.error(f"圖片標記處理失敗: {e}")
            return content, 0
    
    def _find_image_files(self, folder_path: str) -> List[Dict[str, str]]:
        """
        搜尋資料夾中的圖片檔案，包含存在性檢查
        
        Args:
            folder_path: 資料夾路徑
            
        Returns:
            圖片檔案資訊列表，每個元素包含 'path', 'name', 'exists' 等資訊
        """
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.tiff', '.tif'}
        image_files = []
        
        try:
            folder = Path(folder_path)
            if not folder.exists():
                logger.warning(f"資料夾不存在: {folder_path}")
                return image_files
            
            # 搜尋圖片檔案
            for file_path in folder.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    # 檢查檔案是否真的存在且可讀取
                    file_exists = file_path.exists() and file_path.is_file()
                    file_readable = False
                    
                    if file_exists:
                        try:
                            # 嘗試讀取檔案的前幾個位元組來確認可讀性
                            with open(file_path, 'rb') as f:
                                f.read(10)
                            file_readable = True
                        except:
                            file_readable = False
                    
                    # 使用相對路徑
                    relative_path = file_path.relative_to(folder)
                    
                    image_info = {
                        'path': str(relative_path),
                        'full_path': str(file_path),
                        'name': file_path.name,
                        'stem': file_path.stem,
                        'exists': file_exists,
                        'readable': file_readable,
                        'size': file_path.stat().st_size if file_exists else 0,
                        'extension': file_path.suffix.lower()
                    }
                    
                    image_files.append(image_info)
            
            # 按檔名排序
            image_files.sort(key=lambda x: x['name'])
            
            # 統計資訊
            total_files = len(image_files)
            valid_files = len([f for f in image_files if f['exists'] and f['readable']])
            
            logger.info(f"找到 {total_files} 個圖片檔案，其中 {valid_files} 個有效")
            
            if total_files != valid_files:
                invalid_files = [f['name'] for f in image_files if not (f['exists'] and f['readable'])]
                logger.warning(f"無效的圖片檔案: {', '.join(invalid_files)}")
            
        except Exception as e:
            logger.error(f"搜尋圖片檔案時發生錯誤: {e}")
        
        return image_files
    
    def _process_image_insertion(self, content: str, image_files: List[Dict[str, str]]) -> tuple[str, int]:
        """
        處理圖片插入邏輯，生成 Markdown 格式圖片連結
        
        Args:
            content: 原始內容
            image_files: 圖片檔案資訊列表
            
        Returns:
            (處理後的內容, 插入的圖片數量)
        """
        if not image_files:
            return content, 0
        
        # 只使用有效的圖片檔案
        valid_images = [img for img in image_files if img['exists'] and img['readable']]
        
        if not valid_images:
            logger.warning("沒有有效的圖片檔案可插入")
            return content, 0
        
        # 分割內容為段落
        paragraphs = content.split('\n\n')
        processed_paragraphs = []
        inserted_count = 0
        image_index = 0
        
        for i, paragraph in enumerate(paragraphs):
            processed_paragraphs.append(paragraph)
            
            # 在適當的段落後插入圖片
            if self._should_insert_image(paragraph, i, len(paragraphs)):
                if image_index < len(valid_images):
                    image_info = valid_images[image_index]
                    
                    # 生成 Markdown 圖片連結
                    image_marker = self._generate_image_markdown(image_info, image_index + 1)
                    processed_paragraphs.append(image_marker)
                    inserted_count += 1
                    image_index += 1
        
        # 如果還有剩餘圖片，在最後添加
        while image_index < len(valid_images):
            image_info = valid_images[image_index]
            image_marker = self._generate_image_markdown(image_info, image_index + 1)
            processed_paragraphs.append(image_marker)
            inserted_count += 1
            image_index += 1
        
        return '\n\n'.join(processed_paragraphs), inserted_count
    
    def _generate_image_markdown(self, image_info: Dict[str, str], sequence: int) -> str:
        """
        生成 Markdown 格式的圖片連結
        
        Args:
            image_info: 圖片資訊
            sequence: 圖片序號
            
        Returns:
            Markdown 格式的圖片連結
        """
        # 生成圖片描述
        alt_text = f"投影片 {sequence}"
        
        # 如果檔名包含有意義的資訊，加入描述
        stem = image_info['stem']
        if stem and not stem.isdigit():
            # 移除常見的檔名前綴
            clean_stem = re.sub(r'^(slide|img|image|pic|picture)[-_]?', '', stem, flags=re.IGNORECASE)
            if clean_stem:
                alt_text += f" - {clean_stem}"
        
        # 生成圖片路徑（使用相對路徑）
        image_path = image_info['path']
        
        # 生成完整的 Markdown 圖片標記
        markdown = f"\n\n![{alt_text}]({image_path})"
        
        # 添加圖片資訊註釋（可選）
        if image_info['size'] > 0:
            size_mb = image_info['size'] / (1024 * 1024)
            if size_mb > 0.1:  # 只顯示大於 0.1MB 的檔案大小
                markdown += f"\n*圖片大小: {size_mb:.1f}MB*"
        
        markdown += "\n"
        
        return markdown
    
    def _should_insert_image(self, paragraph: str, index: int, total: int) -> bool:
        """
        判斷是否應該在此段落後插入圖片
        
        Args:
            paragraph: 段落內容
            index: 段落索引
            total: 總段落數
            
        Returns:
            是否應該插入圖片
        """
        # 跳過太短的段落
        if len(paragraph.strip()) < 50:
            return False
        
        # 在標題後插入
        if paragraph.strip().startswith('#'):
            return True
        
        # 在包含特定關鍵詞的段落後插入
        keywords = ['結果', '數據', '研究', '發現', '結論', '圖表', '統計']
        if any(keyword in paragraph for keyword in keywords):
            return True
        
        # 定期插入（每3-4個段落）
        if index > 0 and index % 3 == 0:
            return True
        
        return False
    
    def validate_image_files(self, folder_path: str) -> Dict[str, Any]:
        """
        驗證圖片檔案的存在性和可讀性
        
        Args:
            folder_path: 資料夾路徑
            
        Returns:
            驗證結果統計
        """
        validation_result = {
            'folder_exists': False,
            'total_images': 0,
            'valid_images': 0,
            'invalid_images': 0,
            'image_formats': {},
            'total_size_mb': 0.0,
            'issues': []
        }
        
        try:
            folder = Path(folder_path)
            validation_result['folder_exists'] = folder.exists()
            
            if not folder.exists():
                validation_result['issues'].append(f"資料夾不存在: {folder_path}")
                return validation_result
            
            # 搜尋圖片檔案
            image_files = self._find_image_files(folder_path)
            validation_result['total_images'] = len(image_files)
            
            valid_count = 0
            total_size = 0
            format_count = {}
            
            for img_info in image_files:
                if img_info['exists'] and img_info['readable']:
                    valid_count += 1
                    total_size += img_info['size']
                    
                    # 統計格式
                    ext = img_info['extension']
                    format_count[ext] = format_count.get(ext, 0) + 1
                else:
                    validation_result['issues'].append(
                        f"無效圖片: {img_info['name']} "
                        f"(存在: {img_info['exists']}, 可讀: {img_info['readable']})"
                    )
            
            validation_result['valid_images'] = valid_count
            validation_result['invalid_images'] = len(image_files) - valid_count
            validation_result['image_formats'] = format_count
            validation_result['total_size_mb'] = total_size / (1024 * 1024)
            
            logger.info(f"圖片檔案驗證完成: {valid_count}/{len(image_files)} 有效")
            
        except Exception as e:
            validation_result['issues'].append(f"驗證過程發生錯誤: {e}")
            logger.error(f"圖片檔案驗證失敗: {e}")
        
        return validation_result
    
    def generate_image_gallery_markdown(self, folder_path: str) -> str:
        """
        生成圖片畫廊的 Markdown 內容
        
        Args:
            folder_path: 圖片資料夾路徑
            
        Returns:
            圖片畫廊的 Markdown 內容
        """
        try:
            image_files = self._find_image_files(folder_path)
            valid_images = [img for img in image_files if img['exists'] and img['readable']]
            
            if not valid_images:
                return "<!-- 未找到有效的圖片檔案 -->"
            
            gallery_parts = []
            gallery_parts.append("## 相關圖片")
            gallery_parts.append("")
            
            for i, img_info in enumerate(valid_images, 1):
                markdown = self._generate_image_markdown(img_info, i)
                gallery_parts.append(markdown.strip())
            
            return '\n'.join(gallery_parts)
            
        except Exception as e:
            logger.error(f"生成圖片畫廊失敗: {e}")
            return f"<!-- 生成圖片畫廊時發生錯誤: {e} -->"
    
    def validate_summary_quality(self, summary: SummaryResult) -> Dict[str, Any]:
        """
        驗證摘要品質
        
        Args:
            summary: 摘要結果
            
        Returns:
            品質驗證結果
        """
        quality_metrics = {
            'has_content': False,
            'has_structure': False,
            'has_medical_terms': False,
            'appropriate_length': False,
            'has_formatting': False,
            'language_quality': False,
            'completeness': False,
            'overall_score': 0.0,
            'issues': [],
            'recommendations': []
        }
        
        if not summary.success or not summary.content:
            quality_metrics['issues'].append("摘要生成失敗或內容為空")
            return quality_metrics
        
        content = summary.content
        content_length = len(content.strip())
        
        # 檢查是否有內容
        quality_metrics['has_content'] = content_length > 100
        if not quality_metrics['has_content']:
            quality_metrics['issues'].append(f"內容過短 ({content_length} 字符)")
            quality_metrics['recommendations'].append("增加更詳細的內容描述")
        
        # 檢查是否有結構（標題）
        title_matches = re.findall(r'^#+\s+', content, re.MULTILINE)
        quality_metrics['has_structure'] = len(title_matches) >= 2
        if not quality_metrics['has_structure']:
            quality_metrics['issues'].append(f"結構不清晰 (只有 {len(title_matches)} 個標題)")
            quality_metrics['recommendations'].append("添加更多章節標題來組織內容")
        
        # 檢查是否包含醫學術語
        medical_terms = ['糖尿病', '血糖', '胰島素', '藥物', '治療', '患者', '臨床', '研究', 
                        '療法', '診斷', '症狀', '併發症', '預防', '管理', '指引']
        found_terms = [term for term in medical_terms if term in content]
        quality_metrics['has_medical_terms'] = len(found_terms) >= 3
        if not quality_metrics['has_medical_terms']:
            quality_metrics['issues'].append(f"醫學術語不足 (只找到 {len(found_terms)} 個)")
            quality_metrics['recommendations'].append("增加更多相關的醫學專業術語")
        
        # 檢查長度是否適當（500-5000字符）
        quality_metrics['appropriate_length'] = 500 <= content_length <= 5000
        if content_length < 500:
            quality_metrics['issues'].append("內容過短，可能缺少重要資訊")
            quality_metrics['recommendations'].append("擴展內容，添加更多細節")
        elif content_length > 5000:
            quality_metrics['issues'].append("內容過長，可能包含冗餘資訊")
            quality_metrics['recommendations'].append("精簡內容，突出重點")
        
        # 檢查是否有格式化（粗體、斜體等）
        formatting_patterns = [
            r'\*\*.*?\*\*',  # 粗體
            r'_.*?_',        # 斜體
            r'\*.*?\*',      # 斜體
            r'`.*?`',        # 代碼
            r'^\s*[-*+]\s+', # 列表
            r'^\s*\d+\.\s+'  # 編號列表
        ]
        formatting_count = sum(1 for pattern in formatting_patterns 
                             if re.search(pattern, content, re.MULTILINE))
        quality_metrics['has_formatting'] = formatting_count >= 2
        if not quality_metrics['has_formatting']:
            quality_metrics['issues'].append("格式化不足，影響可讀性")
            quality_metrics['recommendations'].append("使用粗體、列表等格式突出重點")
        
        # 檢查語言品質
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        total_chars = len(re.sub(r'\s', '', content))
        chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0
        quality_metrics['language_quality'] = chinese_ratio > 0.7
        if not quality_metrics['language_quality']:
            quality_metrics['issues'].append(f"中文內容比例偏低 ({chinese_ratio:.1%})")
            quality_metrics['recommendations'].append("確保主要內容使用中文表達")
        
        # 檢查完整性（是否有結論或總結）
        conclusion_keywords = ['結論', '總結', '摘要', '重點', '建議', '未來', '展望']
        quality_metrics['completeness'] = any(keyword in content for keyword in conclusion_keywords)
        if not quality_metrics['completeness']:
            quality_metrics['issues'].append("缺少結論或總結部分")
            quality_metrics['recommendations'].append("添加結論或重點總結")
        
        # 計算總體分數
        boolean_metrics = ['has_content', 'has_structure', 'has_medical_terms', 
                          'appropriate_length', 'has_formatting', 'language_quality', 'completeness']
        score = sum(1 for metric in boolean_metrics if quality_metrics[metric])
        quality_metrics['overall_score'] = score / len(boolean_metrics)
        
        # 品質等級
        if quality_metrics['overall_score'] >= 0.8:
            quality_metrics['grade'] = '優秀'
        elif quality_metrics['overall_score'] >= 0.6:
            quality_metrics['grade'] = '良好'
        elif quality_metrics['overall_score'] >= 0.4:
            quality_metrics['grade'] = '普通'
        else:
            quality_metrics['grade'] = '需改進'
        
        return quality_metrics
    
    def handle_api_failure(self, error: Exception, attempt: int) -> Dict[str, Any]:
        """
        處理 API 呼叫失敗
        
        Args:
            error: 異常對象
            attempt: 當前嘗試次數
            
        Returns:
            錯誤處理結果
        """
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'attempt': attempt,
            'is_retryable': True,
            'suggested_delay': self.retry_delay,
            'fallback_strategy': None
        }
        
        error_str = str(error).lower()
        
        # 分析錯誤類型
        if 'authentication' in error_str or 'api key' in error_str:
            error_info['error_type'] = 'AuthenticationError'
            error_info['is_retryable'] = False
            error_info['fallback_strategy'] = 'check_api_key'
            
        elif 'quota' in error_str or 'rate limit' in error_str:
            error_info['error_type'] = 'QuotaError'
            error_info['is_retryable'] = True
            error_info['suggested_delay'] = self.retry_delay * 3  # 更長的延遲
            error_info['fallback_strategy'] = 'wait_and_retry'
            
        elif 'timeout' in error_str or 'connection' in error_str:
            error_info['error_type'] = 'NetworkError'
            error_info['is_retryable'] = True
            error_info['suggested_delay'] = self.retry_delay * 2
            error_info['fallback_strategy'] = 'retry_with_backoff'
            
        elif 'content policy' in error_str or 'safety' in error_str:
            error_info['error_type'] = 'ContentPolicyError'
            error_info['is_retryable'] = False
            error_info['fallback_strategy'] = 'modify_content'
            
        elif 'model' in error_str or 'not found' in error_str:
            error_info['error_type'] = 'ModelError'
            error_info['is_retryable'] = False
            error_info['fallback_strategy'] = 'use_alternative_model'
            
        else:
            error_info['error_type'] = 'UnknownError'
            error_info['is_retryable'] = attempt < self.retry_attempts
            error_info['fallback_strategy'] = 'generic_retry'
        
        logger.warning(f"API 錯誤分析: {error_info}")
        return error_info
    
    def apply_fallback_strategy(self, request: SummaryRequest, error_info: Dict[str, Any]) -> Optional[SummaryResult]:
        """
        應用備用策略
        
        Args:
            request: 原始請求
            error_info: 錯誤資訊
            
        Returns:
            備用策略結果，如果沒有可用策略則返回 None
        """
        strategy = error_info.get('fallback_strategy')
        
        if strategy == 'use_alternative_model':
            # 嘗試使用備用模型
            return self._try_alternative_model(request)
            
        elif strategy == 'modify_content':
            # 修改內容以符合內容政策
            return self._try_modified_content(request)
            
        elif strategy == 'simple_summary':
            # 生成簡單摘要
            return self._generate_simple_summary(request)
            
        else:
            logger.info(f"沒有適用的備用策略: {strategy}")
            return None
    
    def _try_alternative_model(self, request: SummaryRequest) -> Optional[SummaryResult]:
        """
        嘗試使用備用模型
        """
        try:
            # 使用 Gemini 2.0 Flash 作為備用模型
            original_model = self.model
            self.model = SummaryModel.GEMINI_FLASH_LITE.value
            
            logger.info(f"嘗試使用備用模型: {self.model}")
            
            # 重新生成摘要
            result = self.generate_summary(request)
            
            # 恢復原始模型
            self.model = original_model
            
            if result.success:
                result.model_used = f"{result.model_used} (備用模型)"
                logger.info("備用模型生成摘要成功")
                return result
            
        except Exception as e:
            logger.error(f"備用模型也失敗: {e}")
        
        return None
    
    def _try_modified_content(self, request: SummaryRequest) -> Optional[SummaryResult]:
        """
        嘗試修改內容以符合內容政策
        """
        try:
            # 簡化轉錄內容，移除可能敏感的部分
            modified_transcript = self._sanitize_content(request.transcript)
            
            modified_request = SummaryRequest(
                transcript=modified_transcript,
                agenda_content=request.agenda_content,
                audio_folder=request.audio_folder,
                file_name=request.file_name,
                language=request.language
            )
            
            logger.info("嘗試使用修改後的內容生成摘要")
            return self.generate_summary(modified_request)
            
        except Exception as e:
            logger.error(f"修改內容策略失敗: {e}")
        
        return None
    
    def _sanitize_content(self, content: str) -> str:
        """
        清理內容，移除可能敏感的部分
        """
        # 移除可能的敏感詞彙或內容
        # 這裡可以根據實際需要添加更多的清理邏輯
        sanitized = content
        
        # 移除過長的段落（可能包含敏感內容）
        paragraphs = sanitized.split('\n\n')
        filtered_paragraphs = [p for p in paragraphs if len(p) < 1000]
        
        return '\n\n'.join(filtered_paragraphs)
    
    def _generate_simple_summary(self, request: SummaryRequest) -> SummaryResult:
        """
        生成簡單的摘要（不使用 AI）
        """
        try:
            # 提取關鍵資訊
            transcript = request.transcript
            
            # 簡單的關鍵詞提取
            medical_terms = ['糖尿病', '血糖', '胰島素', '藥物', '治療', '患者', '臨床', '研究']
            found_terms = [term for term in medical_terms if term in transcript]
            
            # 生成基本摘要
            summary_parts = []
            summary_parts.append("# 會議摘要")
            summary_parts.append("\n## 基本資訊")
            summary_parts.append(f"- 檔案: {request.file_name}")
            summary_parts.append(f"- 內容長度: {len(transcript)} 字符")
            
            if request.agenda_content:
                summary_parts.append("- 包含議程資訊")
            
            if found_terms:
                summary_parts.append("\n## 主要主題")
                for term in found_terms[:5]:  # 只顯示前5個
                    summary_parts.append(f"- {term}")
            
            summary_parts.append("\n## 內容概述")
            summary_parts.append("此為自動生成的基本摘要。由於 AI 摘要服務暫時不可用，")
            summary_parts.append("建議手動檢視完整的轉錄內容以獲取詳細資訊。")
            
            if request.agenda_content:
                summary_parts.append("\n## 議程資訊")
                summary_parts.append(request.agenda_content[:500] + "..." if len(request.agenda_content) > 500 else request.agenda_content)
            
            summary_content = '\n'.join(summary_parts)
            
            return SummaryResult(
                success=True,
                content=summary_content,
                processing_time=0.1,
                model_used="簡單摘要生成器",
                agenda_used=bool(request.agenda_content),
                images_inserted=0
            )
            
        except Exception as e:
            logger.error(f"簡單摘要生成失敗: {e}")
            return SummaryResult(
                success=False,
                error=f"簡單摘要生成失敗: {e}",
                processing_time=0.0
            )


if __name__ == "__main__":
    """測試摘要服務"""
    import logging
    
    # 設定日誌
    logging.basicConfig(level=logging.INFO)
    
    print("=== 摘要服務測試 ===\n")
    
    try:
        # 創建配置
        from batch_audio_models import ProcessingConfig
        config = ProcessingConfig()
        
        # 創建摘要服務
        summary_service = SummaryService(config)
        
        # 測試摘要請求
        test_request = SummaryRequest(
            transcript="這是一個關於糖尿病新藥物研究的會議內容。研究顯示新藥物能有效降低血糖水平，改善患者的生活品質。",
            agenda_content="1. 糖尿病新藥物介紹\n2. 臨床試驗結果\n3. 安全性評估",
            file_name="test_meeting"
        )
        
        # 生成摘要
        result = summary_service.generate_summary(test_request)
        
        if result.success:
            print("✅ 摘要生成成功")
            print(f"內容長度: {len(result.content)}")
            print(f"處理時間: {result.processing_time:.2f}秒")
            print(f"使用議程: {result.agenda_used}")
            
            # 驗證品質
            quality = summary_service.validate_summary_quality(result)
            print(f"品質分數: {quality['overall_score']:.2f}")
        else:
            print(f"❌ 摘要生成失敗: {result.error}")
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
    
    print("\n=== 測試完成 ===")