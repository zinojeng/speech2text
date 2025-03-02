import os
from typing import Tuple

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
                from pydub import AudioSegment
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