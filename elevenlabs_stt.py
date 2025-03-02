import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict, Any
import ssl
import urllib3
import logging
import re

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

def create_retry_session() -> requests.Session:
    """建立具有重試機制和安全配置的 Session"""
    session = requests.Session()
    
    # 重試策略 (官方建議)
    retry = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset(['POST'])
    )
    
    # 掛載自定義適配器
    adapter = TLSAdapter(max_retries=retry)
    session.mount("https://", adapter)
    
    return session

def transcribe_audio(
    api_key: str,
    file_path: str,
    language_code: Optional[str] = None,
    diarize: bool = False
) -> Optional[Dict[str, Any]]:
    """
    強化版音訊轉文字函數，包含：
    1. 自定義 TLS 配置
    2. 重試機制
    3. 安全連線優化
    """
    url = "https://api.elevenlabs.io/v1/speech-to-text"
    
    # 根據官方文件建議的 headers
    headers = {
        "xi-api-key": api_key,
        "Accept": "application/json",
        "User-Agent": "ElevenLabs-Python-Client/1.0"
    }
    
    # 修正 language_code 處理方式
    form_data = {
        "model_id": "scribe_v1",
        "diarize": str(diarize).lower(),
        "tag_audio_events": "true",
        "timestamps_granularity": "word"
    }
    
    # 根據官方文件正確處理語言代碼
    if language_code:
        # 驗證語言代碼格式
        if not re.match(r"^[a-z]{3}$", language_code):
            raise ValueError("Invalid ISO 639-3 language code format")
        form_data["language_code"] = language_code
    else:
        # 當不指定語言時完全省略此參數（官方建議）
        form_data.pop("language_code", None)

    try:
        with open(file_path, "rb") as audio_file:
            files = {"file": (file_path.split("/")[-1], audio_file)}
            
            # 使用強化版 Session
            session = create_retry_session()
            
            response = session.post(
                url,
                headers=headers,
                data=form_data,
                files=files,
                timeout=30,  # 包含連線和讀取超時
                verify=True  # 保持 SSL 驗證但使用自定義配置
            )
            
            # 處理 API 響應
            if response.status_code == 200:
                return response.json()
                
            # 記錄詳細錯誤信息
            logger.error(f"API 響應錯誤: {response.status_code} - {response.text}")
            response.raise_for_status()
            
    except urllib3.exceptions.SSLError as e:
        logger.error(f"SSL 連線錯誤: {str(e)}")
    except requests.exceptions.RequestException as e:
        logger.error(f"請求異常: {str(e)}")
    except Exception as e:
        logger.error(f"未預期錯誤: {str(e)}")
        
    return None

# Example usage:
# transcription = transcribe_audio(
#     api_key="YOUR_API_KEY",
#     file_path="audio.mp3",
#     language_code="en",
#     diarize=True
# ) 