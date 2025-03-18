import os
from typing import Tuple
from pydub import AudioSegment
import math

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

def split_large_audio(file_path: str, max_size_mb: int = 25) -> list:
    """
    將大音訊檔案分割成小於指定大小的片段
    
    Args:
        file_path: 音訊檔案路徑
        max_size_mb: 每個片段的最大大小（MB）
    
    Returns:
        分割後的檔案路徑列表
    """
    try:
        # 載入音訊檔案
        audio = AudioSegment.from_file(file_path)
        
        # 計算檔案總大小（MB）
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        # 如果檔案小於限制，直接返回原檔案
        if file_size_mb <= max_size_mb:
            return [file_path]
        
        # 計算需要分割的數量
        num_parts = math.ceil(file_size_mb / max_size_mb)
        
        # 計算每個片段的長度（毫秒）
        part_length = len(audio) // num_parts
        
        # 分割音訊
        output_files = []
        for i in range(num_parts):
            start = i * part_length
            end = (i + 1) * part_length if i < num_parts - 1 else len(audio)
            
            # 建立分割片段
            segment = audio[start:end]
            
            # 儲存分割檔案
            output_path = f"{os.path.splitext(file_path)[0]}_part{i+1}{os.path.splitext(file_path)[1]}"
            segment.export(output_path, format=os.path.splitext(file_path)[1][1:])
            output_files.append(output_path)
        
        return output_files
        
    except Exception as e:
        print(f"檔案分割失敗：{str(e)}")
        return [] 

def check_file_size(file_path: str, max_size_mb: int = 25) -> bool:
    """檢查檔案大小是否超過限制"""
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    return file_size_mb <= max_size_mb 