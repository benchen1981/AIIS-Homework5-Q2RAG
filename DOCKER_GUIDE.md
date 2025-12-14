# Docker 部署指南

## 🐳 使用 Docker 部署企業文件智能平台

Docker 部署是最簡單的方式，包含所有必要的服務（PostgreSQL、後端、前端）。

---

## 📋 前置需求

1. **Docker Desktop** 已安裝並運行
   - macOS: https://www.docker.com/products/docker-desktop
   - 確認 Docker 正在運行: `docker info`

2. **OpenAI API Key** (可選，但建議設置以啟用 AI 功能)
   - 從 https://platform.openai.com/api-keys 獲取

---

## 🚀 快速啟動

### 方法 1: 使用啟動腳本（推薦）

```bash
# 1. 設置 OpenAI API Key（可選）
export OPENAI_API_KEY=sk-your-api-key-here

# 2. 運行啟動腳本
./start_docker.sh
```

### 方法 2: 手動啟動

```bash
# 1. 設置環境變數
export OPENAI_API_KEY=sk-your-api-key-here

# 2. 構建映像
docker-compose build

# 3. 啟動服務
docker-compose up -d

# 4. 查看狀態
docker-compose ps
```

---

## 🌐 訪問應用

啟動成功後，訪問以下地址：

- **前端 UI**: http://localhost:8501
- **後端 API**: http://localhost:8000
- **API 文檔**: http://localhost:8000/docs
- **健康檢查**: http://localhost:8000/api/health

---

## 📊 服務組成

Docker Compose 會啟動 3 個服務：

1. **postgres** (Port 5432)
   - PostgreSQL 14 資料庫
   - 自動初始化 schema
   - 數據持久化存儲

2. **backend** (Port 8000)
   - FastAPI 後端服務
   - 文件處理和 AI 抽取
   - RAG 查詢引擎

3. **frontend** (Port 8501)
   - Streamlit Web 介面
   - 多頁面應用
   - 實時 API 連接

---

## 🔧 常用命令

### 查看日誌
```bash
# 查看所有服務日誌
docker-compose logs -f

# 查看特定服務日誌
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### 重啟服務
```bash
# 重啟所有服務
docker-compose restart

# 重啟特定服務
docker-compose restart backend
```

### 停止服務
```bash
# 停止但保留數據
docker-compose stop

# 停止並移除容器（保留數據卷）
docker-compose down

# 完全清理（包括數據）
docker-compose down -v
```

### 查看服務狀態
```bash
docker-compose ps
```

### 進入容器
```bash
# 進入後端容器
docker-compose exec backend bash

# 進入資料庫容器
docker-compose exec postgres psql -U docuser -d docdb
```

---

## 🔑 環境變數配置

### 必需的環境變數

- `OPENAI_API_KEY`: OpenAI API 密鑰（用於 AI 功能）

### 可選的環境變數

- `SECRET_KEY`: JWT 密鑰（默認: docker-secret-key-change-in-production）
- `MAX_FILE_SIZE_MB`: 最大文件大小（默認: 50）
- `CHUNK_SIZE`: 文本塊大小（默認: 1000）
- `DEFAULT_TOP_K`: 默認檢索數量（默認: 4）

### 設置方式

**方法 1: 環境變數**
```bash
export OPENAI_API_KEY=sk-your-key
export SECRET_KEY=your-secret-key
docker-compose up -d
```

**方法 2: .env 文件**
```bash
# 創建 .env 文件
cat > .env << EOF
OPENAI_API_KEY=sk-your-key
SECRET_KEY=your-secret-key
EOF

docker-compose up -d
```

---

## 📦 數據持久化

### 數據存儲位置

- **PostgreSQL 數據**: Docker volume `postgres_data`
- **上傳文件**: `./uploads` 目錄
- **向量數據**: `./chromadb_data` 目錄
- **日誌文件**: `./logs` 目錄

### 備份數據

```bash
# 備份 PostgreSQL
docker-compose exec postgres pg_dump -U docuser docdb > backup.sql

# 備份文件
tar -czf uploads_backup.tar.gz uploads/
tar -czf chromadb_backup.tar.gz chromadb_data/
```

### 恢復數據

```bash
# 恢復 PostgreSQL
docker-compose exec -T postgres psql -U docuser docdb < backup.sql

# 恢復文件
tar -xzf uploads_backup.tar.gz
tar -xzf chromadb_backup.tar.gz
```

---

## 🐛 故障排除

### 問題 1: 端口已被佔用

**錯誤**: `Bind for 0.0.0.0:8000 failed: port is already allocated`

**解決**:
```bash
# 查找佔用端口的進程
lsof -i :8000
lsof -i :8501
lsof -i :5432

# 停止佔用的進程或修改 docker-compose.yml 中的端口
```

### 問題 2: 資料庫連接失敗

**解決**:
```bash
# 檢查 PostgreSQL 是否健康
docker-compose ps postgres

# 查看 PostgreSQL 日誌
docker-compose logs postgres

# 重啟 PostgreSQL
docker-compose restart postgres
```

### 問題 3: 前端無法連接後端

**解決**:
```bash
# 檢查後端是否運行
curl http://localhost:8000/api/health

# 檢查網絡連接
docker-compose exec frontend ping backend

# 重啟服務
docker-compose restart backend frontend
```

### 問題 4: OpenAI API 錯誤

**解決**:
```bash
# 檢查 API Key 是否設置
docker-compose exec backend env | grep OPENAI

# 重新設置並重啟
export OPENAI_API_KEY=sk-your-correct-key
docker-compose up -d backend
```

---

## 🔄 更新應用

```bash
# 1. 停止服務
docker-compose down

# 2. 拉取最新代碼（如果有）
git pull

# 3. 重新構建
docker-compose build

# 4. 啟動服務
docker-compose up -d
```

---

## 🧹 完全清理

如果需要完全重新開始：

```bash
# 停止並刪除所有容器、網絡、數據卷
docker-compose down -v

# 刪除映像（可選）
docker rmi $(docker images | grep docdb | awk '{print $3}')

# 清理本地數據
rm -rf uploads/* logs/* chromadb_data/*

# 重新啟動
./start_docker.sh
```

---

## ✅ 驗證部署

### 1. 檢查服務狀態
```bash
docker-compose ps
# 所有服務應該是 "Up" 狀態
```

### 2. 測試後端 API
```bash
curl http://localhost:8000/api/health
# 應返回: {"status":"healthy",...}
```

### 3. 測試前端
- 打開瀏覽器訪問 http://localhost:8501
- 應該看到多頁面應用界面

### 4. 測試文件上傳
- 在前端上傳一個測試文件
- 檢查是否成功處理

---

## 📝 生產部署建議

1. **修改默認密碼**
   - 修改 `docker-compose.yml` 中的 PostgreSQL 密碼
   - 設置強密鑰 `SECRET_KEY`

2. **使用環境變數文件**
   - 創建 `.env` 文件存儲敏感信息
   - 不要提交 `.env` 到版本控制

3. **配置反向代理**
   - 使用 Nginx 或 Traefik
   - 啟用 HTTPS

4. **監控和日誌**
   - 配置日誌聚合
   - 設置監控告警

5. **定期備份**
   - 自動化資料庫備份
   - 備份上傳的文件

---

## 🆚 Docker vs Demo Mode

| 特性 | Docker 部署 | Demo Mode |
|------|------------|-----------|
| 資料庫 | ✅ PostgreSQL | ❌ 記憶體 |
| AI 功能 | ✅ 完整 | ❌ 禁用 |
| 數據持久化 | ✅ 是 | ❌ 否 |
| 設置難度 | 🟡 中等 | 🟢 簡單 |
| 生產就緒 | ✅ 是 | ❌ 否 |

---

**建議**: 使用 Docker 部署進行開發和生產環境，Demo Mode 僅用於快速評估。
