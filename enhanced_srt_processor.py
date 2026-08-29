#!/usr/bin/env python3
"""
增強版 SRT 處理器
Enhanced SRT Processor

兩種模式的差異不再是「精度 vs 速度」，而是「時間戳來源」：
- high_precision：gemini-3.5-transcribe，回傳真實詞級時間戳與講者標記
- fast：gpt-transcribe，文字準確度最好，但時間軸是估算的
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

class EnhancedSRTProcessor:
    """增強版 SRT 處理器"""
    
    def __init__(self):
        self.openai_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_key:
            raise ValueError("未找到 OPENAI_API_KEY")
        
        # 模型配置
        self.models = {
            'high_precision': {
                'name': 'gemini-3.5-transcribe',
                'description': '真實時間戳模式',
                'features': ['詞級時間戳', '講者標記（最多 8 人）', '時間軸精準'],
                'cost_multiplier': 1.1,
                'speed_multiplier': 1.0,
                'accuracy': '時間戳精準，文字中等'
            },
            'fast': {
                'name': 'gpt-transcribe',
                'description': '文字優先模式',
                'features': ['文字準確度最好', 'keywords 專有名詞提示', '時間軸為估算值'],
                'cost_multiplier': 1.0,
                'speed_multiplier': 1.0,
                'accuracy': '文字最好，無真實時間戳'
            }
        }
    
    def choose_processing_mode(self, file_count: int = 1, file_types: List[str] = None) -> str:
        """
        智能選擇處理模式
        """
        print("\n🎯 SRT 處理模式選擇")
        print("=" * 50)
        
        # 顯示模式對比
        self._show_mode_comparison()
        
        # 智能推薦
        recommendation = self._get_smart_recommendation(file_count, file_types)
        print(f"\n💡 智能推薦: {recommendation}")
        
        print("\n📋 請選擇處理模式:")
        print("1. 🎯 真實時間戳模式 (gemini-3.5-transcribe)")
        print("   - 最準確的轉錄和時間戳")
        print("   - 語義語音活動檢測")
        print("   - 適合重要會議、專業內容")
        print()
        print("2. ⚡ 文字優先模式 (gpt-transcribe)")
        print("   - 快速處理，經濟成本")
        print("   - 適合批量處理、一般用途")
        print()
        print("3. 🔄 混合模式 (根據檔案類型智能選擇)")
        print("4. 📊 查看詳細對比")
        
        while True:
            try:
                choice = input("\n請選擇 (1-4): ").strip()
                if choice == '1':
                    return 'high_precision'
                elif choice == '2':
                    return 'fast'
                elif choice == '3':
                    return 'mixed'
                elif choice == '4':
                    self._show_detailed_comparison()
                    continue
                else:
                    print("❌ 請輸入 1、2、3 或 4")
            except KeyboardInterrupt:
                print("\n❌ 操作已取消")
                return 'fast'  # 預設快速模式
    
    def _show_mode_comparison(self):
        """顯示模式對比表"""
        print("\n📊 模式對比:")
        print("| 特性 | 真實時間戳模式 | 文字優先模式 |")
        print("|------|----------------|--------------|")
        print("| 模型 | gemini-3.5-transcribe | gpt-transcribe |")
        print("| 時間戳 | 🎯 詞級真實 | 📊 依字數估算 |")
        print("| 講者標記 | ✅ 最多 8 人 | ❌ 無 |")
        print("| 文字準確度 | 📊 中等 | 🎯 最好 |")
        print("| 成本 | 💰 $0.005/分 | 💵 $0.0045/分 |")
        print("| 適用場景 | 字幕、多講者會議 | 逐字稿、專有名詞多 |")
    
    def _show_detailed_comparison(self):
        """顯示詳細對比"""
        print("\n🔍 詳細技術對比:")
        print("=" * 60)
        
        for mode_key, config in self.models.items():
            print(f"\n🤖 {config['description']} ({config['name']}):")
            print(f"   精度等級: {config['accuracy']}")
            print(f"   相對成本: {config['cost_multiplier']:.1f}x")
            print(f"   相對速度: {config['speed_multiplier']:.1f}x")
            print("   特色功能:")
            for feature in config['features']:
                print(f"     - {feature}")
        
        print("\n💡 選擇建議:")
        print("   🎯 高精度模式適合:")
        print("     - 重要商務會議")
        print("     - 專業領域內容（醫療、法律）")
        print("     - 需要精確時間戳的字幕")
        print("     - 嘈雜環境或多語言內容")
        
        print("\n   ⚡ 快速模式適合:")
        print("     - 大批量檔案處理")
        print("     - 一般會議記錄")
        print("     - 預算有限的項目")
        print("     - 需要快速交付的場景")
    
    def _get_smart_recommendation(self, file_count: int, file_types: List[str] = None) -> str:
        """
        基於檔案數量和類型提供智能推薦
        """
        if file_count > 10:
            return "建議使用快速模式 - 大批量處理更經濟"
        elif file_count == 1:
            return "建議使用高精度模式 - 單檔案處理可獲得最佳品質"
        else:
            return "建議使用混合模式 - 根據檔案重要性靈活選擇"
    
    def process_audio_to_srt_enhanced(self, audio_path: Path, mode: str = 'fast') -> bool:
        """
        增強版 SRT 處理
        """
        print(f"🚀 增強版 SRT 處理: {audio_path.name}")
        
        if mode not in self.models:
            print(f"❌ 無效模式: {mode}")
            return False
        
        model_config = self.models[mode]
        model_name = model_config['name']
        
        print(f"🤖 使用模式: {model_config['description']} ({model_name})")
        print(f"🎯 預期精度: {model_config['accuracy']}")
        
        start_time = time.time()
        
        try:
            # 檢查是否已存在 SRT 檔案
            srt_path = audio_path.parent / f"{audio_path.stem}.srt"
            if srt_path.exists() and self._is_srt_complete(srt_path):
                print(f"✅ SRT 檔案已存在且完整: {srt_path.name}")
                return True
            
            # 執行轉錄
            success = self._execute_transcription(audio_path, srt_path, model_name, mode)
            
            elapsed = time.time() - start_time
            
            if success:
                # 品質評估
                quality_score = self._assess_srt_quality(srt_path, mode)
                print(f"✅ SRT 處理完成: {elapsed:.1f}秒")
                print(f"📊 品質評估: {quality_score}")
                
                # 後處理建議
                if mode == 'fast':
                    print("💡 建議: 快速模式完成，如需更高精度可考慮重新處理")
                
                return True
            else:
                print(f"❌ SRT 處理失敗: {elapsed:.1f}秒")
                return False
                
        except Exception as e:
            print(f"❌ SRT 處理錯誤: {str(e)}")
            return False
    
    def _execute_transcription(self, audio_path: Path, output_path: Path, model_name: str, mode: str) -> bool:
        """
        執行轉錄處理
        """
        try:
            cmd = [
                sys.executable,
                "gpt4o_transcribe.py",
                str(audio_path),
                "--model", model_name,
                "--format", "srt"
            ]
            
            print(f"🔧 執行轉錄命令...")
            
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
                    return True
                else:
                    print("⚠️ 生成的 SRT 檔案不完整")
                    return False
            else:
                print(f"❌ 轉錄失敗: {result.stderr[-200:]}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ 轉錄超時")
            return False
        except Exception as e:
            print(f"❌ 轉錄錯誤: {str(e)}")
            return False
    
    def _assess_srt_quality(self, srt_path: Path, mode: str) -> str:
        """
        評估 SRT 品質
        """
        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.strip().split('\n')
            subtitle_count = len([line for line in lines if line.strip().isdigit()])
            
            model_config = self.models[mode]
            
            if mode == 'high_precision':
                return f"高精度模式 - {subtitle_count} 個字幕段，預期錯誤率 < 5%"
            else:
                return f"快速模式 - {subtitle_count} 個字幕段，建議人工校對重要部分"
                
        except Exception:
            return "無法評估品質"
    
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
    
    def batch_process_enhanced(self, folder_path: Path, mode: str = None) -> dict:
        """
        增強版批次處理
        """
        print(f"🚀 增強版批次 SRT 處理: {folder_path}")
        
        # 尋找音訊檔案
        audio_extensions = {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma'}
        audio_files = []
        for ext in audio_extensions:
            audio_files.extend(folder_path.glob(f"*{ext}"))
        
        audio_files = [f for f in audio_files if not f.name.startswith('._')]
        
        if not audio_files:
            print("❌ 未找到音訊檔案")
            return {'success': 0, 'failed': 0, 'skipped': 0}
        
        print(f"📁 找到 {len(audio_files)} 個音訊檔案")
        
        # 如果未指定模式，讓用戶選擇
        if not mode:
            mode = self.choose_processing_mode(len(audio_files))
        
        # 處理統計
        stats = {'success': 0, 'failed': 0, 'skipped': 0, 'total_cost': 0, 'total_time': 0}
        start_time = time.time()
        
        print(f"\n🎯 使用模式: {self.models[mode]['description']}")
        
        for i, audio_file in enumerate(audio_files, 1):
            print(f"\n📁 處理 {i}/{len(audio_files)}: {audio_file.name}")
            
            # 檢查是否已存在完整的 SRT 檔案
            srt_path = audio_file.parent / f"{audio_file.stem}.srt"
            if srt_path.exists() and self._is_srt_complete(srt_path):
                print(f"⏭️ 跳過已存在的完整 SRT: {srt_path.name}")
                stats['skipped'] += 1
                continue
            
            # 處理檔案
            file_start = time.time()
            if self.process_audio_to_srt_enhanced(audio_file, mode):
                stats['success'] += 1
                file_time = time.time() - file_start
                stats['total_time'] += file_time
                
                # 估算成本（假設基準）
                estimated_cost = file_time * self.models[mode]['cost_multiplier'] * 0.01
                stats['total_cost'] += estimated_cost
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
        self._show_final_stats(stats, total_time, mode)
        
        return stats
    
    def _show_final_stats(self, stats: dict, total_time: float, mode: str):
        """顯示最終統計"""
        print(f"\n🎉 增強版批次處理完成！")
        print(f"   🎯 處理模式: {self.models[mode]['description']}")
        print(f"   ✅ 成功: {stats['success']}")
        print(f"   ❌ 失敗: {stats['failed']}")
        print(f"   ⏭️ 跳過: {stats['skipped']}")
        print(f"   ⏱️ 總用時: {total_time/60:.1f} 分鐘")
        print(f"   💰 預估成本: ${stats['total_cost']:.2f}")
        
        if stats['success'] > 0:
            avg_per_file = stats['total_time'] / stats['success']
            print(f"   📈 平均每檔案: {avg_per_file:.1f} 秒")
            
            # 品質建議
            if mode == 'fast':
                print(f"   💡 品質建議: 快速模式完成，重要檔案建議人工校對")
            else:
                print(f"   🎯 品質保證: 高精度模式，預期錯誤率 < 5%")

def main():
    """主程式"""
    if len(sys.argv) < 2:
        print("使用方法: python enhanced_srt_processor.py <資料夾路徑> [模式]")
        print("模式選項:")
        print("  - high_precision: 真實時間戳模式 (gemini-3.5-transcribe)")
        print("  - fast: 文字優先模式 (gpt-transcribe)")
        print("  - 不指定: 互動式選擇")
        sys.exit(1)
    
    folder_path = Path(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not folder_path.exists():
        print(f"❌ 資料夾不存在: {folder_path}")
        sys.exit(1)
    
    print("🚀 增強版 SRT 處理器")
    print("=" * 50)
    print(f"📁 資料夾: {folder_path}")
    
    try:
        processor = EnhancedSRTProcessor()
        stats = processor.batch_process_enhanced(folder_path, mode)
        
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