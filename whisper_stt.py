import whisper
import logging
from typing import Optional, Dict, Any
import torch

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def transcribe_audio_whisper(
    file_path: str,
    model_name: str = "base",
    language: Optional[str] = None,
    initial_prompt: Optional[str] = None,
    task: str = "transcribe"
) -> Optional[Dict[str, Any]]:
    """
    使用 Whisper 模型進行音訊轉文字
    
    Args:
        file_path: 音訊檔案路徑
        model_name: Whisper 模型名稱 ("tiny", "base", "small", "medium", "large")
        language: 音訊語言（ISO 639-1 代碼，如 "zh" 表示中文）
        initial_prompt: 初始提示詞
        task: 任務類型 ("transcribe" 或 "translate")
    
    Returns:
        包含轉錄結果的字典，如果失敗則返回 None
    """
    try:
        # 檢查 CUDA 是否可用
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"使用設備: {device}")
        
        # 載入模型
        logger.info(f"載入 Whisper {model_name} 模型...")
        model = whisper.load_model(model_name, device=device)
        
        # 轉錄選項
        options = {
            "task": task,
            "verbose": True
        }
        if language:
            options["language"] = language
        if initial_prompt:
            options["initial_prompt"] = initial_prompt
            
        # 執行轉錄
        logger.info("開始轉錄...")
        result = model.transcribe(file_path, **options)
        
        # 整理結果
        response = {
            "text": result["text"],
            "language": result.get("language", "unknown"),
            "segments": result.get("segments", [])
        }
        
        logger.info("轉錄完成")
        return response
        
    except Exception as e:
        logger.error(f"轉錄失敗：{str(e)}")
        return None

def get_available_models() -> list:
    """
    取得可用的 Whisper 模型列表
    """
    return ["tiny", "base", "small", "medium", "large"]

def get_model_description(model_name: str) -> str:
    """
    取得模型描述
    """
    descriptions = {
        "tiny": "最小的模型，速度最快但準確度較低",
        "base": "基礎模型，平衡速度和準確度",
        "small": "小型模型，準確度較好",
        "medium": "中型模型，準確度高",
        "large": "最大的模型，準確度最高但需要較多資源"
    }
    return descriptions.get(model_name, "未知模型") 