# ERAS CDSS (Enhanced Recovery After Surgery Clinical Decision Support System)

完整的臨床決策支援系統，整合 FastAPI、Multi-Agent、RAG/FAISS、版本增量更新、引用強制驗證（S2）、以及可插拔的 LLM 後端（vLLM/Ollama/TRT-LLM）。

## 功能特色

- **Multi-Agent 系統**：SURGEON、ANESTHESIOLOGIST、NURSE 三個專家代理 + Arbiter 仲裁
- **RAG/FAISS 檢索**：支援版本控制和增量更新
- **引用強制驗證（S2）**：自動修復不合格的引用和 schema，重試一次
- **可插拔 LLM 後端**：支援 Ollama、vLLM、TensorRT-LLM（使用 completions 介面）
- **完整的追蹤日誌**：每次請求產生 trace 檔
- **輸入驗證**：針對不同 scenario（PONV/POD/CHEST_TUBE）的資料驗證

## 安裝

### 1. 環境要求

- Python 3.10+
- 建議使用虛擬環境

### 2. 安裝依賴

```bash
pip install -r requirements.txt
```

### 3. 準備 RAG 文件

**目前沒有 RAG 資料庫，需要手動建立。**

將 ERAS 臨床指南文件（PDF、TXT、MD）放入 `data/rag_sources/` 目錄：

```bash
mkdir -p data/rag_sources
# 將文件複製到此目錄
```

**範例文件已包含**：
- `data/rag_sources/example_guideline.txt` - 範例 ERAS 指南（包含 POD、PONV、CHEST_TUBE）

**文件來源建議**：
- ERAS Society 官方指南 (https://erassociety.org/)
- PubMed/醫學資料庫中的 ERAS 協議
- 醫院內部的 ERAS 標準作業程序

詳細說明請參考：
- `data/rag_sources/README.md` - 文件準備指南
- `docs/RAG_SETUP_GUIDE.md` - 完整建立指南

### 4. 建立 FAISS 索引

```bash
python scripts/rag_update_faiss.py
```

這會：
- 掃描 `data/rag_sources/` 目錄中的所有文件
- 將文件分塊（chunking，預設 512 字元）
- 產生嵌入向量（embeddings）
- 建立 FAISS 索引
- 產生新的 build ID
- 更新 `data/rag_store/manifest.json`

**注意**：首次執行會下載嵌入模型（sentence-transformers/all-MiniLM-L6-v2），可能需要一些時間。

## 配置

### 環境變數

建立 `.env` 檔案或設定環境變數：

```bash
# RAG 配置
RAG_ENABLED=true
RAG_STORE_ROOT=data/rag_store
RAG_SOURCE_DIR=data/rag_sources
RAG_EMB_MODEL=sentence-transformers/all-MiniLM-L6-v2
RAG_CHUNK_SIZE=512
RAG_CHUNK_OVERLAP=50

# LLM 配置（選擇一個後端）
LLM_BACKEND=ollama  # 或 vllm, trtllm
LLM_BASE_URL=http://localhost:11434
MODEL_ID=gpt-oss:20b   # 若 404 model not found 請執行：ollama pull gpt-oss:20b
REQUEST_TIMEOUT_S=60

# vLLM 特定（如果使用 vLLM）
VLLM_COMPLETIONS_PATH=/v1/completions

# 追蹤配置
TRACE_ENABLED=true
TRACE_ROOT=logs/traces
```

### LLM 後端配置

#### Ollama

```bash
# 安裝 Ollama（如果尚未安裝）
# https://ollama.ai/

# 啟動 Ollama（通常已作為服務運行）
# 或手動啟動：ollama serve

# 下載模型（須與 .env 的 MODEL_ID 一致）
ollama pull gpt-oss:20b

# 設定環境變數（或寫入 .env）
export LLM_BACKEND=ollama
export LLM_BASE_URL=http://localhost:11434
export MODEL_ID=gpt-oss:20b
```

**若出現 `HTTP 404: {"error":"model 'xxx' not found"}`**：表示本機尚未下載該模型，請執行 `ollama pull <MODEL_ID>`，或將 `MODEL_ID` 改為你已有的模型名稱（可用 `ollama list` 查看）。

#### vLLM

vLLM 必須使用 OpenAI-compatible API server。啟動範例：

```bash
# 啟動 vLLM server（範例）
python -m vllm.entrypoints.openai.api_server \
    --model <your-model-path> \
    --served-model-name <model-name> \
    --host 0.0.0.0 \
    --port 8000 \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.9 \
    --dtype float16

# 設定環境變數
export LLM_BACKEND=vllm
export LLM_BASE_URL=http://localhost:8000
export MODEL_ID=<model-name>
```

**注意**：vLLM 使用 `/v1/completions` 端點（非 chat）。

#### TensorRT-LLM

TensorRT-LLM 需要配置為 OpenAI-compatible server。如果使用 trtllm-executor 或其他包裝：

```bash
# 啟動 TRT-LLM server（範例，依實際部署方式調整）
# 確保提供 /v1/completions 端點

# 設定環境變數
export LLM_BACKEND=trtllm
export LLM_BASE_URL=http://your-trtllm-server:port
export MODEL_ID=<model-name>
```

如果未配置，backend 會回傳清楚的錯誤訊息，不會讓 API crash。

## 啟動 API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

或使用 Python：

```bash
python -m app.main
```

### 健康檢查

```bash
curl http://localhost:8080/healthz
```

回應範例：

```json
{
  "status": "ok",
  "rag_current_build_id": "20240101_120000",
  "llm_backend": "ollama"
}
```

### 前端介面

啟動 API 後，在瀏覽器中訪問：

```
http://localhost:8080/
```

或

```
http://localhost:8080/static/index.html
```

前端功能：
- ✅ 情境選擇（PONV/POD/CHEST_TUBE）
- ✅ 動態表單（根據情境自動調整欄位）
- ✅ 即時評估結果顯示
- ✅ 引用文獻可展開查看
- ✅ 多代理決策顯示
- ✅ 系統指標顯示

詳細說明請參考 `README_FRONTEND.md`

## API 使用

### 評估病人

```bash
curl -X POST http://localhost:8080/eras/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": "POD",
    "question": "Should this patient be assessed for delirium?",
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

### 回應格式

```json
{
  "final_recommendation": "...",
  "final_actions": ["action1", "action2"],
  "key_reasons": ["reason1", "reason2"],
  "risks_and_notes": ["risk1"],
  "missing_data": [],
  "conflicts": [],
  "citations": [
    {
      "source": "guideline.pdf",
      "chunk_id": "guideline.pdf_0",
      "text": "Cited text excerpt..."
    }
  ],
  "agents": [
    {
      "name": "SURGEON",
      "decision": {...},
      "error": null
    },
    ...
  ],
  "metrics": {
    "latency_ms": 1234,
    "trace_id": "trace_20240101_120000_abc123",
    "scenario": "POD",
    "backend": "ollama",
    "errors": [],
    "citations_count": 2,
    "hits_count": 6
  }
}
```

## 評估腳本

### 評估 30 位病人

系統已包含範例病人資料檔案 `data/patients.jsonl`（30位病人，涵蓋 PONV、POD、CHEST_TUBE 三種情境）。

檔案格式（每行一個 JSON 物件）：

```json
{"patient_id": "P001", "scenario": "POD", "question": "...", "top_k": 6, "patient_fhir": {...}}
{"patient_id": "P002", "scenario": "PONV", "question": "...", "top_k": 6, "patient_fhir": {...}}
...
```

執行評估：

```bash
export PATIENTS_JSONL=data/patients.jsonl
python scripts/eval_30_patients.py
```

輸出：
- `results.jsonl`：完整結果
- `summary.csv`：摘要（patient_id, scenario, final_recommendation, latency_ms, citations_n, trace_id, errors_arbiter）

### 測試 LLM 後端

```bash
python scripts/smoke_test_backends.py
```

這會依序測試 ollama、vllm、trtllm 三個後端，顯示是否成功、延遲、回傳字數。

## 追蹤日誌

每次請求會產生 trace 檔在 `logs/traces/<trace_id>.json`。

Trace 檔包含：
- 請求資料
- Scenario
- 檢索 hits
- 各 agent 決策
- Arbiter 決策
- 最終回應

查詢 trace：

```bash
# 從回應的 metrics.trace_id 取得 trace_id
cat logs/traces/trace_20240101_120000_abc123.json
```

## 目錄結構

```
.
├── app/
│   ├── main.py                 # FastAPI 主程式
│   ├── config.py               # 配置管理
│   ├── schemas.py              # API schemas
│   └── services/
│       ├── decision_pipeline.py    # 決策管道
│       ├── scenario_router.py      # Scenario 路由
│       ├── input_validator.py      # 輸入驗證
│       ├── schema_guard.py          # Schema 驗證
│       ├── citation_guard.py       # 引用驗證
│       ├── trace_logger.py         # 追蹤日誌
│       ├── retrieval_postproc.py   # 檢索後處理
│       ├── retriever_hybrid.py     # 混合檢索器
│       ├── rag_store_manager.py     # RAG 儲存管理
│       ├── rag_faiss_incremental.py # FAISS 增量索引
│       └── llm/
│           ├── base.py              # LLM 基礎介面
│           ├── factory.py           # LLM 工廠
│           └── backends/
│               ├── ollama_backend.py
│               ├── vllm_backend.py
│               └── trtllm_backend.py
├── scripts/
│   ├── rag_update_faiss.py      # 更新 FAISS 索引
│   ├── eval_30_patients.py      # 評估 30 病人
│   └── smoke_test_backends.py  # 測試後端
├── data/
│   ├── rag_sources/             # RAG 來源文件
│   └── rag_store/               # RAG 儲存（索引、manifest）
│       ├── builds/              # 各版本 build
│       ├── manifest.json        # 版本清單
│       └── sources.json         # 來源檔案 SHA256
├── logs/
│   └── traces/                  # 追蹤日誌
├── requirements.txt
└── README.md
```

## 系統特性

### 引用強制驗證（S2）

系統會自動驗證：
1. Agent/Arbiter 輸出是否符合 schema
2. Citations 是否引用有效的 hits

如果驗證失敗，會自動：
1. 產生 repair prompt（包含 hits 清單和 schema）
2. 重試一次（S2）
3. 如果仍失敗，回傳保守決策（不會 crash）

### 版本增量更新

`scripts/rag_update_faiss.py` 支援：
- 偵測新增/修改/刪除的來源檔案
- 增量更新索引（新增/修改的檔案）
- 產生新 build ID
- 更新 manifest.json

### 錯誤處理

系統設計確保：
- 欄位缺失時回傳 `INSUFFICIENT_DATA`（不 crash）
- LLM 格式錯誤時自動修復重試
- 網路錯誤時重試一次
- 所有錯誤記錄在 metrics.errors 中

## 開發

### 執行測試

```bash
# 測試後端
python scripts/smoke_test_backends.py

# 測試單一病人（使用 Python）
python -c "
import asyncio
from app.schemas import ERASRequest
from app.services.decision_pipeline import run_decision

async def test():
    req = ERASRequest(
        scenario='POD',
        question='Test question',
        patient_fhir={'age': 75, 'nu_desc': {...}}
    )
    result = await run_decision(req)
    print(result)

asyncio.run(test())
"
```

## 授權

[依專案需求設定]

## 聯絡

[依專案需求設定]
