
import json
import sys
import os
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))


def load_data(path: str = "data/constraints.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _is_valid(cls: dict, slot: str, room: dict,
              room_booked: dict, prof_booked: dict, group_booked: dict) -> bool:
    """Return True iff placing cls in (slot, room) violates no hard constraint."""
    if room["capacity"] < cls["enrolled_students"]:
        return False
    if slot in room_booked.get(room["room_id"], set()):
        return False
    if slot in prof_booked.get(cls["professor_id"], set()):
        return False
    if any(slot in group_booked.get(g, set()) for g in cls["student_groups"]):
        return False
    return True


def _has_any_option(cls: dict, time_slots: list, rooms: list,
                    room_booked: dict, prof_booked: dict, group_booked: dict) -> bool:
    """Forward-checking probe: does cls have at least one valid (slot, room)?"""
    for slot in time_slots:
        for room in rooms:
            if _is_valid(cls, slot, room, room_booked, prof_booked, group_booked):
                return True
    return False


class _Backtracker:
    def __init__(self, classes, time_slots, rooms, time_limit_s: float = 10.0):
        self.classes      = classes
        self.time_slots   = time_slots
        self.rooms        = sorted(rooms, key=lambda r: r["capacity"])
        self.best         = []        
        self.best_count   = 0
        self.time_limit_s = time_limit_s
        self._deadline    = None

    def solve(self):
        import time as _time
        self._deadline = _time.perf_counter() + self.time_limit_s
        room_booked  = {r["room_id"]: set() for r in self.rooms}
        prof_booked  : dict[str, set] = {}
        group_booked : dict[str, set] = {}
        self._recurse(0, [], room_booked, prof_booked, group_booked)

    def _recurse(self, idx: int, current: list,
                 room_booked, prof_booked, group_booked):
        import time as _time
      
        if _time.perf_counter() >= self._deadline:
            return
       
        if len(current) > self.best_count:
            self.best       = list(current)
            self.best_count = len(current)

        if idx == len(self.classes):
            return   

        cls = self.classes[idx]

        placed = False
        for slot in self.time_slots:
          
            if slot in prof_booked.get(cls["professor_id"], set()):
                continue
            if any(slot in group_booked.get(g, set()) for g in cls["student_groups"]):
                continue

            for room in self.rooms:
                if not _is_valid(cls, slot, room, room_booked, prof_booked, group_booked):
                    continue

           
                waste = room["capacity"] - cls["enrolled_students"]
                record = dict(
                    cls,
                    time_slot     = slot,
                    room_id       = room["room_id"],
                    room_capacity = room["capacity"],
                    wasted_seats  = waste,
                    status        = "Perfect Fit" if waste == 0 else f"Wasted {waste} seats",
                )
                current.append(record)
                room_booked[room["room_id"]].add(slot)
                prof_booked.setdefault(cls["professor_id"], set()).add(slot)
                for g in cls["student_groups"]:
                    group_booked.setdefault(g, set()).add(slot)

             
                lookahead = min(5, len(self.classes) - idx - 1)
                forward_ok = all(
                    _has_any_option(self.classes[k], self.time_slots, self.rooms,
                                    room_booked, prof_booked, group_booked)
                    for k in range(idx + 1, idx + 1 + lookahead)
                )

                if forward_ok:
                    self._recurse(idx + 1, current,
                                  room_booked, prof_booked, group_booked)

                
                current.pop()
                room_booked[room["room_id"]].discard(slot)
                prof_booked[cls["professor_id"]].discard(slot)
                for g in cls["student_groups"]:
                    group_booked[g].discard(slot)

        if self.best_count == len(self.classes):
            return




def run(data: Optional[dict] = None, path: str = "data/constraints.json") -> dict:

    if data is None:
        data = load_data(path)

    classes    = data["classes"]
    time_slots = data["time_slots"]
    rooms      = data["rooms"]

   
    sorted_classes = sorted(classes, key=lambda c: c["enrolled_students"], reverse=True)

    time_limit = 10.0   
    bt = _Backtracker(sorted_classes, time_slots, rooms, time_limit_s=time_limit)
    bt.solve()

    placed_ids = {r["class_id"] for r in bt.best}
    unscheduled = []
    for cls in classes:
        if cls["class_id"] not in placed_ids:
            unscheduled.append(dict(
                cls,
                time_slot    = None,
                room_id      = None,
                wasted_seats = None,
                status       = "Unscheduled – requires manual intervention",
                reason       = ("Search timed out before placing this class; "
                               "try increasing time_limit_s or use Stage 2+3 result"),
            ))

    total_waste = sum(r["wasted_seats"] for r in bt.best if r["wasted_seats"] is not None)

    return {
        "schedule":    bt.best,
        "unscheduled": unscheduled,
        "complete":    len(unscheduled) == 0,
        "stats": {
            "total_classes":      len(classes),
            "placed":             len(bt.best),
            "unscheduled":        len(unscheduled),
            "total_wasted_seats": total_waste,
        },
    }


if __name__ == "__main__":
    result = run()
    print("\n=== BACKTRACKING SOLVER RESULTS ===")
    print(f"Complete solution : {'YES [OK]' if result['complete'] else 'NO - best effort'}")
    print(f"Placed            : {result['stats']['placed']} / {result['stats']['total_classes']}")
    print(f"Unscheduled       : {result['stats']['unscheduled']}")
    print(f"Total waste       : {result['stats']['total_wasted_seats']} seats\n")

    print(f"{'Class':<12} {'Time Slot':<14} {'Room':<8} {'Enrolled':>8} {'Capacity':>8} {'Status'}")
    print("-" * 72)
    for r in sorted(result["schedule"], key=lambda x: (x["time_slot"], x["class_id"])):
        print(f"{r['class_id']:<12} {r['time_slot']:<14} {r['room_id']:<8} "
              f"{r['enrolled_students']:>8} {r['room_capacity']:>8}  {r['status']}")

    if result["unscheduled"]:
        print("\n--- ⚠  UNSCHEDULED (Manual Intervention Required) ---")
        for u in result["unscheduled"]:
            print(f"  {u['class_id']:<12}  {u.get('reason', u['status'])}")