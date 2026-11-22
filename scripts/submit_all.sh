#!/usr/bin/env bash
# Submit all simulated scaffolds to the LOVAMAP C++ API.
# Usage: nohup bash scripts/submit_all.sh > submit_all.log 2>&1 &

SCAFFOLD_JSONS="/Users/dzen/Library/CloudStorage/Box-Box/Lindsay Riley/Electronic Notebook/Void Space Project/MIMC/Data/Domains/Particles/Simulated/Jsons"
SCAFFOLD_DATS="/Users/dzen/Library/CloudStorage/Box-Box/Lindsay Riley/Electronic Notebook/Void Space Project/MIMC/Data/Domains/Particles/Simulated/Dats"
OUTPUT_DIR="data/descriptors/cpp/batch_all_$(date +%m%d%Y)"

python run.py submit \
  --scaffold-dir "$SCAFFOLD_JSONS" "$SCAFFOLD_DATS" \
  --output-dir "$OUTPUT_DIR" \
  --timeout 300
