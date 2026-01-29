#!/bin/bash
# 数据库备份脚本
# 用法: ./scripts/backup_db.sh

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/skyeye_bot_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"

docker exec skyeye-db pg_dump -U postgres skyeye_bot > "$BACKUP_FILE"

echo "Backup saved to: $BACKUP_FILE"
