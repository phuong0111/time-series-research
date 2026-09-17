#!/usr/bin/env bash
# Strip the '?download=1' query string wget kept in Zenodo filenames.
cd /root/time-series-research/dataset
find . -name '*\?download=1' -print0 | while IFS= read -r -d '' f; do mv -n "$f" "${f%\?download=1}"; done
