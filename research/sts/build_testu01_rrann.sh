#!/usr/bin/env bash
# Build testu01_rrann against a local or system TestU01 install.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
RESEARCH_DIR="$(cd "${ROOT}/.." && pwd)"
PREFIX="${TESTU01_PREFIX:-$HOME/.local/testu01}"

# Prefer local prefix; fall back to system paths
CFLAGS=(-O2 -Wall)
INCS=()
LIBS=()

if [[ -d "${PREFIX}/include" ]]; then
  INCS+=(-I"${PREFIX}/include")
  LIBS+=(-L"${PREFIX}/lib" -Wl,-rpath,"${PREFIX}/lib")
elif [[ -d /usr/include/testu01 ]]; then
  INCS+=(-I/usr/include/testu01)
fi

# Upstream source tree under research/third_party if configured
TP="${RESEARCH_DIR}/third_party/TestU01-1.2.3"
if [[ -d "${TP}/include" ]]; then
  INCS+=(-I"${TP}/include")
  LIBS+=(-L"${TP}/testu01/.libs" -L"${TP}/probdist/.libs" -L"${TP}/mylib/.libs")
fi

# TestU01 splits into several libraries on Debian/Ubuntu packaging;
# the classic upstream build produces libtestu01, libprobdist, libmylib.
LIBS+=( -ltestu01 -lprobdist -lmylib -lm )

echo "Building testu01_rrann..."
echo "  includes: ${INCS[*]:-(system default)}"
echo "  prefix:   ${PREFIX}"

gcc "${CFLAGS[@]}" "${INCS[@]}" -o "${ROOT}/testu01_rrann" \
    "${ROOT}/testu01_rrann.c" \
    "${LIBS[@]}"

echo "OK → ${ROOT}/testu01_rrann"
echo
echo "Examples (run from research/sts or use absolute paths):"
echo "  ./testu01_rrann smallcrush ../results/rrann_sts_1e6x1000.bin"
echo "  ./testu01_rrann rabbit     ../results/rrann_sts_1e6x1000.bin 33554432"
echo "  ./testu01_rrann alphabit   ../results/rrann_sts_1e6x1000.bin 33554432"
echo "  ./testu01_rrann crush      ../results/rrann_sts_1e6x1000.bin   # long"
echo "  ./testu01_rrann bigcrush   ../results/rrann_sts_1e6x1000.bin   # very long"
