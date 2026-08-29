#!/usr/bin/env python3
"""
ADA2025 簡化版音訊批次處理器
ADA2025 Simple Audio Batch Processor

回到原始的、經過驗證的方法
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from ada2025_batch_processor import ADA2025BatchProcessor

# 載入 .env 檔案中的環境變數
load_dotenv()

def main():
    """主程式入口"""
    print("🎵 ADA2025 簡化版音訊批次處理器")
    print("=" * 50)
    
    # 初始化處理器
    processor = ADA2025BatchProcessor()
    
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
        print("4. ❌ 退出")
        
        choice = input("\n請選擇 (1-4): ").strip()
        
        if choice == '1':
            show_audio_statistics(processor)
        elif choice == '2':
            process_single_folder(processor)
        elif choice == '3':
            batch_process_audio(processor)
        elif choice == '4':
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
            
            # 使用原始的 audio_auto.sh 方法
            success = process_folder_with_audio_auto(selected_folder, output_format)
            
            if success:
                print(f"✅ 資料夾處理完成: {selected_folder.name}")
            else:
                print(f"❌ 資料夾處理失敗: {selected_folder.name}")
        else:
            print("❌ 無效選擇")
    except ValueError:
        print("❌ 請輸入有效數字")

def choose_output_format():
    """選擇輸出格式"""
    print("\n📝 選擇轉錄輸出格式：")
    print("1. 📄 TXT (純文字格式)")
    print("2. 🎬 SRT (字幕格式，含時間戳)")
    print("3. 📝 Markdown (格式化文字)")
    
    while True:
        try:
            choice = input("\n請選擇格式 (1-3): ").strip()
            if choice == '1':
                return 'text'
            elif choice == '2':
                return 'srt'
            elif choice == '3':
                return 'markdown'
            else:
                print("❌ 請輸入 1、2 或 3")
        except KeyboardInterrupt:
            print("\n❌ 操作已取消")
            return 'text'

def process_folder_with_audio_auto(folder_path, output_format):
    """使用原始的 audio_auto.sh 方法處理資料夾"""
    try:
        # 使用原始的、經過驗證的 audio_auto.sh 腳本
        script_path = "./audio_auto.sh"
        if not os.path.exists(script_path):
            print("❌ 找不到 audio_auto.sh 腳本")
            return False
        
        # 構建命令 - 使用原始方法
        cmd = [
            script_path,
            str(folder_path),
            "gpt-transcribe",  # 使用經濟型模型
            output_format
        ]
        
        print(f"🚀 使用原始 audio_auto.sh 方法")
        print(f"📋 命令: {' '.join(cmd)}")
        
        # 執行命令 - 不捕獲輸出，讓用戶看到實時進度
        result = subprocess.run(cmd, timeout=3600)  # 1小時超時
        
        if result.returncode == 0:
            print("✅ 處理成功")
            return True
        else:
            print("❌ 處理失敗")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 處理超時（超過1小時）")
        return False
    except Exception as e:
        print(f"❌ 處理過程中發生錯誤: {str(e)}")
        return False

def batch_process_audio(processor):
    """批次處理音訊檔案"""
    print("\n🚀 音訊檔案批次處理選項：")
    print("1. 快速批次 (3個資料夾)")
    print("2. 小批次 (5個資料夾)")
    print("3. 中批次 (10個資料夾)")
    print("4. 返回主選單")
    
    choice = input("\n請選擇 (1-4): ").strip()
    
    batch_sizes = {'1': 3, '2': 5, '3': 10}
    
    if choice in batch_sizes:
        batch_size = batch_sizes[choice]
    elif choice == '4':
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
    folders_to_process = unprocessed_folders[:batch_size]
    
    print(f"\n🎵 準備處理 {len(folders_to_process)} 個音訊資料夾：")
    for i, folder in enumerate(folders_to_process, 1):
        audio_count = len(processor.find_audio_files(folder))
        print(f"   {i}. {folder.name} ({audio_count} 個音訊檔案)")
    
    confirm = input(f"\n確認開始批次處理？(y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 取消處理")
        return
    
    # 開始批次處理
    print(f"\n🚀 開始批次處理 {len(folders_to_process)} 個音訊資料夾...")
    
    successful = 0
    failed = 0
    
    for i, folder in enumerate(folders_to_process, 1):
        print(f"\n📁 處理資料夾 {i}/{len(folders_to_process)}: {folder.name}")
        
        try:
            success = process_folder_with_audio_auto(folder, output_format)
            if success:
                successful += 1
                print(f"✅ 完成: {folder.name}")
            else:
                failed += 1
                print(f"❌ 失敗: {folder.name}")
        except Exception as e:
            failed += 1
            print(f"❌ 錯誤: {folder.name} - {str(e)}")
    
    # 處理完成統計
    print(f"\n🎉 批次處理完成！")
    print(f"   ✅ 成功: {successful} 個資料夾")
    print(f"   ❌ 失敗: {failed} 個資料夾")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 程式已中斷，再見！")
    except Exception as e:
        print(f"\n❌ 程式錯誤: {str(e)}")
        sys.exit(1)