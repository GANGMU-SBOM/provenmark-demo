#!/usr/bin/env bash
# Verify a sample evidence bundle with the public package only (no secret key).
#   bash demos/verify_sample_evidence.sh leak        # copy / leak evidence
#   bash demos/verify_sample_evidence.sh training    # training-use evidence (needs: pip install -e ".[torch]")
set -euo pipefail
d="$(cd "$(dirname "$0")" && pwd)/sample_evidence"
case "${1:-leak}" in
  leak)
    provenmark-verify verify-evidence "$d/leak/evidence.json" "$d/leak/found_online.csv" --pubkey "$d/leak/owner.pub.json"
    echo; echo "Owner's report: $d/leak/evidence.md" ;;
  training)
    provenmark-verify verify-evidence "$d/training/evidence_training.json" --original "$d/training/plant.csv" \
        --predictions "$d/training/predictions.npy" --pubkey "$d/training/owner.pub.json"
    echo; echo "Owner's report: $d/training/evidence_training.md" ;;
  *) echo "usage: $0 leak|training" >&2; exit 2 ;;
esac
