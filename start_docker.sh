#!/bin/bash
# Docker 啟動腳本 - 使用完整路徑

echo "🐳 企業文件智能平台 - Docker 部署"
echo "================================================================"
echo ""

# 尋找 Docker 可執行文件
DOCKER_PATH=""
if [ -f "/usr/local/bin/docker" ]; then
    DOCKER_PATH="/usr/local/bin/docker"
elif [ -f "/Applications/Docker.app/Contents/Resources/bin/docker" ]; then
    DOCKER_PATH="/Applications/Docker.app/Contents/Resources/bin/docker"
else
    # 嘗試使用 PATH 中的 docker
    if command -v docker &> /dev/null; then
        DOCKER_PATH="docker"
    else
        echo "❌ 找不到 Docker"
        echo ""
        echo "請確認："
        echo "1. Docker Desktop 已安裝"
        echo "2. Docker Desktop 正在運行"
        echo "3. 重啟終端或添加 Docker 到 PATH"
        echo ""
        echo "手動添加到 PATH:"
        echo '  export PATH="/usr/local/bin:$PATH"'
        echo ""
        exit 1
    fi
fi

echo "✅ 找到 Docker: $DOCKER_PATH"

# 檢查 Docker 是否運行
if ! $DOCKER_PATH info &> /dev/null; then
    echo "❌ Docker 未運行"
    echo ""
    echo "請啟動 Docker Desktop 應用程序"
    echo "等待 Docker Desktop 完全啟動後再試"
    exit 1
fi

echo "✅ Docker 正在運行"
echo ""

# 檢查 OpenAI API Key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  警告: OPENAI_API_KEY 未設置"
    echo ""
    echo "AI 功能將無法使用。要啟用 AI 功能，請設置:"
    echo "  export OPENAI_API_KEY=sk-your-api-key-here"
    echo ""
    read -p "繼續部署（不含 AI 功能）? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    export OPENAI_API_KEY="sk-placeholder-key"
fi

echo "================================================================"
echo "🔨 構建 Docker 映像..."
echo "================================================================"
echo ""

# 停止現有容器
echo "停止現有容器..."
$DOCKER_PATH compose down 2>/dev/null

# 構建映像
$DOCKER_PATH compose build

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 構建失敗"
    exit 1
fi

echo ""
echo "================================================================"
echo "🚀 啟動服務..."
echo "================================================================"
echo ""

# 啟動服務
$DOCKER_PATH compose up -d

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 啟動失敗"
    echo ""
    echo "查看日誌:"
    echo "  $DOCKER_PATH compose logs"
    exit 1
fi

echo ""
echo "⏳ 等待服務啟動..."
sleep 10

# 檢查服務狀態
echo ""
echo "================================================================"
echo "📊 服務狀態"
echo "================================================================"
echo ""
$DOCKER_PATH compose ps

echo ""
echo "================================================================"
echo "✅ 部署完成！"
echo "================================================================"
echo ""
echo "🌐 訪問地址:"
echo "  - 前端 UI:    http://localhost:8501"
echo "  - 後端 API:   http://localhost:8000"
echo "  - API 文檔:   http://localhost:8000/docs"
echo ""
echo "📝 查看日誌:"
echo "  $DOCKER_PATH compose logs -f"
echo ""
echo "🛑 停止服務:"
echo "  $DOCKER_PATH compose down"
echo ""
echo "================================================================"
