# Claude Code 記錄

## Streamlit 應用程式無法在 Safari 連接 localhost 的問題診斷

### 問題現象
- `http://localhost:8081` 無法在 Safari 中開啟
- Safari 顯示「無法連接伺服器」錯誤
- 使用 `curl localhost:8081` 也失敗

### 根本原因分析
1. **服務綁定地址問題**：
   - 原始啟動命令：`streamlit run main_app.py --server.port 8081`
   - 預設可能只綁定到特定介面，不是所有介面

2. **IPv4 vs IPv6 解析問題**：
   - Safari 解析 `localhost` 時可能優先使用 IPv6 (::1)
   - 如果 Streamlit 只綁定到 IPv4 (127.0.0.1)，就會連接失敗

3. **服務未正確啟動**：
   - 可能存在 Python 環境或虛擬環境問題
   - 需要確保在正確的 venv 中啟動

### 解決方案
**成功的啟動命令**：
```bash
source venv/bin/activate && streamlit run main_app.py --server.address 0.0.0.0 --server.port 8082 --server.headless true &
```

**關鍵參數**：
- `--server.address 0.0.0.0`：綁定到所有網路介面
- `--server.port 8082`：使用未被占用的端口
- `--server.headless true`：無頭模式運行

### 診斷工具
1. **檢查服務是否監聽**：
   ```bash
   lsof -nP -iTCP:8082 -sTCP:LISTEN
   ```

2. **測試連接**：
   ```bash
   curl -I http://127.0.0.1:8082
   ```

3. **檢查所有監聽端口**：
   ```bash
   lsof -i -P | grep LISTEN
   ```

### 瀏覽器建議
- 使用 `http://127.0.0.1:8082/` 而不是 `http://localhost:8082`
- 確保輸入完整 URL 包含 `http://` 和結尾 `/`
- 如果 Safari 仍有問題，建議使用 Chrome 或 Firefox

### 端口使用情況
- 8080：被 nginx 占用（已停止）
- 8081：之前嘗試失敗
- 8082：成功運行 ✓

## 轉錄功能無法顯示文字的問題診斷與修復

### 問題現象
- 轉錄過程看起來正常運行
- 進度條顯示完成
- 但沒有呈現出轉錄文字

### 根本原因
**變數作用域和異常處理問題**：
1. `full_transcript` 變數在 try-except 塊中可能未正確賦值
2. 異常處理後 `full_transcript` 保持空字串狀態
3. 結果判斷 `if full_transcript:` 失敗，導致顯示"轉錄失敗"

### 修復內容

#### 1. 改善異常處理
```python
except Exception as e:
    st.error(f"處理失敗：{str(e)}")
    logger.error(f"處理失敗：{str(e)}")
    full_transcript = ""  # 確保異常時重置變數
```

#### 2. 增強結果判斷
```python
# 原本：
if full_transcript:
    st.session_state.transcribed_text = full_transcript
    st.rerun()
else:
    st.error("轉錄失敗")

# 修復後：
if full_transcript and full_transcript.strip():
    st.session_state.transcribed_text = full_transcript
    st.success("轉錄完成！")
    logger.info("轉錄結果已儲存至 session_state")
    st.rerun()
else:
    st.error("轉錄失敗或結果為空")
    logger.error("轉錄失敗：結果為空或無效")
```

#### 3. 添加調試日誌
```python
# 處理結果統計
logger.info(f"共處理 {len(segment_results)} 個分段結果")

# 轉錄結果長度
logger.info(f"轉錄結果長度: {len(full_transcript) if full_transcript else 0}")
```

### 修復檔案
- `/Users/zino/Desktop/OpenAI/speech2text/main_app.py`
- 修復行數：1641-1692

### 測試建議
1. 上傳短音訊檔案測試
2. 檢查瀏覽器控制台錯誤
3. 查看應用程式日誌輸出
4. 確認 session_state 正確設定

## Safari localhost 連接問題完整分析

### 問題描述
- 使用 `http://localhost:8501` 在 Safari 中無法開啟
- 使用 `http://0.0.0.0:8080` 會導向 `about:blank`
- 但使用 `http://127.0.0.1:8501` 可以正常工作

### 根本原因詳解

#### 1. IPv4 vs IPv6 解析差異
- **Safari 行為**：解析 `localhost` 時優先嘗試 IPv6 地址 `::1`
- **Streamlit 預設**：可能只綁定到 IPv4 地址 `127.0.0.1`
- **結果**：Safari 嘗試連接 `::1:8501` 但服務實際在 `127.0.0.1:8501`

#### 2. 服務綁定限制
- 預設啟動命令缺少 `--server.address` 參數
- Streamlit 可能只綁定到特定網路介面
- 限制了可訪問服務的地址範圍

#### 3. 瀏覽器特性差異
- **Safari**：對 localhost 處理較嚴格，優先使用 IPv6
- **Chrome/Firefox**：通常會自動回退到 IPv4
- **0.0.0.0 問題**：這是監聽地址，不是有效的訪問地址

### 最佳解決方案

#### 啟動命令
```bash
streamlit run main_app.py --server.address 0.0.0.0 --server.port 8501 --server.headless false
```

#### 訪問方式
- **推薦**：`http://127.0.0.1:8501`
- **備選**：`http://[::1]:8501`（如果服務支援 IPv6）
- **避免**：`http://localhost:8501`（在 Safari 中可能失敗）

### 診斷步驟
1. 確認服務監聽狀態：
   ```bash
   lsof -nP -iTCP:8501 -sTCP:LISTEN
   ```

2. 測試連接：
   ```bash
   # IPv4 測試
   curl -I http://127.0.0.1:8501
   # IPv6 測試
   curl -I http://[::1]:8501
   ```

3. 檢查 hosts 檔案配置：
   ```bash
   cat /etc/hosts | grep localhost
   ```

### 建議配置
- 始終在啟動命令中包含 `--server.address 0.0.0.0`
- 在文檔和提示中使用 `127.0.0.1` 而非 `localhost`
- 為 Safari 使用者提供特別說明