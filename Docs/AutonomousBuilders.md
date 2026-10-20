# Autonomous builders — isolated project copy

Open **D:/shite-autonomous/shite.uproject** with Unreal Engine 5.8.2. The original project remains in **D:/shite**.

## Try it

1. The existing **Untitled** map opens automatically; press Play.
2. The copied map starts with two snowman colonists and two piles containing 30 building materials each.
3. Choose **Road**, **Building**, **Material Workbench**, or **Material Storage** in the existing building menu, then place it on the grid.
4. Workers reserve jobs, collect supplies, deliver them, and perform construction. Several colonists can haul to and build the same site from separate work positions. The orange construction appearance returns to the building's original materials when it finishes.
5. Press **T** to cycle simulation speed: **1× → 2× → 4× → 8× → 1×**. Each new Play session starts at 1×.
6. **B** still cancels the placement preview. Existing right-click manual movement is retained; it interrupts that worker's job, preserves supplies, and autonomous work resumes after the move.

A road costs **1** building material. The 2×2 building costs **6**. Workers carry **3** at a time. A site waits when supplies run out; adding another matching pile allows work to resume.

To add supplies in the editor, place **BP_ResourcePile** on the grid and edit **Resources → Amount** and **Resource Type**. Use the name **BuildingMaterial**. The test map's pile centers use Z=16 to rest above the grid. Piles have no collision and do not claim the building occupancy layer.

## Where the logic lives

| Blueprint | Responsibility |
| --- | --- |
| BP_JobManager | Discover construction sites, register configurable worker slots per site, recover abandoned assignments, and reserve the highest-priority reachable job. |
| BP_JobBase | Shared readiness, work-position, and work-execution contract. |
| BP_Job_Construction | Wait for delivered materials; supply safe construction positions; delegate labour to the building. |
| BP_Job_DeliverMaterials | Choose a matching finite pile, pick up a bounded load, travel to the site, and deliver it. |
| BP_Colonist | Own the assignment and inventory; request movement; handle its request ID; perform or advance the job; release cleanly on interruption. |
| BP_BuildingBase | Own material cost, delivered quantity, construction progress, and completed appearance. |
| BP_GridManager | Existing weighted eight-direction pathfinding, placement, work positions, and atomic safe completion. |
| BP_ResourcePile | Own resource type/quantity and expose walkable pickup positions on or beside its tile. |
| BP_ProductionStation | Configurable labour recipe, interior work positions, bounded output pile, and preserved partial progress. |
| BP_Job_Production | Advertise ready stations and delegate production labour through the same job contract. |

The gameplay is compiled Blueprint logic. Python files under **Tests/Unreal** and **Saved/Codex** are editor testing/authoring tools; gameplay does not require the Python bridge.

## Contracts to keep when extending it

- **EvaluateReadiness** returns Ready, Waiting, AlreadyComplete, or Invalid.
- **GetWorkTiles** returns legal positions for the current job stage.
- **PerformWork** returns **Finished**, **CanContinue**, and **NeedsTravel**. NeedsTravel allows a job to change its destination after pickup without hard-coding hauling into the worker.
- **JobKey + TargetActor** identify a worker slot at a site. Construction_0, Construction_1, and similar keys keep parallel assignments independent and deduplicated. Delivery has priority 60; construction has priority 50. Equal priority uses estimated travel time.
- Each slot belongs to one worker at a time; multiple slots may share a building. Builders add labour to the same WorkDone total. Completed sites invalidate the remaining assignments.
- **TryReserveWorker** is the assignment hook. Delivery reserves min(carry capacity, uncommitted site demand) before assignment returns. **GetUnreservedMaterialAmount** subtracts delivered and other haulers' committed quantities. Pickup rechecks both demand and pile quantity, then updates its claim to actual cargo. Delivery, cancellation, and worker destruction free those claims. This prevents over-delivery and duplicate supplies.
- Work positions are reserved before assignment returns and held during travel/work. BP_GridManager.IsWorkTileAvailable checks other workers' claimed, current, and incoming tiles. The worker owns HasWorkTileReservation + JobWorkTile; ReleaseJob clears the claim. Stage changes choose a new position and arrival rechecks availability. Workers choose another position or wait if none is free. This does not add movement collision or prevent pawns passing through one another.
- Request IDs prevent a cancelled old job from cancelling a newer manual movement command.
- Releasing a job drops carried resources at the worker's location. Destroying a carrier also drops them. Already delivered materials remain allocated to the site.
- Resource names are generic: a building requests one named resource, rather than a hard-coded global material counter. Food production, shelves, and other resource jobs can build on that contract later.

## Tuning

- Building: MaterialCost, RequiredResource, WorkRequired, **MaxConstructionWorkers**, **MaxDeliveryWorkers**. Both worker limits default to 4; set them on the building class before placing a site. Zero disables that work type. Available work positions and remaining material demand may reduce actual staffing.
- Colonist **Work**: AutoWork, CarryCapacity, WorkRate.
- Pile **Resources**: Amount, ResourceType.
- Existing BaseMoveSpeed remains 100 units/second; WorkRate is 1 labour unit/second. Keep carrying capacity positive.
- Set MaterialCost to zero for labour-only objects.

## Completion safety

Unfinished footprints remain walkable but reserved against overlapping placement. Solid completion validates every reserved cell and refuses to overlap a colonist's current tile, next tile, or diagonal transit clearance.

The current conservative escape rule requires every colonist to retain a cardinal route to a grid edge after a solid finishes. A building that would close the last exit waits with its progress preserved. Move the trapped colonist out or provide another opening. Roads are exempt because they remain walkable.

This is an explicit prototype policy, not a finished room/door system. Door-aware access and a designated safe-area policy can replace the single **HasExitAfterConstruction** check later.

## Scope and next work

This copy implements autonomous construction, finite resource hauling, production, solid storage shelves, and live click inspection. It does not yet implement food needs, beds, demolition/refunds, or persistent game saves. The original camera, building menu, pathfinding conventions, and snowman mesh are retained.

The registry discovers sites every 0.75 seconds. Selection compares paths for candidate work positions; this is aimed at the current small grid and small colony. Optimize candidate caching and registry indexing when scale warrants it, without changing the job contract.

New graphs retain horizontal execution chains with supporting data below. Completion and worker-update sections are labelled. Existing user-authored movement graphs were kept, with small entry-point connections added.

## Validation

Actual Blueprint tests cover:
- 59 weighted pathfinding cases, including diagonal/corner rules.
- 20 job registration and deduplication checks.
- 15 construction safety and scheduling checks.
- 20 live movement/construction recovery assertions.
- Finite-material transfer, shortage, concurrent hauling, wrong resource types, adjacent pickup, manual interruption, site destruction, and carrier destruction.

All **136** assertions passed. A fresh-editor smoke test also completed a road and a 2×2 building at the normal saved speed, consuming exactly 7 of 60 materials.

Final machine-readable results are recorded in **Tests/Unreal/Results/autonomous_builders_2026-10-19.json**. Test fixtures use disposable PIE worlds; material stress tests increase test-worker movement speed to keep the suite short. Production movement speed is unchanged.

To run the tests, start PIE and execute the corresponding file with Unreal's Python tools. Run one suite at a time; they deliberately reset the test play world. The asynchronous suites write progress under Saved/Codex and finish after their tick-driven scenarios. **test_job_registration.py** can run outside PIE. **BP_AutonomousTestHarness** is test support and has no gameplay references.

## Work-position reservation follow-up

The reservation fix passed 12 focused checks, including live shared-spot waiting, simultaneous builders on different tiles, release/destruction recovery, and reselection when a destination becomes occupied before arrival. The 15 construction and 22 material-delivery regression checks also passed. Results: **Tests/Unreal/Results/work_tile_reservations_2026-10-19.json**.

## Multiple workers per site

Sites now have configurable construction and delivery slots (4 of each by default). Idle workers can join the same site, with independent work-position and material-quantity reservations. Labour accumulates on the building; material delivery stops at its exact cost. Workers without a free position or uncommitted material demand wait or choose another site.

Equivalent slots at the same target, class, and priority share one candidate path search during each worker selection. This avoids multiplying expensive A* searches by the slot count. Job types grouped this way must advertise equivalent candidate positions for an idle worker.

Validated with **65 checks**: 16 shared-site cases, 15 construction checks, 22 material checks, and 12 work-position checks. See **Tests/Unreal/Results/multiworker_sites_2026-10-19.json**.

## Material production workbench

Choose **Material Workbench** in the building menu. It costs **6 building materials and 10 labour** to construct. The single static mesh forms a **П-shaped 3×3 table**, occupying seven cells. Its open front-middle cell leads to the interior work cell; both remain walkable after completion.

After construction, one colonist operates from the inner cell. Each **5 labour** produces a full batch of **2 BuildingMaterial**, stored in a normal resource pile on the front-right (lower-right in the footprint) counter. The default buffer holds **20**. Production waits when another whole batch will not fit, then resumes when builders collect stock. Workers yield after each batch, allowing higher-priority delivery (60) and construction (50) jobs to precede production (40). Partial labour survives interruption.

**BP_ProductionStation** is the reusable production class. Child buildings can change OutputResource, OutputPerBatch, ProductionWorkRequired, OutputCapacity, ProductionEnabled, MaxProductionWorkers, WorkTileOffsets, OutputTileOffset, ProductionMesh, and the inherited footprint/build cost/display name. MaxProductionWorkers must have enough distinct WorkTileOffsets to be useful. This table defaults to one interior position and one producer. OutputTileOffset defaults to **(2,0)** relative to the placement anchor; output rests 95 units above the grid origin.

Recipes currently consume labour only. Output is real inventory compatible with existing hauling. A changed output resource cannot mix with existing stock; empty the buffer first. Destroying the station leaves already-produced supplies in its pile. Demolition and clearing destroyed-building grid occupancy remain outside the existing prototype's scope.

Production passed **48 checks** (17 production, 15 construction, 16 shared-site), including construction funded entirely from table output. Results: **Tests/Unreal/Results/production_station_2026-10-19.json**. [Rendered preview](Images/material-workbench.png).

Geometry is saved as **Meshes/SM_ProductionTable_P**, with **M_ProductionWood**. Runtime gameplay uses ordinary Blueprint and static-mesh assets; Geometry Script was used only to author the mesh.

## Simulation speed

**T** cycles 1×, 2×, 4×, and 8×. BP_GridManager owns SimulationSpeed, SetSimulationSpeed, and CycleSimulationSpeed. The setter clamps the supported range and applies global time dilation, so movement, labour, job timers, and production accelerate together. BP_Cam receives the inverse rate through SetCameraSimulationRate, keeping camera movement and keyboard rotation at normal speed; mouse rotation and zoom remain unchanged. BeginPlay restores 1×.

All **14 speed/output checks passed**, including measured fourfold movement and production at 4×, and an end-to-end production, hauling, and construction run at 8× consuming the exact material cost. Results: **Tests/Unreal/Results/simulation_speed_2026-10-19.json**.

Camera independence passed two additional checks: measured camera movement was **1200 units per real second at both 1× and 8×**, and effective camera tick time stayed normal at all four speeds. Results: **Tests/Unreal/Results/camera_speed_2026-10-19.json**.

## Click inspection and names

Left-click an occupied grid tile when no placement preview is active. The upper-left inspector follows the selected object and refreshes its data automatically. Click empty ground to clear it. Placement retains priority while choosing a building, and clicking over the inspector does not place or select through the panel.

- Colonists: editable **ColonistName**, readable current job, activity, automatic-work state, carried resource/quantity/capacity, base movement speed, and work rate. New colonists receive names such as Milo 1 and Pip 2; a custom name is preserved.
- Loose stacks: resource and live quantity.
- Buildings: status, delivered/required materials, and completed/required construction labour.
- Workstations: production enabled/full/in-progress status, output inventory/capacity, batch size, and batch labour.
- Storage: accepted resource, inventory/capacity, delivery state, and hauling slots.

If several objects share a cell, selection prioritizes a colonist, then a nonempty resource stack, then the building. Selecting a shelf's inventory opens the shelf itself. Destroyed selections safely return to the help panel. The needs extension below also exposes nutrition and rest. Health is not simulated.

**WBP_Inspector** handles presentation. Each inspected actor supplies **GetInspectionText**; building children reuse **GetConstructionSummary** and extend it. Job labels are data in **BP_JobBase.JobDisplayName**, so new job types can provide readable labels without changing the UI. [Rendered inspector preview](Images/inspector-storage.png).

## Solid 2×2 storage

**Material Storage** costs **4 building materials and 8 labour**. Its four tiles become solid on completion. Workers use the eight exterior edge tiles, with existing work-position reservations preventing workers from standing on the same working tile.

Default capacity is **100 BuildingMaterial**, with **two storage-hauling slots**. Choose **Food** or **Building materials** in the live inspector when the shelf is empty and has no incoming claims. **AcceptedResource**, **StorageCapacity**, **MaxStorageWorkers**, and **StorageEnabled** are also available in BP_Stockpile defaults or a child class. The same system supports Food; a nonempty shelf rejects a changed incompatible filter until its old inventory is emptied.

Storage is an ordinary owned **BP_ResourcePile**, not a separate global resource counter. Builders can collect it using existing material-delivery jobs. Storage hauling has priority **30**, below material delivery (60), construction (50), and production (40). Workers gather loose piles and workstation output. They do not move inventory from one storage building to another, preventing transfer loops.

Capacity is reserved before a hauler accepts its job, rechecked at pickup, and updated to the actual load. Concurrent workers cannot overfill a shelf. Cancellation releases the capacity claim and uses the existing carried-resource drop behavior. Disabling a shelf stops new and in-flight deposits without destroying the worker's cargo; construction can still withdraw supplies.

The inventory pile is hidden while empty and visible after a deposit. Pickup access covers the shelf's perimeter. Shelf destruction retains already-stored resources, but the existing lack of demolition/grid cleanup still applies.

Implementation: **BP_Stockpile**, **BP_Job_StoreResource**, **Meshes/SM_StorageShelf**, the storage registration hook in **BP_JobManager**, and **BP_ResourcePile.StorageOwner**.

Validated with **28 inventory/inspection checks plus 4 display/menu checks**: concurrent bounded transfers, real autonomous production → storage → construction, food filtering, pause/cancellation, live inspection updates, safe destroyed selections, custom names, and automatic menu discovery. Reports: **Tests/Unreal/Results/inspection_storage_2026-10-19.json** and **inspection_storage_display_2026-10-19.json**.

The existing **17 production regression checks** also passed after these changes: **Tests/Unreal/Results/production_after_storage_2026-10-19.json**.

## Isolation

The copied editor's MCP endpoint is **http://127.0.0.1:8001/mcp**. The original retains its previous endpoint and configuration. Both folders contain a file named shite.uproject, so check the full path before opening.

A verified labour-only checkpoint is in **Saved/Codex/Backups/VerifiedLabourBuilders**. Saved/ is intentionally ignored by Git. The gameplay assets, source tests, config, and this guide live in ordinary project folders and should be included when committing the copy.

## Food, configurable storage and colonist needs

Click a stockpile and choose **Building materials** or **Food**. A change is rejected while inventory or incoming delivery claims remain, preserving the existing cargo and resource type. The inspector explains rejected changes. New stockpiles default to building materials.

Two labour-only food producers use the same production/hauling framework as the material workbench:

| Building | Footprint | Construction | Food per batch | Labour per batch | Output capacity |
|---|---|---|---|---|---|
| Food Garden | 3×3 П, seven occupied cells | 4 materials + 8 labour | 4 | 6 | 20 |
| Food Kitchen | 2×2 L, three occupied cells | 6 materials + 10 labour | 2 | 4 | 12 |

The kitchen's open front-right cell is its working position. The garden retains the workbench's interior working cell. Food is a real **Food** resource, with green resource-stack visuals; **BP_FoodPile** is a placeable food-stack preset. Production output, ground stacks and stockpiles all supply meals. **OutputHeight** lets production children place their stack on their own counter height.

Colonists have **Nutrition** and **Rest**, both from 0–100, shown in their inspector. Higher is better. Defaults start at 85; nutrition decreases by 0.08 per simulation second and rest by 0.04. A need activates at 30 and remains active until 90, avoiding constant task switching near the threshold. Needs continue during manual control. NeedsEnabled can explicitly suspend the subsystem. These rates follow simulation speed.

An activated need interrupts ordinary labour through the existing ReleaseJob path: work positions and material claims are freed, and uneaten carried resources are dropped safely. Personal need jobs have priority 150. Jobs belong to their colonist and cannot be claimed by others. If no reachable food exists, the worker can still perform ordinary work, including producing food, then retry eating. Manual movement retains its existing priority.

Eating picks up exactly one actual food item at a time. Each item provides up to **40 nutrition**, restored over time at **10 points per simulation second** on the ground. Consumed-but-not-yet-applied nutrition is retained on the personal need job across interruptions. Uneaten carried food returns to inventory through normal cancellation. No material stack can be eaten, and unrelated cargo cannot be overwritten. Hunger waits at zero without health damage in this version.

Sleeping requires no resource and restores **4 rest per simulation second** on the ground. The **Bed** (1×2, 3 materials + 6 labour) doubles recovery from its single adjacent use position. The **Dining Table** (2×1, 4 materials + 8 labour) doubles eating recovery and provides four adjacent use positions. Furniture remains solid. Colonists stand in their reserved use positions; there is no lying-down animation yet.

Workers prefer the closest available, reachable matching furniture within **8 seconds of base-speed path travel**, otherwise use their current ground tile. Reservations prevent simultaneous stationary use of the same position. Unfinished, destroyed, blocked or occupied furniture cannot grant its bonus. Distinct table positions support simultaneous meals. Completed needs release their jobs and reservations, allowing ordinary work to resume.

### Extension points

**BP_Job_Need** is a reusable persistent personal job and need state, with NeedName, Level, DecayPerSecond, TriggerLevel, SatisfiedLevel, RecoveryPerSecond, RequiredResource, NutritionPerItem, FurnitureKind and FurnitureSearchSeconds. Hunger and sleep are configured children **BP_Need_Hunger** and **BP_Need_Sleep**. Add compatible need classes to **BP_Colonist.NeedTypes**; the colonist constructs and registers its own instances. Needs use simulation seconds through **BP_JobBase.UsesSimulationSeconds**, independent of construction/production WorkRate.

**BP_NeedsFurniture** is an abstract building definition with FurnitureKind, RecoveryMultiplier, UseTileOffsets and FurnitureMesh. The bed and table are children. **ShowInBuildMenu** controls menu inclusion for reusable building definitions. New menu buttons use a compact font and an automatically sized bottom-anchored wrap panel.

Gameplay remains in saved Blueprint assets; Python is used only for authoring and tests. The original project is unchanged.

Validation: **72 checks passed** — 20 direct needs/resource/furniture cases, 7 autonomous needs scenarios, 17 existing production checks and 28 existing storage/inspection checks. Reports are in **Tests/Unreal/Results/colonist_needs_2026-10-19.json**, **production_after_needs_2026-10-19.json**, and **storage_after_needs_2026-10-19.json**. Run **Tests/Unreal/test_colonist_needs.py** in a disposable play world to repeat the new suite.

Verified UMG renders: [Food stockpile controls](Images/food-stockpile-inspector.png) and [Colonist needs](Images/colonist-needs-inspector.png).


## Placement rotation, walls, and road-queue stability

Press **R** while placing a building to turn it 90 degrees. Rotation keeps the footprint normalized to its lower-left grid anchor. The current orientation carries into subsequent placements, including Shift-repeat placement and a newly selected building. With no active ghost, R does nothing.

Rotation updates the actual occupied cells and mesh together. Production work positions and output cells, bed/table use positions, and the stockpile's initial inventory cell rotate with the building. Placement bounds and overlap validation use the rotated footprint. Placed buildings keep their orientation; this is placement rotation, not relocation of completed structures.

The automatic menu includes **Wall**, a solid **1x1** building costing **2 building materials + 4 labour**. Like other solid structures, an unfinished wall reserves placement space while remaining walkable. Safe completion blocks its cell and uses the existing occupied-tile and escape checks.

The large-road-queue fix has two parts:
- **BP_GridManager.BuildTravelField** computes weighted travel costs once for the worker's job search. **GetTravelCost** reuses that scoped field, falling back to FindPath outside it. Actual movement still uses the existing eight-direction pathfinder. Road bonuses and diagonal corner restrictions are unchanged.
- **BP_JobManager.JobIndex** maps building/colonist identity plus job-slot key to an existing job. Site registration uses this lookup instead of repeatedly looping over every active job. RefreshJobs rebuilds the index and removes terminal or destroyed-target entries from ActiveJobs.

The engine's default loop limit remains unchanged. The stress scenario placed 100 roads, created 800 job slots, and let four autonomous workers deliver real materials and finish all roads. Their movement/work rates were accelerated in the disposable test world; gameplay defaults were not changed.

### Extending rotation

A new building child inherits footprint and BuildingMesh rotation automatically. If it adds other tile-relative interaction data, override **RotateAdditionalOffsets(TileShift)** and apply **(x, y) -> (-y, x) + TileShift**. Return Changed=true when specialized offsets are updated. Production and furniture children already inherit suitable implementations. **BP_Stockpile.StoredTileOffset** is the rotatable initial inventory cell, defaulting to (0,0).

Repeatable checks: **Tests/Unreal/test_placement_rotation.py** and **test_road_queue_stress.py**, run in a disposable PIE world. Reports accompany the other regression results under **Tests/Unreal/Results**.

Validation for rotation/walls: 13 rotation cases, 25 rotated-operation/menu cases, 12 weighted-route comparisons, 5 registry checks, invalid-input checks, the 100-road/four-worker stress scenario, and all 72 production/storage/needs regression checks passed. Consolidated report: **Tests/Unreal/Results/rotation_walls_road_queue_2026-10-19.json**. All 119 baseline original-project file hashes remain unchanged.
