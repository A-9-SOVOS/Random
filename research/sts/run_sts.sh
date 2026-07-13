#!/usr/bin/env bash
# Tiny interactive-style STS smoke (legacy). Prefer run_nist_sts.sh.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
RESEARCH="$(cd "${ROOT}/.." && pwd)"
BIN="${RESEARCH}/results/rrann_sts.bin"
STS="${RESEARCH}/third_party/sts-2_1_2/sts-2.1.2/sts-2.1.2"
printf '0\n%s\n1\n0\n1\n' "${BIN}" > /tmp/sts_input.txt
ls -l "${BIN}"
"${STS}/assess" 80000000 < /tmp/sts_input.txt 2>&1 | head -80
