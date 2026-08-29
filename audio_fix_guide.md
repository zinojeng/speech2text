# 音檔轉錄錯誤解決指南

## 錯誤訊息
```
轉錄失敗: Error code: 400 - {'error': {'message': 'Audio file might be corrupted or unsupported', 'type': 'invalid_request_error', 'param': 'file', 'code': 'invalid_value'}}
```

## 可能原因與解決方法

### 1. 檢查音檔格式

支援的格式：
- mp3, wav, m4a, aac, flac, ogg, wma

檢查檔案格式：
```bash
# 使用 file 命令檢查
file your_audio_file.mp3

# 使用 ffprobe 檢查詳細資訊
ffprobe -v quiet -print_format json -show_format -show_streams your_audio_file.mp3
```

### 2. 轉換音檔格式

如果格式不支援，使用 ffmpeg 轉換：

```bash
# 轉換為 MP3
ffmpeg -i input_file.xxx -acodec mp3 -ab 192k output_file.mp3

# 轉換為 WAV（高品質）
ffmpeg -i input_file.xxx -acodec pcm_s16le -ar 44100 output_file.wav

# 轉換為 M4A
ffmpeg -i input_file.xxx -c:a aac -b:a 192k output_file.m4a
```

### 3. 修復損壞的音檔

```bash
# 使用 ffmpeg 重新編碼（可能修復輕微損壞）
ffmpeg -i corrupted_file.mp3 -c:a copy -bsf:a aac_adtstoasc fixed_file.mp3

# 或重新編碼整個檔案
ffmpeg -i corrupted_file.mp3 -acodec libmp3lame -ab 192k fixed_file.mp3
```

### 4. 檢查檔案大小

OpenAI API 限制：
- 最大檔案大小：25MB
- 如果超過，需要分割檔案

檢查檔案大小：
```bash
ls -lh your_audio_file.mp3
```

### 5. 自動分割大檔案

使用專案內建工具：
```python
from utils import split_large_audio

# 分割成 5 分鐘片段
segments = split_large_audio("large_file.mp3")
```

或使用 ffmpeg：
```bash
# 分割成 5 分鐘片段
ffmpeg -i input.mp3 -f segment -segment_time 300 -c copy output_%03d.mp3
```

### 6. 檢查音檔是否真的包含音訊

```bash
# 檢查音訊流
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,channels,sample_rate -of default=nw=1 your_file.mp3
```

### 7. 使用 Python 驗證音檔

```python
from pydub import AudioSegment

try:
    audio = AudioSegment.from_file("your_file.mp3")
    print(f"音檔長度: {len(audio)/1000:.2f} 秒")
    print(f"聲道數: {audio.channels}")
    print(f"採樣率: {audio.frame_rate}")
    print("音檔正常！")
except Exception as e:
    print(f"音檔有問題: {e}")
```

### 8. 常見問題檢查清單

1. **檔案是否存在？**
   ```bash
   ls -la /path/to/your/audio/file.mp3
   ```

2. **檔案是否為空？**
   ```bash
   # 檢查檔案大小
   stat -f%z your_file.mp3  # macOS
   stat -c%s your_file.mp3  # Linux
   ```

3. **檔案是否可讀？**
   ```bash
   # 檢查權限
   ls -l your_file.mp3
   
   # 修改權限（如需要）
   chmod 644 your_file.mp3
   ```

4. **路徑是否包含特殊字元？**
   - 避免使用中文或特殊符號的檔名
   - 使用引號處理空格：`"my audio file.mp3"`

### 9. 測試用簡單音檔

建立測試音檔：
```bash
# 使用 ffmpeg 建立 10 秒測試音檔
ffmpeg -f lavfi -i "sine=frequency=1000:duration=10" test_audio.mp3
```

### 10. 完整的修復流程

```bash
# 1. 檢查原始檔案
file original.mp3
ffprobe original.mp3

# 2. 轉換並修復
ffmpeg -i original.mp3 -acodec libmp3lame -ab 192k -ar 44100 fixed.mp3

# 3. 如果檔案太大，分割
ffmpeg -i fixed.mp3 -f segment -segment_time 300 -c copy segment_%03d.mp3

# 4. 使用修復後的檔案進行轉錄
python gpt4o_transcribe.py fixed.mp3 --model gpt-4o-mini-transcribe
```

### 11. 替代方案

如果問題持續：

1. **使用本地 Whisper**
   ```python
   python whisper_stt.py your_file.mp3
   ```

2. **使用 Google Speech-to-Text**
   - 需要設定 GOOGLE_API_KEY

3. **使用 Streamlit UI**
   - 執行 `./start_app.sh`
   - UI 會自動處理檔案檢查和轉換

### 12. 預防措施

1. **錄音時使用標準格式**
   - MP3: 192kbps, 44.1kHz
   - WAV: 16-bit, 44.1kHz

2. **定期檢查音檔**
   ```bash
   # 批次檢查資料夾中的音檔
   for f in *.mp3; do
     echo "檢查: $f"
     ffprobe -v error "$f" 2>&1 | grep -E "Invalid|Error|corrupt"
   done
   ```

3. **建立音檔處理腳本**
   ```bash
   #!/bin/bash
   # fix_audio.sh
   INPUT="$1"
   OUTPUT="${INPUT%.*}_fixed.mp3"
   
   ffmpeg -i "$INPUT" -acodec libmp3lame -ab 192k -ar 44100 "$OUTPUT"
   echo "已修復: $OUTPUT"
   ```

如果以上方法都無法解決問題，請提供：
1. 音檔的詳細資訊（大小、格式、長度）
2. 使用的完整命令
3. 完整的錯誤訊息

這樣可以進一步診斷問題。