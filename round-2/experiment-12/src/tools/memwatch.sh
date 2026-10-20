#!/usr/bin/env bash
# Memory watchdog for this workspace only. The container's cgroup-v1 limit is ~31 GB (host `free` shows 251 GB).
# Every heavy job appends its PID to logs/heavy_pids.txt; when the cgroup's anonymous memory (total_rss + total_shmem) exceeds
# LIMIT_GB, the watchdog kills those registered PIDs (and their children) -- never processes matched by name.
LIMIT_GB=${LIMIT_GB:-26}
PIDS_FILE="$(dirname "$0")/../logs/heavy_pids.txt"
LOG="$(dirname "$0")/../logs/memwatch.log"
touch "$PIDS_FILE"
while true; do
  # anonymous memory only: page cache (incl. active_file from reading 16 GB of safetensors) is reclaimable
  anon=$(awk '/^total_rss /{r=$2} /^total_shmem /{s=$2} END{print r+s}' /sys/fs/cgroup/memory/memory.stat)
  used=$(( anon / 1073741824 ))
  if [ "$used" -ge "$LIMIT_GB" ]; then
    echo "$(date -u +%FT%TZ) used=${used}GB >= ${LIMIT_GB}GB -> killing registered PIDs: $(cat "$PIDS_FILE" | tr '\n' ' ')" >> "$LOG"
    for p in $(cat "$PIDS_FILE"); do
      for c in $(pgrep -P "$p" 2>/dev/null); do kill -9 "$c" 2>/dev/null; done
      kill -9 "$p" 2>/dev/null
    done
    : > "$PIDS_FILE"
  fi
  sleep 2
done
