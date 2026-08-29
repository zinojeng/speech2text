#!/usr/bin/env python3
"""
確保所有圖片都被插入的增強版 SRT 處理器
即使沒有完美的時間匹配，也會找到最接近的位置插入圖片
"""

import os
import sys
import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import glob

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ImageTimeExtractor:
    """從圖片檔名提取時間"""
    
    @staticmethod
    def extract_time(filename: str) -> Optional[float]:
        """從檔名提取時間（秒）"""
        # 嘗試 tXmYs 格式
        match = re.search(r't(\d+)m([\d.]+)s', filename)
        if match:
            minutes = int(match.group(1))
            seconds = float(match.group(2))
            return minutes * 60 + seconds
        
        # 嘗試其他可能的格式
        # 例如：slide_001_00-30.jpg (表示0分30秒)
        match = re.search(r'(\d+)-(\d+)', filename)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            return minutes * 60 + seconds
        
        return None


def analyze_image_usage(srt_file: str, image_folders: List[str]) -> Dict:
    """分析圖片使用情況"""
    
    # 1. 載入所有圖片
    all_images = {}  # {time: [(path, folder), ...]}
    total_count = 0
    
    for folder in image_folders:
        if not os.path.exists(folder):
            logger.warning(f"資料夾不存在: {folder}")
            continue
        
        folder_name = os.path.basename(folder)
        patterns = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
        
        for pattern in patterns:
            for img_path in glob.glob(os.path.join(folder, '**', pattern), recursive=True):
                filename = os.path.basename(img_path)
                time_sec = ImageTimeExtractor.extract_time(filename)
                
                if time_sec is not None:
                    if time_sec not in all_images:
                        all_images[time_sec] = []
                    all_images[time_sec].append((img_path, folder_name))
                    total_count += 1
                else:
                    logger.warning(f"無法從檔名提取時間: {filename}")
    
    logger.info(f"總共找到 {total_count} 張有時間戳的圖片")
    
    # 2. 分析 SRT 時間範圍
    srt_start = float('inf')
    srt_end = 0
    
    try:
        with open(srt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 找出所有時間戳
        time_pattern = r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})'
        matches = re.findall(time_pattern, content)
        
        for start_str, end_str in matches:
            start_time = parse_srt_time(start_str)
            end_time = parse_srt_time(end_str)
            srt_start = min(srt_start, start_time)
            srt_end = max(srt_end, end_time)
    
    except Exception as e:
        logger.error(f"解析 SRT 檔案失敗: {e}")
        return {}
    
    # 3. 分析使用情況
    within_range = 0
    before_start = 0
    after_end = 0
    orphaned_images = []
    
    for time_sec, images in all_images.items():
        if time_sec < srt_start:
            before_start += len(images)
            orphaned_images.extend([(time_sec, img) for img in images])
        elif time_sec > srt_end:
            after_end += len(images)
            orphaned_images.extend([(time_sec, img) for img in images])
        else:
            within_range += len(images)
    
    # 4. 生成報告
    report = {
        'total_images': total_count,
        'srt_time_range': (srt_start, srt_end),
        'within_range': within_range,
        'before_start': before_start,
        'after_end': after_end,
        'orphaned_images': sorted(orphaned_images, key=lambda x: x[0]),
        'all_images': all_images
    }
    
    # 5. 顯示報告
    print("\n" + "=" * 60)
    print("圖片使用分析報告")
    print("=" * 60)
    print(f"SRT 時間範圍: {format_time(srt_start)} - {format_time(srt_end)}")
    print(f"總圖片數: {total_count}")
    print(f"  - 在時間範圍內: {within_range}")
    print(f"  - 在開始之前: {before_start}")
    print(f"  - 在結束之後: {after_end}")
    
    if orphaned_images:
        print(f"\n孤立的圖片 (可能需要手動調整):")
        for time_sec, (img_path, folder) in orphaned_images[:10]:
            print(f"  {format_time(time_sec)}: {os.path.basename(img_path)} ({folder})")
        if len(orphaned_images) > 10:
            print(f"  ... 還有 {len(orphaned_images) - 10} 張")
    
    print("\n建議:")
    if before_start > 0:
        print(f"- 有 {before_start} 張圖片在 SRT 開始之前，考慮在開頭添加介紹段落")
    if after_end > 0:
        print(f"- 有 {after_end} 張圖片在 SRT 結束之後，考慮在結尾添加總結段落")
    
    print("=" * 60 + "\n")
    
    return report


def parse_srt_time(time_str: str) -> float:
    """解析 SRT 時間格式"""
    time_str = time_str.strip().replace(',', '.')
    parts = time_str.split(':')
    if len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    return 0.0


def format_time(seconds: float) -> str:
    """格式化時間"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def ensure_all_images_inserted(srt_file: str, image_folders: List[str], 
                              output_markdown: str) -> bool:
    """確保所有圖片都被插入到適當位置"""
    
    # 1. 分析圖片使用情況
    report = analyze_image_usage(srt_file, image_folders)
    if not report:
        return False
    
    # 2. 載入 SRT 內容
    try:
        with open(srt_file, 'r', encoding='utf-8') as f:
            srt_content = f.read()
    except Exception as e:
        logger.error(f"無法讀取 SRT 檔案: {e}")
        return False
    
    # 3. 解析 SRT 段落
    segments = []
    blocks = srt_content.strip().split('\n\n')
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            time_line = lines[1]
            time_match = re.match(r'(\S+)\s*-->\s*(\S+)', time_line)
            if time_match:
                start_time = parse_srt_time(time_match.group(1))
                end_time = parse_srt_time(time_match.group(2))
                text = ' '.join(lines[2:])
                segments.append({
                    'start': start_time,
                    'end': end_time,
                    'text': text
                })
    
    # 4. 為每張圖片找到最佳位置
    output_lines = ["# 演講內容與投影片整合（確保所有圖片）\n"]
    
    # 處理 SRT 開始之前的圖片
    before_images = []
    for time_sec, images in report['all_images'].items():
        if time_sec < report['srt_time_range'][0]:
            before_images.extend([(time_sec, img) for img in images])
    
    if before_images:
        output_lines.append("## 開場投影片\n")
        for time_sec, (img_path, folder) in sorted(before_images):
            output_lines.append(f"[IMAGE: {img_path}]")
            output_lines.append(f"*({format_time(time_sec)} - {folder})*\n")
    
    # 處理主要內容
    output_lines.append("## 演講內容\n")
    
    for i, segment in enumerate(segments):
        # 添加該段落時間範圍內的所有圖片
        segment_images = []
        for time_sec, images in report['all_images'].items():
            if segment['start'] <= time_sec <= segment['end']:
                segment_images.extend([(time_sec, img) for img in images])
        
        # 按時間排序並插入圖片
        if segment_images:
            for time_sec, (img_path, folder) in sorted(segment_images):
                output_lines.append(f"[IMAGE: {img_path}]\n")
        
        # 添加文字內容
        output_lines.append(f"[{format_time(segment['start'])}] {segment['text']}\n")
    
    # 處理 SRT 結束之後的圖片
    after_images = []
    for time_sec, images in report['all_images'].items():
        if time_sec > report['srt_time_range'][1]:
            after_images.extend([(time_sec, img) for img in images])
    
    if after_images:
        output_lines.append("## 結尾投影片\n")
        for time_sec, (img_path, folder) in sorted(after_images):
            output_lines.append(f"[IMAGE: {img_path}]")
            output_lines.append(f"*({format_time(time_sec)} - {folder})*\n")
    
    # 5. 寫入檔案
    try:
        with open(output_markdown, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output_lines))
        logger.info(f"✅ 已生成包含所有圖片的 Markdown: {output_markdown}")
        return True
    except Exception as e:
        logger.error(f"寫入檔案失敗: {e}")
        return False


def main():
    """主函數"""
    if len(sys.argv) < 3:
        print("用法: python ensure_all_images.py <srt檔案> <圖片資料夾1> [圖片資料夾2] ...")
        print("\n範例:")
        print("  python ensure_all_images.py transcript.srt folder1/ folder2/")
        sys.exit(1)
    
    srt_file = sys.argv[1]
    image_folders = sys.argv[2:]
    
    # 生成輸出檔名
    output_base = Path(srt_file).stem
    output_markdown = f"{output_base}_all_images.md"
    
    # 確保所有圖片都被插入
    if ensure_all_images_inserted(srt_file, image_folders, output_markdown):
        print(f"\n✅ 成功！請查看 {output_markdown}")
        
        # 轉換為 DOCX
        try:
            from srt_merge_processor import SRTMergeProcessor
            processor = SRTMergeProcessor()
            
            with open(output_markdown, 'r', encoding='utf-8') as f:
                content = f.read()
            
            docx_path = f"{output_base}_all_images.docx"
            if processor.markdown_to_docx(content, docx_path):
                print(f"✅ 已生成 DOCX: {docx_path}")
        except Exception as e:
            print(f"⚠️  無法生成 DOCX: {e}")
    else:
        print("\n❌ 處理失敗")


if __name__ == "__main__":
    main()