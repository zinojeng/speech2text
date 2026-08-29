"""
批次音訊處理系統 - 檔案發現和匹配服務
File Discovery and Matching Service for Batch Audio Processing

此模組實作檔案發現和匹配功能，包括：
- AudioFileScanner: 遞歸搜索音訊檔案
- AgendaFileMatcher: 匹配議程文字檔案
- FileDiscovery: 協調檔案發現和匹配

Requirements: 1.1, 1.2, 1.3, 4.1, 4.2, 4.3, 4.4, 4.5
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
import mimetypes

# 導入資料模型
from ..core.models import DiscoveryResult, FileInfo

# 設定日誌
logger = logging.getLogger(__name__)


class AudioFileScanner:
    """
    音訊檔案掃描器
    
    負責遞歸搜索指定資料夾中的音訊檔案
    Requirements: 1.1, 1.2, 1.3
    """
    
    # 支援的音訊格式
    SUPPORTED_AUDIO_FORMATS = {
        # 常見音訊格式
        '.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma',
        # 視訊格式（通常包含音訊）
        '.mp4', '.mov', '.avi', '.mkv', '.webm'
    }
    
    def __init__(self, skip_transcribed: bool = True):
        """
        初始化音訊檔案掃描器
        
        Args:
            skip_transcribed: 是否跳過已有轉錄檔案的音訊檔案
        """
        self.scanned_files = []
        self.total_size_mb = 0.0
        self.skip_transcribed = skip_transcribed
        self.skipped_files = []  # 記錄被跳過的檔案
        
    def scan_folder(self, folder_path: str, recursive: bool = True) -> List[str]:
        """
        掃描資料夾中的音訊檔案
        
        Args:
            folder_path: 要掃描的資料夾路徑
            recursive: 是否遞歸搜索子資料夾
            
        Returns:
            找到的音訊檔案路徑列表
            
        Requirements: 1.1, 1.2
        """
        try:
            folder_path = Path(folder_path).resolve()
            
            if not folder_path.exists():
                logger.error(f"資料夾不存在: {folder_path}")
                return []
            
            if not folder_path.is_dir():
                logger.error(f"路徑不是資料夾: {folder_path}")
                return []
            
            logger.info(f"開始掃描音訊檔案: {folder_path} (遞歸: {recursive})")
            
            audio_files = []
            total_size = 0.0
            
            # 選擇掃描方式
            if recursive:
                pattern = "**/*"
            else:
                pattern = "*"
            
            # 掃描檔案
            for file_path in folder_path.glob(pattern):
                if file_path.is_file():
                    if self._is_audio_file(file_path):
                        try:
                            # 檢查是否已有轉錄檔案
                            if self.skip_transcribed and self._has_transcription_file(file_path):
                                self.skipped_files.append(str(file_path))
                                logger.info(f"跳過已轉錄的音訊檔案: {file_path.name}")
                                continue
                            
                            # 驗證檔案
                            if self._validate_audio_file(file_path):
                                audio_files.append(str(file_path))
                                
                                # 計算檔案大小
                                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                                total_size += file_size_mb
                                
                                logger.debug(f"找到音訊檔案: {file_path.name} ({file_size_mb:.2f}MB)")
                            else:
                                logger.warning(f"音訊檔案驗證失敗: {file_path}")
                        except Exception as e:
                            logger.warning(f"處理檔案時發生錯誤 {file_path}: {e}")
            
            self.scanned_files = audio_files
            self.total_size_mb = total_size
            
            logger.info(f"掃描完成: 找到 {len(audio_files)} 個音訊檔案，總大小 {total_size:.2f}MB")
            
            return audio_files
            
        except Exception as e:
            logger.error(f"掃描資料夾時發生錯誤: {e}")
            return []
    
    def _is_audio_file(self, file_path: Path) -> bool:
        """
        檢查檔案是否為支援的音訊格式
        
        Args:
            file_path: 檔案路徑
            
        Returns:
            如果是支援的音訊格式則返回 True
            
        Requirements: 1.2
        """
        try:
            # 檢查副檔名
            file_extension = file_path.suffix.lower()
            
            if file_extension in self.SUPPORTED_AUDIO_FORMATS:
                return True
            
            # 使用 mimetypes 進行額外檢查
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type:
                if mime_type.startswith('audio/') or mime_type.startswith('video/'):
                    logger.debug(f"透過 MIME 類型識別音訊檔案: {file_path} ({mime_type})")
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"檢查檔案格式時發生錯誤 {file_path}: {e}")
            return False
    
    def _validate_audio_file(self, file_path: Path) -> bool:
        """
        驗證音訊檔案的有效性
        
        Args:
            file_path: 檔案路徑
            
        Returns:
            如果檔案有效則返回 True
            
        Requirements: 1.3
        """
        try:
            # 檢查檔案是否存在且可讀取
            if not file_path.exists():
                logger.warning(f"檔案不存在: {file_path}")
                return False
            
            if not file_path.is_file():
                logger.warning(f"不是檔案: {file_path}")
                return False
            
            # 檢查檔案大小
            file_size = file_path.stat().st_size
            if file_size == 0:
                logger.warning(f"檔案大小為 0: {file_path}")
                return False
            
            # 檢查檔案權限
            if not os.access(file_path, os.R_OK):
                logger.warning(f"檔案無法讀取: {file_path}")
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"驗證檔案時發生錯誤 {file_path}: {e}")
            return False
    
    def _has_transcription_file(self, audio_file_path: Path) -> bool:
        """
        檢查音訊檔案是否已有對應的轉錄檔案
        
        Args:
            audio_file_path: 音訊檔案路徑
            
        Returns:
            如果已有轉錄檔案則返回 True
        """
        try:
            # 取得音訊檔案的基本名稱（不含副檔名）
            base_name = audio_file_path.stem
            parent_dir = audio_file_path.parent
            
            # 定義可能的轉錄檔案模式
            transcription_patterns = [
                f"transcription_{base_name}.txt",
                f"transcription_{base_name}.md",
                f"transcription.txt",
                f"transcription.md",
                f"{base_name}_transcription.txt",
                f"{base_name}_transcription.md",
                f"{base_name}.txt",
                f"{base_name}.md"
            ]
            
            # 也檢查包含 "transcription" 的檔案（如 transcription-6.txt）
            for ext in ['.txt', '.md', '.srt']:
                for file_path in parent_dir.glob(f"*transcription*{ext}"):
                    if file_path.is_file() and file_path.stat().st_size > 0:
                        logger.debug(f"找到包含 transcription 的檔案: {file_path}")
                        return True
            
            # 檢查每個可能的轉錄檔案
            for pattern in transcription_patterns:
                transcription_file = parent_dir / pattern
                if transcription_file.exists() and transcription_file.is_file():
                    # 檢查檔案是否有內容（不是空檔案）
                    try:
                        if transcription_file.stat().st_size > 0:
                            logger.debug(f"找到轉錄檔案: {transcription_file}")
                            return True
                    except Exception as e:
                        logger.warning(f"檢查轉錄檔案時發生錯誤 {transcription_file}: {e}")
            
            # 也檢查同名但不同副檔名的檔案
            for ext in ['.txt', '.md']:
                transcription_file = parent_dir / f"{base_name}{ext}"
                if transcription_file.exists() and transcription_file.is_file():
                    try:
                        if transcription_file.stat().st_size > 0:
                            # 簡單檢查內容是否像轉錄檔案
                            content = transcription_file.read_text(encoding='utf-8', errors='ignore')[:200]
                            if len(content.strip()) > 50:  # 假設轉錄檔案至少有50個字符
                                logger.debug(f"找到可能的轉錄檔案: {transcription_file}")
                                return True
                    except Exception as e:
                        logger.warning(f"讀取可能的轉錄檔案時發生錯誤 {transcription_file}: {e}")
            
            return False
            
        except Exception as e:
            logger.warning(f"檢查轉錄檔案時發生錯誤: {e}")
            return False
    
    def get_skipped_files(self) -> List[str]:
        """
        取得被跳過的檔案列表
        
        Returns:
            被跳過的音訊檔案路徑列表
        """
        return self.skipped_files.copy()
    
    def get_file_info(self, file_path: str) -> Optional[FileInfo]:
        """
        取得檔案的詳細資訊
        
        Args:
            file_path: 檔案路徑
            
        Returns:
            FileInfo 物件，如果檔案無效則返回 None
        """
        try:
            path = Path(file_path)
            
            if not self._validate_audio_file(path):
                return None
            
            file_info = FileInfo(
                audio_path=str(path),
                audio_name=path.stem
            )
            
            return file_info
            
        except Exception as e:
            logger.error(f"取得檔案資訊時發生錯誤 {file_path}: {e}")
            return None
    
    def get_scan_summary(self) -> Dict[str, any]:
        """
        取得掃描結果摘要
        
        Returns:
            包含掃描統計資訊的字典
        """
        return {
            'total_files': len(self.scanned_files),
            'total_size_mb': self.total_size_mb,
            'supported_formats': list(self.SUPPORTED_AUDIO_FORMATS),
            'files': self.scanned_files
        }


class AgendaFileMatcher:
    """
    議程檔案匹配器
    
    負責尋找與音訊檔案對應的議程文字檔案
    Requirements: 4.1, 4.2, 4.3, 4.4
    """
    
    # 支援的文字檔案格式
    SUPPORTED_TEXT_FORMATS = {
        '.txt', '.md', '.rtf', '.doc', '.docx', '.pdf', 
        '.html', '.htm', '.xml', '.json', '.csv'
    }
    
    # 常見的議程檔案名稱
    COMMON_AGENDA_NAMES = {
        'agenda', 'schedule', 'program', 'programme',
        '議程', '議程表', '流程', '安排', '計畫'
    }
    
    def __init__(self):
        """初始化議程檔案匹配器"""
        self.text_files = []
        self.matched_pairs = {}
        
    def find_text_files(self, folder_path: str, recursive: bool = True) -> List[str]:
        """
        尋找資料夾中的文字檔案
        
        Args:
            folder_path: 要搜索的資料夾路徑
            recursive: 是否遞歸搜索子資料夾
            
        Returns:
            找到的文字檔案路徑列表
            
        Requirements: 4.2
        """
        try:
            folder_path = Path(folder_path).resolve()
            
            if not folder_path.exists() or not folder_path.is_dir():
                logger.warning(f"資料夾不存在或不是目錄: {folder_path}")
                return []
            
            logger.info(f"開始搜索文字檔案: {folder_path} (遞歸: {recursive})")
            
            text_files = []
            
            # 選擇搜索方式
            if recursive:
                pattern = "**/*"
            else:
                pattern = "*"
            
            # 搜索檔案
            for file_path in folder_path.glob(pattern):
                if file_path.is_file():
                    if self._is_text_file(file_path):
                        if self._validate_text_file(file_path):
                            text_files.append(str(file_path))
                            logger.debug(f"找到文字檔案: {file_path.name}")
            
            self.text_files = text_files
            logger.info(f"搜索完成: 找到 {len(text_files)} 個文字檔案")
            
            return text_files
            
        except Exception as e:
            logger.error(f"搜索文字檔案時發生錯誤: {e}")
            return []
    
    def _is_text_file(self, file_path: Path) -> bool:
        """
        檢查檔案是否為支援的文字格式
        
        Args:
            file_path: 檔案路徑
            
        Returns:
            如果是支援的文字格式則返回 True
            
        Requirements: 4.2
        """
        try:
            file_extension = file_path.suffix.lower()
            return file_extension in self.SUPPORTED_TEXT_FORMATS
            
        except Exception as e:
            logger.warning(f"檢查文字檔案格式時發生錯誤 {file_path}: {e}")
            return False
    
    def _validate_text_file(self, file_path: Path) -> bool:
        """
        驗證文字檔案的有效性
        
        Args:
            file_path: 檔案路徑
            
        Returns:
            如果檔案有效則返回 True
        """
        try:
            # 基本檢查
            if not file_path.exists() or not file_path.is_file():
                return False
            
            # 檢查檔案大小
            if file_path.stat().st_size == 0:
                logger.warning(f"文字檔案大小為 0: {file_path}")
                return False
            
            # 檢查讀取權限
            if not os.access(file_path, os.R_OK):
                logger.warning(f"文字檔案無法讀取: {file_path}")
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"驗證文字檔案時發生錯誤 {file_path}: {e}")
            return False
    
    def match_agenda_files(self, audio_files: List[str], text_files: List[str]) -> Dict[str, str]:
        """
        匹配音訊檔案和議程檔案
        
        Args:
            audio_files: 音訊檔案路徑列表
            text_files: 文字檔案路徑列表
            
        Returns:
            匹配結果字典 {音訊檔案路徑: 議程檔案路徑}
            
        Requirements: 4.1, 4.3, 4.4
        """
        try:
            logger.info(f"開始匹配 {len(audio_files)} 個音訊檔案和 {len(text_files)} 個文字檔案")
            
            matched_pairs = {}
            
            for audio_file in audio_files:
                audio_path = Path(audio_file)
                audio_name = audio_path.stem.lower()
                audio_dir = audio_path.parent
                
                # 1. 尋找同名檔案
                exact_match = self._find_exact_name_match(audio_name, text_files, audio_dir)
                if exact_match:
                    matched_pairs[audio_file] = exact_match
                    logger.debug(f"找到同名匹配: {audio_path.name} -> {Path(exact_match).name}")
                    continue
                
                # 2. 尋找相似名稱檔案
                similar_match = self._find_similar_name_match(audio_name, text_files, audio_dir)
                if similar_match:
                    matched_pairs[audio_file] = similar_match
                    logger.debug(f"找到相似匹配: {audio_path.name} -> {Path(similar_match).name}")
                    continue
                
                # 3. 尋找常見議程檔案名稱
                agenda_match = self._find_common_agenda_match(text_files, audio_dir)
                if agenda_match:
                    matched_pairs[audio_file] = agenda_match
                    logger.debug(f"找到議程匹配: {audio_path.name} -> {Path(agenda_match).name}")
                    continue
                
                logger.debug(f"未找到匹配的議程檔案: {audio_path.name}")
            
            self.matched_pairs = matched_pairs
            logger.info(f"匹配完成: {len(matched_pairs)} 對成功匹配")
            
            return matched_pairs
            
        except Exception as e:
            logger.error(f"匹配議程檔案時發生錯誤: {e}")
            return {}
    
    def _find_exact_name_match(self, audio_name: str, text_files: List[str], audio_dir: Path) -> Optional[str]:
        """
        尋找完全同名的文字檔案
        
        Args:
            audio_name: 音訊檔案名稱（不含副檔名，小寫）
            text_files: 文字檔案列表
            audio_dir: 音訊檔案所在目錄
            
        Returns:
            匹配的文字檔案路徑，如果沒找到則返回 None
            
        Requirements: 4.1
        """
        try:
            # 優先在同一目錄中尋找
            for text_file in text_files:
                text_path = Path(text_file)
                text_name = text_path.stem.lower()
                
                if text_name == audio_name:
                    # 如果在同一目錄，優先選擇
                    if text_path.parent == audio_dir:
                        return text_file
                    # 否則記錄為候選
                    return text_file
            
            return None
            
        except Exception as e:
            logger.warning(f"尋找同名檔案時發生錯誤: {e}")
            return None
    
    def _find_similar_name_match(self, audio_name: str, text_files: List[str], audio_dir: Path) -> Optional[str]:
        """
        尋找相似名稱的文字檔案
        
        Args:
            audio_name: 音訊檔案名稱（不含副檔名，小寫）
            text_files: 文字檔案列表
            audio_dir: 音訊檔案所在目錄
            
        Returns:
            匹配的文字檔案路徑，如果沒找到則返回 None
        """
        try:
            best_match = None
            best_score = 0
            
            for text_file in text_files:
                text_path = Path(text_file)
                text_name = text_path.stem.lower()
                
                # 計算相似度分數
                score = self._calculate_similarity_score(audio_name, text_name)
                
                # 如果在同一目錄，加分
                if text_path.parent == audio_dir:
                    score += 0.2
                
                if score > best_score and score > 0.6:  # 相似度閾值
                    best_score = score
                    best_match = text_file
            
            return best_match
            
        except Exception as e:
            logger.warning(f"尋找相似名稱檔案時發生錯誤: {e}")
            return None
    
    def _find_common_agenda_match(self, text_files: List[str], audio_dir: Path) -> Optional[str]:
        """
        尋找常見的議程檔案名稱
        
        Args:
            text_files: 文字檔案列表
            audio_dir: 音訊檔案所在目錄
            
        Returns:
            匹配的議程檔案路徑，如果沒找到則返回 None
            
        Requirements: 4.3
        """
        try:
            # 優先在同一目錄中尋找
            same_dir_files = [f for f in text_files if Path(f).parent == audio_dir]
            
            for text_file in same_dir_files:
                text_path = Path(text_file)
                text_name = text_path.stem.lower()
                
                for agenda_name in self.COMMON_AGENDA_NAMES:
                    if agenda_name in text_name or text_name in agenda_name:
                        logger.debug(f"找到常見議程檔案: {text_path.name}")
                        return text_file
            
            # 如果同一目錄沒找到，擴大搜索範圍
            for text_file in text_files:
                text_path = Path(text_file)
                text_name = text_path.stem.lower()
                
                for agenda_name in self.COMMON_AGENDA_NAMES:
                    if agenda_name in text_name or text_name in agenda_name:
                        logger.debug(f"找到常見議程檔案（其他目錄）: {text_path.name}")
                        return text_file
            
            return None
            
        except Exception as e:
            logger.warning(f"尋找常見議程檔案時發生錯誤: {e}")
            return None
    
    def _calculate_similarity_score(self, name1: str, name2: str) -> float:
        """
        計算兩個檔案名稱的相似度分數
        
        Args:
            name1: 第一個檔案名稱
            name2: 第二個檔案名稱
            
        Returns:
            相似度分數 (0.0 - 1.0)
        """
        try:
            # 簡單的相似度計算
            # 可以使用更複雜的算法如 Levenshtein 距離
            
            # 檢查包含關係
            if name1 in name2 or name2 in name1:
                return 0.8
            
            # 檢查共同詞彙
            words1 = set(name1.replace('_', ' ').replace('-', ' ').split())
            words2 = set(name2.replace('_', ' ').replace('-', ' ').split())
            
            if words1 and words2:
                common_words = words1.intersection(words2)
                total_words = words1.union(words2)
                
                if total_words:
                    return len(common_words) / len(total_words)
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"計算相似度時發生錯誤: {e}")
            return 0.0
    
    def read_agenda_content(self, agenda_file_path: str) -> Optional[str]:
        """
        讀取議程檔案內容
        
        Args:
            agenda_file_path: 議程檔案路徑
            
        Returns:
            議程檔案內容，如果讀取失敗則返回 None
            
        Requirements: 4.4
        """
        try:
            agenda_path = Path(agenda_file_path)
            
            if not agenda_path.exists():
                logger.warning(f"議程檔案不存在: {agenda_path}")
                return None
            
            # 根據檔案格式選擇讀取方式
            file_extension = agenda_path.suffix.lower()
            
            if file_extension in ['.txt', '.md']:
                # 純文字檔案
                return self._read_text_file(agenda_path)
            elif file_extension in ['.doc', '.docx', '.pdf', '.html', '.htm']:
                # 需要特殊處理的檔案格式，使用 markitdown_utils
                return self._read_with_markitdown(agenda_path)
            elif file_extension in ['.json', '.xml', '.csv']:
                # 結構化檔案
                return self._read_structured_file(agenda_path)
            else:
                # 嘗試作為純文字讀取
                return self._read_text_file(agenda_path)
                
        except Exception as e:
            logger.error(f"讀取議程檔案時發生錯誤 {agenda_file_path}: {e}")
            return None
    
    def _read_text_file(self, file_path: Path) -> Optional[str]:
        """讀取純文字檔案"""
        try:
            # 嘗試不同的編碼
            encodings = ['utf-8', 'utf-8-sig', 'big5', 'gbk', 'cp1252']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read().strip()
                        if content:
                            logger.debug(f"成功讀取文字檔案 ({encoding}): {file_path.name}")
                            return content
                except UnicodeDecodeError:
                    continue
            
            logger.warning(f"無法以任何編碼讀取文字檔案: {file_path}")
            return None
            
        except Exception as e:
            logger.warning(f"讀取文字檔案時發生錯誤 {file_path}: {e}")
            return None
    
    def _read_with_markitdown(self, file_path: Path) -> Optional[str]:
        """使用 markitdown_utils 讀取檔案"""
        try:
            # 導入 markitdown_utils
            from markitdown_utils import convert_file_to_markdown
            
            success, content, info = convert_file_to_markdown(str(file_path))
            
            if success and content:
                logger.debug(f"成功使用 MarkItDown 讀取檔案: {file_path.name}")
                return content
            else:
                logger.warning(f"MarkItDown 讀取檔案失敗: {file_path}")
                return None
                
        except ImportError:
            logger.warning("找不到 markitdown_utils 模組，無法讀取特殊格式檔案")
            return None
        except Exception as e:
            logger.warning(f"使用 MarkItDown 讀取檔案時發生錯誤 {file_path}: {e}")
            return None
    
    def _read_structured_file(self, file_path: Path) -> Optional[str]:
        """讀取結構化檔案"""
        try:
            file_extension = file_path.suffix.lower()
            
            if file_extension == '.json':
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return json.dumps(data, ensure_ascii=False, indent=2)
            
            elif file_extension == '.csv':
                import csv
                content_lines = []
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        content_lines.append(' | '.join(row))
                return '\n'.join(content_lines)
            
            elif file_extension == '.xml':
                # 簡單讀取 XML 內容
                return self._read_text_file(file_path)
            
            return None
            
        except Exception as e:
            logger.warning(f"讀取結構化檔案時發生錯誤 {file_path}: {e}")
            return None


class FileDiscovery:
    """
    檔案發現協調器
    
    整合 AudioFileScanner 和 AgendaFileMatcher，提供統一的檔案發現介面
    Requirements: 4.5
    """
    
    def __init__(self, skip_transcribed: bool = True):
        """
        初始化檔案發現協調器
        
        Args:
            skip_transcribed: 是否跳過已有轉錄檔案的音訊檔案
        """
        self.audio_scanner = AudioFileScanner(skip_transcribed=skip_transcribed)
        self.agenda_matcher = AgendaFileMatcher()
        self.skip_transcribed = skip_transcribed
        
    def discover_files(self, folder_path: str, recursive: bool = True) -> DiscoveryResult:
        """
        發現並匹配資料夾中的音訊檔案和議程檔案
        
        Args:
            folder_path: 要搜索的資料夾路徑
            recursive: 是否遞歸搜索子資料夾
            
        Returns:
            DiscoveryResult 物件包含發現和匹配結果
            
        Requirements: 4.5
        """
        try:
            logger.info(f"開始檔案發現流程: {folder_path}")
            
            # 1. 搜索音訊檔案
            audio_files = self.audio_scanner.scan_folder(folder_path, recursive)
            
            # 2. 搜索文字檔案
            text_files = self.agenda_matcher.find_text_files(folder_path, recursive)
            
            # 3. 匹配音訊檔案和議程檔案
            matched_pairs = self.agenda_matcher.match_agenda_files(audio_files, text_files)
            
            # 4. 取得跳過的檔案
            skipped_files = self.audio_scanner.get_skipped_files()
            
            # 5. 創建發現結果
            discovery_result = DiscoveryResult(
                audio_files=audio_files,
                text_files=text_files,
                matched_pairs=matched_pairs,
                skipped_files=skipped_files,
                total_size_mb=self.audio_scanner.total_size_mb
            )
            
            logger.info(f"檔案發現完成: {discovery_result.get_display_summary()}")
            
            return discovery_result
            
        except Exception as e:
            logger.error(f"檔案發現流程發生錯誤: {e}")
            return DiscoveryResult()
    
    def create_file_info_list(self, discovery_result: DiscoveryResult) -> List[FileInfo]:
        """
        根據發現結果創建 FileInfo 物件列表
        
        Args:
            discovery_result: 檔案發現結果
            
        Returns:
            FileInfo 物件列表
        """
        try:
            file_info_list = []
            
            for audio_file in discovery_result.audio_files:
                # 創建基本的 FileInfo
                file_info = self.audio_scanner.get_file_info(audio_file)
                
                if file_info:
                    # 檢查是否有匹配的議程檔案
                    if audio_file in discovery_result.matched_pairs:
                        agenda_file = discovery_result.matched_pairs[audio_file]
                        file_info.agenda_path = agenda_file
                        
                        # 讀取議程內容
                        agenda_content = self.agenda_matcher.read_agenda_content(agenda_file)
                        if agenda_content:
                            file_info.agenda_content = agenda_content
                            logger.debug(f"已載入議程內容: {Path(agenda_file).name}")
                    
                    file_info_list.append(file_info)
            
            logger.info(f"創建了 {len(file_info_list)} 個 FileInfo 物件")
            
            return file_info_list
            
        except Exception as e:
            logger.error(f"創建 FileInfo 列表時發生錯誤: {e}")
            return []
    
    def get_unmatched_files_report(self, discovery_result: DiscoveryResult) -> Dict[str, List[str]]:
        """
        取得未匹配檔案的報告
        
        Args:
            discovery_result: 檔案發現結果
            
        Returns:
            包含未匹配檔案資訊的字典
        """
        try:
            matched_audio = set(discovery_result.matched_pairs.keys())
            matched_text = set(discovery_result.matched_pairs.values())
            
            unmatched_audio = [f for f in discovery_result.audio_files if f not in matched_audio]
            unmatched_text = [f for f in discovery_result.text_files if f not in matched_text]
            
            return {
                'unmatched_audio': unmatched_audio,
                'unmatched_text': unmatched_text,
                'total_unmatched_audio': len(unmatched_audio),
                'total_unmatched_text': len(unmatched_text)
            }
            
        except Exception as e:
            logger.error(f"生成未匹配檔案報告時發生錯誤: {e}")
            return {
                'unmatched_audio': [],
                'unmatched_text': [],
                'total_unmatched_audio': 0,
                'total_unmatched_text': 0
            }


if __name__ == "__main__":
    """測試檔案發現功能"""
    # 設定日誌
    logging.basicConfig(level=logging.INFO)
    
    print("=== 批次音訊處理系統 - 檔案發現服務測試 ===\n")
    
    # 測試音訊檔案掃描器
    print("1. 測試音訊檔案掃描器...")
    try:
        scanner = AudioFileScanner()
        
        # 使用當前目錄進行測試
        test_folder = "."
        audio_files = scanner.scan_folder(test_folder, recursive=False)
        
        print(f"✅ 找到 {len(audio_files)} 個音訊檔案")
        for audio_file in audio_files[:3]:  # 只顯示前3個
            print(f"   - {Path(audio_file).name}")
        
        if len(audio_files) > 3:
            print(f"   ... 還有 {len(audio_files) - 3} 個檔案")
            
    except Exception as e:
        print(f"❌ 音訊檔案掃描器測試失敗: {e}")
    
    # 測試議程檔案匹配器
    print("\n2. 測試議程檔案匹配器...")
    try:
        matcher = AgendaFileMatcher()
        
        text_files = matcher.find_text_files(test_folder, recursive=False)
        print(f"✅ 找到 {len(text_files)} 個文字檔案")
        
        for text_file in text_files[:3]:  # 只顯示前3個
            print(f"   - {Path(text_file).name}")
        
        if len(text_files) > 3:
            print(f"   ... 還有 {len(text_files) - 3} 個檔案")
            
    except Exception as e:
        print(f"❌ 議程檔案匹配器測試失敗: {e}")
    
    # 測試檔案發現協調器
    print("\n3. 測試檔案發現協調器...")
    try:
        discovery = FileDiscovery()
        
        result = discovery.discover_files(test_folder, recursive=False)
        print(f"✅ 檔案發現完成")
        print(f"   {result.get_display_summary()}")
        
        # 測試創建 FileInfo 列表
        file_info_list = discovery.create_file_info_list(result)
        print(f"   創建了 {len(file_info_list)} 個 FileInfo 物件")
        
        # 顯示未匹配檔案報告
        unmatched_report = discovery.get_unmatched_files_report(result)
        print(f"   未匹配音訊檔案: {unmatched_report['total_unmatched_audio']} 個")
        print(f"   未匹配文字檔案: {unmatched_report['total_unmatched_text']} 個")
        
    except Exception as e:
        print(f"❌ 檔案發現協調器測試失敗: {e}")
    
    print("\n=== 測試完成 ===")