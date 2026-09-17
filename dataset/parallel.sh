#!/usr/bin/env bash
D=/root/time-series-research/dataset; L=$D/_logs
TOK=925dn72ka8n519r4acgsgilp7h
log(){ echo "[$(date +%T)] $*" >> "$L/progress.log"; }
w(){ # w <dir> <url> <outfile>
  wget -c -q --tries=8 --timeout=60 -O "$D/$1/$3" "$2" >>"$L/$1.log" 2>&1 \
    && log "OK    $1/$3" || log "FAIL  $1/$3"
}
c(){ # c <dir> <cic-path> <file>
  curl -sS -L -C - --max-time 21600 --retry 5 --retry-delay 10 \
       -H "Cookie: Token=$TOK" \
       "https://cicresearch.ca/CICDataset/$2/download.php?file=$3" \
       -o "$D/$1/$3" >>"$L/$1.log" 2>&1 \
    && log "OK    $1/$3" || log "FAIL  $1/$3"
}
Z=https://zenodo.org/records

( w 02_CESNET-MINER22 "$Z/7189293/files/DeCryptoDatasets.tar.gz?download=1" DeCryptoDatasets.tar.gz ) &
( for f in $(curl -sS "https://zenodo.org/api/records/4275775" | python3 -c "import json,sys;[print(f['key']) for f in json.load(sys.stdin)['files']]"); do
    w 04_HTTPS-BruteForce "$Z/4275775/files/$f?download=1" "$f"; done ) &
( w 05_DoH-Real-World "$Z/5956044/files/doh_resolver_ip.csv?download=1" doh_resolver_ip.csv
  w 05_DoH-Real-World "$Z/5956044/files/DoH-Real-World.tar.gz?download=1" DoH-Real-World.tar.gz ) &
( w 06_IoT-23 "https://mcfp.felk.cvut.cz/publicDatasets/IoT-23-Dataset/iot_23_datasets_small.tar.gz" iot_23_datasets_small.tar.gz ) &
( w 10_CTU-13 "https://mcfp.felk.cvut.cz/publicDatasets/CTU-13-Dataset/CTU-13-Dataset.tar.bz2" CTU-13-Dataset.tar.bz2 ) &
( c 03_CIC-Bell-DNS-2021 CICBellDNS2021 Scenarios.txt
  c 03_CIC-Bell-DNS-2021 CICBellDNS2021 CSVs-20240207T040926Z-001.zip ) &
( c 13_CIC-DoH-Brw-2020 DoHBrw-2020 CSVs.zip ) &
wait
log "PARALLEL BATCH DONE"
