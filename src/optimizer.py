

import json
import math
from typing import Optional


def load_data(path: str = "data/constraints.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)



def _dp_assign_slot(classes_in_slot: list[dict], rooms: list[dict]) -> list[dict]:

    n_rooms = len(rooms)
    n_cls   = len(classes_in_slot)

    INF = math.inf



    full   = (1 << n_rooms)

    prev_dp = [INF] * full
    prev_dp[0] = 0

    parent_table = [[None] * full for _ in range(n_cls)]

    for i, cls in enumerate(classes_in_slot):
        enrol  = cls["enrolled_students"]
        cur_dp = [INF] * full

        for mask in range(full):
            if prev_dp[mask] == INF:
                continue
       
            for j in range(n_rooms):
                if mask & (1 << j):
                    continue                   # room already used
                if rooms[j]["capacity"] < enrol:
                    continue                   # room too small
                new_mask = mask | (1 << j)
                waste    = rooms[j]["capacity"] - enrol
                cost     = prev_dp[mask] + waste
                if cost < cur_dp[new_mask]:
                    cur_dp[new_mask]        = cost
                    parent_table[i][new_mask] = (mask, j)

        prev_dp = cur_dp

  
    best_mask = min(range(full), key=lambda m: prev_dp[m])

    if prev_dp[best_mask] == INF:
        
        assignment = {}
        used_rooms: set = set()
        for i, cls in enumerate(classes_in_slot):
            enrol = cls["enrolled_students"]
            for j, room in enumerate(rooms):
                if j not in used_rooms and room["capacity"] >= enrol:
                    assignment[i] = j
                    used_rooms.add(j)
                    break
    else:
      
        assignment = {}  
        mask = best_mask
        for i in range(n_cls - 1, -1, -1):
            entry = parent_table[i][mask]
            if entry is None:
                break
            prev_mask, room_idx = entry
            assignment[i] = room_idx
            mask = prev_mask

    result = []
    for i, cls in enumerate(classes_in_slot):
        if i in assignment:
            room  = rooms[assignment[i]]
            waste = room["capacity"] - cls["enrolled_students"]
            result.append(dict(
                cls,
                room_id      = room["room_id"],
                room_capacity= room["capacity"],
                wasted_seats = waste,
                status       = "Perfect Fit" if waste == 0 else f"Wasted {waste} seats",
            ))
        else:
            result.append(dict(cls, room_id=None, room_capacity=None,
                               wasted_seats=None, status="No room available"))
    return result




def run(graph_output: Optional[dict] = None,
        data: Optional[dict] = None,
        path: str = "data/constraints.json") -> dict:

    if data is None:
        data = load_data(path)

    
    if graph_output is None:
        import sys, os
        sys.path.insert(0, os.path.dirname(__file__))
        import graph_engine
        graph_output = graph_engine.run(data=data)

    slot_assignment = graph_output["slot_assignment"]   
    classes         = graph_output["classes"]
    rooms           = sorted(data["rooms"], key=lambda r: r["capacity"])

    
    slot_to_classes: dict[str, list] = {}
    unscheduled = []

    for cls in classes:
        slot = slot_assignment.get(cls["class_id"])
        if slot is None:
            unscheduled.append(dict(cls, time_slot=None, room_id=None,
                                    wasted_seats=None,
                                    status="No time slot (graph overflow)"))
        else:
            slot_to_classes.setdefault(slot, []).append(dict(cls, time_slot=slot))


    schedule = []
    for slot, cls_list in slot_to_classes.items():
        assigned = _dp_assign_slot(cls_list, rooms)
        for rec in assigned:
            if rec["room_id"] is None:
                unscheduled.append(rec)
            else:
                schedule.append(rec)

    total_waste = sum(r["wasted_seats"] for r in schedule
                      if r["wasted_seats"] is not None)

    return {
        "schedule":    schedule,
        "unscheduled": unscheduled,
        "stats": {
            "total_classes":      len(classes),
            "placed":             len(schedule),
            "unscheduled":        len(unscheduled),
            "total_wasted_seats": total_waste,
        },
    }


if __name__ == "__main__":
    result = run()
    print("\n=== DP ROOM OPTIMIZER RESULTS ===")
    print(f"Placed:       {result['stats']['placed']} / {result['stats']['total_classes']}")
    print(f"Unscheduled:  {result['stats']['unscheduled']}")
    print(f"Total waste:  {result['stats']['total_wasted_seats']} seats\n")

    print(f"{'Class':<12} {'Time Slot':<14} {'Room':<8} {'Enrolled':>8} {'Capacity':>8} {'Status'}")
    print("-" * 72)
    for r in sorted(result["schedule"], key=lambda x: (x["time_slot"], x["class_id"])):
        print(f"{r['class_id']:<12} {r['time_slot']:<14} {r['room_id']:<8} "
              f"{r['enrolled_students']:>8} {r['room_capacity']:>8}  {r['status']}")

    if result["unscheduled"]:
        print("\n--- UNSCHEDULED ---")
        for u in result["unscheduled"]:
            print(f"  {u['class_id']:<12}  {u['status']}")