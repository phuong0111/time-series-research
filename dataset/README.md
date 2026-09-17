# Datasets — Table 2 of BaiLuanNCS_Phuong_Edited_Final.docx

Benchmark datasets listed in *Bảng 2. Một số tập dữ liệu chuẩn phổ biến để xây dựng IDSs*
(section "Khảo sát các tập dữ liệu…").

Scope: **processed CSV / extracted flow features only** — raw PCAP archives are
deliberately skipped (they add ~300 GB and are not directly usable for model training).

| # | Dataset | Dir | Status | Source | What was taken |
|---|---------|-----|--------|--------|----------------|
| 1 | CESNET-TimeSeries24 (Koumar 2024) | `01_CESNET-TimeSeries24` | 4/5 done, 40 GB file downloading | Zenodo 13382427 | all time-series CSVs incl. `ip_addresses_full` |
| 2 | CESNET-MINER22 (Plný 2022) | `02_CESNET-MINER22` | **done + extracted** | Zenodo 7189293 | `DeCryptoDatasets` design + evaluation CSVs |
| 3 | CIC-Bell-DNS-2021 (Mahdavifar 2021) | `03_CIC-Bell-DNS-2021` | **done + extracted** | UNB CIC (registered session) | 4 CSVs: benign / malware / phishing / spam (290 MB) |
| 4 | HTTPS Brute-force (Luxemburk 2020) | `04_HTTPS-BruteForce` | **done + extracted** | Zenodo 4275775 | extended network flows |
| 5 | DoH-Real-World (Jeřábek 2022) | `05_DoH-Real-World` | downloading (12.8 GB) | Zenodo 5956044 | `DoH-Real-World.tar.gz` + resolver IPs |
| 6 | IoT-23 (Garcia) | `06_IoT-23` | downloading (9.4 GB) | mcfp.felk.cvut.cz | **light** version: labelled `conn.log` flows, no pcaps |
| 7 | Edge-IIoTset (Ferrag 2022) | `07_Edge-IIoTset` | **done** | HF `Sunayanajagadesh/ML_EdgeIIoT_dataset` | `ML-EdgeIIoT-dataset.csv` (79 MB) — third-party mirror |
| 8 | ISCX-Tor-2016 (Lashkari 2016) | `08_ISCX-Tor-2016` | **done** | GitHub `trevor-m/deep-tor-detection` | Scenario-A/B flow features, CSV + ARFF — third-party mirror |
| 9 | VNAT (Jorgensen 2022) | `09_VNAT` | **done** | archive.ll.mit.edu | both HDF5 dataframes (1.0 GB); 34.5 GB pcap zip skipped |
| 10 | CTU-13 (Garcia 2014) | `10_CTU-13` | downloading (2.0 GB) | mcfp.felk.cvut.cz | NetFlow `.binetflow` + logs |
| 11 | CIC-IDS-2017 (Sharafaldin 2018) | `11_CIC-IDS-2017` | **done** | HF `rdpahalavan/CIC-IDS2017` | `CICIDS_Flow.parquet` — third-party mirror |
| 12 | UNSW-NB15 (Moustafa 2015) | `12_UNSW-NB15` | **done** | Zenodo 10140548 | 4 original CSVs (586 MB) — third-party mirror |
| 13 | CIC-DoH-Brw-2020 (MontazeriShatoori 2020) | `13_CIC-DoH-Brw-2020` | **done + extracted** | UNB CIC (registered session) | all CSV sets, md5-verified (810 MB) |

**All 13 datasets acquired.** Nothing is blocked.

## Provenance caveats
Datasets 7, 8, 11, 12 came from community mirrors, not the original publishers —
the official hosts (Kaggle, UNB CIC, UNSW SharePoint) all require an account or a
signed request form. Verify row counts and column schemas against the source papers
before citing.

## The two CIC datasets
Obtained via a registered browser session. `cicresearch.ca` gates `browse.php`/`download.php`
on a `Token` cookie set when the registration form (`insert.php`) is submitted — the `?t=`
URL parameter alone is not authorization. The cookie expires 24 h after registration, so
re-fetching these later means registering again.

DoH-Brw CSVs ship as nested zips with `.md5` sidecars; all three verified MATCH on extraction.

## Scripts
| Script | Purpose |
|--------|---------|
| `download.sh` | original sequential fetch (superseded by `parallel.sh`) |
| `parallel.sh` | fetches all remaining datasets concurrently — much faster, hosts differ |
| `extract.sh` | integrity-checks and extracts archives; skips in-flight and already-done |
| `autoextract.sh` | watcher: waits for all downloads, then runs `extract.sh` automatically |
| `rename.sh` | strips `?download=1` from Zenodo filenames |

All are resumable (`wget -c` / `curl -C -`). Progress: `_logs/progress.log`;
per-dataset logs and `_logs/autoextract.log` alongside.

Note: this box has no `unzip`, so the scripts use Python's `zipfile` for zip handling.

## Extraction

`./extract.sh` unpacks completed archives, skipping anything wget is still writing
and integrity-checking each file (`gzip -t` / `bzip2 -t` / `unzip -t`) before extracting.
Safe to re-run; it skips already-extracted dirs.

Extracted so far (CESNET-TimeSeries24):

| Tree | Size | Files |
|------|------|-------|
| `institution_subnets/` | 2.0 GB | 1641 |
| `institutions/` | 1.2 GB | 850 |
| `ip_addresses_sample/` | 527 MB | 3001 |
| `times/` | 1.5 MB | 3 |

Layout: `<tree>/agg_10_minutes|agg_1_hour|agg_1_day/<id>.csv`, one series per entity,
plus `identifiers.csv`. Each CSV is 19 columns — `id_time` plus 18 traffic features
(`n_flows`, `n_packets`, `n_bytes`, dest ASN/port/IP counts with mean+std,
tcp/udp and direction ratios, `avg_duration`, `avg_ttl`). Hourly files hold ~6718
rows ≈ 40 weeks, matching the dataset description in the proposal.
