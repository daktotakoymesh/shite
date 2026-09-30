# Grid pathfinding

`BP_GridManager.FindPath` contains the A* search in one Blueprint function,
organized into six comment boxes. It calls the existing
`GetWalkableNeighbors`, `GetTileSpeedMultiplier`, and `GetStepTravelTime` helpers.

## Calling FindPath

Inputs:

- `StartTile`, `GoalTile`: integer tile coordinates stored as Vector2D.
- `BaseMoveSpeed`: positive movement speed in Unreal units per second, before
  applying the terrain multiplier.

Outputs:

- `Success`: whether a route exists.
- `Path`: tile coordinates ordered from start to goal, **including both**.
  When start equals goal, this contains one tile. A movement follower should
  begin with element 1 after snapping to element 0.
- `TotalTravelTime`: estimated seconds along the route.

Failure returns false, an empty array, and zero time. Missing or blocked
endpoints and nonpositive movement speed/tile size are rejected. Shelves,
workstations, and other solid destinations will require an adjacent walkable
interaction tile as the goal.

## Costs and movement rules

The function respects `AllowDiagonalMovement`. Diagonals require the destination
and both orthogonal side tiles to be walkable. Ground resources and pawns do not
block this search unless their tiles are explicitly marked unwalkable.

Travel time charges half of each step at the source terrain speed and half at
the destination terrain speed. Diagonal steps are sqrt(2) times longer. Roads
are preferred when they actually make the route faster, including detours.

The heuristic uses octile distance for eight directions and Manhattan distance
for four, scaled by the fastest of the road and ground multipliers. This keeps
the estimate admissible and consistent with the step costs. Closed tiles can
therefore remain closed. All search arrays and scratch variables are local;
each invocation starts with empty arrays.

The open list is scanned for the minimum F score. This is a straightforward
Blueprint implementation for the current 20x20 grid; substantially larger maps
or many simultaneous requests may eventually need a priority queue or searches
spread over multiple frames. Call on a new destination or necessary reroute,
not every Tick.

The function only computes a route. Colonist movement, road speed changes while
following it, and rerouting after new construction are the next integration step.

## Verification

On 2026-09-29, the compiled Blueprint passed 59 checks: fixed cases, 32 seeded
random maps compared with independent Dijkstra search, and 20x20 cases including
an exhausted open list. Each returned route was also checked for legal steps,
corner clearance, cycles, endpoints, and agreement between reported and summed
travel time.

To rerun, start PIE or Simulate in the existing grid level, then run this in
Unreal's Cmd console (adjust the project path):

```text
py "D:/shite/Tests/Unreal/test_astar.py"
```

The script borrows a tile-data template from the play world, temporarily supplies
test maps to the Grid Manager class default object, and restores its original
properties in a finally block. It saves no assets. Results are written to
`Saved/Codex/astar_test_results.json`. Stop PIE when finished.
