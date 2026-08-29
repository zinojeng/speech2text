# 核心依賴
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict, Any
import ssl
import logging
from elevenlabs.client import ElevenLabs
from io import BytesIO
import time


# 設定日誌記錄
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TLSAdapter(HTTPAdapter):
    """自定義 TLS 適配器解決 SSL 協議問題"""
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')  # 降低安全等級以兼容舊協議
        ctx.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3  # 禁用不安全的 SSL 版本
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)


def create_retry_session():
    """建立具有重試機制的 Session"""
    session = requests.Session()
    retry = Retry(
        total=5,  # 總重試次數
        backoff_factor=1,  # 重試間隔
        status_forcelist=[500, 502, 503, 504],  # 需要重試的狀態碼
        allowed_methods=["POST"]  # 只重試 POST 請求
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session


def transcribe_audio_elevenlabs(
    api_key: str,
    file_path: str,
    language_code: Optional[str] = None,
    diarize: bool = False,
    max_retries: int = 5,
    timeout: int = 600  # 10 分鐘超時
) -> Optional[Dict[str, Any]]:
    """
    使用 ElevenLabs API 將音訊轉換為文字，包含重試機制
    
    Args:
        api_key: ElevenLabs API 金鑰
        file_path: 音訊檔案路徑
        language_code: 語言代碼（可選，使用 ISO-639-1 或 ISO-639-3 格式）
        diarize: 是否啟用說話者辨識（限制音訊長度最長 8 分鐘）
        max_retries: 最大重試次數
        timeout: 請求超時時間（秒）
    """
    # 初始化 ElevenLabs 客戶端
    client = ElevenLabs(
        api_key=api_key,
    )
    
    for attempt in range(max_retries):
        try:
            # 讀取音訊檔案
            with open(file_path, 'rb') as audio_file:
                audio_data = BytesIO(audio_file.read())
                
                # 準備 API 參數
                params = {
                    "file": audio_data,
                    "model_id": "scribe_v1",
                    "diarize": diarize,
                    "tag_audio_events": True,
                    "timestamps_granularity": "word"
                }
                
                # 只有當語言代碼不是 None 且不是空字串時才加入
                if language_code and language_code.strip():
                    params["language_code"] = language_code.strip()
                
                # 呼叫語音轉文字 API
                response = client.speech_to_text.convert(**params)
                
                # 檢查回應格式
                if hasattr(response, 'text'):
                    language_code = getattr(
                        response, 'language_code', None
                    )
                    language_prob = getattr(
                        response, 'language_probability', None
                    )
                    return {
                        'text': response.text,
                        'language_code': language_code,
                        'language_probability': language_prob
                    }
                return response
                
        except Exception as e:
            logger.error(f"第 {attempt + 1} 次嘗試失敗：{str(e)}")
            if attempt < max_retries - 1:
                wait_time = min((attempt + 1) * 5, 30)  # 最長等待 30 秒
                logger.info(f"{wait_time} 秒後重試...")
                time.sleep(wait_time)
            else:
                logger.error("已達最大重試次數，轉換失敗")
                return None

# Example usage:
# transcription = transcribe_audio_elevenlabs(
#     api_key="YOUR_API_KEY",
#     file_path="audio.mp3",
#     language_code="en",
#     diarize=True
# ) 