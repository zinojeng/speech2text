"""
gpt4o_transcribe.py

此程式用於測試使用新的 GPT-4o 語音轉文字模型，
提供兩種模型:
- gpt-4o-transcribe
- gpt-4o-mini-transcribe

參考文件: https://platform.openai.com/docs/guides/speech-to-text

使用方法:
  python gpt4o_transcribe.py <音訊檔案路徑> [--model <模型名稱>] [--language <語言代碼>] [--format <輸出格式>]

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
    parser.add_argument(
        "--format",
        type=str,
        default="text",
        choices=["text", "markdown", "srt"],
        help="輸出格式: text, markdown, srt (預設: text)"
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
            
            # 根據格式設定 response_format
            response_format = "text"
            if args.format == "srt":
                response_format = "srt"
            elif args.format == "markdown":
                response_format = "text"  # 先取得文字再轉換為 markdown
            
            transcript = client.audio.transcriptions.create(
                model=args.model,
                file=audio_file,
                language=args.language,
                response_format=response_format
            )
            
            print("轉錄結果:")
            if args.format == "markdown":
                # 將文字轉換為 markdown 格式
                markdown_text = f"# 語音轉錄結果\n\n{transcript.text}\n"
                print(markdown_text)
            else:
                # text 或 srt 格式直接輸出
                print(transcript.text)
                
    except Exception as e:
        print(f"轉錄失敗: {e}")


if __name__ == "__main__":
    main() 