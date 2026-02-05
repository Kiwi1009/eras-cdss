# ERAS CDSS 前端介面使用說明

## 功能確認

### ✅ 已實作功能對照規格書

#### 1. 情境支援 ✅
- **PONV (Koivuranta)**: ✅ 已更新驗證器支援所有必填欄位
  - `female`, `non_smoker`, `hx_ponv`, `hx_motion_sickness`, `surgery_duration_min`
- **POD (Nu-DESC)**: ✅ 已實作
  - 五項 Nu-DESC 評分 (0-2)
  - `surgery_duration_min`
- **CHEST_TUBE**: ✅ 已更新驗證器
  - `air_leak_present`, `drain_output_ml_24h`, `fluid_quality`, `active_bleeding_suspected`, `lung_expanded`, `threshold_ml_24h`

#### 2. RAG/FAISS ✅
- ✅ 支援 PDF/TXT/MD/HTML
- ✅ 版本控制 (manifest.json)
- ✅ 增量更新 (檔案層級)
- ✅ 引用追溯 (source/chunk_id/text)

#### 3. Multi-Agent ✅
- ✅ 三代理：SURGEON, ANESTHESIOLOGIST, NURSE
- ✅ 仲裁者整合
- ✅ 引用強制 (S2 修復機制)

#### 4. Trace 可追溯 ✅
- ✅ 每次請求產生 trace_id
- ✅ 保存到 `logs/traces/<trace_id>.json`

#### 5. 30 病人評估腳本 ✅
- ✅ `scripts/eval_30_patients.py`
- ✅ 輸出 `results.jsonl` 和 `summary.csv`

## 前端介面使用

### 啟動方式

1. **啟動 FastAPI 後端**：
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8080
   ```

2. **開啟瀏覽器**：
   訪問 `http://localhost:8080/` 或 `http://localhost:8080/static/index.html`

### 功能說明

#### 1. 情境選擇
- 可選擇特定情境（PONV/POD/CHEST_TUBE）
- 或選擇「自動判斷」讓系統推斷

#### 2. 動態表單
- 根據選擇的情境自動顯示對應的必填欄位
- **PONV**: 性別、吸菸狀態、病史、手術時長
- **POD**: Nu-DESC 五項評分、手術時長
- **CHEST_TUBE**: 氣漏、引流量、引流液性質、出血、肺部擴張、閾值

#### 3. 結果顯示
- **最終建議**: 系統的綜合建議
- **關鍵原因**: 決策的主要理由
- **風險與注意事項**: 安全警示
- **參考文獻**: 可展開查看完整引用內容
- **多代理決策**: 顯示三個代理的個別決策
- **系統指標**: 延遲時間、Trace ID、後端名稱、引用數量

### 前端特色

1. **響應式設計**: 支援桌面和行動裝置
2. **即時狀態**: 顯示系統健康狀態和 RAG build ID
3. **動態表單**: 根據情境自動調整輸入欄位
4. **可展開引用**: 點擊可查看完整引用文本
5. **錯誤處理**: 清楚的錯誤訊息顯示
6. **載入狀態**: 評估進行中的視覺回饋

## 技術規格對照

### 規格書要求 vs 實作狀態

| 功能 | 規格書要求 | 實作狀態 | 備註 |
|------|-----------|---------|------|
| PONV Koivuranta | ✅ | ✅ | 已更新驗證器 |
| POD Nu-DESC | ✅ | ✅ | 完整實作 |
| CHEST_TUBE | ✅ | ✅ | 已更新驗證器 |
| RAG 版本控制 | ✅ | ✅ | manifest.json |
| RAG 增量更新 | ✅ | ✅ | 檔案層級 |
| Multi-Agent | ✅ | ✅ | 3代理+1仲裁 |
| S2 引用強制 | ✅ | ✅ | 自動修復重試 |
| Trace 可追溯 | ✅ | ✅ | JSON 落地 |
| 30病人評估 | ✅ | ✅ | 批次腳本 |
| 前端介面 | ❓ | ✅ | **新增完成** |

## 測試建議

1. **測試各情境**:
   - 分別測試 PONV、POD、CHEST_TUBE
   - 驗證表單欄位是否正確顯示

2. **測試錯誤處理**:
   - 故意缺少必填欄位
   - 驗證是否正確顯示 INSUFFICIENT_DATA

3. **測試引用**:
   - 檢查 citations 是否可展開
   - 驗證引用文本是否正確顯示

4. **測試 Trace**:
   - 提交評估後，檢查 `logs/traces/` 是否有對應的 trace 檔

## 已知限制

1. 前端使用 Tailwind CDN，需要網路連線
2. API 預設連接到 `http://localhost:8080`，可在 `static/app.js` 修改
3. 引用文本較長時，展開後可能需要滾動查看

## 下一步

1. ✅ 前端介面已完成
2. ✅ 驗證器已更新符合規格書
3. 可進行完整系統測試
4. 可準備 demo 展示
