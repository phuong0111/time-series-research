#!/usr/bin/env bash
# Waits for every dataset download to finish, then extracts all archives.
D=/root/time-series-research/dataset; L=$D/_logs
cd "$D" || exit 1
log(){ echo "[$(date '+%F %T')] $*" >> "$L/progress.log"; }

log "AUTOEXTRACT watcher started (pid $$)"
# 1. wait for downloads
while :; do
  n=$(pgrep -af 'wget|curl' | grep -c "$D")
  [ "$n" -eq 0 ] && break
  sleep 60
done
log "AUTOEXTRACT all downloads finished"

# 2. wait for any extract.sh already running
while pgrep -f "$D/extract.sh" >/dev/null || pgrep -f 'bash ./extract.sh' >/dev/null; do sleep 30; done

# 3. extract everything (integrity-checked, skips already-done dirs)
log "AUTOEXTRACT extracting"
"$D/extract.sh" >> "$L/autoextract.log" 2>&1
log "AUTOEXTRACT extraction complete"

# 4. summary
{ echo "=== $(date '+%F %T') final state ==="
  du -sh "$D"/*/ 2>/dev/null | grep -v _logs
  echo "TOTAL $(du -sh "$D" | cut -f1)"
  echo "--- archives still present (originals, safe to delete) ---"
  find "$D" -maxdepth 2 -type f \( -name '*.tar.gz' -o -name '*.tar.bz2' -o -name '*.zip' \) -printf '%10s %p\n'
} >> "$L/autoextract.log"
log "AUTOEXTRACT done - summary in _logs/autoextract.log"
