#!/usr/bin/env bash
# Unzips one PPG-DaLiA pickle at a time (each is 0.8-1.7 GB) into WSL /tmp,
# converts it to 1 Hz CSV, removes the temporary pickle.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
Z="$ROOT/data/raw/dalia/data.zip"
TMP="${TMPDIR:-/tmp}/dalia_pkl"
mkdir -p "$TMP"
for k in ${SUBJECTS:-$(seq 1 15)}; do
  python3 -c "import sys,zipfile,shutil; shutil.copyfileobj(zipfile.ZipFile(sys.argv[1]).open(sys.argv[2]), open(sys.argv[3],'wb'), 1<<24)" "$Z" "PPG_FieldStudy/S$k/S$k.pkl" "$TMP/S$k.pkl"
  python3 "$ROOT/sim/prep_dalia.py" --pkl "$TMP/S$k.pkl" --subject "$k" --out "$ROOT/data/dalia_1hz"
  rm -f "$TMP/S$k.pkl"
done
