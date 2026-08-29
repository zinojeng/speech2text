#!/usr/bin/env python3
"""
修正版優化 SRT 處理器
Fixed Optimized SRT Processor

針對不同模型的 SRT 支援情況進行智能處理
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

class FixedOptimizedSRTProcessor:
    """修正版優化 SRT 處理器"""
    
    def __init__(self):
        self.openai_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_key:
            raise ValueError("未找到 OPENAI_API_KEY")
    
    def process_audio_to_srt_smart(self, audio_path: Path, model: str = "gpt-transcribe") -> bool:
        """
        智能處理音訊檔案為 SRT 格式
        根據模型支援情況選擇最佳方法
        """
        print(f"🚀 智能 SRT 處理: {audio_path.name}")
        print(f"🤖 使用模型: {model}")
        start_time = time.time()
        
        try:
            # 檢查是否已存在 SRT 檔案
            srt_path = audio_path.parent / f"{audio_path.stem}.srt"
            if srt_path.exists() and self._is_srt_complete(srt_path):
                print(f"✅ SRT 檔案已存在且完整: {srt_path.name}")
                return True
            
            # 根據模型選擇處理方法
            if self._model_supports_srt(model):
                print(f"✅ 模型 {model} 支援 SRT，使用直接 API 方法")
                success = self._direct_api_srt(audio_path, srt_path, model)
            else:
                print(f"⚠️ 模型 {model} 不支援 SRT，使用文字轉換方法")
                success = self._text_to_srt_conversion(audio_path, srt_path, model)
            
            elapsed = time.time() - start_time
            if success:
                print(f"✅ SRT 處理完成: {elapsed:.1f}秒")
                return True
            else:
                print(f"❌ SRT 處理失敗: {elapsed:.1f}秒")
                return False
                
        except Exception as e:
            print(f"❌ SRT 處理錯誤: {str(e)}")
            return False
    
    def _model_supports_srt(self, model: str) -> bool:
        """
        檢查模型是否支援 SRT 格式
        根據 OpenAI API 文檔和實際測試結果
        """
        srt_supported_models = {
            "gpt-transcribe"  # 確認支援 SRT
        }
        return model in srt_supported_models
    
    def _direct_api_srt(self, audio_path: Path, output_path: Path, model: str) -> bool:
        """
        直接使用 API 的 SRT 格式輸出
        """
        try:
            cmd = [
                sys.executable,
                "gpt4o_transcribe.py",
                str(audio_path),
                "--model", model,
                "--format", "srt"
            ]
            
            print(f"🔧 執行直接 SRT 命令: {' '.join(cmd[-3:])}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30分鐘超時
            )
            
            if result.returncode == 0:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)
                
                if self._is_srt_complete(output_path):
                    print("✅ 直接 SRT 生成成功")
                    return True
                else:
                    print("⚠️ 直接 SRT 生成不完整")
                    return False
            else:
                print(f"❌ 直接 SRT 失敗: {result.stderr[-200:]}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ 直接 SRT 超時")
            return False
        except Exception as e:
            print(f"❌ 直接 SRT 錯誤: {str(e)}")
            return False
    
    def _text_to_srt_conversion(self, audio_path: Path, output_path: Path, model: str) -> bool:
        """
        先獲取文字轉錄，然後轉換為 SRT 格式
        適用於不支援 SRT 的模型
        """
        try:
            print("🔄 步驟 1: 獲取文字轉錄")
            
            # 先獲取文字轉錄
            cmd = [
                sys.executable,
                "gpt4o_transcribe.py",
                str(audio_path),
                "--model", model,
                "--format", "text"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800
            )
            
            if result.returncode != 0:
                print(f"❌ 文字轉錄失敗: {result.stderr[-200:]}")
                return False
            
            print("✅ 文字轉錄完成")
            print("🔄 步驟 2: 轉換為 SRT 格式")
            
            # 將文字轉換為 SRT
            text_content = result.stdout.strip()
            if not text_content:
                print("❌ 轉錄內容為空")
                return False
            
            srt_content = self._convert_text_to_srt(text_content, audio_path)
            
            # 寫入 SRT 檔案
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            print("✅ SRT 轉換完成")
            return True
            
        except subprocess.TimeoutExpired:
            print("❌ 文字轉錄超時")
            return False
        except Exception as e:
            print(f"❌ 文字轉 SRT 錯誤: {str(e)}")
            return False
    
    def _convert_text_to_srt(self, text: str, audio_path: Path) -> str:
        """
        將純文字轉換為 SRT 格式
        使用簡單但有效的分段邏輯
        """
        try:
            # 獲取音訊長度
            duration = self._get_audio_duration(audio_path)
            if not duration:
                duration = 300  # 預設 5 分鐘
            
            print(f"📏 音訊長度: {duration:.1f} 秒")
            
            # 清理和分段文字
            text = text.replace('\n', ' ').strip()
            
            # 按句號分段，但保持合理長度
            segments = []
            sentences = text.split('. ')
            
            current_segment = ""
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # 如果當前段落太長，就分割
                if len(current_segment) + len(sentence) > 100 and current_segment:
                    segments.append(current_segment.strip() + '.')
                    current_segment = sentence
                else:
                    if current_segment:
                        current_segment += '. ' + sentence
                    else:
                        current_segment = sentence
            
            # 添加最後一段
            if current_segment:
                segments.append(current_segment.strip() + ('.' if not current_segment.endswith('.') else ''))
            
            if not segments:
                return "1\n00:00:00,000 --> 00:00:05,000\n[無轉錄內容]\n"
            
            print(f"📝 分為 {len(segments)} 段")
            
            # 生成 SRT
            time_per_segment = duration / len(segments)
            srt_lines = []
            
            for i, segment in enumerate(segments, 1):
                start_time = (i - 1) * time_per_segment
                end_time = min(i * time_per_segment, duration)
                
                start_srt = self._seconds_to_srt_time(start_time)
                end_srt = self._seconds_to_srt_time(end_time)
                
                srt_lines.append(f"{i}")
                srt_lines.append(f"{start_srt} --> {end_srt}")
                srt_lines.append(segment)
                srt_lines.append("")  # 空行分隔
            
            return "\n".join(srt_lines)
            
        except Exception as e:
            print(f"⚠️ 文字轉 SRT 錯誤: {str(e)}")
            return "1\n00:00:00,000 --> 00:00:05,000\n[轉換錯誤]\n"
    
    def _get_audio_duration(self, audio_path: Path) -> Optional[float]:
        """
        獲取音訊檔案長度
        """
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', str(audio_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except:
            print("⚠️ 無法獲取音訊長度，使用預設值")
            return None
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """
        將秒數轉換為 SRT 時間格式 (HH:MM:SS,mmm)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def _is_srt_complete(self, srt_path: Path) -> bool:
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
    
    def batch_process_srt(self, folder_path: Path, model: str = "gpt-transcribe") -> dict:
        """
        批次處理資料夾中的音訊檔案
        """
        print(f"🚀 智能批次 SRT 處理: {folder_path}")
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
            if srt_path.exists() and self._is_srt_complete(srt_path):
                print(f"⏭️ 跳過已存在的完整 SRT: {srt_path.name}")
                stats['skipped'] += 1
                continue
            
            # 處理檔案
            if self.process_audio_to_srt_smart(audio_file, model):
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
        print(f"\n🎉 智能批次處理完成！")
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
        print("使用方法: python optimized_srt_processor_fixed.py <資料夾路徑> [模型]")
        print("模型選項:")
        print("  - gpt-transcribe (預設，支援 SRT)")
        print("  - gpt-transcribe (不支援 SRT，會自動轉換)")
        sys.exit(1)
    
    folder_path = Path(sys.argv[1])
    model = sys.argv[2] if len(sys.argv) > 2 else "gpt-transcribe"
    
    if not folder_path.exists():
        print(f"❌ 資料夾不存在: {folder_path}")
        sys.exit(1)
    
    print("🚀 修正版優化 SRT 處理器")
    print("=" * 50)
    print(f"📁 資料夾: {folder_path}")
    print(f"🤖 模型: {model}")
    
    # 顯示模型支援狀態
    processor = FixedOptimizedSRTProcessor()
    if processor._model_supports_srt(model):
        print(f"✅ 模型支援 SRT: 將使用直接 API 方法")
    else:
        print(f"⚠️ 模型不支援 SRT: 將使用文字轉換方法")
    
    print()
    
    try:
        stats = processor.batch_process_srt(folder_path, model)
        
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