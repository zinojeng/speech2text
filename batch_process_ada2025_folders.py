"""
批次處理 ADA2025 多個資料夾
Batch process multiple ADA2025 folders sequentially
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import time
import json

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_audio_files(folder_path: Path) -> list:
    """
    在資料夾中尋找音訊檔案
    
    Args:
        folder_path: 資料夾路徑
        
    Returns:
        音訊檔案路徑列表
    """
    audio_extensions = {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma', '.mp4', '.mov', '.avi', '.mkv', '.webm'}
    audio_files = []
    
    try:
        for file_path in folder_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                audio_files.append(file_path)
        
        # 按檔名排序
        audio_files.sort(key=lambda x: x.name)
        
    except Exception as e:
        logger.error(f"搜尋音訊檔案時發生錯誤: {e}")
    
    return audio_files

def find_transcript_files(folder_path: Path) -> list:
    """
    在資料夾中尋找轉錄檔案
    
    Args:
        folder_path: 資料夾路徑
        
    Returns:
        轉錄檔案路徑列表
    """
    transcript_files = []
    
    try:
        for file_path in folder_path.rglob('*轉錄*.txt'):
            if file_path.is_file():
                transcript_files.append(file_path)
        
        # 按檔名排序
        transcript_files.sort(key=lambda x: x.name)
        
    except Exception as e:
        logger.error(f"搜尋轉錄檔案時發生錯誤: {e}")
    
    return transcript_files

def process_single_folder(folder_path: Path, output_base_path: Path) -> dict:
    """
    處理單一資料夾
    
    Args:
        folder_path: 要處理的資料夾路徑
        output_base_path: 輸出基礎路徑
        
    Returns:
        處理結果統計
    """
    start_time = time.time()
    
    result = {
        'folder_name': folder_path.name,
        'folder_path': str(folder_path),
        'audio_files_found': 0,
        'transcript_files_found': 0,
        'processed_files': 0,
        'failed_files': 0,
        'processing_time': 0,
        'success': False,
        'error': None,
        'generated_files': []
    }
    
    try:
        print(f"\n{'='*80}")
        print(f"處理資料夾: {folder_path.name}")
        print(f"路徑: {folder_path}")
        print(f"{'='*80}")
        
        # 搜尋音訊檔案
        audio_files = find_audio_files(folder_path)
        result['audio_files_found'] = len(audio_files)
        
        # 搜尋轉錄檔案
        transcript_files = find_transcript_files(folder_path)
        result['transcript_files_found'] = len(transcript_files)
        
        print(f"找到 {len(audio_files)} 個音訊檔案")
        print(f"找到 {len(transcript_files)} 個轉錄檔案")
        
        if not transcript_files:
            print("⚠️ 未找到轉錄檔案，跳過此資料夾")
            result['error'] = "未找到轉錄檔案"
            return result
        
        # 處理每個轉錄檔案
        for transcript_file in transcript_files:
            try:
                print(f"\n處理轉錄檔案: {transcript_file.name}")
                
                # 使用現有的增強版摘要生成功能
                success = process_transcript_file(transcript_file, output_base_path)
                
                if success:
                    result['processed_files'] += 1
                    result['generated_files'].append(transcript_file.name)
                    print(f"✅ 成功處理: {transcript_file.name}")
                else:
                    result['failed_files'] += 1
                    print(f"❌ 處理失敗: {transcript_file.name}")
                
                # 添加延遲避免 API 限制
                time.sleep(2)
                
            except Exception as e:
                result['failed_files'] += 1
                print(f"❌ 處理 {transcript_file.name} 時發生錯誤: {e}")
        
        result['success'] = result['processed_files'] > 0
        
    except Exception as e:
        result['error'] = str(e)
        print(f"❌ 處理資料夾時發生錯誤: {e}")
    
    finally:
        result['processing_time'] = time.time() - start_time
    
    return result

def process_transcript_file(transcript_file: Path, output_base_path: Path) -> bool:
    """
    處理單一轉錄檔案
    
    Args:
        transcript_file: 轉錄檔案路徑
        output_base_path: 輸出基礎路徑
        
    Returns:
        處理是否成功
    """
    try:
        # 檢查 API 金鑰
        google_key = os.getenv('GOOGLE_API_KEY')
        if not google_key:
            print("❌ 未找到 GOOGLE_API_KEY 環境變數")
            return False
        
        # 讀取轉錄內容
        with open(transcript_file, 'r', encoding='utf-8') as f:
            full_content = f.read()
        
        # 提取轉錄內容（跳過檔案資訊部分）
        content_lines = full_content.split('\n')
        transcript_start = False
        transcript_lines = []
        
        for line in content_lines:
            if line.strip() == "轉錄內容:":
                transcript_start = True
                continue
            elif transcript_start and line.strip():
                transcript_lines.append(line)
        
        transcript_content = '\n'.join(transcript_lines)
        
        if not transcript_content.strip():
            print("⚠️ 轉錄內容為空")
            return False
        
        # 生成檔案名稱
        base_name = transcript_file.stem.replace('_轉錄_20250727_094703', '')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 使用增強版 prompt 生成摘要
        from batch_summary_service import SummaryService, SummaryRequest
        from batch_audio_models import ProcessingConfig, SummaryModel
        
        config = ProcessingConfig(
            summary_model=SummaryModel.GEMINI_FLASH,
            retry_attempts=2,
            retry_delay=1.0
        )
        
        summary_service = SummaryService(config)
        
        request = SummaryRequest(
            transcript=transcript_content,
            file_name=base_name,
            language="zh"
        )
        
        # 生成摘要
        result = summary_service.generate_summary(request)
        
        if not result.success:
            print(f"❌ 摘要生成失敗: {result.error}")
            return False
        
        # 保存結果
        output_folder = output_base_path / transcript_file.parent.name
        output_folder.mkdir(parents=True, exist_ok=True)
        
        # 保存 Markdown 格式
        md_file = output_folder / f"{base_name}_詳細筆記_v4_{timestamp}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# {base_name} - 超強化版詳細筆記\n\n")
            f.write(f"**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**處理時間**: {result.processing_time:.1f} 秒\n")
            f.write(f"**使用模型**: {result.model_used}\n")
            f.write(f"**筆記版本**: 超強化版詳細筆記 v4\n")
            f.write(f"**原始轉錄**: {transcript_file.name}\n")
            f.write(f"**資料夾**: {transcript_file.parent.name}\n")
            f.write("\n" + "="*50 + "\n\n")
            f.write(result.content)
        
        # 生成 DOCX 格式
        try:
            from convert_summary_to_docx import MarkdownToDocxConverter
            
            converter = MarkdownToDocxConverter()
            converter.convert_markdown_to_docx(
                markdown_content=result.content,
                title=f"{base_name} - 超強化版詳細筆記"
            )
            
            docx_file = output_folder / f"{base_name}_詳細筆記_v4_{timestamp}.docx"
            converter.save_document(str(docx_file))
            
            print(f"   📄 Markdown: {md_file.name}")
            print(f"   📄 DOCX: {docx_file.name}")
            
        except Exception as e:
            print(f"   ⚠️ DOCX 生成失敗: {e}")
            print(f"   📄 Markdown: {md_file.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ 處理轉錄檔案時發生錯誤: {e}")
        return False

def batch_process_ada2025_folders():
    """批次處理 ADA2025 所有資料夾"""
    
    print("=== ADA2025 批次資料夾處理器 ===")
    
    # 設定路徑
    base_path = Path("/Volumes/WD_BLACK/國際年會/ADA2025")
    output_base_path = Path("temp/ada2025_batch_results")
    
    if not base_path.exists():
        print(f"❌ 基礎路徑不存在: {base_path}")
        return False
    
    # 創建輸出目錄
    output_base_path.mkdir(parents=True, exist_ok=True)
    
    # 獲取所有子資料夾
    folders = []
    for item in base_path.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            folders.append(item)
    
    folders.sort(key=lambda x: x.name)
    
    print(f"找到 {len(folders)} 個資料夾需要處理")
    
    # 處理統計
    total_start_time = time.time()
    results = []
    total_processed = 0
    total_failed = 0
    
    # 依序處理每個資料夾
    for i, folder in enumerate(folders, 1):
        print(f"\n[{i}/{len(folders)}] 開始處理資料夾...")
        
        result = process_single_folder(folder, output_base_path)
        results.append(result)
        
        total_processed += result['processed_files']
        total_failed += result['failed_files']
        
        print(f"資料夾處理完成: {result['processed_files']} 成功, {result['failed_files']} 失敗")
        
        # 在資料夾之間添加延遲
        if i < len(folders):
            print("等待 5 秒後處理下一個資料夾...")
            time.sleep(5)
    
    # 生成總結報告
    total_time = time.time() - total_start_time
    
    print(f"\n{'='*80}")
    print("=== 批次處理完成 ===")
    print(f"總處理時間: {total_time:.1f} 秒")
    print(f"處理資料夾數: {len(folders)}")
    print(f"成功處理檔案: {total_processed}")
    print(f"失敗檔案: {total_failed}")
    print(f"成功率: {(total_processed / (total_processed + total_failed) * 100):.1f}%" if (total_processed + total_failed) > 0 else "N/A")
    
    # 保存詳細報告
    report_file = output_base_path / f"batch_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    report_data = {
        'processing_summary': {
            'total_time': total_time,
            'folders_processed': len(folders),
            'files_processed': total_processed,
            'files_failed': total_failed,
            'success_rate': (total_processed / (total_processed + total_failed) * 100) if (total_processed + total_failed) > 0 else 0
        },
        'folder_results': results,
        'timestamp': datetime.now().isoformat()
    }
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print(f"📊 詳細報告已保存: {report_file}")
    
    # 顯示成功處理的資料夾
    successful_folders = [r for r in results if r['success']]
    if successful_folders:
        print(f"\n✅ 成功處理的資料夾 ({len(successful_folders)}):")
        for result in successful_folders:
            print(f"   - {result['folder_name']}: {result['processed_files']} 檔案")
    
    # 顯示失敗的資料夾
    failed_folders = [r for r in results if not r['success']]
    if failed_folders:
        print(f"\n❌ 處理失敗的資料夾 ({len(failed_folders)}):")
        for result in failed_folders:
            print(f"   - {result['folder_name']}: {result.get('error', '未知錯誤')}")
    
    print(f"\n📁 輸出目錄: {output_base_path}")
    
    return True

if __name__ == "__main__":
    try:
        success = batch_process_ada2025_folders()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 使用者中斷處理")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 批次處理發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)