#!/usr/bin/env bash
# Extract completed archives. Skips anything an active wget is still writing.
D=/root/time-series-research/dataset
cd "$D" || exit 1
INFLIGHT=$(pgrep -af wget | grep -oP '[^ /]+\.(tar\.gz|tar\.bz2|zip|csv|h5)(\?download=1)?' | sort -u)
skip(){ grep -qxF "$(basename "$1")" <<<"$INFLIGHT"; }

# strip ?download=1 from anything finished
find . -name '*\?download=1' | while read -r f; do
  skip "$f" && continue
  mv -n "$f" "${f%\?download=1}"
done

for a in $(find . -maxdepth 2 -type f \( -name '*.tar.gz' -o -name '*.tar.bz2' -o -name '*.zip' \) | sort); do
  skip "$a" && { echo "SKIP (downloading) $a"; continue; }
  out="$(dirname "$a")/$(basename "${a%%.tar.*}" .zip)"
  [ -d "$out" ] && [ -n "$(ls -A "$out" 2>/dev/null)" ] && { echo "SKIP (done)        $a"; continue; }
  case "$a" in
    *.tar.gz)  gzip -t "$a"  2>/dev/null || { echo "CORRUPT/PARTIAL    $a"; continue; };;
    *.tar.bz2) bzip2 -t "$a" 2>/dev/null || { echo "CORRUPT/PARTIAL    $a"; continue; };;
    *.zip)     python3 -c "import zipfile,sys; sys.exit(0 if zipfile.ZipFile(sys.argv[1]).testzip() is None else 1)" "$a" 2>/dev/null || { echo "CORRUPT/PARTIAL    $a"; continue; };;
  esac
  mkdir -p "$out"
  echo "EXTRACT            $a -> $out"
  case "$a" in
    *.tar.gz)  tar -xzf "$a" -C "$out";;
    *.tar.bz2) tar -xjf "$a" -C "$out";;
    *.zip)     python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$a" "$out";;
  esac && echo "[$(date +%T)] EXTRACTED $a" >> "$D/_logs/progress.log"
done
