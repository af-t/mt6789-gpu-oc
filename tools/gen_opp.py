#!/usr/bin/env python3
# 45-entry OPP table generator per OC variant. Usage: gen_opp.py 1700 > opp_table.h
# Volt model (anchored at stock: 1100MHz @ 0.75V):
# - V(F) = snap625(round(F_MHz * 0.682) * 100), same ratio for the whole head
# - argv[2] optional: V0 override (peak volt, uV); applied as a flat delta to
#   the whole head so UV/OV step tests keep the curve shape
# - all volts snapped to the 625 PMIC grid (round-half-up)
# - below 1100: live-UV tail (boot result + AVS/aging, -1250), proven
# - vsram = volt ; posdiv 1 ; margin 1875 ; power=0 (computed by the module)
# Bridge (fixed 1050/1000/950): the old merge jumped 1100 straight to the
# tail start (165-207MHz + posdiv switch in one governor step) and crashed
# dynamic DVFS while pinned was safe. The bridge displaces 3 live tail
# entries so idx alignment with the live table is preserved
# (baked idx HEAD_NUM+3+j == live idx HEAD_NUM+3+j); its volts interpolate
# linearly head-bottom -> (kept-tail-first - UV_OFFSET) so the runtime
# joint (module rebuilds idx HEAD_NUM+ from live - UV) stays smooth.
# posdiv follows stock (1 above the 948/962 switch window, 2 below).
# Driver ceilings (from mtk_gpufreq_mt6789.ko decompile — exceeding any of
# these panics via __gpufreq_abort, there is nothing to "bypass"):
# - regulator_set_voltage max 0x13BB45 uV -> table units <= 129696
# - freq_scale fallback ladder rejects > 1900000; the table-hit path has no
#   clamp but the PLL-lock readback aborts on mismatch, so raise fmax gradually
import sys

RATIO = 682  # V = F_MHz * 0.682 (x1000 for integer math)
PMIC_GRID = 625
V_MAX = 129696  # 0x13BB45 uV regulator ceiling / 10
F_STEP = 50000
F_MERGE = 1100000
OPP_NUM = 45  # must match gpu_uvoc_mt6789.c (driver working-table size)
UV_OFFSET = 1250  # must match gpu_uvoc_mt6789.c (module rebuilds tail as live - UV)
BRIDGE = (1050000, 1000000, 950000)
POSDIV_SWITCH = 955000  # midpoint of stock 948/962 switch window

# tail idx3..44: freq, volt, vsram, posdiv, margin (live-UV, from unit, OK)
TAIL = [
 (1058000,75000,76250,1,1875),(1045000,74375,75625,1,1875),
 (1031000,73750,75000,1,1875),(1017000,73125,75000,1,1875),
 (1003000,72500,75000,1,1875),(990000,71875,75000,1,1875),
 (976000,71250,75000,1,1875),(962000,71250,75000,1,1875),
 (948000,70625,75000,2,1875),(935000,70000,75000,2,1875),
 (921000,69375,75000,2,1875),(907000,68750,75000,2,1875),
 (893000,68125,75000,2,1875),(880000,67500,75000,2,1875),
 (868000,66875,75000,2,1875),(857000,66875,75000,2,1875),
 (846000,66250,75000,2,1875),(835000,65625,75000,2,1250),
 (823000,65000,75000,2,1250),(812000,65000,75000,2,1250),
 (801000,64375,75000,2,1250),(790000,63750,75000,2,1250),
 (778000,63750,75000,2,1250),(767000,63125,75000,2,1250),
 (756000,62500,75000,2,1250),(745000,61875,75000,2,1250),
 (733000,61875,75000,2,1250),(722000,61250,75000,2,1250),
 (711000,60625,75000,2,1250),(700000,60000,75000,2,1250),
 (674000,60000,75000,2,1250),(648000,59375,75000,2,1250),
 (622000,59375,75000,2,1250),(596000,58750,75000,2,625),
 (570000,58750,75000,2,625),(545000,58125,75000,2,625),
 (519000,58125,75000,2,625),(493000,57500,75000,2,625),
 (467000,57500,75000,2,625),(441000,56875,75000,2,625),
 (415000,56875,75000,2,625),(390000,56250,75000,2,625),
]

def snap(v):
    return (v + PMIC_GRID // 2) // PMIC_GRID * PMIC_GRID

def volt_raw(f):
    return (f * RATIO + 5000) // 10000

def main():
    fmax = int(sys.argv[1]) * 1000
    assert 1200000 <= fmax <= 1900000 and fmax % 50000 == 0, "variants 1200-1900 step 50"
    delta = 0
    if len(sys.argv) > 2:  # UV/OV step: shift the whole curve, keep its shape
        delta = snap(int(sys.argv[2])) - snap(volt_raw(fmax))
    v0 = snap(volt_raw(fmax) + delta)
    head = []
    f = fmax
    while f >= F_MERGE:
        v = snap(volt_raw(f) + delta)
        s = v if v > 75000 else 75000  # sram retention floor, same as module tail
        head.append((f, v, s, 1, 1875))
        f -= F_STEP
    assert len(TAIL) == OPP_NUM - 3, f"TAIL has {len(TAIL)} entries, expected {OPP_NUM - 3}"
    # kept tail starts past the live entries displaced by the bridge, so baked
    # idx HEAD_NUM+3+j still matches live idx HEAD_NUM+3+j (live idx3 == TAIL[0]).
    # Low variants (short head) pull back dropped entries that still fit below
    # the bridge; the count constraint IS the alignment constraint, so the
    # module's live-merge (idx HEAD_NUM+ from live - UV) stays correct.
    kept_start = len(head)
    while True:
        bridge = [f for f in BRIDGE if f > TAIL[kept_start][0]]
        assert bridge, f"empty bridge at kept_start {kept_start}"
        if len(head) + len(bridge) + (len(TAIL) - kept_start) == OPP_NUM:
            break
        kept_start -= 1
        assert kept_start >= 0, "kept tail underflow"
    kept = TAIL[kept_start:]
    assert kept[0][0] < min(bridge), "bridge overlaps kept tail"
    # bridge volts: linear head-bottom -> (kept-first - UV), i.e. what the
    # runtime joint looks like after the module rebuilds the tail as live - UV.
    hfreq, hvolt = head[-1][0], head[-1][1]
    kfreq, kvolt = kept[0][0], kept[0][1]
    bridge_rows = []
    for f in bridge:
        v = snap(hvolt + (f - hfreq) * (kvolt - UV_OFFSET - hvolt) // (kfreq - hfreq))
        s = v if v > 75000 else 75000
        p = 1 if f >= POSDIV_SWITCH else 2
        bridge_rows.append((f, v, s, p, 1875))
    # emit the kept tail UV-shifted, mirroring the module's live-merge math, so
    # the baked table is self-consistent (monotonic, guard-meaningful) instead
    # of mixing UV-targeted bridge volts with raw snapshot volts at the joint.
    kept_out = []
    for (f, v, s, p, m) in kept:
        nv = v - UV_OFFSET if v > UV_OFFSET else v
        if nv < 50000:
            nv = 50000
        ns = s - UV_OFFSET if s > 75000 + UV_OFFSET else s
        if ns < 75000:
            ns = 75000
        kept_out.append((f, nv, ns, p, m))
    tbl = head + bridge_rows + kept_out
    assert len(tbl) == OPP_NUM, f"entry count {len(tbl)} != {OPP_NUM}"
    for i in range(1, len(tbl)):  # monotonic: freq falls, volt never rises
        assert tbl[i][0] < tbl[i - 1][0], f"freq idx{i} not descending"
        assert tbl[i][1] <= tbl[i - 1][1], f"volt idx{i} rises"
    # guard = largest step in the table + 5000 slack (live tail can drift with AVS
    # from the TAIL snapshot; the module validates the live-merged result, not the snapshot)
    maxstep = max(abs(tbl[i][1] - tbl[i - 1][1]) for i in range(1, len(tbl)))
    V_GUARD = maxstep + 5000
    for i, (f, v, s, p, m) in enumerate(tbl):
        assert 187500 <= f <= 1900000, f"freq idx{i} {f}"
        assert 50000 <= v <= V_MAX, f"volt idx{i} {v}"
        assert 75000 <= s <= V_MAX, f"vsram idx{i} {s}"
        if i:
            pf, pv = tbl[i-1][0], tbl[i-1][1]
            assert f < pf, f"freq idx{i} not descending"
            assert abs(v - pv) <= V_GUARD, f"volt step idx{i} {abs(v-pv)}"
    print(f"// generated by gen_opp.py, variant {fmax//1000}MHz @{v0}uV "
          f"(F*0.682 snapped 625) + 1050/1000/950 bridge + live-UV tail. "
          f"power=0 (computed by module).")
    print(f"#define HEAD_NUM {len(head) + len(bridge_rows)}")
    print(f"#define HEAD_VGUARD {V_GUARD}")
    print("static struct opp opp_new[OPP_NUM] = {")
    for f, v, s, p, m in tbl:
        print(f"  {{{f},{v},{s},{p},{m},0}},")
    print("};")
    print(f"// idx0 {fmax} {v0} | head {len(head)} bridge {len(bridge_rows)} "
          f"tail {len(kept)} | entries {len(tbl)} | OK",
          file=sys.stderr)

main()
