# ERAS RAG 資料庫來源文件

此目錄用於存放 ERAS（Enhanced Recovery After Surgery）相關的臨床指南、文獻、協議等文件。

## 支援的檔案格式

- **PDF** (`.pdf`) - 臨床指南、研究論文
- **文字檔** (`.txt`) - 純文字格式的指南
- **Markdown** (`.md`) - Markdown 格式的文件

## 建議的文件類型

### 1. ERAS 協議文件
- ERAS 協會發布的官方指南
- 各專科（外科、麻醉、護理）的 ERAS 協議
- 醫院內部的 ERAS 標準作業程序

### 2. 臨床指南
- PONV（術後噁心嘔吐）預防與治療指南
- POD（術後譫妄）評估與管理指南
- 胸腔引流管管理指南
- 疼痛管理指南
- 營養支持指南

### 3. 研究文獻
- ERAS 相關的系統性回顧
- 臨床試驗結果
- 最佳實務建議

### 4. 評估工具
- Nu-DESC 量表說明
- CAM-ICU 評估工具
- PONV 風險評分工具

## 檔案命名建議

使用清楚、描述性的檔名，例如：
- `ERAS_General_Guidelines_2023.pdf`
- `PONV_Prevention_Protocol.md`
- `POD_Assessment_Toolkit.pdf`
- `Chest_Tube_Management_Guidelines.txt`

## 建立索引

將文件放入此目錄後，執行：

```bash
python scripts/rag_update_faiss.py
```

這會：
1. 掃描 `data/rag_sources/` 目錄中的所有文件
2. 將文件分塊（chunking）
3. 產生嵌入向量（embeddings）
4. 建立 FAISS 索引
5. 儲存到 `data/rag_store/` 目錄

## 範例文件結構

```
data/rag_sources/
├── ERAS_General_Guidelines.pdf
├── PONV_Protocol_2023.pdf
├── POD_Assessment_Guidelines.md
├── Chest_Tube_Management.txt
└── ERAS_Nutrition_Support.pdf
```

## 注意事項

1. **文件品質**：確保文件內容清晰、結構良好，有助於檢索
2. **版權**：確保您有權使用這些文件
3. **更新**：當文件更新時，重新執行 `rag_update_faiss.py` 會自動增量更新索引
4. **檔案大小**：建議單個文件不超過 50MB

## 取得 ERAS 文件的來源

1. **ERAS Society** (https://erassociety.org/)
   - 官方指南和協議
   
2. **PubMed/醫學資料庫**
   - 搜尋 "ERAS protocol"、"Enhanced Recovery After Surgery"
   
3. **專業學會**
   - 各外科、麻醉、護理學會的 ERAS 指南
   
4. **醫院內部文件**
   - 各醫院的 ERAS 標準作業程序
