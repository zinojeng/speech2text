# Implementation Plan

- [x] 1. 建立核心資料模型和配置系統
  - 創建 ProcessingConfig, FileInfo, TranscriptionResult, SummaryResult 等資料類別
  - 實作配置載入和驗證邏輯
  - 建立 API 金鑰檢查機制
  - _Requirements: 1.1, 7.1, 7.2, 7.5_

- [x] 2. 實作檔案發現和匹配服務
  - [x] 2.1 建立 AudioFileScanner 類別
    - 實作遞歸搜索音訊檔案功能
    - 支援多種音訊格式 (mp3, wav, m4a, aac, flac, ogg, wma, mp4, mov, avi, mkv, webm)
    - 建立檔案大小和格式驗證
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 2.2 建立 AgendaFileMatcher 類別
    - 實作同名檔案匹配邏輯
    - 支援多種文字檔案格式 (txt, md, rtf, doc, docx, pdf, html, htm, xml, json, csv)
    - 實作常見議程檔案名搜索 (agenda, schedule, program, 議程)
    - 整合 markitdown_utils.py 處理各種格式
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 2.3 建立 FileDiscovery 協調器
    - 整合 AudioFileScanner 和 AgendaFileMatcher
    - 實作檔案配對結果回報
    - 建立未匹配檔案處理邏輯
    - _Requirements: 4.5_

- [x] 3. 建立轉錄服務包裝器
  - [x] 3.1 實作 TranscriptionService 基礎類別
    - 整合現有的 audio2text/gpt4o_stt.py
    - 支援 gpt-4o-transcribe 和 gpt-4o-mini-transcribe 模型
    - 實作基本的錯誤處理和重試機制
    - _Requirements: 2.1, 2.2, 8.1, 8.2_

  - [x] 3.2 實作大型檔案處理邏輯
    - 整合 utils.py 的 check_file_size 和 split_large_audio 功能
    - 實作分段轉錄和結果合併
    - 建立臨時檔案清理機制
    - _Requirements: 2.5, 8.3, 8.4_

  - [x] 3.3 實作進度追蹤和日誌記錄
    - 建立轉錄進度回報機制
    - 整合現有的日誌系統
    - 實作處理時間統計
    - _Requirements: 2.3, 6.1, 6.2_

- [x] 4. 建立摘要服務包裝器
  - [x] 4.1 實作 SummaryService 基礎類別
    - 整合現有的 gemini_utils.py
    - 使用 gemini-2.5-pro-preview-06-05 模型
    - 實作 ADA 2025 會議專用系統提示詞
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 4.2 實作議程內容整合
    - 建立議程內容與轉錄文字的合併邏輯
    - 實作智能摘要生成
    - 支援中文輸出格式化
    - _Requirements: 3.2, 4.4_

  - [x] 4.3 實作圖片標記處理
    - 建立投影片圖片標記插入功能
    - 實作圖片檔案存在性檢查
    - 支援 Markdown 格式圖片連結生成
    - _Requirements: 3.5_

  - [x] 4.4 實作摘要錯誤處理
    - 建立 API 呼叫失敗處理
    - 實作重試機制和備用策略
    - 建立摘要品質驗證
    - _Requirements: 3.4, 8.2, 8.3_

- [x] 5. 建立文件生成器
  - [x] 5.1 實作 MarkdownProcessor 類別
    - 建立 Markdown 格式生成邏輯
    - 支援標題、粗體、底線等格式
    - 實作圖片連結處理
    - _Requirements: 5.1, 5.2_

  - [x] 5.2 實作 DocxConverter 類別
    - 整合現有的 Markdown 到 Word 轉換邏輯
    - 保持文字格式和結構
    - 支援中文字體和排版
    - _Requirements: 5.3, 5.4_

  - [x] 5.3 實作 DocumentGenerator 協調器
    - 整合 MarkdownProcessor 和 DocxConverter
    - 建立檔案命名邏輯
    - 實作輸出路徑管理
    - _Requirements: 5.5_

- [x] 6. 建立處理流程編排器
  - [x] 6.1 實作 ProcessingOrchestrator 基礎架構
    - 建立單一檔案處理流程
    - 整合轉錄、摘要、文件生成服務
    - 實作處理狀態追蹤
    - _Requirements: 6.1, 6.2_

  - [x] 6.2 實作批次處理邏輯
    - 建立多檔案並行處理機制
    - 整合 ThreadPoolExecutor 進行並行處理
    - 實作處理佇列管理
    - _Requirements: 7.3, 8.1_

  - [x] 6.3 實作組合輸出模式
    - 建立 SRT 格式組合輸出
    - 實作連續時間戳記處理
    - 支援文字/Markdown 組合模式
    - _Requirements: 5.1, 5.2_

- [x] 7. 建立錯誤處理和恢復系統
  - [x] 7.1 實作 ErrorHandler 類別
    - 建立錯誤分類和處理策略
    - 實作指數退避重試機制
    - 建立錯誤記錄和統計
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 7.2 實作進度追蹤器
    - 建立 ProgressTracker 類別
    - 整合 tqdm 進度條顯示
    - 實作處理狀態更新機制
    - _Requirements: 6.2, 6.3_

  - [x] 7.3 實作日誌和監控系統
    - 建立結構化日誌記錄
    - 實作處理時間統計
    - 建立錯誤統計和報告
    - _Requirements: 6.1, 6.4, 6.5_

- [x] 8. 建立報告生成系統
  - [x] 8.1 實作 ReportGenerator 類別
    - 建立處理結果統計
    - 生成 JSON 格式詳細報告
    - 建立 Markdown 格式摘要報告
    - _Requirements: 6.3, 6.4_

  - [x] 8.2 實作 Word 格式報告
    - 建立 Word 文件報告生成
    - 包含統計圖表和詳細資訊
    - 支援中文格式化
    - _Requirements: 6.4_

- [ ] 9. 建立主要協調器和使用者介面
  - [ ] 9.1 實作 BatchAudioManager 主類別
    - 建立主要的協調器邏輯
    - 整合所有服務組件
    - 實作配置管理和驗證
    - _Requirements: 7.1, 7.2_

  - [ ] 9.2 實作命令列介面
    - 建立 argparse 命令列參數處理
    - 支援資料夾路徑、模型選擇、輸出格式等選項
    - 實作互動式輸入模式
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ] 9.3 建立 Shell 腳本包裝器
    - 創建 enhanced_audio_auto.sh 腳本
    - 整合現有的 audio_auto.sh 功能
    - 支援組合輸出模式參數
    - _Requirements: 7.3, 7.4_

- [ ] 10. 整合測試和驗證
  - [ ] 10.1 建立單元測試套件
    - 為每個主要類別建立單元測試
    - 實作模擬 API 呼叫測試
    - 建立邊界條件測試
    - _Requirements: 1.4, 2.4, 3.4, 4.5, 5.4, 8.5_

  - [ ] 10.2 實作整合測試
    - 建立端到端處理流程測試
    - 使用測試音訊檔案驗證功能
    - 測試並行處理和錯誤恢復
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ] 10.3 建立效能測試和優化
    - 測試大量檔案處理能力
    - 驗證記憶體使用和效能
    - 優化 API 呼叫和並行處理
    - _Requirements: 8.1, 8.5_