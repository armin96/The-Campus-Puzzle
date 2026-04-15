
import json
from typing import Optional


def load_data(path: str = "data/constraints.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run(data: Optional[dict] = None, path: str = "data/constraints.json") -> dict:

    if data is None:
        data = load_data(path)

    time_slots = data["time_slots"]
    rooms      = sorted(data["rooms"], key=lambda r: r["capacity"])
    classes    = data["classes"]

    
    sorted_classes = sorted(classes, key=lambda c: c["enrolled_students"], reverse=True)

    #State tracking
    room_booked: dict[str, set] = {r["room_id"]: set() for r in rooms}  
    prof_booked: dict[str, set] = {}                                       
    group_booked: dict[str, set] = {}                                     

    schedule     = []
    unscheduled  = []

    for cls in sorted_classes:
        placed = False
        cid    = cls["class_id"]
        enrol  = cls["enrolled_students"]
        prof   = cls["professor_id"]
        groups = cls["student_groups"]

        for slot in time_slots:
            
            if slot in prof_booked.get(prof, set()):
                continue

          
            group_conflict = any(slot in group_booked.get(g, set()) for g in groups)
            if group_conflict:
                continue

           
            for room in rooms:
                if room["capacity"] < enrol:
                    continue                        # room too small
                if slot in room_booked[room["room_id"]]:
                    continue                        # room already taken

                
                waste = room["capacity"] - enrol

           
                room_booked[room["room_id"]].add(slot)
                prof_booked.setdefault(prof, set()).add(slot)
                for g in groups:
                    group_booked.setdefault(g, set()).add(slot)

                schedule.append({
                    "class_id":         cid,
                    "name":             cls["name"],
                    "professor_id":     prof,
                    "enrolled_students": enrol,
                    "student_groups":   groups,
                    "time_slot":        slot,
                    "room_id":          room["room_id"],
                    "room_capacity":    room["capacity"],
                    "wasted_seats":     waste,
                    "status":           "Perfect Fit" if waste == 0 else f"Wasted {waste} seats",
                })
                placed = True
                break

            if placed:
                break

        if not placed:
            unscheduled.append({
                "class_id":       cid,
                "name":           cls["name"],
                "enrolled":       enrol,
                "student_groups": groups,
                "professor_id":   prof,
                "reason":         _diagnose(cls, time_slots, room_booked, prof_booked,
                                            group_booked, rooms),
            })

    total_waste = sum(r["wasted_seats"] for r in schedule)

    return {
        "schedule":    schedule,
        "unscheduled": unscheduled,
        "stats": {
            "total_classes":     len(classes),
            "placed":            len(schedule),
            "unscheduled":       len(unscheduled),
            "total_wasted_seats": total_waste,
        },
    }


def _diagnose(cls, time_slots, room_booked, prof_booked, group_booked, rooms) -> str:
    """Produce a human-readable reason why this class could not be placed."""
    enrol  = cls["enrolled_students"]
    prof   = cls["professor_id"]
    groups = cls["student_groups"]

    eligible_rooms = [r for r in rooms if r["capacity"] >= enrol]
    if not eligible_rooms:
        return f"No room with capacity >= {enrol}"

    for slot in time_slots:
        if slot in prof_booked.get(prof, set()):
            continue
        if any(slot in group_booked.get(g, set()) for g in groups):
            continue
        
        return "No available room in any conflict-free time slot"

    return "Professor or student-group conflict blocks every time slot"


if __name__ == "__main__":
    result = run()
    print("\n=== GREEDY SOLVER RESULTS ===")
    print(f"Placed:       {result['stats']['placed']} / {result['stats']['total_classes']}")
    print(f"Unscheduled:  {result['stats']['unscheduled']}")
    print(f"Total waste:  {result['stats']['total_wasted_seats']} seats\n")

    print(f"{'Class':<12} {'Time Slot':<14} {'Room':<8} {'Enrolled':>8} {'Capacity':>8} {'Status'}")
    print("-" * 72)
    for r in result["schedule"]:
        print(f"{r['class_id']:<12} {r['time_slot']:<14} {r['room_id']:<8} "
              f"{r['enrolled_students']:>8} {r['room_capacity']:>8}  {r['status']}")

    if result["unscheduled"]:
        print("\n--- UNSCHEDULED ---")
        for u in result["unscheduled"]:
            print(f"  {u['class_id']:<12} {u['enrolled']:>4} students  Reason: {u['reason']}")