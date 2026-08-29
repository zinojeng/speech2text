#!/usr/bin/env python3
"""
[DEPRECATED] 改進版 SRT 處理器

注意：此檔案已被棄用。主要的 srt_merge_processor.py 現已包含所有改進功能：
- 自動移除時間戳記
- 正確整合投影片內容
- 使用 gemini-2.5-pro-preview-06-05 模型

請直接使用 srt_merge_processor.py 或 interactive_merge.sh
"""

import re
from pathlib import Path
from srt_merge_processor import SRTMergeProcessor, SRTSegment
from typing import List, Dict, Tuple
import logging
from gemini_client import GeminiTextModel
from model_config import GEMINI_REFINE_CHEAP

logger = logging.getLogger(__name__)


class ImprovedSRTProcessor(SRTMergeProcessor):
    """改進的 SRT 處理器，更好地整合投影片內容"""
    
    def format_time_inline(self, seconds: float) -> str:
        """格式化時間為更簡潔的內嵌格式"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"({minutes:02d}:{secs:02d})"
    
    def clean_timestamps_from_text(self, text: str) -> str:
        """清理文字中的時間戳記，使其更優雅"""
        # 移除 [HH:MM:SS] 格式的時間戳
        text = re.sub(r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]', '', text)
        # 移除多餘的空格
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def merge_with_gemini_improved(self, segments: List[SRTSegment],
                                  segment_images: Dict[int, List[str]],
                                  slide_contents: List[Tuple[str, str]]) -> str:
        """改進的 Gemini 合併，確保投影片內容被充分利用"""
        try:
            model = GeminiTextModel(GEMINI_REFINE_CHEAP)
            
            # 準備 SRT 內容（不含時間戳）
            srt_lines = []
            for i, segment in enumerate(segments):
                # 添加段落前的圖片
                if i in segment_images:
                    for img_path in segment_images[i]:
                        srt_lines.append(f"[IMAGE: {img_path}]")
                
                # 只添加內容，不加時間戳
                srt_lines.append(segment.text)
            
            srt_text = '\n\n'.join(srt_lines)
            
            # 準備投影片內容，包含更多細節
            slides_text = ""
            for i, (name, content) in enumerate(slide_contents):
                slides_text += f"\n\n=== 投影片 {i+1}: {name} ===\n"
                slides_text += "以下是投影片的詳細內容分析：\n"
                slides_text += content
            
            # 改進的提示詞
            prompt = f"""請根據以下演講內容和投影片分析，創建一份整合的會議筆記。

重要指示：
1. 以演講者的內容為主要架構
2. 從投影片分析中提取關鍵資訊（如數據、圖表說明、研究結果等），補充到相關的演講段落中
3. 當演講者提到某個概念時，查找投影片中是否有更詳細的解釋或數據，並整合進去
4. 投影片中的圖表分析、統計數據、參考文獻等重要資訊必須被納入
5. 保留所有的 [IMAGE: 路徑] 標記在適當位置
6. 不要在文中加入時間戳記
7. 使用繁體中文

格式要求：
- 使用清晰的標題和子標題
- 重要數據用粗體標示
- 在每個主要段落後，如果投影片有補充資訊，用「📊 投影片補充」標示
- 引用具體數據時，註明來源（如：根據投影片顯示...）

演講內容：
{srt_text}

投影片詳細分析：
{slides_text}

請創建一份整合的筆記，確保投影片中的重要資訊都被適當地整合到演講內容中。"""
            
            response = model.generate_content(prompt)
            
            # 清理可能殘留的時間戳
            result = self.clean_timestamps_from_text(response.text)
            return result
            
        except Exception as e:
            logger.error(f"Gemini API 處理失敗: {e}")
            return self.simple_merge(segments, segment_images)
    
    def process_files_improved(self, srt_file: str, slide_folders: List[str], 
                              slide_files: List[str] = None, output_base: str = None) -> dict:
        """改進的處理流程"""
        # 先調用父類的處理
        result = super().process_files(srt_file, slide_folders, slide_files, output_base)
        
        if result['success'] and slide_files:
            # 使用改進的 Gemini 處理
            try:
                # 重新載入投影片內容
                slide_contents = []
                for slide_file in slide_files:
                    if Path(slide_file).exists():
                        with open(slide_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        slide_contents.append((Path(slide_file).name, content))
                
                if slide_contents and hasattr(self, 'segments'):
                    # 重新建立圖片映射
                    segment_images = {}
                    for image_time, image_path in sorted(self.all_images.items()):
                        insert_pos = self.find_best_insertion_point(image_time, self.segments)
                        if insert_pos not in segment_images:
                            segment_images[insert_pos] = []
                        segment_images[insert_pos].append(image_path)
                    
                    # 使用改進的合併方法
                    improved_content = self.merge_with_gemini_improved(
                        self.segments, segment_images, slide_contents
                    )
                    
                    # 儲存改進版本
                    output_dir = Path(srt_file).parent
                    improved_md = output_dir / f"{output_base}_improved.md"
                    self.save_markdown(improved_content, str(improved_md))
                    
                    improved_docx = output_dir / f"{output_base}_improved.docx"
                    self.markdown_to_docx(improved_content, str(improved_docx))
                    
                    result['improved_markdown'] = str(improved_md)
                    result['improved_docx'] = str(improved_docx)
                    
                    logger.info("生成了改進版本的文件")
            
            except Exception as e:
                logger.error(f"生成改進版本失敗: {e}")
        
        return result


def main():
    """測試改進版處理器"""
    import sys
    
    print("\n⚠️  警告：此檔案已被棄用！")
    print("主要的 srt_merge_processor.py 現已包含所有改進功能。")
    print("請使用: python srt_merge_processor.py <srt檔案> <圖片資料夾> [--slides <md檔案>...]\n")
    
    if len(sys.argv) < 3:
        print("用法: python improved_srt_processor.py <srt檔案> <圖片資料夾> [--slides <md檔案>...]")
        sys.exit(1)
    
    # 使用改進的處理器
    processor = ImprovedSRTProcessor()
    
    # 解析參數
    srt_file = sys.argv[1]
    image_folders = []
    slide_files = []
    
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--slides':
            i += 1
            while i < len(sys.argv) and not sys.argv[i].startswith('--'):
                slide_files.append(sys.argv[i])
                i += 1
        else:
            image_folders.append(sys.argv[i])
            i += 1
    
    # 處理檔案
    result = processor.process_files_improved(
        srt_file,
        image_folders,
        slide_files
    )
    
    if result['success']:
        print("\n✅ 處理成功！")
        if 'improved_markdown' in result:
            print(f"改進版 Markdown: {result['improved_markdown']}")
            print(f"改進版 DOCX: {result['improved_docx']}")
    else:
        print(f"\n❌ 處理失敗: {result.get('error', '未知錯誤')}")


if __name__ == "__main__":
    main()