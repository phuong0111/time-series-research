#!/usr/bin/env bash
# Downloads the openly-available datasets from Table 2 (processed CSV / flow features).
set -u
D=/root/time-series-research/dataset
L=$D/_logs
get(){ # get <subdir> <url>
  mkdir -p "$D/$1"
  echo "[$(date +%T)] START $1 <- $2" >> "$L/progress.log"
  wget -c -q --show-progress --progress=dot:giga --tries=5 --timeout=60 \
       -P "$D/$1" "$2" >> "$L/$1.log" 2>&1 \
    && echo "[$(date +%T)] OK    $1" >> "$L/progress.log" \
    || echo "[$(date +%T)] FAIL  $1 ($2)" >> "$L/progress.log"
}
Z=https://zenodo.org/records

# 1. CESNET-TimeSeries24 (Koumar 2024) - the core time-series dataset
for f in ids_relationship.csv weekends_and_holidays.csv times.tar.gz \
         ip_addresses_sample.tar.gz institutions.tar.gz institution_subnets.tar.gz \
         ip_addresses_full.tar.gz; do
  get 01_CESNET-TimeSeries24 "$Z/13382427/files/$f?download=1"
done

# 2. CESNET-MINER22 (Plny 2022)
get 02_CESNET-MINER22 "$Z/7189293/files/DeCryptoDatasets.tar.gz?download=1"

# 4. HTTPS Brute-force (Luxemburk 2020)
curl -sS "https://zenodo.org/api/records/4275775" \
  | python3 -c "import json,sys;[print(f['links']['self']) for f in json.load(sys.stdin)['files']]" \
  > "$L/httpsbf.urls" 2>/dev/null
while read -r u; do [ -n "$u" ] && get 04_HTTPS-BruteForce "$u"; done < "$L/httpsbf.urls"

# 5. DoH-Real-World (Jerabek 2022)
get 05_DoH-Real-World "$Z/5956044/files/doh_resolver_ip.csv?download=1"
get 05_DoH-Real-World "$Z/5956044/files/DoH-Real-World.tar.gz?download=1"

# 6. IoT-23 (Garcia) - light version: labelled conn.log flow features, no pcaps
get 06_IoT-23 "https://mcfp.felk.cvut.cz/publicDatasets/IoT-23-Dataset/iot_23_datasets_small.tar.gz"

# 10. CTU-13 (Garcia 2014) - NetFlow (.binetflow) + logs
get 10_CTU-13 "https://mcfp.felk.cvut.cz/publicDatasets/CTU-13-Dataset/CTU-13-Dataset.tar.bz2"

echo "[$(date +%T)] ALL DONE" >> "$L/progress.log"
