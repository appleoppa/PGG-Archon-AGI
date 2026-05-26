#!/bin/bash
# Apex仓库同步脚本 - 拉取最新代码并同步到"苹果哥的文件"
# 路径: ~/Documents/Apex仓库/sync_apex.sh

DEST_DIR="$HOME/Documents/Apex仓库"
REPOS_DIR="$HOME/Documents/Apex仓库"
LOG="$REPOS_DIR/sync_log.txt"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') 同步开始 ===" >> "$LOG"

for repo in apex-spiral LLM-Pangu CodeGenesis GeneNexus XuanjiQuant; do
    if [ -d "$REPOS_DIR/$repo/.git" ]; then
        echo "拉取 $repo ..." >> "$LOG"
        cd "$REPOS_DIR/$repo"
        git pull --ff origin HEAD >> "$LOG" 2>&1
        echo "$repo 更新完成" >> "$LOG"
    fi
done

echo "=== $(date '+%Y-%m-%d %H:%M:%S') 同步结束 ===" >> "$LOG"
