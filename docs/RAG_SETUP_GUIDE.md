# ERAS RAG 資料庫建立指南

## 目前狀態

**目前沒有 RAG 資料庫**，需要手動建立。

## 快速建立步驟

### 步驟 1: 準備文件

將 ERAS 相關文件放入 `data/rag_sources/` 目錄：

```bash
# 確保目錄存在
mkdir -p data/rag_sources

# 將您的文件複製到此目錄
# 支援格式：.pdf, .txt, .md
```

**範例文件已包含**：
- `data/rag_sources/example_guideline.txt` - 範例 ERAS 指南

### 步驟 2: 執行索引建立腳本

```bash
python scripts/rag_update_faiss.py
```

這會：
1. ✅ 掃描 `data/rag_sources/` 中的所有文件
2. ✅ 將文件分塊（chunking，預設 512 字元，重疊 50 字元）
3. ✅ 產生嵌入向量（使用 sentence-transformers/all-MiniLM-L6-v2）
4. ✅ 建立 FAISS 索引
5. ✅ 儲存到 `data/rag_store/builds/<build_id>/`
6. ✅ 更新 `data/rag_store/manifest.json`

### 步驟 3: 驗證索引

檢查是否成功建立：

```bash
# 檢查 manifest
cat data/rag_store/manifest.json

# 檢查健康端點（如果 API 已啟動）
curl http://localhost:8080/healthz
```

應該會看到 `rag_current_build_id` 有值。

## 詳細說明

### 支援的文件格式

| 格式 | 副檔名 | 說明 |
|------|--------|------|
| PDF | `.pdf` | 臨床指南、研究論文 |
| 文字檔 | `.txt` | 純文字格式 |
| Markdown | `.md` | Markdown 格式 |

### 文件來源建議

#### 1. ERAS Society 官方文件
- 網站：https://erassociety.org/
- 下載官方指南和協議

#### 2. 醫學資料庫
- PubMed：搜尋 "ERAS protocol"
- Cochrane Reviews：ERAS 相關系統性回顧
- 各專科學會指南

#### 3. 醫院內部文件
- ERAS 標準作業程序
- 臨床路徑文件
- 多專科協議

### 文件準備建議

1. **文件品質**
   - 確保文字清晰可讀（PDF 需可選取文字）
   - 結構化內容效果更好
   - 避免掃描圖片（需 OCR）

2. **文件組織**
   - 使用清楚的檔名
   - 例如：`ERAS_PONV_Protocol_2023.pdf`
   - 避免特殊字元

3. **內容建議**
   - 包含完整的臨床指南
   - 評估工具說明
   - 決策流程
   - 藥物劑量和用法

### 增量更新

當您新增或修改文件時，再次執行：

```bash
python scripts/rag_update_faiss.py
```

系統會：
- ✅ 自動偵測新增/修改/刪除的文件
- ✅ 只更新變更的部分（增量更新）
- ✅ 產生新的 build ID
- ✅ 保留舊版本（在 `data/rag_store/builds/`）

### 配置選項

可在 `.env` 或環境變數中調整：

```bash
# RAG 配置
RAG_ENABLED=true
RAG_STORE_ROOT=data/rag_store
RAG_SOURCE_DIR=data/rag_sources
RAG_EMB_MODEL=sentence-transformers/all-MiniLM-L6-v2  # 嵌入模型
RAG_CHUNK_SIZE=512                                    # 分塊大小
RAG_CHUNK_OVERLAP=50                                 # 重疊大小
```

### 測試 RAG 功能

建立索引後，可以透過 API 測試：

```bash
# 啟動 API
uvicorn app.main:app --host 0.0.0.0 --port 8080

# 測試查詢（另一個終端）
curl -X POST http://localhost:8080/eras/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": "POD",
    "question": "What are the risk factors for postoperative delirium?",
    "top_k": 6,
    "patient_fhir": {
      "age": 75,
      "gender": "M",
      "nu_desc": {
        "disorientation": 1,
        "inappropriate_behavior": 0,
        "inappropriate_communication": 1,
        "illusions": 0,
        "psychomotor_retardation": 0
      },
      "surgery_duration_min": 180
    }
  }'
```

回應中的 `citations` 欄位應該包含從 RAG 檢索到的相關文件片段。

## 常見問題

### Q: 索引建立失敗？
**A:** 檢查：
1. 文件是否在 `data/rag_sources/` 目錄
2. 文件格式是否支援（.pdf, .txt, .md）
3. PDF 是否可讀取文字（非純圖片）
4. 是否有足夠的磁碟空間

### Q: 如何知道索引是否建立成功？
**A:** 
- 檢查 `data/rag_store/manifest.json` 是否有 `current_build_id`
- 檢查 `data/rag_store/builds/` 是否有新目錄
- 執行 `/healthz` 端點查看 `rag_current_build_id`

### Q: 可以更新嵌入模型嗎？
**A:** 可以，修改 `RAG_EMB_MODEL` 後重新建立索引：
```bash
# 修改 .env 中的 RAG_EMB_MODEL
# 然後重新執行
python scripts/rag_update_faiss.py
```

### Q: 索引檔案很大？
**A:** 這是正常的，FAISS 索引和嵌入向量需要儲存空間。可以：
- 使用 `faiss-gpu` 替代 `faiss-cpu`（如果有多個索引）
- 定期清理舊的 build（如果不需要版本歷史）

## 下一步

1. ✅ 準備 ERAS 文件
2. ✅ 執行 `python scripts/rag_update_faiss.py`
3. ✅ 測試 API 查詢
4. ✅ 執行 30 病人評估：`python scripts/eval_30_patients.py`
