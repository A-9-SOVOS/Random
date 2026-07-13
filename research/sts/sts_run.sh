#!/usr/bin/env bash
# Legacy one-shot STS run; prefer run_nist_sts.sh for timestamped reports.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
RESEARCH="$(cd "${ROOT}/.." && pwd)"
BIN="${RESEARCH}/results/rrann_sts.bin"
STS="${RESEARCH}/third_party/sts-2_1_2/sts-2.1.2/sts-2.1.2"
printf '0\n%s\n1\n0\n1\n' "${BIN}" > /tmp/sts_input.txt
cd "${STS}"
./assess 80000000 < /tmp/sts_input.txt
