
import json
from collections import defaultdict
from typing import Optional


def load_data(path: str = "data/constraints.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)



def build_conflict_graph(classes: list[dict]) -> dict[str, set]:
  
    graph: dict[str, set] = {c["class_id"]: set() for c in classes}

    for i in range(len(classes)):
        for j in range(i + 1, len(classes)):
            ci, cj = classes[i], classes[j]
            conflict = False

            # Shared professor
            if ci["professor_id"] == cj["professor_id"]:
                conflict = True

            # Shared student group
            if not conflict:
                if set(ci["student_groups"]) & set(cj["student_groups"]):
                    conflict = True

            if conflict:
                graph[ci["class_id"]].add(cj["class_id"])
                graph[cj["class_id"]].add(ci["class_id"])

    return graph


def graph_stats(graph: dict[str, set]) -> dict:
    degrees = {node: len(neighbours) for node, neighbours in graph.items()}
    edges   = sum(degrees.values()) // 2
    return {
        "nodes":       len(graph),
        "edges":       edges,
        "max_degree":  max(degrees.values(), default=0),
        "avg_degree":  round(sum(degrees.values()) / max(len(graph), 1), 2),
    }



def welsh_powell(graph: dict[str, set], time_slots: list[str]) -> dict:


    
    nodes_sorted = sorted(graph.keys(), key=lambda n: len(graph[n]), reverse=True)

    color_assignment: dict[str, int] = {}   

    for node in nodes_sorted:
      
        neighbour_colors = {color_assignment[nb] for nb in graph[node]
                            if nb in color_assignment}
        
        color = 0
        while color in neighbour_colors:
            color += 1
        color_assignment[node] = color

    colors_used  = max(color_assignment.values(), default=-1) + 1


    color_map    = {c: time_slots[c] if c < len(time_slots) else None
                    for c in range(colors_used)}

    coloring   : dict[str, Optional[str]] = {}
    overflow   : list[str] = []

    for class_id, color in color_assignment.items():
        if color < len(time_slots):
            coloring[class_id] = time_slots[color]
        else:
            coloring[class_id] = None
            overflow.append(class_id)

    return {
        "coloring":    coloring,
        "overflow":    overflow,
        "colors_used": colors_used,
        "color_map":   color_map,
    }



def run(data: Optional[dict] = None, path: str = "data/constraints.json") -> dict:

    if data is None:
        data = load_data(path)

    classes    = data["classes"]
    time_slots = data["time_slots"]

    graph   = build_conflict_graph(classes)
    stats   = graph_stats(graph)
    result  = welsh_powell(graph, time_slots)

    return {
        "graph":           graph,
        "graph_stats":     stats,
        "coloring_result": result,
        "slot_assignment": result["coloring"],
        "classes":         classes,
        "time_slots":      time_slots,
        "rooms":           data["rooms"],
    }


if __name__ == "__main__":
    output = run()
    gs     = output["graph_stats"]
    cr     = output["coloring_result"]

    print("\n=== CONFLICT GRAPH ===")
    print(f"  Nodes (classes) : {gs['nodes']}")
    print(f"  Edges (conflicts): {gs['edges']}")
    print(f"  Max degree       : {gs['max_degree']}")
    print(f"  Avg degree       : {gs['avg_degree']}")

    print(f"\n=== WELSH–POWELL COLOURING ===")
    print(f"  Colours used (= distinct time slots needed): {cr['colors_used']}")
    print(f"  Available time slots                       : {len(output['time_slots'])}")
    print(f"  Overflow classes (no slot available)       : {len(cr['overflow'])}")

    print(f"\n{'Class':<14} {'Assigned Slot':<16} {'Degree':>6}")
    print("-" * 40)
    for cls in sorted(output["classes"], key=lambda c: c["class_id"]):
        cid    = cls["class_id"]
        slot   = cr["coloring"].get(cid, "OVERFLOW")
        degree = len(output["graph"][cid])
        print(f"  {cid:<12} {str(slot):<16} {degree:>6}")

    if cr["overflow"]:
        print(f"\n⚠  OVERFLOW: {cr['overflow']}")
        print("   These classes require additional time slots or manual intervention.")