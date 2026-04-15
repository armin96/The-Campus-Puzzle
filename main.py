
import sys
import os
import json
import argparse
import time


ROOT = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(ROOT, "src")
DATA = os.path.join(ROOT, "data", "constraints.json")
sys.path.insert(0, SRC)

import greedy_solver
import graph_engine
import optimizer
import backtracker



HEADER = "=" * 80

def _banner(title: str):
    print(f"\n{HEADER}")
    print(f"  {title}")
    print(HEADER)


def _print_schedule(schedule: list, unscheduled: list):
    col = f"  {'Status':<12} {'Class':<12} {'Time Slot':<16} {'Room':<8} {'Enrolled':>8} {'Capacity':>9}  {'Note'}"
    print(col)
    print("  " + "-" * 78)

    for r in sorted(schedule, key=lambda x: (x.get("time_slot", ""), x.get("class_id", ""))):
        slot = r.get("time_slot") or "N/A"
        room = r.get("room_id")   or "N/A"
        cap  = r.get("room_capacity") or "-"
        note = r.get("status", "")
        print(f"  {'Scheduled':<12} {r['class_id']:<12} {slot:<16} {room:<8} "
              f"{r.get('enrolled_students', r.get('enrolled', 0)):>8} {str(cap):>9}  {note}")

    for u in unscheduled:
        note = u.get("reason") or u.get("status") or "Unknown"
        print(f"  {'Unscheduled':<12} {u['class_id']:<12} {'N/A':<16} {'N/A':<8} "
              f"{u.get('enrolled_students', u.get('enrolled', 0)):>8} {'N/A':>9}  {note}")


def _print_stats(stats: dict, elapsed: float):
    placed = stats['placed']
    total  = stats['total_classes']
    waste  = stats.get('total_wasted_seats', 0)
    unsched= stats['unscheduled']
    pct    = 100 * placed / total if total else 0
    print(f"\n  Summary: {placed}/{total} classes placed ({pct:.1f}%)  |  "
          f"Unscheduled: {unsched}  |  Total wasted seats: {waste}  |  "
          f"Elapsed: {elapsed:.3f}s")


def run_stage1(data: dict) -> dict:
    _banner("STAGE 1 — GREEDY BASELINE")
    print("\n  Strategy : Sort classes by enrollment (largest first); assign first")
    print("             valid (time_slot, room) pair satisfying all hard constraints.\n")
    t0     = time.perf_counter()
    result = greedy_solver.run(data=data)
    elapsed= time.perf_counter() - t0
    _print_schedule(result["schedule"], result["unscheduled"])
    _print_stats(result["stats"], elapsed)
    return result


def run_stage2(data: dict) -> dict:
    _banner("STAGE 2 — CONFLICT GRAPH + WELSH–POWELL COLOURING")
    print("\n  Strategy : Build a conflict graph (edges = shared professor or student")
    print("             group). Apply Welsh–Powell colouring to assign time slots.")
    print("             Nodes coloured with the same colour share NO conflicts.\n")
    t0     = time.perf_counter()
    g_out  = graph_engine.run(data=data)
    elapsed= time.perf_counter() - t0
    gs     = g_out["graph_stats"]
    cr     = g_out["coloring_result"]

    print(f"  Conflict graph : {gs['nodes']} nodes, {gs['edges']} edges, "
          f"max_degree={gs['max_degree']}, avg_degree={gs['avg_degree']}")
    print(f"  Colours used   : {cr['colors_used']}  (available slots: {len(data['time_slots'])})")
    print(f"  Overflow       : {len(cr['overflow'])} class(es) without a slot\n")

    print(f"  {'Class':<12} {'Assigned Slot':<18} {'Degree':>6}")
    print("  " + "-" * 40)
    for cls in sorted(data["classes"], key=lambda c: c["class_id"]):
        cid  = cls["class_id"]
        slot = cr["coloring"].get(cid) or "OVERFLOW"
        deg  = len(g_out["graph"][cid])
        print(f"  {cid:<12} {slot:<18} {deg:>6}")

    print(f"\n  Elapsed: {elapsed:.3f}s")
    return g_out


def run_stage3(data: dict, graph_output: dict = None) -> dict:
    _banner("STAGE 3 — DP ROOM OPTIMIZER")
    print("\n  Strategy : Given the conflict-free time slots from Stage 2, assign")
    print("             rooms using bitmask DP to minimise total wasted capacity.\n")
    t0     = time.perf_counter()
    result = optimizer.run(graph_output=graph_output, data=data)
    elapsed= time.perf_counter() - t0
    _print_schedule(result["schedule"], result["unscheduled"])
    _print_stats(result["stats"], elapsed)
    return result


def run_stage4(data: dict) -> dict:
    _banner("STAGE 4 — BACKTRACKING (BEST-EFFORT)")
    print("\n  Strategy : Recursive backtracking with forward checking. Guarantees")
    print("             completeness; falls back to best partial solution if the")
    print("             problem is infeasible. Unplaced classes flagged for manual")
    print("             intervention.\n")
    t0     = time.perf_counter()
    result = backtracker.run(data=data)
    elapsed= time.perf_counter() - t0
    flag   = "[OK] COMPLETE" if result["complete"] else "[!] PARTIAL (best effort)"
    print(f"  Result: {flag}\n")
    _print_schedule(result["schedule"], result["unscheduled"])
    _print_stats(result["stats"], elapsed)
    return result



def _comparison_report(s1: dict, s3: dict, s4: dict):
    _banner("COMPARISON REPORT")
    total = s1["stats"]["total_classes"]
    rows  = [
        ("Stage 1 – Greedy",     s1["stats"]["placed"], s1["stats"]["unscheduled"],
         s1["stats"]["total_wasted_seats"]),
        ("Stage 2+3 – Graph+DP", s3["stats"]["placed"], s3["stats"]["unscheduled"],
         s3["stats"]["total_wasted_seats"]),
        ("Stage 4 – Backtrack",  s4["stats"]["placed"], s4["stats"]["unscheduled"],
         s4["stats"]["total_wasted_seats"]),
    ]
    print(f"\n  {'Algorithm':<26} {'Placed':>8} {'Unscheduled':>12} {'Wasted Seats':>14}")
    print("  " + "-" * 65)
    for name, placed, unsched, waste in rows:
        pct = 100 * placed / total if total else 0
        print(f"  {name:<26} {placed:>5}/{total:<3} ({pct:5.1f}%)  "
              f"{unsched:>8}       {waste:>10}")

    
    print("\n  Key observations:")
    print("  * Stage 2 graph colouring guarantees ZERO time-slot conflicts by")
    print("    construction - no two conflicting classes share a slot.")
    _diff = s1['stats']['total_wasted_seats'] - s3['stats']['total_wasted_seats']
    print("  * Stage 3 DP achieves globally optimal room assignment per slot.")
    if _diff >= 0:
        print(f"    Result: {_diff} fewer wasted seat(s) vs Stage 1 Greedy.")
    else:
        print(f"    Note: Stage 2 slot grouping caused {abs(_diff)} more wasted seat(s) vs Greedy;")
        print("    graph colouring bundles classes by conflict, not by room fit.")
    print("  * Stage 4 backtracking is the most thorough: it is complete and")
    print("    sound, but may be slower on very large inputs.")

 
    all_unscheduled = {u["class_id"]: u
                       for stage in (s1, s3, s4)
                       for u in stage.get("unscheduled", [])}

    if all_unscheduled:
        _banner("MANUAL FIX LOG - Classes Requiring Human Intervention")
        print("  The following classes could not be automatically scheduled.")
        print("  Recommended actions for the university manager:\n")
        for cid, u in sorted(all_unscheduled.items()):
            reason = u.get("reason") or u.get("status") or "See algorithm output"
            enrol  = u.get("enrolled_students") or u.get("enrolled") or "?"
            print(f"  [{cid}]  Enrolled: {enrol}")
            print(f"    Reason : {reason}")
            print(f"    Action : Consider splitting into two sections, moving to an")
            print(f"             evening slot, or booking an external venue.\n")
    else:
        print("\n  [OK] All classes were successfully scheduled - no manual fixes needed.")



def main():
    parser = argparse.ArgumentParser(description="Campus Puzzle Scheduler")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3, 4],
                        help="Run only a specific stage (default: all)")
    args = parser.parse_args()

    with open(DATA, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("\n" + HEADER)
    print("  CAMPUS PUZZLE – University Scheduling System")
    print(f"  Classes: {len(data['classes'])}  |  Rooms: {len(data['rooms'])}  |  "
          f"Time slots: {len(data['time_slots'])}  |  "
          f"Student groups: {len(data['student_groups'])}")
    print(HEADER)

    if args.stage == 1:
        run_stage1(data)
    elif args.stage == 2:
        run_stage2(data)
    elif args.stage == 3:
        g_out = graph_engine.run(data=data)
        run_stage3(data, graph_output=g_out)
    elif args.stage == 4:
        run_stage4(data)
    else:
        
        s1     = run_stage1(data)
        g_out  = run_stage2(data)
        s3     = run_stage3(data, graph_output=g_out)
        s4     = run_stage4(data)
        _comparison_report(s1, s3, s4)

    print("\n" + HEADER + "\n")


if __name__ == "__main__":
    main()