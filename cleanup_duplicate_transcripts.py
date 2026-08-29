#!/usr/bin/env python3
"""
清理重複的轉錄檔案工具
Cleanup Duplicate Transcript Files Tool

用於清理 ADA2025 資料夾中重複的轉錄檔案，只保留最新的版本
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
import argparse

def find_duplicate_transcripts(base_path: str) -> dict:
    """
    尋找重複的轉錄檔案
    
    Args:
        base_path: 基礎路徑
        
    Returns:
        重複檔案的字典 {base_name: [file_paths]}
    """
    base_path = Path(base_path)
    duplicates = defaultdict(list)
    
    # 遞迴搜尋所有轉錄檔案
    for transcript_file in base_path.rglob("*_轉錄_*.txt"):
        # 提取基礎名稱（去掉時間戳）
        name_parts = transcript_file.stem.split("_轉錄_")
        if len(name_parts) >= 2:
            base_name = name_parts[0]
            duplicates[base_name].append(transcript_file)
    
    # 只返回有重複的檔案
    return {k: v for k, v in duplicates.items() if len(v) > 1}

def analyze_duplicates(duplicates: dict) -> None:
    """分析重複檔案的統計資訊"""
    total_files = sum(len(files) for files in duplicates.values())
    total_duplicates = total_files - len(duplicates)  # 減去每組要保留的一個檔案
    
    print(f"📊 重複檔案分析:")
    print(f"   重複的基礎檔案數: {len(duplicates)}")
    print(f"   總轉錄檔案數: {total_files}")
    print(f"   可刪除的重複檔案數: {total_duplicates}")
    
    # 顯示前10個重複最多的檔案
    sorted_duplicates = sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)
    
    print(f"\n📁 重複最多的檔案 (前10個):")
    for i, (base_name, files) in enumerate(sorted_duplicates[:10], 1):
        print(f"   {i:2d}. {base_name}: {len(files)} 個版本")
        for file_path in files:
            mtime = file_path.stat().st_mtime
            size = file_path.stat().st_size
            print(f"       - {file_path.name} ({size:,} bytes, {mtime})")

def cleanup_duplicates(duplicates: dict, dry_run: bool = True) -> dict:
    """
    清理重複檔案，只保留最新的版本
    
    Args:
        duplicates: 重複檔案字典
        dry_run: 是否為測試模式
        
    Returns:
        清理結果統計
    """
    results = {
        'deleted_files': 0,
        'kept_files': 0,
        'errors': 0,
        'deleted_list': [],
        'kept_list': [],
        'error_list': []
    }
    
    for base_name, files in duplicates.items():
        try:
            # 按修改時間排序，最新的在前
            sorted_files = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 保留最新的檔案
            keep_file = sorted_files[0]
            delete_files = sorted_files[1:]
            
            results['kept_files'] += 1
            results['kept_list'].append(keep_file)
            
            print(f"\n📁 處理: {base_name}")
            print(f"   ✅ 保留: {keep_file.name}")
            
            # 刪除舊版本
            for delete_file in delete_files:
                if dry_run:
                    print(f"   🗑️  [測試] 將刪除: {delete_file.name}")
                    results['deleted_files'] += 1
                    results['deleted_list'].append(delete_file)
                else:
                    try:
                        delete_file.unlink()
                        print(f"   🗑️  已刪除: {delete_file.name}")
                        results['deleted_files'] += 1
                        results['deleted_list'].append(delete_file)
                    except Exception as e:
                        print(f"   ❌ 刪除失敗: {delete_file.name} - {e}")
                        results['errors'] += 1
                        results['error_list'].append((delete_file, str(e)))
                        
        except Exception as e:
            print(f"❌ 處理 {base_name} 時發生錯誤: {e}")
            results['errors'] += 1
            results['error_list'].append((base_name, str(e)))
    
    return results

def main():
    """主程式"""
    parser = argparse.ArgumentParser(
        description="清理重複的轉錄檔案，只保留最新版本"
    )
    parser.add_argument(
        "--base-path",
        type=str,
        default="/Volumes/WD_BLACK/國際年會/ADA2025",
        help="ADA2025 基礎路徑"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="測試模式，不實際刪除檔案"
    )
    parser.add_argument(
        "--auto-confirm",
        action="store_true",
        help="自動確認，不詢問用戶"
    )
    
    args = parser.parse_args()
    
    print("=== ADA2025 重複轉錄檔案清理工具 ===")
    print(f"基礎路徑: {args.base_path}")
    print(f"模式: {'測試模式' if args.dry_run else '實際清理'}")
    print()
    
    # 檢查路徑是否存在
    base_path = Path(args.base_path)
    if not base_path.exists():
        print(f"❌ 錯誤：路徑不存在 - {base_path}")
        sys.exit(1)
    
    # 尋找重複檔案
    print("🔍 搜尋重複的轉錄檔案...")
    duplicates = find_duplicate_transcripts(args.base_path)
    
    if not duplicates:
        print("✅ 未找到重複的轉錄檔案")
        return
    
    # 分析重複檔案
    analyze_duplicates(duplicates)
    
    # 確認清理
    if not args.auto_confirm:
        print(f"\n{'='*60}")
        if args.dry_run:
            confirm = input("確定要執行測試清理嗎？(y/N): ").strip().lower()
        else:
            confirm = input("⚠️  確定要刪除重複檔案嗎？此操作無法復原！(y/N): ").strip().lower()
        
        if confirm not in ['y', 'yes']:
            print("❌ 使用者取消操作")
            return
    
    # 執行清理
    print(f"\n{'='*60}")
    print(f"開始清理重複檔案...")
    
    results = cleanup_duplicates(duplicates, args.dry_run)
    
    # 顯示結果
    print(f"\n{'='*60}")
    print("=== 清理完成 ===")
    print(f"✅ 保留檔案: {results['kept_files']}")
    print(f"🗑️  {'測試刪除' if args.dry_run else '已刪除'}檔案: {results['deleted_files']}")
    print(f"❌ 錯誤: {results['errors']}")
    
    if results['error_list']:
        print(f"\n❌ 錯誤詳情:")
        for item, error in results['error_list']:
            print(f"   - {item}: {error}")
    
    if args.dry_run and results['deleted_files'] > 0:
        print(f"\n💡 提示：這是測試模式，沒有實際刪除檔案")
        print(f"   要實際執行清理，請移除 --dry-run 參數")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 使用者中斷程式")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 程式執行失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)