#!/usr/bin/env python3
"""
ADA2025 Audio-Only Batch Processor
專門處理音訊檔案的批次處理器
"""

import os
import sys
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv
from ada2025_batch_processor import ADA2025BatchProcessor

# 載入 .env 檔案中的環境變數
load_dotenv()

def parse_args():
    parser = argparse.ArgumentParser(description="ADA2025 Audio-Only Batch Processor")
    parser.add_argument(
        "--base-path",
        dest="base_path",
        default=None,
        help="ADA2025 音訊資料根目錄，預設使用環境變數 ADA2025_BASE_PATH 或內建路徑",
    )
    return parser.parse_args()


def main():
    """主程式入口"""
    print("🎵 ADA2025 Audio-Only Batch Processor")
    print("=" * 50)
    
    args = parse_args()
    base_path = (
        args.base_path
        or os.getenv("ADA2025_BASE_PATH")
        or "/Volumes/WD_BLACK/國際年會/ADA2025"
    )
    
    processor = ADA2025BatchProcessor(base_path=base_path)
    print(f"📂 目錄: {processor.base_path}")
    
    # 檢查 API 金鑰
    if not processor.openai_key or not processor.google_key:
        print("❌ 錯誤：缺少必要的 API 金鑰")
        print("請設定以下環境變數：")
        print("   export OPENAI_API_KEY='your-key'")
        print("   export GOOGLE_API_KEY='your-key'")
        return
    
    while True:
        print("\n📋 選擇操作：")
        print("1. 📊 顯示音訊檔案統計")
        print("2. 🎵 處理單一資料夾")
        print("3. 🚀 批次處理音訊檔案")
        print("4. 📝 查看處理報告")
        print("5. ❌ 退出")
        
        choice = input("\n請選擇 (1-5): ").strip()
        
        if choice == '1':
            show_audio_statistics(processor)
        elif choice == '2':
            process_single_folder(processor)
        elif choice == '3':
            batch_process_audio(processor)
        elif choice == '4':
            show_processing_report(processor)
        elif choice == '5':
            print("👋 再見！")
            break
        else:
            print("❌ 無效選擇，請重試")

def show_audio_statistics(processor):
    """顯示音訊檔案統計"""
    print("\n🎵 掃描音訊檔案...")
    
    audio_folders = []
    processed_folders = []
    unprocessed_folders = []
    total_audio_files = 0
    
    for folder in processor.base_path.iterdir():
        if folder.is_dir() and not folder.name.startswith('.'):
            # 只查找音訊檔案
            audio_files = processor.find_audio_files(folder)
            if audio_files:
                audio_folders.append(folder)
                total_audio_files += len(audio_files)
                
                # 檢查是否已處理
                is_processed, reason = processor.is_folder_already_processed(folder)
                if is_processed:
                    processed_folders.append((folder.name, len(audio_files), reason))
                else:
                    unprocessed_folders.append((folder.name, len(audio_files)))
    
    print(f"\n📊 音訊檔案統計：")
    print(f"   📁 包含音訊檔案的資料夾: {len(audio_folders)}")
    print(f"   🎵 總音訊檔案數: {total_audio_files}")
    print(f"   ✅ 已處理: {len(processed_folders)} 個資料夾")
    print(f"   ⏳ 待處理: {len(unprocessed_folders)} 個資料夾")
    
    if unprocessed_folders:
        unprocessed_files = sum(count for _, count in unprocessed_folders)
        print(f"   🔄 待處理音訊檔案: {unprocessed_files} 個")
        print(f"   ⏱️  預估處理時間: {unprocessed_files * 3:.1f} 分鐘")
    
    # 顯示待處理資料夾
    if unprocessed_folders:
        print(f"\n⏳ 待處理的音訊資料夾:")
        for i, (folder_name, count) in enumerate(unprocessed_folders[:10], 1):
            print(f"   {i:2d}. {folder_name} ({count} 個音訊檔案)")
        if len(unprocessed_folders) > 10:
            print(f"   ... 還有 {len(unprocessed_folders) - 10} 個資料夾")

def process_single_folder(processor):
    """處理單一資料夾"""
    print("\n🎵 選擇要處理的音訊資料夾：")
    
    # 獲取包含音訊檔案的資料夾
    audio_folders = []
    for folder in processor.base_path.iterdir():
        if folder.is_dir() and not folder.name.startswith('.'):
            audio_files = processor.find_audio_files(folder)
            if audio_files:
                is_processed, reason = processor.is_folder_already_processed(folder)
                audio_folders.append((folder, len(audio_files), is_processed, reason))
    
    if not audio_folders:
        print("❌ 沒有找到包含音訊檔案的資料夾")
        return
    
    # 顯示資料夾列表
    for i, (folder, count, is_processed, reason) in enumerate(audio_folders, 1):
        status = "✅ 已處理" if is_processed else "⏳ 待處理"
        print(f"   {i:2d}. {folder.name} ({count} 個音訊檔案) - {status}")
    
    try:
        choice = int(input(f"\n請選擇資料夾 (1-{len(audio_folders)}): "))
        if 1 <= choice <= len(audio_folders):
            selected_folder, count, is_processed, reason = audio_folders[choice - 1]
            
            if is_processed:
                print(f"⚠️  資料夾已處理過：{reason}")
                confirm = input("是否要重新處理？(y/N): ").strip().lower()
                if confirm != 'y':
                    return
            
            # 選擇輸出格式
            output_format = choose_output_format()
            
            print(f"\n🎵 開始處理音訊資料夾: {selected_folder.name}")
            print(f"📝 輸出格式: {output_format}")
            
            # 使用 audio_auto.sh 腳本進行處理
            success = process_folder_with_format(selected_folder, output_format)
            
            if success:
                print(f"✅ 資料夾處理完成: {selected_folder.name}")
            else:
                print(f"❌ 資料夾處理失敗: {selected_folder.name}")
        else:
            print("❌ 無效選擇")
    except ValueError:
        print("❌ 請輸入有效數字")

def batch_process_audio(processor):
    """批次處理音訊檔案"""
    print("\n🚀 音訊檔案批次處理選項：")
    print("1. 快速批次 (3個資料夾) - 約10-15分鐘")
    print("2. 小批次 (5個資料夾) - 約15-25分鐘")
    print("3. 中批次 (10個資料夾) - 約30-50分鐘")
    print("4. 大批次 (20個資料夾) - 約1-2小時")
    print("5. 自訂批次大小")
    print("6. 處理所有待處理音訊資料夾")
    print("7. 返回主選單")
    
    choice = input("\n請選擇 (1-7): ").strip()
    
    batch_sizes = {'1': 3, '2': 5, '3': 10, '4': 20}
    
    if choice in batch_sizes:
        batch_size = batch_sizes[choice]
    elif choice == '5':
        try:
            batch_size = int(input("請輸入批次大小: "))
            if batch_size <= 0:
                print("❌ 批次大小必須大於 0")
                return
        except ValueError:
            print("❌ 請輸入有效數字")
            return
    elif choice == '6':
        batch_size = None  # 處理所有
    elif choice == '7':
        return
    else:
        print("❌ 無效選擇")
        return
    
    # 選擇輸出格式
    output_format = choose_output_format()
    
    # 獲取待處理的音訊資料夾
    unprocessed_folders = []
    for folder in processor.base_path.iterdir():
        if folder.is_dir() and not folder.name.startswith('.'):
            audio_files = processor.find_audio_files(folder)
            if audio_files:
                is_processed, _ = processor.is_folder_already_processed(folder)
                if not is_processed:
                    unprocessed_folders.append(folder)
    
    unprocessed_folders.sort(key=lambda x: x.name)
    
    if not unprocessed_folders:
        print("✅ 所有音訊資料夾都已處理完成！")
        return
    
    # 確定要處理的資料夾
    if batch_size is None:
        folders_to_process = unprocessed_folders
    else:
        folders_to_process = unprocessed_folders[:batch_size]
    
    print(f"\n🎵 準備處理 {len(folders_to_process)} 個音訊資料夾：")
    for i, folder in enumerate(folders_to_process, 1):
        audio_count = len(processor.find_audio_files(folder))
        print(f"   {i}. {folder.name} ({audio_count} 個音訊檔案)")
    
    total_files = sum(len(processor.find_audio_files(f)) for f in folders_to_process)
    estimated_time = total_files * 3
    print(f"\n⏱️  預估處理時間: {estimated_time:.1f} 分鐘")
    
    confirm = input("\n確認開始批次處理？(y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 取消處理")
        return
    
    # 開始批次處理
    print(f"\n🚀 開始批次處理 {len(folders_to_process)} 個音訊資料夾...")
    print(f"📝 輸出格式: {output_format}")
    start_time = time.time()
    
    successful = 0
    failed = 0
    
    for i, folder in enumerate(folders_to_process, 1):
        print(f"\n📁 處理資料夾 {i}/{len(folders_to_process)}: {folder.name}")
        
        try:
            success = process_folder_with_format(folder, output_format)
            if success:
                successful += 1
                print(f"✅ 完成: {folder.name}")
            else:
                failed += 1
                print(f"❌ 失敗: {folder.name}")
        except Exception as e:
            failed += 1
            print(f"❌ 錯誤: {folder.name} - {str(e)}")
        
        # 顯示進度
        progress = (i / len(folders_to_process)) * 100
        elapsed = time.time() - start_time
        if i > 0:
            avg_time = elapsed / i
            remaining = (len(folders_to_process) - i) * avg_time
            print(f"📊 進度: {progress:.1f}% | 已用時: {elapsed/60:.1f}分 | 預估剩餘: {remaining/60:.1f}分")
    
    # 處理完成統計
    total_time = time.time() - start_time
    print(f"\n🎉 批次處理完成！")
    print(f"   ✅ 成功: {successful} 個資料夾")
    print(f"   ❌ 失敗: {failed} 個資料夾")
    print(f"   ⏱️  總用時: {total_time/60:.1f} 分鐘")

def choose_output_format():
    """選擇輸出格式"""
    print("\n📝 選擇轉錄輸出格式：")
    print("1. 📄 TXT (純文字格式)")
    print("2. 🎬 SRT (字幕格式) - 🚀 增強版，支援精度選擇")
    print("3. 📝 Markdown (格式化文字)")
    
    while True:
        try:
            choice = input("\n請選擇格式 (1-3): ").strip()
            if choice == '1':
                return 'text'
            elif choice == '2':
                return 'srt_enhanced'  # 使用增強版 SRT
            elif choice == '3':
                return 'markdown'
            else:
                print("❌ 請輸入 1、2 或 3")
        except KeyboardInterrupt:
            print("\n❌ 操作已取消")
            return 'text'

def process_folder_with_format(folder_path, output_format):
    """使用指定格式處理資料夾"""
    import subprocess
    import os
    
    try:
        # 如果是增強版 SRT 格式，使用增強版處理器
        if output_format == 'srt_enhanced':
            return process_folder_srt_enhanced(folder_path)
        elif output_format == 'srt':
            return process_folder_srt_optimized(folder_path)
        
        # 其他格式使用 audio_auto.sh 腳本處理
        script_path = "./audio_auto.sh"
        if not os.path.exists(script_path):
            print("❌ 找不到 audio_auto.sh 腳本")
            return False
        
        # 構建命令
        cmd = [
            script_path,
            str(folder_path),
            "gpt-transcribe",  # 使用經濟型模型
            output_format
        ]
        
        print(f"🚀 執行命令: {' '.join(cmd)}")
        
        # 執行命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1小時超時
        )
        
        if result.returncode == 0:
            print("✅ 處理成功")
            if result.stdout:
                print("📋 輸出:")
                print(result.stdout[-500:])  # 顯示最後500字符
            return True
        else:
            print("❌ 處理失敗")
            if result.stderr:
                print("❌ 錯誤信息:")
                print(result.stderr[-500:])  # 顯示最後500字符
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 處理超時（超過1小時）")
        return False
    except Exception as e:
        print(f"❌ 處理過程中發生錯誤: {str(e)}")
        return False

def process_folder_srt_enhanced(folder_path):
    """使用增強版 SRT 處理器處理資料夾"""
    import subprocess
    import os
    
    try:
        # 使用增強版 SRT 處理器
        script_path = "./enhanced_srt_processor.py"
        if not os.path.exists(script_path):
            print("❌ 找不到 enhanced_srt_processor.py，回退到修正版")
            return process_folder_srt_optimized(folder_path)
        
        # 確保使用正確的 Python 環境
        python_executable = "./venv/bin/python" if os.path.exists("./venv/bin/python") else sys.executable
        
        cmd = [
            python_executable,
            script_path,
            str(folder_path)
            # 不指定模式，讓用戶互動選擇
        ]
        
        print(f"🚀 使用增強版 SRT 處理器")
        print("💡 系統將提供精度和速度的選擇選項")
        
        # 執行增強處理
        result = subprocess.run(
            cmd,
            # 不使用 capture_output，讓用戶可以互動
            timeout=3600  # 1小時超時
        )
        
        if result.returncode == 0:
            print("✅ 增強版 SRT 處理成功")
            return True
        else:
            print("❌ 增強版 SRT 處理失敗")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ SRT 處理超時")
        return False
    except Exception as e:
        print(f"❌ SRT 處理錯誤: {str(e)}")
        return False

def process_folder_srt_optimized(folder_path):
    """使用簡化版 SRT 處理器處理資料夾"""
    try:
        # 直接導入簡化版處理器
        from simple_srt_processor import process_folder_to_srt
        
        print("🚀 使用簡化版 SRT 處理器")
        
        # 直接調用處理函數，避免子程序問題
        stats = process_folder_to_srt(Path(folder_path), "gpt-transcribe")
        
        # 根據結果判斷成功或失敗
        if stats['success'] > 0 or stats['skipped'] > 0:
            print("✅ SRT 處理完成")
            return True
        else:
            print("❌ SRT 處理失敗")
            return False
            
    except ImportError:
        print("❌ 找不到簡化版 SRT 處理器，使用回退方法")
        return process_folder_srt_fallback(folder_path)
    except Exception as e:
        print(f"❌ SRT 處理錯誤: {str(e)}")
        return False

def process_folder_srt_fallback(folder_path):
    """SRT 處理回退方法"""
    import subprocess
    import os
    
    try:
        # 使用簡化版處理器腳本
        script_path = "./simple_srt_processor.py"
        if not os.path.exists(script_path):
            print("❌ 找不到任何 SRT 處理器")
            return False
        
        # 確保使用正確的 Python 環境
        python_executable = "./venv/bin/python" if os.path.exists("./venv/bin/python") else sys.executable
        
        cmd = [
            python_executable,
            script_path,
            str(folder_path),
            "gpt-transcribe"
        ]
        
        print(f"🚀 使用回退 SRT 處理器")
        
        # 執行處理
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1小時超時
        )
        
        if result.returncode == 0:
            print("✅ 回退 SRT 處理成功")
            if result.stdout:
                print("📋 處理結果:")
                lines = result.stdout.split('\n')
                for line in lines[-10:]:
                    if line.strip():
                        print(f"   {line}")
            return True
        else:
            print("❌ 回退 SRT 處理失敗")
            if result.stderr:
                print("❌ 錯誤信息:")
                print(result.stderr[-300:])
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ SRT 處理超時")
        return False
    except Exception as e:
        print(f"❌ SRT 處理錯誤: {str(e)}")
        return False

def show_processing_report(processor):
    """顯示處理報告"""
    print("\n📝 處理報告")
    print("=" * 40)
    
    # 統計所有資料夾狀態
    total_folders = 0
    audio_folders = 0
    processed_folders = 0
    failed_folders = 0
    
    for folder in processor.base_path.iterdir():
        if folder.is_dir() and not folder.name.startswith('.'):
            total_folders += 1
            audio_files = processor.find_audio_files(folder)
            if audio_files:
                audio_folders += 1
                is_processed, reason = processor.is_folder_already_processed(folder)
                if is_processed:
                    if "錯誤" in reason or "失敗" in reason:
                        failed_folders += 1
                    else:
                        processed_folders += 1
    
    print(f"📊 總體統計：")
    print(f"   📁 總資料夾數: {total_folders}")
    print(f"   🎵 音訊資料夾數: {audio_folders}")
    print(f"   ✅ 成功處理: {processed_folders}")
    print(f"   ❌ 處理失敗: {failed_folders}")
    print(f"   ⏳ 待處理: {audio_folders - processed_folders - failed_folders}")
    
    if audio_folders > 0:
        completion_rate = (processed_folders / audio_folders) * 100
        print(f"   📈 完成率: {completion_rate:.1f}%")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 程式已中斷，再見！")
    except Exception as e:
        print(f"\n❌ 程式錯誤: {str(e)}")
        sys.exit(1)
