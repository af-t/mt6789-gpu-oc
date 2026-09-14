#!/bin/sh
# Lightweight gpu_uvoc_mt6789.ko build for Wild Bypass (force-load).
# Downloads vanilla 6.12.38 (~140MB, ~2-3 min @1MB/s), defconfig+modules_prepare,
# then compiles the module (seconds). Vermagic need not match exactly (Bypass).
set -eu
VER=6.12.38
WORK=${WORK:-$HOME/gpu-uvoc-build}
OPP=${OPP:-1200}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$WORK"; cd "$WORK"

if [ ! -d "linux-$VER" ]; then
  echo "[1/4] download linux-$VER.tar.xz ..."
  curl -L -o "linux-$VER.tar.xz" "https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-$VER.tar.xz"
  echo "[2/4] extract ..."
  tar xf "linux-$VER.tar.xz"
fi
cd "linux-$VER"

if command -v aarch64-linux-gnu-gcc >/dev/null 2>&1; then
  export CROSS_COMPILE=aarch64-linux-gnu-
  export LLVM=0
  echo "[*] using gcc cross aarch64"
else
  export LLVM=1
  echo "[*] using clang (LLVM=1)"
fi

if [ ! -f .config ]; then
  echo "[3/4] defconfig + modules_prepare (5-15 min on Celeron) ..."
  make ARCH=arm64 ${LLVM:+LLVM=1} defconfig
  make ARCH=arm64 ${LLVM:+LLVM=1} -j"$(nproc)" modules_prepare
fi

echo "[4/4] building module ..."
python3 "$ROOT/tools/gen_opp.py" "$OPP" > "$ROOT/src/opp_table.h"
make -C "$WORK/linux-$VER" ARCH=arm64 ${LLVM:+LLVM=1} \
  ${CROSS_COMPILE:+CROSS_COMPILE=$CROSS_COMPILE} M="$ROOT" modules

echo "== result =="
file "$ROOT/src/gpu_uvoc_mt6789.ko"
modinfo "$ROOT/src/gpu_uvoc_mt6789.ko" | grep -E "vermagic|description" || true
echo "Copy src/gpu_uvoc_mt6789.ko to the phone, then:"
echo "  su -c 'insmod /sdcard/gpu_uvoc_mt6789.ko'"
echo "Load fails (vermagic)? use Wild Bypass + insmod -f"
