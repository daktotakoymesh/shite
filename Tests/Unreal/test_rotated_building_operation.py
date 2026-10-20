"""Rotated production output, furniture access and storage inventory checks. Run in disposable PIE."""
import unreal,json
from pathlib import Path
ROOT=Path(unreal.Paths.project_dir())
fixture=(ROOT/"Tests/Unreal/test_autonomous_builders.py").read_text()
exec(fixture[:fixture.index("def unfinished():")],globals())

operation_results=[]
for turn in range(4):
 for bn in ['BP_ProductionStation','BP_FoodGarden','BP_FoodKitchen','BP_Bed','BP_DiningTable','BP_Stockpile']:
  reset();setp('Bool',worker,'NeedsEnabled',False);setp('Int',gm,'PlacementQuarterTurns',turn)
  b=place(bn,5,5);finish_ready(b);check(gm.call_method('TryCompleteConstruction',(b,)),(bn,turn,'completion'))
  anchor=b.get_editor_property('AnchorTIle')
  if bn in ['BP_ProductionStation','BP_FoodGarden','BP_FoodKitchen']:
   positions=list(b.call_method('GetProductionWorkTiles',(gm,)))
   check(positions,'No rotated work position');tile(worker,int(positions[0].x),int(positions[0].y))
   done,cont=b.call_method('WorkOnProduction',(worker,gm,float(b.get_editor_property('ProductionWorkRequired'))))
   check(done and cont,(bn,turn,'production'))
   pile=b.get_editor_property('OutputPile');offset=b.get_editor_property('OutputTileOffset')
   expected=gm.call_method('GetTileCenter',(anchor+offset,));actual=pile.get_actor_location()
   check(abs(actual.x-expected.x)<.001 and abs(actual.y-expected.y)<.001,(bn,turn,'output position'))
   check(pile.get_editor_property('Amount')==b.get_editor_property('OutputPerBatch'))
  elif bn=='BP_Stockpile':
   pile=b.call_method('EnsureStoredPile',(gm,));offset=b.get_editor_property('StoredTileOffset')
   expected=gm.call_method('GetTileCenter',(anchor+offset,));actual=pile.get_actor_location()
   check(abs(actual.x-expected.x)<.001 and abs(actual.y-expected.y)<.001,('stockpile',turn))
   check(len(pile.call_method('GetPickupTiles',(gm,)))==8)
  else:
   positions=list(b.call_method('GetUseTiles',(gm,)))
   check(len(positions)==(1 if bn=='BP_Bed' else 4))
   check(all(gm.call_method('IsTileWalkable',(p,)) for p in positions))
  operation_results.append(bn+' operates after '+str(turn*90)+' degree placement')
lib=unreal.get_default_object(unreal.load_class(None,'/Script/UMG.WidgetBlueprintLibrary'))
entries=lib.call_method('GetAllWidgetsOfClass',(world,cls('WBP_BuildEntry'),False))
check(sum(w.get_editor_property('BuildingClass')==cls('BP_Wall') for w in entries)==1,'Wall missing from automatic menu')
operation_results.append('Wall appears exactly once in automatic menu')
reset();setp('Int',gm,'PlacementQuarterTurns',0)

(ROOT/"Saved/Codex/rotated_building_operation.json").write_text(json.dumps(operation_results,indent=2))
