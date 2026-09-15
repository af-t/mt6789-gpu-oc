#!/bin/sh
# Load gpu_uvoc_mt6789.ko with full sync (working + GED HAL + signed).
# KASLR re-randomizes module bases every boot, so the BSS addresses must be
# read live after lowering kptr_restrict (resets to 2 on reboot).
# Usage (as root): sh scripts/insmod-uvoc.sh [path/to/gpu_uvoc_mt6789.ko]
set -eu
KO=${1:-src/gpu_uvoc_mt6789.ko}
[ -f "$KO" ] || { echo "missing: $KO"; exit 1; }

KPTR=$(cat /proc/sys/kernel/kptr_restrict)
echo 0 > /proc/sys/kernel/kptr_restrict
trap 'echo "$KPTR" > /proc/sys/kernel/kptr_restrict' EXIT

GB=$(cat /sys/module/ged/sections/.bss)
MB=$(cat /sys/module/mtk_gpufreq_mt6789/sections/.bss)
echo "GED=$GB MTK=$MB"
case "$GB $MB" in
  *0x0000000000000000*) echo "BSS still hidden, kptr_restrict stuck?"; exit 1;;
esac

dmesg -c > /dev/null 2>&1 || true
insmod "$KO" ged_bss="$GB" mt6789_bss="$MB"
dmesg -c | grep gpu-uvoc
