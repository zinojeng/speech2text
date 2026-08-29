# Requirements Document

## Introduction

本功能旨在創建一個完整的批次音訊處理系統，能夠自動化處理資料夾中的所有音訊檔案。系統將整合現有的 gpt4o_transcribe.py 和 gemini_utils.py 工具，提供一個統一的批次處理介面，支援遞歸搜索、語音轉錄、智能摘要和文件生成功能。

## Requirements

### Requirement 1

**User Story:** 作為使用者，我希望能夠指定一個資料夾路徑，系統自動搜索該資料夾及其子資料夾中的所有音訊檔案，並優先處理音訊檔案而非影片檔案，以便批次處理多個音訊檔案。

#### Acceptance Criteria

1. WHEN 使用者提供資料夾路徑 THEN 系統 SHALL 遞歸搜索該資料夾及所有子資料夾中的音訊檔案
2. WHEN 系統搜索音訊檔案 THEN 系統 SHALL 支援純音訊格式包括 mp3, wav, m4a, aac, flac, ogg, wma
3. WHEN 系統搜索檔案 THEN 系統 SHALL 支援影片格式包括 mp4, mov, avi, mkv, webm 作為備選
4. WHEN 資料夾中存在任何音訊檔案 THEN 系統 SHALL 跳過該資料夾同一層以及所有子資料夾中的影片檔案
5. WHEN 資料夾及其所有子資料夾中都沒有音訊檔案 THEN 系統 SHALL 處理該資料夾樹中的影片檔案
6. WHEN 搜索完成 THEN 系統 SHALL 顯示找到的檔案數量、類型和路徑列表
7. WHEN 應用優先級邏輯 THEN 系統 SHALL 記錄跳過的影片檔案數量和原因
8. IF 資料夾不存在或無法存取 THEN 系統 SHALL 顯示錯誤訊息並停止執行

### Requirement 2

**User Story:** 作為使用者，我希望系統能夠呼叫現有的 gpt4o_transcribe.py 程式來進行語音轉錄，以便重用已經測試過的轉錄功能。

#### Acceptance Criteria

1. WHEN 系統處理音訊檔案 THEN 系統 SHALL 呼叫 gpt4o_transcribe.py 進行語音轉錄
2. WHEN 呼叫轉錄程式 THEN 系統 SHALL 支援選擇 gpt-4o-transcribe 或 gpt-4o-mini-transcribe 模型
3. WHEN 轉錄過程中 THEN 系統 SHALL 顯示當前處理進度和狀態
4. IF 轉錄失敗 THEN 系統 SHALL 記錄錯誤訊息並繼續處理下一個檔案
5. WHEN 音訊檔案過大 THEN 系統 SHALL 自動分割檔案並合併轉錄結果

### Requirement 3

**User Story:** 作為使用者，我希望系統能夠呼叫現有的 gemini_utils.py 來進行智能摘要，以便重用已經配置好的 Gemini API 功能。

#### Acceptance Criteria

1. WHEN 轉錄完成 THEN 系統 SHALL 呼叫 gemini_utils.py 使用 Gemini 2.5 Pro 進行摘要處理
2. WHEN 進行摘要處理 THEN 系統 SHALL 使用專門針對 ADA 2025 會議的系統提示詞
3. WHEN 存在同名的議程文字檔案 THEN 系統 SHALL 將議程內容納入摘要處理
4. IF 摘要處理失敗 THEN 系統 SHALL 記錄錯誤訊息並保留原始轉錄文字
5. WHEN 摘要完成 THEN 系統 SHALL 支援插入對應的投影片圖片標記

### Requirement 4

**User Story:** 作為使用者，我希望系統能夠自動尋找與音訊檔案同名的議程文字檔案，以便提供更準確的摘要內容。

#### Acceptance Criteria

1. WHEN 處理音訊檔案 THEN 系統 SHALL 搜索同名的文字檔案作為議程內容
2. WHEN 搜索議程檔案 THEN 系統 SHALL 支援 txt, md, rtf, doc, docx, pdf, html, htm, xml, json, csv 格式
3. IF 找不到同名檔案 THEN 系統 SHALL 搜索常見的議程檔案名如 agenda, schedule, program, 議程
4. WHEN 找到議程檔案 THEN 系統 SHALL 將內容整合到摘要處理中
5. IF 無法讀取議程檔案 THEN 系統 SHALL 記錄警告訊息並繼續處理

### Requirement 5

**User Story:** 作為使用者，我希望系統能夠將處理結果輸出為 Markdown 和 Word 文件格式，以便後續編輯和分享。

#### Acceptance Criteria

1. WHEN 摘要處理完成 THEN 系統 SHALL 將結果轉換為 Markdown 格式
2. WHEN 生成 Markdown THEN 系統 SHALL 保持原有的格式包括標題、粗體、底線等
3. WHEN Markdown 生成完成 THEN 系統 SHALL 將其轉換為 Word 文件格式
4. WHEN 生成 Word 文件 THEN 系統 SHALL 保持文字格式和結構
5. WHEN 輸出檔案 THEN 系統 SHALL 使用與原音訊檔案相同的檔名但不同的副檔名

### Requirement 6

**User Story:** 作為使用者，我希望系統提供詳細的處理日誌和最終報告，以便了解處理狀態和結果。

#### Acceptance Criteria

1. WHEN 系統開始處理 THEN 系統 SHALL 建立詳細的日誌記錄包括時間戳記和處理狀態
2. WHEN 處理每個檔案 THEN 系統 SHALL 顯示當前進度和檔案資訊
3. WHEN 所有檔案處理完成 THEN 系統 SHALL 生成包含統計資訊的處理報告
4. WHEN 生成報告 THEN 系統 SHALL 包括成功處理數量、失敗數量和錯誤詳情
5. WHEN 發生錯誤 THEN 系統 SHALL 記錄詳細的錯誤訊息但繼續處理其他檔案

### Requirement 7

**User Story:** 作為使用者，我希望系統支援命令列參數和互動式輸入，以便靈活使用不同的處理選項。

#### Acceptance Criteria

1. WHEN 使用者執行程式 THEN 系統 SHALL 支援命令列參數指定資料夾路徑
2. WHEN 未提供命令列參數 THEN 系統 SHALL 提供互動式介面讓使用者輸入路徑
3. WHEN 使用命令列 THEN 系統 SHALL 支援指定轉錄模型選項
4. WHEN 使用命令列 THEN 系統 SHALL 支援指定輸出格式選項
5. IF 提供的參數無效 THEN 系統 SHALL 顯示使用說明並停止執行

### Requirement 8

**User Story:** 作為使用者，我希望系統能夠智能跳過已經處理過的資料夾，以便避免重複處理和浪費時間。

#### Acceptance Criteria

1. WHEN 系統選擇要處理的資料夾 THEN 系統 SHALL 檢查資料夾中是否已存在處理結果檔案
2. WHEN 檢查處理結果檔案 THEN 系統 SHALL 搜尋 transcription*.txt, *.docx, *詳細筆記*.md 等檔案
3. WHEN 資料夾中已存在完整的處理結果 THEN 系統 SHALL 跳過該資料夾並記錄跳過原因
4. WHEN 資料夾中只有部分處理結果 THEN 系統 SHALL 根據缺失的檔案類型決定是否處理
5. WHEN 使用者明確要求重新處理 THEN 系統 SHALL 提供選項覆蓋已存在的檔案
6. WHEN 跳過已處理的資料夾 THEN 系統 SHALL 在統計報告中顯示跳過的資料夾數量和原因
7. WHEN 顯示可處理的資料夾列表 THEN 系統 SHALL 優先顯示未處理的資料夾

### Requirement 9

**User Story:** 作為使用者，我希望系統能夠處理 API 限制和錯誤恢復，以便確保批次處理的穩定性。

#### Acceptance Criteria

1. WHEN 呼叫 API 時 THEN 系統 SHALL 在請求之間加入適當的延遲避免超出限制
2. WHEN API 呼叫失敗 THEN 系統 SHALL 實施重試機制最多重試 3 次
3. WHEN 遇到暫時性錯誤 THEN 系統 SHALL 等待後重試而不是立即失敗
4. WHEN 遇到永久性錯誤 THEN 系統 SHALL 記錄錯誤並跳過該檔案繼續處理
5. WHEN 系統資源不足 THEN 系統 SHALL 優雅地處理並提供有用的錯誤訊息