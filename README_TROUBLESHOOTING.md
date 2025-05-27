# 故障排除指南

## PDF 轉 Markdown 轉換失敗問題

### 問題描述
當嘗試上傳 PDF 檔案並轉換為 Markdown 時，可能會遇到以下錯誤：
```
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

### 原因分析
這個錯誤通常是由於 `magika` 套件的模型配置檔案損壞或不完整所導致。`magika` 是 MarkItDown 用來檢測檔案類型的套件。

### 解決方案

#### 方法一：使用自動修復腳本
1. 在專案目錄中執行修復腳本：
```bash
python fix_magika.py
```

#### 方法二：手動修復
1. 卸載現有的 magika 套件：
```bash
pip uninstall magika -y
```

2. 清理 pip 快取：
```bash
pip cache purge
```

3. 重新安裝 magika 套件：
```bash
pip install magika --no-cache-dir
```

4. 重新啟動應用程式

#### 方法三：測試修復結果
執行測試腳本確認功能正常：
```bash
python test_pdf_conversion.py
```

### 預防措施
- 定期更新套件版本
- 使用虛擬環境避免套件衝突
- 在安裝新套件前備份工作環境

### 其他常見問題

#### 1. 缺少 ffmpeg
如果看到以下警告：
```
RuntimeWarning: Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work
```

這不會影響 PDF 轉換功能，但如果需要處理音訊檔案，請安裝 ffmpeg：

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
下載並安裝 ffmpeg 從官方網站：https://ffmpeg.org/download.html

#### 2. 記憶體不足
處理大型 PDF 檔案時可能遇到記憶體不足問題：
- 嘗試分割大型 PDF 檔案
- 增加系統記憶體
- 使用較小的檔案進行測試

#### 3. 權限問題
如果遇到檔案權限錯誤：
- 確保有讀取上傳檔案的權限
- 檢查臨時目錄的寫入權限
- 在 Linux/macOS 上可能需要調整檔案權限

### 聯絡支援
如果以上方法都無法解決問題，請提供以下資訊：
1. 錯誤訊息的完整內容
2. 作業系統版本
3. Python 版本
4. 嘗試轉換的檔案類型和大小
5. 已嘗試的解決方案

---

**最後更新：** 2025-05-28  
**版本：** 1.0.0 