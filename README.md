
# Campus Puzzle – University Scheduling System
<br><br>
Name : Seyedarmin Hosseinilargani
<br><br>
Student ID: GH1042143
<br><br><br>

This project address a real-world university course timetabling problem through a multi-stage algorithmic solution. 

---

##  Key Features

-   **4-Stage Optimization**: Hybrid approach using Greedy, Welsh–Powell, Bitmask DP, and DFS Backtracking.
-   **Conflict-Free Guarantee**: Stage 2 ensures zero professor or student-group overlaps via graph colouring.
-   **Resource Efficiency**: Stage 3 minimizes wasted seating capacity using optimal packing (DP).
-   **Exhaustive Search**: Stage 4 uses recursive backtracking with forward checking for 100% completeness.
  -   **Transparent Reporting**: Detailed per-class status logs and a "Manual Fix" system for impossible constraints.

---





###  Requirements
-   Python 3.10 or higher.
-   No external dependencies (Standard Library only).

###  Run the Full Suite
Execute all stages and see the comparison report:
```bash
py main.py
```

###  Run Specific Stages
```bash
py main.py --stage 1  # Baseline only
py main.py --stage 3  # Slot-based DP optimization
py main.py --stage 4  # Exhaustive search
```

---

##  Algorithmic Breakdown

| Stage | Algorithm | Responsibility | Complexity |
|---|---|---|---|
| **1** | **Greedy** | Instant "Good Enough" schedule | $O(C \times T \times R)$ |
| **2** | **Welsh–Powell** | Provably conflict-free time slots | $O(C^2)$ |
| **3** | **Bitmask DP** | Globally optimal room allocation | $O(S \times 2^R)$ |
| **4** | **Backtracking**| Guaranteed completeness / Best Effort | Exponential (Pruned) |

---

##  Repository Structure

-   `data/`: Contains `constraints.json` (the system's "database").
-   `src/`:
    -   `greedy_solver.py`: Stage 1 baseline.
    -   `graph_engine.py`: Graph construction and vertex colouring.
    -   `optimizer.py`: Bitmask DP implementation.
    -   `backtracker.py`: Recursive search with forward checking.
-   `main.py`: The central orchestrator and reporting engine.

---

##  Manual Fix Log
If the system detects a mathematically impossible constraint (e.g., more students than total campus capacity), it flags the specific class:
```text
[CS304]  Enrolled: 210
  Reason : No available room for this size in conflict-free slots.
  Action : Consider splitting class sections or booking external venues.
```

---
