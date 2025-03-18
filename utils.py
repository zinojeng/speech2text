import os
from typing import Tuple, List, Optional
from pydub import AudioSegment
import math
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 常數定義
MAX_FILE_SIZE_MB = 25  # ElevenLabs 的檔案大小限制
SEGMENT_LENGTH_MS = 300000  # 5 分鐘，單位為毫秒

def check_file_constraints(file_path: str, diarize: bool = False) -> Tuple[bool, str]:
    """檢查檔案限制條件"""
    # 檔案大小限制 (25MB)
    MAX_FILE_SIZE = 25 * 1024 * 1024  
    # 音訊長度限制（使用 diarize 時為 8 分鐘）
    MAX_DURATION_DIARIZE = 8 * 60  

    try:
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            return False, f"檔案大小超過限制（最大 25MB）：目前 {file_size/1024/1024:.1f}MB"

        # 如果需要的話，這裡可以加入音訊長度檢查
        # 需要安裝 pydub: pip install pydub
        if diarize:
            try:
                audio = AudioSegment.from_file(file_path)
                duration_seconds = len(audio) / 1000
                if duration_seconds > MAX_DURATION_DIARIZE:
                    return False, (
                        f"使用說話者辨識時，音訊長度不能超過 8 分鐘："
                        f"目前 {duration_seconds/60:.1f} 分鐘"
                    )
            except ImportError:
                pass  # 如果沒有安裝 pydub，就跳過長度檢查

        return True, "檔案檢查通過"
    except Exception as e:
        return False, f"檔案檢查失敗：{str(e)}" 

def check_file_size(file_path: str, max_size_mb: int = MAX_FILE_SIZE_MB) -> bool:
    """
    檢查檔案大小是否超過限制
    
    Args:
        file_path: 檔案路徑
        max_size_mb: 最大檔案大小（MB）
        
    Returns:
        如果檔案大小超過限制則返回 True
    """
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    return file_size_mb > max_size_mb

def split_large_audio(file_path: str) -> Optional[List[str]]:
    """
    將大型音訊檔案分割成較小的片段
    
    Args:
        file_path: 音訊檔案路徑
        
    Returns:
        分割後的檔案路徑列表，如果失敗則返回 None
    """
    try:
        # 載入音訊檔案
        audio = AudioSegment.from_file(file_path)
        
        # 如果檔案小於限制，直接返回原始檔案路徑
        if not check_file_size(file_path):
            return [file_path]
        
        # 分割音訊
        segments = []
        for i, start in enumerate(range(0, len(audio), SEGMENT_LENGTH_MS)):
            end = start + SEGMENT_LENGTH_MS
            segment = audio[start:end]
            
            # 儲存分割片段
            segment_path = f"temp_segment_{i}.mp3"
            segment.export(segment_path, format="mp3")
            segments.append(segment_path)
            
            logger.info(f"已建立分割片段：{segment_path}")
        
        return segments
        
    except Exception as e:
        logger.error(f"分割音訊失敗：{str(e)}")
        return None 