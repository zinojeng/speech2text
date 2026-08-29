"""
GPT-4o Speech-to-Text 改進模組
使用 OpenAI GPT-4o 語音轉文字模型，並處理常見問題

主要改進：
1. 自動檢測和轉換音頻格式
2. 處理大檔案（>25MB）自動分段
3. 正確設定檔名和 MIME 類型
4. 提供詳細的錯誤資訊
"""

import os
import subprocess
import tempfile
import math
from pathlib import Path
from openai import OpenAI
import mimetypes


class GPT4oTranscriber:
    """改進的 GPT-4o 轉錄器"""
    
    SUPPORTED_FORMATS = {'.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm'}
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
    
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.temp_files = []  # 追蹤臨時檔案
        
    def __del__(self):
        """清理臨時檔案"""
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
                    
    def check_audio_format(self, file_path):
        """檢查音頻格式"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"找不到檔案：{file_path}")
            
        file_size = os.path.getsize(file_path)
        file_ext = Path(file_path).suffix.lower()
        
        return {
            'size': file_size,
            'extension': file_ext,
            'supported': file_ext in self.SUPPORTED_FORMATS,
            'too_large': file_size > self.MAX_FILE_SIZE
        }
        
    def convert_to_mp3(self, input_path):
        """轉換為相容的 MP3 格式"""
        output_path = os.path.join(
            tempfile.gettempdir(),
            f"{Path(input_path).stem}_converted.mp3"
        )
        
        cmd = [
            "ffmpeg", "-i", input_path,
            "-ar", "16000",      # 16kHz 採樣率
            "-ac", "1",          # 單聲道
            "-c:a", "libmp3lame", # MP3 編碼器
            "-b:a", "64k",       # 固定位元率
            "-y",                # 覆蓋
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"音頻轉換失敗：{result.stderr}")
            
        self.temp_files.append(output_path)
        return output_path
        
    def get_audio_duration(self, file_path):
        """獲取音頻時長（秒）"""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return float(result.stdout.strip())
        return 0
        
    def split_audio(self, input_path, segment_duration=600):
        """分割音頻檔案"""
        duration = self.get_audio_duration(input_path)
        if duration == 0:
            return [input_path]
            
        num_segments = math.ceil(duration / segment_duration)
        if num_segments == 1:
            return [input_path]
            
        segments = []
        
        for i in range(num_segments):
            start_time = i * segment_duration
            output_path = os.path.join(
                tempfile.gettempdir(),
                f"{Path(input_path).stem}_segment_{i:03d}.mp3"
            )
            
            cmd = [
                "ffmpeg", "-i", input_path,
                "-ss", str(start_time),
                "-t", str(segment_duration),
                "-ar", "16000",
                "-ac", "1",
                "-c:a", "libmp3lame",
                "-b:a", "64k",
                "-y",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(output_path):
                segments.append(output_path)
                self.temp_files.append(output_path)
                
        return segments
        
    def transcribe_single_file(self, file_path, model, language, response_format):
        """轉錄單個檔案"""
        # 確保檔案名有副檔名
        file_name = os.path.basename(file_path)
        if not Path(file_name).suffix:
            file_name = file_name + ".mp3"
            
        # 讀取檔案內容
        with open(file_path, "rb") as f:
            file_content = f.read()
            
        # 創建 BytesIO 物件（允許設定 name 屬性）
        import io
        file_like = io.BytesIO(file_content)
        file_like.name = file_name
        
        transcript = self.client.audio.transcriptions.create(
            model=model,
            file=file_like,
            language=language,
            response_format=response_format
        )
            
        return transcript
        
    def transcribe(self, file_path, model="gpt-transcribe", 
                  language="zh", output_format="text", auto_convert=True):
        """主要轉錄方法"""
        # 檢查格式
        audio_info = self.check_audio_format(file_path)
        
        # 準備處理的檔案
        process_path = file_path
        
        # 格式轉換（如需要）
        if auto_convert and (not audio_info['supported'] or audio_info['extension'] != '.mp3'):
            try:
                process_path = self.convert_to_mp3(file_path)
                audio_info = self.check_audio_format(process_path)
            except:
                # 如果轉換失敗，仍嘗試原檔案
                pass
                
        # 處理大檔案
        if audio_info['too_large']:
            segments = self.split_audio(process_path)
            transcripts = []
            
            for segment in segments:
                try:
                    response_format = "srt" if output_format == "srt" else "text"
                    transcript = self.transcribe_single_file(
                        segment, model, language, response_format
                    )
                    
                    if hasattr(transcript, 'text'):
                        transcripts.append(transcript.text)
                    else:
                        transcripts.append(str(transcript))
                except Exception as e:
                    # 記錄錯誤但繼續處理
                    print(f"分段轉錄錯誤: {e}")
                    
            result = "\n".join(transcripts)
            
        else:
            # 單檔案轉錄
            response_format = "srt" if output_format == "srt" else "text"
            transcript = self.transcribe_single_file(
                process_path, model, language, response_format
            )
            
            if hasattr(transcript, 'text'):
                result = transcript.text
            else:
                result = str(transcript)
                
        # 格式化輸出
        if output_format == "markdown":
            result = f"# 語音轉錄結果\n\n{result}\n"
            
        return result


def transcribe_audio_gpt4o(file_path, api_key, model="gpt-transcribe", 
                          language=None, output_format="text", auto_convert=True):
    """
    使用改進的 GPT-4o 模型轉錄音頻
    
    Args:
        file_path: 音頻檔案路徑
        api_key: OpenAI API 金鑰
        model: 模型名稱
        language: 語言代碼
        output_format: 輸出格式
        auto_convert: 是否自動轉換格式
    
    Returns:
        轉錄結果文字
    """
    try:
        transcriber = GPT4oTranscriber(api_key)
        return transcriber.transcribe(
            file_path, model, language, output_format, auto_convert
        )
    except Exception as e:
        raise Exception(f"GPT-4o 轉錄失敗: {str(e)}")


# 相容性：保留原始函數名稱
def transcribe_audio_gpt4o_improved(*args, **kwargs):
    """別名函數，提供向後相容性"""
    return transcribe_audio_gpt4o(*args, **kwargs)