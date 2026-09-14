#!/bin/sh
# Build 11 OC variants 1200-1700 (step 50) -> variants/gpu_uvoc_mt6789_<F>.ko
# Runs in a container, needs the GKI-patched tree at /var/tmp/kbuild (persistent).
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
K=/var/tmp/kbuild/linux-6.12.38
export PATH="/usr/lib/llvm-21/bin:$PATH"
mkdir -p "$ROOT/variants"
for f in 1200 1250 1300 1350 1400 1450 1500 1550 1600 1650 1700; do
  python3 "$ROOT/tools/gen_opp.py" "$f" > "$ROOT/src/opp_table.h"
  make -s -C "$K" ARCH=arm64 LLVM=1 LOCALVERSION=-Wild M="$ROOT" \
    KBUILD_EXTRA_SYMBOLS="$ROOT/Extra.symvers" KBUILD_MODPOST_WARN=1 modules
  mv "$ROOT/src/gpu_uvoc_mt6789.ko" "$ROOT/variants/gpu_uvoc_mt6789_$f.ko"
  sz=$(readelf -SW "$ROOT/variants/gpu_uvoc_mt6789_$f.ko" | awk '/this_module/ && /PROGBITS/{print $6}')
  [ "$sz" = "000640" ] || { echo "VARIANT $f struct size $sz WRONG"; exit 1; }
  undef=$(nm "$ROOT/variants/gpu_uvoc_mt6789_$f.ko" | grep " U " | grep -v -E " _(printk|fortify_panic)|gpufreq_get_(working_table|opp_num)|module_layout" || true)
  [ -z "$undef" ] || { echo "VARIANT $f foreign undef: $undef"; exit 1; }
  echo "OK $f"
done
python3 "$ROOT/tools/gen_opp.py" 1200 > "$ROOT/src/opp_table.h" # default = tested variant
cp "$ROOT/variants/gpu_uvoc_mt6789_1200.ko" "$ROOT/src/gpu_uvoc_mt6789.ko"
echo "== done: $(ls "$ROOT/variants" | wc -l) variants in variants/ =="
