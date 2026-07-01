#!/bin/bash
BACKUP_DIR="$HOME/db_backups"
DB_DIR="$HOME/yp_project/instance"
LOG_FILE="$BACKUP_DIR/backup.log"

mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M)

for db in yangpyeong_v10.db; do
  if [ -f "$DB_DIR/$db" ]; then
    cp "$DB_DIR/$db" "$BACKUP_DIR/${db%.db}_${TIMESTAMP}.db"
  fi
done

# 7일 이상 오래된 백업 삭제
find "$BACKUP_DIR" -name '*.db' -mtime +7 -delete 2>/dev/null

# 오늘자 1시간 이상 된 중복 백업 정리 (최신 1개만 유지)
for db_prefix in yangpyeong_v10; do
  today=$(date +%Y%m%d)
  # 오늘자 백업들 시간순 정렬
  today_backups=$(ls -t "$BACKUP_DIR/${db_prefix}_${today}"* 2>/dev/null || true)
  count=0
  if [ -n "$today_backups" ]; then
    for b in $today_backups; do
      count=$((count + 1))
      if [ $count -gt 1 ]; then
        file_mtime=$(stat -c %Y "$b" 2>/dev/null || echo 0)
        now=$(date +%s)
        age=$((now - file_mtime))
        if [ $age -gt 3600 ]; then
          rm -f "$b"
        fi
      fi
    done
  fi
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup complete: $BACKUP_DIR/yangpyeong_v10_${TIMESTAMP}.db" >> "$LOG_FILE"
