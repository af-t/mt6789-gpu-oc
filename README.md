# MT6789 GPU UV+OC

LKM for undervolt + overclock of the Mali GPU on MT6789 (Helio G99) via working-table patch (option B). OPP_NUM stays 45, no hot-path hooks.

- Tested target: OC 1200MHz @93750uV + 1150/1100 staircase, UV -12.5mV mid-stack. Status: WORKING.
- Kernel: WildKernels GKI `6.12.38-android16-Wild` (GKI `android16-6.12-2025-09_r1` + patch)
- Driver: `mtk_gpufreq_mt6789.ko` + `mtk_gpufreq_wrapper_legacy.ko`
- Method: call the wrapper's `gpufreq_get_working_table(1)` / `gpufreq_get_opp_num(1)` directly, backup/restore on init/exit.

## Layout

```
src/gpu_uvoc_mt6789.c  # LKM source
src/opp_table.h           # generated (do not edit by hand)
tools/gen_opp.py        # 45-entry OPP table generator, usage: gen_opp.py 1500 > src/opp_table.h
scripts/build-local.sh  # local build (vanilla 6.12.38, for Wild Bypass)
scripts/build-all.sh    # build 11 variants 1200-1700 in GKI-patched container
Extra.symvers           # module_layout/_printk CRCs from vendor .ko
.github/workflows/build.yml # CI matrix, 11 variants -> Artifacts
```

`src/opp_table.h`, `*.ko`, `variants/`, `dist/` are build output (gitignored).

## Build

OC variants 1200-1700 in 50MHz steps:

```sh
# fast local build (default OPP=1200, override with OPP=1500)
OPP=1200 sh scripts/build-local.sh
# output: src/gpu_uvoc_mt6789.ko

# all variants (needs GKI-patched tree at /var/tmp/kbuild)
sh scripts/build-all.sh
# output: variants/gpu_uvoc_mt6789_<F>.ko

# manual via Makefile
make gen OPP=1500
make -C <KDIR> ARCH=arm64 LLVM=1 M=$PWD modules
```

CI: push / workflow_dispatch -> matrix job builds 11 `.ko` files as Artifacts. Binaries are not committed to the repo, get them from Releases/Artifacts.

## Verify on device (root)

```sh
su -c 'insmod /sdcard/gpu_uvoc_mt6789.ko'
cat /proc/gpufreqv2/gpu_working_opp_table | head -n 5  # idx0 must show the OC freq
echo 0 > /proc/gpufreqv2/fix_target_opp_index          # max-lock test
cat /sys/kernel/ged/hal/current_freqency               # want: 0 <OC freq>
# ... check freq, then release:
echo -1 > /proc/gpufreqv2/fix_target_opp_index
dmesg | grep -iE "gpufreq.*(fail|error)"               # must be empty
```

Full sync (working + GED HAL + signed) needs the runtime BSS bases —
KASLR re-randomizes them every boot, so they cannot be hardcoded; read
them after lowering `kptr_restrict` (resets to 2 on reboot):

```sh
echo 0 > /proc/sys/kernel/kptr_restrict
insmod /sdcard/gpu_uvoc_mt6789.ko \
  ged_bss=$(cat /sys/module/ged/sections/.bss) \
  mt6789_bss=$(cat /sys/module/mtk_gpufreq_mt6789/sections/.bss)
# dmesg must show: patched + GED tables synced + signed table synced
```
Shortcut (does the above + restores kptr_restrict): `sh scripts/insmod-uvoc.sh`

Unload restores the stock table (restore on exit).

## Disclaimer

Overclocking/undervolting can hang, reboot, or damage hardware. You are responsible for what you run. Start from the tested 1200MHz variant, go up gradually, watch thermals.

## License

GPL-2.0, see LICENSE.
