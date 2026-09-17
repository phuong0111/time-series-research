#!/usr/bin/env bash
# The two real-world benchmarks of Read (2018) §6, from the source the paper
# cites in its footnote 8:  https://moa.cms.waikato.ac.nz/datasets/
#
#   elecNormNew.arff   45,312 instances, 8 attributes + class {UP,DOWN}
#   covtypeNorm.arff  581,012 instances, 54 attributes + class {1..7}
#
# Both counts match the paper's text exactly. Both files are already normalised
# to [0,1] by Weka's Normalize filter (see each @relation line), so no scaling
# is applied downstream in code/data.py.
#
# CAVEAT on elec's `day`: it is declared nominal {1..7} but read ordinally as a
# float by data.py, i.e. the model is told Sunday > Monday. Harmless for the
# bias-variance questions here, wrong if day is ever the variable of interest --
# one-hot it first in that case.
#
# This box has no `unzip`; extraction goes through Python's zipfile, matching
# ../../dataset/extract.sh.
set -euo pipefail
cd "$(dirname "$0")"

BASE="https://sourceforge.net/projects/moa-datastream/files/Datasets/Classification"

for f in elecNormNew covtypeNorm; do
    if [ -f "$f.arff" ]; then
        echo "skip $f.arff (already extracted)"
        continue
    fi
    echo "fetching $f.arff.zip"
    curl -sL -o "$f.arff.zip" "$BASE/$f.arff.zip/download"   # -L: SourceForge redirects
    python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall('.')" "$f.arff.zip"
done

# Row counts, as a cheap integrity check against the paper's stated sizes.
for f in elecNormNew covtypeNorm; do
    n=$(grep -n '^@data' "$f.arff" | head -1 | cut -d: -f1)
    echo "$f.arff: $(( $(grep -c '^' "$f.arff") - n )) instances"
done
