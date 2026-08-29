import os
from typing import Tuple, List, Optional, Dict, Any
from pydub import AudioSegment
import math
import logging
import tiktoken
from llm_provider_kit import (
    MODEL_PRICING,
    OPENAI_REASONING,
    OPENAI_REFINE,
    OPENAI_REFINE_CHEAP,
)

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 常數定義
MAX_FILE_SIZE_MB = 25  # ElevenLabs 的檔案大小限制
SEGMENT_LENGTH_MS = 300000  # 5 分鐘，單位為毫秒

# OpenAI 模型定義（實際模型 id 見 model_config.py）
OPENAI_MODELS = {
    OPENAI_REFINE: "GPT-5.6 Terra（品質優先）",
    OPENAI_REFINE_CHEAP: "GPT-5.6 Luna（省錢／量大）",
    OPENAI_REASONING: "GPT-5.6 Sol（最強推理）",
}

# 模型價格定義（每千 tokens 的 USD 價格）
# model_config.MODEL_PRICING 記的是每 1M tokens，這裡換算成每 1K。
MODEL_PRICES = {
    model: {"input": price["input"] / 1000, "output": price["output"] / 1000}
    for model, price in MODEL_PRICING.items()
}

def calculate_tokens_and_cost(
    original_text: str,
    refined_text: str,
    model: str = OPENAI_REFINE_CHEAP
) -> Tuple[str, str]:
    """
    計算處理文字消耗的 tokens 和成本
    
    Args:
        original_text: 原始文字
        refined_text: 優化後的文字
        model: 使用的模型
        
    Returns:
        tokens_info: token 使用信息
        cost_info: 成本信息
    """
    try:
        # 確保選擇的模型在支援列表中
        if model not in MODEL_PRICES:
            model = "gpt-5.6-luna"
            
        # 獲取模型對應的編碼器
        encoding_name = "cl100k_base"  # 大多數新模型使用此編碼
        
        # 使用 tiktoken 計算 token 數量
        encoding = tiktoken.get_encoding(encoding_name)
        original_tokens = len(encoding.encode(original_text))
        refined_tokens = len(encoding.encode(refined_text))
        
        # 估算 API 調用成本
        input_cost = original_tokens * MODEL_PRICES[model]["input"] / 1000
        output_cost = refined_tokens * MODEL_PRICES[model]["output"] / 1000
        total_cost = input_cost + output_cost
        
        # 格式化輸出信息
        tokens_info = (
            f"原始文字: {original_tokens} tokens\n"
            f"優化文字: {refined_tokens} tokens\n"
            f"總計: {original_tokens + refined_tokens} tokens"
        )
        
        cost_info = (
            f"輸入成本: ${input_cost:.4f}\n"
            f"輸出成本: ${output_cost:.4f}\n"
            f"總成本: ${total_cost:.4f}"
        )
        
        return tokens_info, cost_info
        
    except Exception as e:
        logger.error(f"計算 tokens 和成本時發生錯誤: {str(e)}")
        return "無法計算 tokens", "無法計算成本"

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

def split_large_audio(
    file_path: str,
    max_duration_seconds: Optional[int] = None
) -> Optional[List[str]]:
    """
    將大型音訊檔案分割成較小的片段
    
    Args:
        file_path: 音訊檔案路徑
        max_duration_seconds: 每個片段的最大時長（秒），如果未指定則使用檔案大小來判斷
        
    Returns:
        分割後的檔案路徑列表，如果失敗則返回 None
    """
    try:
        # 載入音訊檔案
        audio = AudioSegment.from_file(file_path)
        
        # 如果指定了最大時長，使用時長來分割
        if max_duration_seconds:
            segment_length = max_duration_seconds * 1000  # 轉換為毫秒
        else:
            # 如果檔案小於限制，直接返回原始檔案路徑
            if not check_file_size(file_path):
                return [file_path]
            segment_length = SEGMENT_LENGTH_MS
        
        # 分割音訊
        segments = []
        for i, start in enumerate(range(0, len(audio), segment_length)):
            end = start + segment_length
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