# Demo Mode Backup

此目錄包含 Demo Mode (Option 3) 的備份文件。

## 文件說明

- `main_demo.py` - Demo 模式後端（無需資料庫）
- `start_demo.sh` - Demo 模式啟動腳本
- `DEMO_MODE.md` - Demo 模式使用說明

## 如何使用 Demo Mode

```bash
# 從項目根目錄執行
cd backend
python3 -m uvicorn main_demo:app --host 0.0.0.0 --port 8000

# 或使用啟動腳本
./start_demo.sh
```

## Demo Mode 特點

✅ 無需 PostgreSQL 資料庫
✅ 無需 OpenAI API Key
✅ 立即可用，快速測試
⚠️ 資料存儲在記憶體中（重啟後消失）
⚠️ AI 功能被禁用

## 升級到完整版本

參考主目錄的 `README.md` 或 `DEMO_MODE.md` 文件。

---

**備份日期**: 2025-12-12  
**狀態**: 已測試並運行成功
