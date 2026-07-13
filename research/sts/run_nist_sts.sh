#!/usr/bin/env bash
# Non-interactive NIST STS 2.1.2 runner for RRann binary dumps.
#
# Usage (from anywhere):
#   research/sts/run_nist_sts.sh [binary_file] [bits_per_stream] [num_streams]
#
# Defaults:
#   binary_file     = research/results/rrann_sts_1e6x1000.bin
#   bits_per_stream = 1000000
#   num_streams     = 1000

set -euo pipefail

STS_SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESEARCH_DIR="$(cd "${STS_SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${RESEARCH_DIR}/.." && pwd)"

STS_DIR="${RESEARCH_DIR}/third_party/sts-2_1_2/sts-2.1.2/sts-2.1.2"
ASSESS="${STS_DIR}/assess"
RESULTS_DIR="${RESEARCH_DIR}/results"
REPORT_DIR="${RESULTS_DIR}/sts_results"

BIN_FILE="${1:-${RESULTS_DIR}/rrann_sts_1e6x1000.bin}"
N_BITS="${2:-1000000}"
N_STREAMS="${3:-1000}"

if [[ "${BIN_FILE}" != /* ]]; then
  # Prefer CWD-relative, then research/results/
  if [[ -f "${BIN_FILE}" ]]; then
    BIN_FILE="$(cd "$(dirname "${BIN_FILE}")" && pwd)/$(basename "${BIN_FILE}")"
  elif [[ -f "${RESULTS_DIR}/${BIN_FILE}" ]]; then
    BIN_FILE="${RESULTS_DIR}/${BIN_FILE}"
  else
    BIN_FILE="${REPO_ROOT}/${BIN_FILE}"
  fi
fi

if [[ ! -x "${ASSESS}" ]]; then
  echo "ERROR: assess binary missing or not executable: ${ASSESS}" >&2
  echo "  Build: (cd ${STS_DIR} && make clean && make -j\"\$(nproc)\")" >&2
  exit 1
fi

if [[ ! -f "${BIN_FILE}" ]]; then
  echo "ERROR: input file not found: ${BIN_FILE}" >&2
  echo "  Generate: python3 research/sts/export_sts_input.py -o research/results/rrann_sts_1e6x1000.bin" >&2
  exit 1
fi

NEED_BYTES=$(( (N_BITS * N_STREAMS + 7) / 8 ))
HAVE_BYTES=$(stat -c%s "${BIN_FILE}")
if (( HAVE_BYTES < NEED_BYTES )); then
  echo "ERROR: ${BIN_FILE} is ${HAVE_BYTES} bytes; need ≥ ${NEED_BYTES} for ${N_STREAMS}×${N_BITS} bits" >&2
  exit 1
fi

mkdir -p "${REPORT_DIR}"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG="${REPORT_DIR}/assess_${N_BITS}x${N_STREAMS}_${STAMP}.log"
REPORT_COPY="${REPORT_DIR}/finalAnalysisReport_${N_BITS}x${N_STREAMS}_${STAMP}.txt"

echo "=== NIST STS 2.1.2 ==="
echo "  assess:     ${ASSESS}"
echo "  input:      ${BIN_FILE} (${HAVE_BYTES} bytes)"
echo "  n:          ${N_BITS}"
echo "  streams:    ${N_STREAMS}"
echo "  log:        ${LOG}"
echo

EXP="${STS_DIR}/experiments/AlgorithmTesting"
if [[ -d "${EXP}" ]]; then
  find "${EXP}" -type f \( \
      -name 'data*.txt' -o -name 'results.txt' -o -name 'stats.txt' \
      -o -name 'freq.txt' -o -name 'finalAnalysisReport.txt' \
    \) -delete 2>/dev/null || true
fi

INPUT_SCRIPT="${REPORT_DIR}/sts_stdin_${STAMP}.txt"
cat > "${INPUT_SCRIPT}" <<EOF
0
${BIN_FILE}
1
0
${N_STREAMS}
1
EOF

echo "STS stdin feed:"
cat -A "${INPUT_SCRIPT}"
echo

cd "${STS_DIR}"
set +e
./assess "${N_BITS}" < "${INPUT_SCRIPT}" > "${LOG}" 2>&1
RC=$?
set -e

FINAL="${EXP}/finalAnalysisReport.txt"
if [[ -f "${FINAL}" ]]; then
  cp -f "${FINAL}" "${REPORT_COPY}"
  echo "=== finalAnalysisReport (copy) → ${REPORT_COPY} ==="
  cat "${FINAL}"
else
  echo "WARNING: finalAnalysisReport.txt not produced (exit=${RC})"
  echo "--- last 80 log lines ---"
  tail -n 80 "${LOG}" || true
fi

echo
echo "Full log: ${LOG}"
echo "Exit code: ${RC}"
exit "${RC}"
