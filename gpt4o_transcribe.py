"""
gpt4o_transcribe.py

此程式用於測試使用新的 GPT-4o 語音轉文字模型，
提供兩種模型:
- gpt-4o-transcribe
- gpt-4o-mini-transcribe

參考文件: https://platform.openai.com/docs/guides/speech-to-text

使用方法:
  python gpt4o_transcribe.py <音訊檔案路徑> [--model <模型名稱>] [--language <語言代碼>]

請確保已安裝 openai 套件:
  pip install openai>=1.0.0

並在環境變數中設定 OPENAI_API_KEY。

支援的語言代碼:
- zh: 中文
- en: 英文
- ja: 日文
- ko: 韓文
等等...
"""

import os
import sys
import argparse
from openai import OpenAI


def main():
    parser = argparse.ArgumentParser(
        description="使用新的 GPT-4o 語音轉文字模型"
    )
    parser.add_argument(
        "audio_file",
        type=str,
        help="音訊檔案路徑"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-transcribe",
        help="選擇模型: gpt-4o-transcribe, gpt-4o-mini-transcribe"
    )
    parser.add_argument(
        "--language",
        type=str,
        default="zh",
        help="指定語言代碼 (預設: zh)"
    )
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("請在環境變數中設定 OPENAI_API_KEY")
        sys.exit(1)
    
    client = OpenAI(api_key=api_key)

    try:
        with open(args.audio_file, "rb") as audio_file:
            print("開始轉錄...")
            transcript = client.audio.transcriptions.create(
                model=args.model,
                file=audio_file,
                language=args.language
            )
            print("轉錄結果:")
            print(transcript.text)
    except Exception as e:
        print(f"轉錄失敗: {e}")


if __name__ == "__main__":
    main() 