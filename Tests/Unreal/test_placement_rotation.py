"""Run inside a disposable PIE world. Checks rotated footprints, visuals, interaction offsets and wall completion."""
import unreal,json
from pathlib import Path
ROOT=Path(unreal.Paths.project_dir())
fixture=(ROOT/"Tests/Unreal/test_autonomous_builders.py").read_text()
exec(fixture[:fixture.index("def unfinished():")],globals())

reset()
setp('Bool',worker,'NeedsEnabled',False)
results=[]
def coords(a):return [(round(p.x,6),round(p.y,6)) for p in a]
for bn in ['BP_Road','BP_Building_Dummy2x2','BP_ProductionStation','BP_FoodGarden','BP_FoodKitchen','BP_Bed','BP_DiningTable','BP_Stockpile','BP_Wall']:
 setp('Int',gm,'PlacementQuarterTurns',0)
 gm.call_method('StartPlacement',(cls(bn),));b=gm.get_editor_property('CurrentGhostBuilding')
 original=coords(b.get_editor_property('FootprintOffsets'))
 arrays=['FootprintOffsets']
 if bn in ['BP_ProductionStation','BP_FoodGarden','BP_FoodKitchen']:arrays+=['WorkTileOffsets']
 if bn in ['BP_Bed','BP_DiningTable']:arrays+=['UseTileOffsets']
 singles=['OutputTileOffset'] if bn in ['BP_ProductionStation','BP_FoodGarden','BP_FoodKitchen'] else ['StoredTileOffset'] if bn=='BP_Stockpile' else []
 expected={n:coords(b.get_editor_property(n)) for n in arrays}
 expected.update({n:coords([b.get_editor_property(n)]) for n in singles})
 mesh=b.get_editor_property('BuildingMesh');originaltr=mesh.get_relative_transform()
 for turn in range(4):
  shape=expected['FootprintOffsets'];mx=max(y for x,y in shape);mn=min(x for x,y in shape)
  for n,pts in expected.items():expected[n]=[(-y+mx,x-mn) for x,y in pts]
  prior=mesh.get_relative_transform().translation
  gm.call_method('RotateCurrentPlacement',())
  for n in arrays:check(coords(b.get_editor_property(n))==expected[n],(bn,turn,n,expected[n],coords(b.get_editor_property(n))))
  for n in singles:check(coords([b.get_editor_property(n)])==expected[n],(bn,turn,n))
  now=mesh.get_relative_transform().translation
  check(abs(now.x-(-prior.y+(mx+1)*100))<.001 and abs(now.y-(prior.x-mn*100))<.001,(bn,turn,'mesh translation',now,prior))
  check(b.get_editor_property('PlacementQuarterTurns')==(turn+1)%4)
 check(coords(b.get_editor_property('FootprintOffsets'))==original)
 now=mesh.get_relative_transform()
 check((now.translation-originaltr.translation).length()<.001,(bn,'four turns drift'))
 gm.call_method('CancelPlacement',());results.append(bn+' four rotations: shape, mesh, interaction and output offsets')
# No ghost: rotation is a harmless no-op.
gm.call_method('RotateCurrentPlacement',());check(gm.get_editor_property('CurrentGhostBuilding') is None)
# Remembered orientation is applied on a fresh ghost, including repeated placement.
setp('Int',gm,'PlacementQuarterTurns',1);gm.call_method('StartPlacement',(cls('BP_Bed'),));b=gm.get_editor_property('CurrentGhostBuilding')
check(coords(b.get_editor_property('FootprintOffsets'))==[(1,0),(0,0)])
check(b.get_editor_property('PlacementQuarterTurns')==1);gm.call_method('CancelPlacement',())
# Edge validation uses the rotated footprint.
setp('Int',gm,'PlacementQuarterTurns',0);gm.call_method('StartPlacement',(cls('BP_Bed'),));b=gm.get_editor_property('CurrentGhostBuilding')
check(gm.call_method('CheckFootprint',(v(19,18),b.get_editor_property('FootprintOffsets')))[-1])
gm.call_method('RotateCurrentPlacement',())
check(not gm.call_method('CheckFootprint',(v(19,18),b.get_editor_property('FootprintOffsets')))[-1])
gm.call_method('CancelPlacement',());setp('Int',gm,'PlacementQuarterTurns',0)
# Actual wall construction occupies one cell, stays walkable until finished, then blocks movement.
wall=place('BP_Wall',5,5)
check(coords(wall.get_editor_property('FootprintOffsets'))==[(0,0)])
check(gm.call_method('IsTileWalkable',(v(5,5),)))
check(not gm.call_method('CheckFootprint',(v(5,5),[v(0,0)]))[-1])
finish_ready(wall);check(gm.call_method('TryCompleteConstruction',(wall,)))
check(not gm.call_method('IsTileWalkable',(v(5,5),)))
success,path,cost=gm.call_method('FindPath',(v(4,5),v(6,5),100.));check(success and v(5,5) not in path)
results+=['No-ghost rotation safe','Orientation persists across new placement','Rotated edge validation','Wall construction and path detour']

(ROOT/"Saved/Codex/rotation_static_results.json").write_text(json.dumps(results,indent=2))
