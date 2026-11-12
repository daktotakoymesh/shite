# Visual polish

Open `shite.uproject` from the repository root.

GitHub branch: `shite1.1`.

## Scene

- Grass material with subtle world-space variation and support for instanced grid tiles.
- Tile gaps reduced from 5 cm to 0.8 cm; grid coordinates and footprints are unchanged.
- Stone-gray roads, a soil base under the playable board, and a procedural cloudy sky dome.
- Fixed exposure, softer sunlight, and a camera starting at `(900,1000,60)` with a 3100-unit arm and -55-degree pitch. Camera movement and simulation speed remain independent.
- Scene actors and their components are marked modified before saving their external actor packages. The final camera, materials and transforms were checked after reopening the saved level.

## Actors and interface

- The snowman retains the same geometry with separate snow, hat, eyes, carrot and wood materials.
- Beds, gardens and kitchens use styled mesh copies. Resource piles have recognizable timber bundles and food crates.
- Colonists have optional body motion, carried-resource visuals, work feedback and eating/sleeping indicators.
- Buildings have short completion feedback and production activity indicators.
- One optional selection outline; added presentation meshes do not block collision or navigation.
- Charcoal building buttons and inspector, warm-white text and amber meters. The inspector displays construction materials/labour, production/output, storage, and colonist needs.
- A selected-object label and live simulation-speed readout. Keyboard hints: `T` speed, `R` rotation, `B` placement cancellation. The old simulation-speed PrintString no longer overlaps the inspector.

## Validation

- 9 UI checks passed, including live needs, construction, production, storage filters, resource stacks, selection, zero-cost/clamped meters, gameplay-state preservation and simulation-speed text.
- 13 placement/rotation checks passed, including all nine building types, repeated orientation, map-edge rejection, wall completion and path detouring.
- Earlier presentation checks covered colonist, resource and building effects; production and needs regressions also passed.
- SHA-256 comparison of all 184 baseline source-project files found no changes.
- Final gameplay screenshot: `Docs/Images/visual-polish-preview.png`.

The screenshot uses a temporary colony assembled in Play In Editor for visual verification. Those buildings were not saved into the level. Starting Play normally still starts from the project's existing initial colony.

## Main presentation assets

New materials and styled mesh copies are under `/Game/Visual`. `MV_Ground` controls grass; `MV_Sky` controls sky colors, cloud scale, opacity and brightness. `Visual_Grade` is the level's post-process volume. Existing gameplay buildings, job logic and grid data retain their original asset paths.

Presentation behavior is concentrated in `UpdatePresentation` on colonists, resources and buildings, `UpdateSelectionPresentation` on the grid manager, and the `UI_` functions on `WBP_Inspector`. Presentation enable flags allow effects to be disabled without changing simulation state.
