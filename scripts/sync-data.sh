#!/bin/bash
# 数据同步脚本 - 单向同步数据文件夹

# 配置
SERVER="root@8.129.109.139"
LOCAL_DIR="/Users/isenfengming/.openclaw/workspace/工作台/智算"
SERVER_DIR="/root/智算"

echo "=== 智算数据同步 ==="
echo "1. 本地 → 服务器"
echo "2. 服务器 → 本地"
echo "3. 双向同步（先拉取再推送）"
echo "q. 退出"
echo ""

read -p "请选择 (1/2/3/q): " choice

case $choice in
    1)
        echo "同步 data/ ..."
        rsync -avz --exclude='*.tmp' "$LOCAL_DIR/data/" "$SERVER:$SERVER_DIR/data/"
        echo "同步 output/ ..."
        rsync -avz --exclude='*.tmp' "$LOCAL_DIR/output/" "$SERVER:$SERVER_DIR/output/"
        echo "✅ 完成：本地 → 服务器"
        ;;
    2)
        echo "同步 data/ ..."
        rsync -avz --exclude='*.tmp' "$SERVER:$SERVER_DIR/data/" "$LOCAL_DIR/data/"
        echo "同步 output/ ..."
        rsync -avz --exclude='*.tmp' "$SERVER:$SERVER_DIR/output/" "$LOCAL_DIR/output/"
        echo "✅ 完成：服务器 → 本地"
        ;;
    3)
        echo "先拉取服务器数据到本地..."
        rsync -avz --exclude='*.tmp' "$SERVER:$SERVER_DIR/data/" "$LOCAL_DIR/data/"
        rsync -avz --exclude='*.tmp' "$SERVER:$SERVER_DIR/output/" "$LOCAL_DIR/output/"
        echo "再推送本地数据到服务器..."
        rsync -avz --exclude='*.tmp' "$LOCAL_DIR/data/" "$SERVER:$SERVER_DIR/data/"
        rsync -avz --exclude='*.tmp' "$LOCAL_DIR/output/" "$SERVER:$SERVER_DIR/output/"
        echo "✅ 完成：双向同步"
        ;;
    q|Q)
        echo "退出"
        exit 0
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac
