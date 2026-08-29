"""
增強版 GPT-4o 轉錄程式
Enhanced GPT-4o Transcription Script

支援功能：
- 大檔案自動切割（超過 20 分鐘自動分段）
- MP4 影片檔案音軌提取
- 多種音訊格式支援
- 自動合併轉錄結果
- 進度顯示
"""

import os
import sys
import argparse
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from openai import OpenAI

# 支援的音訊格式
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}

def check_ffmpeg():
    """檢查 ffmpeg 是否可用"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_audio_duration(file_path):
    """獲取音訊檔案長度（秒）"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', str(file_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return None

def extract_audio_from_video(video_path, output_path):
    """從影片檔案提取音軌"""
    try:
        cmd = [
            'ffmpeg', '-i', str(video_path), '-vn', '-acodec', 'mp3',
            '-ab', '128k', '-ar', '44100', '-y', str(output_path)
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def split_audio_file(input_path, output_dir, segment_duration=1200):
    """
    切割音訊檔案
    
    Args:
        input_path: 輸入檔案路徑
        output_dir: 輸出目錄
        segment_duration: 每段長度（秒），預設 20 分鐘
        
    Returns:
        切割後的檔案路徑列表
    """
    try:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 使用 ffmpeg 切割檔案
        output_pattern = output_dir / "segment_%03d.mp3"
        
        cmd = [
            'ffmpeg', '-i', str(input_path), '-f', 'segment',
            '-segment_time', str(segment_duration), '-c', 'copy',
            '-reset_timestamps', '1', '-y', str(output_pattern)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        
        # 找到所有生成的片段
        segments = sorted(output_dir.glob("segment_*.mp3"))
        return segments
        
    except subprocess.CalledProcessError as e:
        print(f"檔案切割失敗: {e}")
        return []

def transcribe_audio_file(client, file_path, model, language):
    """轉錄單一音訊檔案"""
    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                language=language,
                response_format="text"
            )
            # 處理不同的回應格式
            if hasattr(transcript, 'text'):
                return transcript.text
            else:
                # 如果回應是字串格式
                return str(transcript)
    except Exception as e:
        print(f"轉錄失敗: {e}")
        return None

def process_audio_file(input_path, model="gpt-transcribe", language="zh", max_duration=1200):
    """
    處理音訊檔案（包括切割和轉錄）
    
    Args:
        input_path: 輸入檔案路徑
        model: 轉錄模型
        language: 語言代碼
        max_duration: 最大片段長度（秒）
        
    Returns:
        轉錄文字內容
    """
    input_path = Path(input_path)
    
    # 檢查檔案是否存在
    if not input_path.exists():
        print(f"檔案不存在: {input_path}")
        return None
    
    # 檢查 API 金鑰
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("請在環境變數中設定 OPENAI_API_KEY")
        return None
    
    client = OpenAI(api_key=api_key)
    
    # 處理影片檔案
    if input_path.suffix.lower() in VIDEO_EXTENSIONS:
        if not check_ffmpeg():
            print("處理影片檔案需要 ffmpeg，請先安裝")
            return None
        
        print("偵測到影片檔案，正在提取音軌...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / f"{input_path.stem}.mp3"
            
            if not extract_audio_from_video(input_path, audio_path):
                print("音軌提取失敗")
                return None
            
            print("音軌提取成功")
            return process_audio_file(audio_path, model, language, max_duration)
    
    # 檢查檔案長度
    duration = get_audio_duration(input_path)
    if duration is None:
        print("無法獲取音訊檔案長度")
        return None
    
    print(f"音訊檔案長度: {duration:.1f} 秒 ({duration/60:.1f} 分鐘)")
    
    # 如果檔案不需要切割
    if duration <= max_duration:
        print("檔案長度在限制內，直接轉錄...")
        return transcribe_audio_file(client, input_path, model, language)
    
    # 需要切割檔案
    print(f"檔案超過 {max_duration/60:.1f} 分鐘限制，開始切割...")
    
    if not check_ffmpeg():
        print("檔案切割需要 ffmpeg，請先安裝")
        return None
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 切割檔案
        segments = split_audio_file(input_path, temp_dir, max_duration)
        
        if not segments:
            print("檔案切割失敗")
            return None
        
        print(f"檔案已切割為 {len(segments)} 個片段")
        
        # 轉錄每個片段
        all_transcripts = []
        
        for i, segment in enumerate(segments, 1):
            print(f"正在轉錄片段 {i}/{len(segments)}: {segment.name}")
            
            transcript = transcribe_audio_file(client, segment, model, language)
            
            if transcript:
                all_transcripts.append(transcript)
                print(f"片段 {i} 轉錄成功 ({len(transcript)} 字符)")
            else:
                print(f"片段 {i} 轉錄失敗")
                all_transcripts.append(f"[片段 {i} 轉錄失敗]")
        
        # 合併所有轉錄結果
        combined_transcript = "\n\n".join(all_transcripts)
        print(f"所有片段轉錄完成，總長度: {len(combined_transcript)} 字符")
        
        return combined_transcript

def save_transcript(transcript, input_path, output_format="text"):
    """保存轉錄結果"""
    input_path = Path(input_path)
    
    # 生成輸出檔案名稱
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = input_path.stem
    
    if output_format == "markdown":
        output_file = input_path.parent / f"{base_name}_轉錄_{timestamp}.md"
        content = f"# {base_name} - 轉錄結果\n\n"
        content += f"**檔案名稱**: {input_path.name}\n"
        content += f"**轉錄時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"**轉錄模型**: gpt-transcribe\n\n"
        content += "## 轉錄內容\n\n"
        content += transcript
    else:
        output_file = input_path.parent / f"{base_name}_轉錄_{timestamp}.txt"
        content = f"檔案名稱: {input_path.name}\n"
        content += f"轉錄時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"轉錄模型: gpt-transcribe\n"
        content += f"檔案長度: {get_audio_duration(input_path):.1f} 秒\n"
        content += "\n" + "="*50 + "\n"
        content += "轉錄內容:\n\n"
        content += transcript
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"轉錄結果已保存: {output_file}")
        return str(output_file)
        
    except Exception as e:
        print(f"保存檔案失敗: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(
        description="增強版 GPT-4o 語音轉文字工具，支援大檔案切割和影片處理"
    )
    parser.add_argument(
        "audio_file",
        type=str,
        help="音訊或影片檔案路徑"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-transcribe",
        choices=["gpt-transcribe", "gemini-3.5-transcribe"],
        help="選擇轉錄模型"
    )
    parser.add_argument(
        "--language",
        type=str,
        default="zh",
        help="指定語言代碼 (預設: zh)"
    )
    parser.add_argument(
        "--format",
        type=str,
        default="text",
        choices=["text", "srt", "markdown"],
        help="輸出格式: text, srt, markdown (預設: text)"
    )
    parser.add_argument(
        "--max-duration",
        type=int,
        default=1200,
        help="最大片段長度（秒），預設 1200 秒（20分鐘）"
    )
    
    args = parser.parse_args()
    
    print("=== 增強版 GPT-4o 轉錄工具 ===")
    print(f"輸入檔案: {args.audio_file}")
    print(f"轉錄模型: {args.model}")
    print(f"語言設定: {args.language}")
    print(f"輸出格式: {args.format}")
    print(f"最大片段: {args.max_duration} 秒")
    print()
    
    # 檢查是否已存在轉錄檔案
    input_path = Path(args.audio_file)
    existing_files = list(input_path.parent.glob(f"{input_path.stem}_轉錄_*.txt"))
    
    if existing_files:
        latest_file = max(existing_files, key=lambda x: x.stat().st_mtime)
        print(f"⚠️  發現已存在的轉錄檔案: {latest_file.name}")
        
        choice = input("是否要重新轉錄？(y/N): ").strip().lower()
        if choice not in ['y', 'yes']:
            print("使用已存在的轉錄檔案")
            print(f"📄 檔案位置: {latest_file}")
            sys.exit(0)
        else:
            print("將重新轉錄...")
    
    # 開始轉錄
    transcript = process_audio_file(
        args.audio_file,
        args.model,
        args.language,
        args.max_duration
    )
    
    if transcript:
        # 保存結果
        output_file = save_transcript(transcript, args.audio_file, args.format)
        
        if output_file:
            print("\n=== 轉錄完成 ===")
            print(f"✅ 轉錄成功")
            print(f"📄 輸出檔案: {output_file}")
            print(f"📊 內容長度: {len(transcript)} 字符")
        else:
            print("\n❌ 保存檔案失敗")
            sys.exit(1)
    else:
        print("\n❌ 轉錄失敗")
        sys.exit(1)

if __name__ == "__main__":
    main()