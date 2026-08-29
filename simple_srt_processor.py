#!/usr/bin/env python3
"""
簡化版 SRT 處理器
Simple SRT Processor

直接整合到主程式中，避免子程序調用問題
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

def process_single_audio_to_srt(audio_path: Path, model: str = "gpt-transcribe") -> bool:
    """
    處理單個音訊檔案為 SRT 格式
    """
    print(f"🎵 處理音訊: {audio_path.name}")
    print(f"🤖 使用模型: {model}")
    
    try:
        # 檢查是否已存在 SRT 檔案
        srt_path = audio_path.parent / f"{audio_path.stem}.srt"
        if srt_path.exists() and is_srt_complete(srt_path):
            print(f"✅ SRT 檔案已存在: {srt_path.name}")
            return True
        
        # 確保使用正確的 Python 環境
        python_executable = "./venv/bin/python" if os.path.exists("./venv/bin/python") else sys.executable
        
        # 執行轉錄
        cmd = [
            python_executable,
            "gpt4o_transcribe.py",
            str(audio_path),
            "--model", model,
            "--format", "srt"
        ]
        
        print(f"🔧 執行轉錄...")
        start_time = time.time()
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800  # 30分鐘超時
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            # 寫入 SRT 檔案
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(result.stdout)
            
            if is_srt_complete(srt_path):
                print(f"✅ SRT 處理完成: {elapsed:.1f}秒")
                return True
            else:
                print(f"⚠️ SRT 檔案不完整: {elapsed:.1f}秒")
                return False
        else:
            print(f"❌ 轉錄失敗: {elapsed:.1f}秒")
            if result.stderr:
                print(f"錯誤: {result.stderr[-200:]}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 轉錄超時")
        return False
    except Exception as e:
        print(f"❌ 處理錯誤: {str(e)}")
        return False

def is_srt_complete(srt_path: Path) -> bool:
    """
    檢查 SRT 檔案是否完整
    """
    try:
        if not srt_path.exists() or srt_path.stat().st_size == 0:
            return False
        
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            return False
        
        # 檢查 SRT 基本格式
        lines = content.split('\n')
        has_index = False
        has_timestamp = False
        has_text = False
        
        for line in lines:
            line = line.strip()
            if line.isdigit():
                has_index = True
            elif '-->' in line:
                has_timestamp = True
            elif line and not line.isdigit() and '-->' not in line:
                has_text = True
        
        return has_index and has_timestamp and has_text
        
    except Exception:
        return False

def process_folder_to_srt(folder_path: Path, model: str = "gpt-transcribe") -> dict:
    """
    處理資料夾中的所有音訊檔案為 SRT 格式
    """
    print(f"🚀 批次 SRT 處理: {folder_path}")
    print(f"🤖 使用模型: {model}")
    
    # 支援的音訊格式
    audio_extensions = {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma'}
    
    # 尋找音訊檔案
    audio_files = []
    for ext in audio_extensions:
        audio_files.extend(folder_path.glob(f"*{ext}"))
    
    # 過濾系統檔案
    audio_files = [f for f in audio_files if not f.name.startswith('._')]
    
    if not audio_files:
        print("❌ 未找到音訊檔案")
        return {'success': 0, 'failed': 0, 'skipped': 0}
    
    print(f"📁 找到 {len(audio_files)} 個音訊檔案")
    
    # 處理統計
    stats = {'success': 0, 'failed': 0, 'skipped': 0}
    start_time = time.time()
    
    for i, audio_file in enumerate(audio_files, 1):
        print(f"\n📁 處理 {i}/{len(audio_files)}: {audio_file.name}")
        
        # 檢查是否已存在完整的 SRT 檔案
        srt_path = audio_file.parent / f"{audio_file.stem}.srt"
        if srt_path.exists() and is_srt_complete(srt_path):
            print(f"⏭️ 跳過已存在的 SRT: {srt_path.name}")
            stats['skipped'] += 1
            continue
        
        # 處理檔案
        if process_single_audio_to_srt(audio_file, model):
            stats['success'] += 1
        else:
            stats['failed'] += 1
        
        # 顯示進度
        progress = (i / len(audio_files)) * 100
        elapsed = time.time() - start_time
        if i > 0:
            avg_time = elapsed / i
            remaining = (len(audio_files) - i) * avg_time
            print(f"📊 進度: {progress:.1f}% | 已用時: {elapsed/60:.1f}分 | 預估剩餘: {remaining/60:.1f}分")
    
    # 最終統計
    total_time = time.time() - start_time
    print(f"\n🎉 批次處理完成！")
    print(f"   ✅ 成功: {stats['success']}")
    print(f"   ❌ 失敗: {stats['failed']}")
    print(f"   ⏭️ 跳過: {stats['skipped']}")
    print(f"   ⏱️ 總用時: {total_time/60:.1f} 分鐘")
    
    if stats['success'] > 0:
        avg_per_file = total_time / (stats['success'] + stats['failed'])
        print(f"   📈 平均每檔案: {avg_per_file:.1f} 秒")
    
    return stats

def main():
    """主程式"""
    if len(sys.argv) < 2:
        print("使用方法: python simple_srt_processor.py <資料夾路徑> [模型]")
        print("模型選項:")
        print("  - gpt-transcribe (預設)")
        print("  - gpt-transcribe")
        sys.exit(1)
    
    folder_path = Path(sys.argv[1])
    model = sys.argv[2] if len(sys.argv) > 2 else "gpt-transcribe"
    
    if not folder_path.exists():
        print(f"❌ 資料夾不存在: {folder_path}")
        sys.exit(1)
    
    print("🚀 簡化版 SRT 處理器")
    print("=" * 50)
    print(f"📁 資料夾: {folder_path}")
    print(f"🤖 模型: {model}")
    print()
    
    try:
        stats = process_folder_to_srt(folder_path, model)
        
        # 根據結果設定退出碼
        if stats['failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ 程式錯誤: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()