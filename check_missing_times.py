#!/usr/bin/env python3
"""
檢查缺失時間點的圖片
"""

import os
import glob
import re

# 缺失的時間點（秒）
missing_times = [
    21,    # 00:00:21
    63,    # 00:01:03
    73,    # 00:01:13
    1060,  # 00:17:40
    1321,  # 00:22:01
    1555,  # 00:25:55
    2238,  # 00:37:18
    2250,  # 00:37:30
    2268,  # 00:37:48
    2292,  # 00:38:12
    2334,  # 00:38:54
    2581,  # 00:43:01
]

def parse_filename_time(filename):
    """從檔名解析時間"""
    match = re.search(r't(\d+)m([\d.]+)s', filename)
    if match:
        minutes = int(match.group(1))
        seconds = float(match.group(2))
        return minutes * 60 + seconds
    return None

def find_nearby_images(base_path, target_time, tolerance=60):
    """找出目標時間附近的圖片"""
    folders = [
        "1. GLP-1 RA",
        "2. GLP-1GIP RA",
        "3. SGLT2i",
        "4. Rebuttal GLP-1 RA",
        "5. Rebuttal SGLT2i",
        "6. Rebuttal GLPGIP"
    ]
    
    nearby_images = []
    
    for folder in folders:
        folder_path = os.path.join(base_path, folder)
        if not os.path.exists(folder_path):
            continue
            
        for img_file in glob.glob(os.path.join(folder_path, "*.jpg")):
            filename = os.path.basename(img_file)
            file_time = parse_filename_time(filename)
            
            if file_time and abs(file_time - target_time) <= tolerance:
                diff = file_time - target_time
                nearby_images.append((diff, file_time, filename, folder))
    
    return sorted(nearby_images, key=lambda x: abs(x[0]))

def format_time(seconds):
    """將秒數格式化為 MM:SS 或 HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def main():
    base_path = "/Volumes/WD_BLACK/國際年會/ADA2025/If You Had to Pick Just One"
    
    print("檢查缺失時間點的附近圖片")
    print("=" * 80)
    
    for missing_time in missing_times:
        print(f"\n目標時間: {format_time(missing_time)} ({missing_time}秒)")
        print("-" * 40)
        
        # 找出前後60秒內的圖片
        nearby = find_nearby_images(base_path, missing_time, tolerance=60)
        
        if nearby:
            print("附近的圖片:")
            for diff, file_time, filename, folder in nearby[:5]:  # 只顯示最近的5個
                if diff > 0:
                    print(f"  +{diff:4.0f}秒: {filename} ({folder})")
                else:
                    print(f"  {diff:4.0f}秒: {filename} ({folder})")
        else:
            print("  [60秒內沒有圖片]")
    
    print("\n" + "=" * 80)
    print("說明：這些時間點可能是演講中沒有投影片的部分，或者是過場時間。")

if __name__ == "__main__":
    main()