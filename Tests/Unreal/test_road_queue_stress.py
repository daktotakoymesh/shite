"""Run inside a disposable PIE world. Places 100 roads and drives four real builders."""
import unreal,json,time,traceback
from pathlib import Path
ROOT=Path(unreal.Paths.project_dir())
fixture=(ROOT/"Tests/Unreal/test_autonomous_builders.py").read_text()
exec(fixture[:fixture.index("def unfinished():")],globals())

reset();setp('Int',gm,'PlacementQuarterTurns',0)
for w in actors('BP_Colonist'):setp('Bool',w,'NeedsEnabled',False)
roads=[place('BP_Road',x,y,True) for x in range(5,15) for y in range(5,15)]
pile=spawn('BP_ResourcePile',3,3);setp('Int',pile,'Amount',1000)
workers=[worker,spawn('BP_Colonist',2,3),spawn('BP_Colonist',3,2),spawn('BP_Colonist',3,4)]
for w in workers:setp('Bool',w,'AutoWork',False);setp('Bool',w,'NeedsEnabled',False)
manager.call_method('RefreshJobs',())
import time
started=time.perf_counter();selected=manager.call_method('FindJobForWorker',(worker,));elapsed=time.perf_counter()-started
check(selected[0] is not None,'No job selected in 100-road stress test')
check(not gm.get_editor_property('TravelFieldActive'),'Scoped field leaked out of selection')
setp('Object',worker,'CurrentJob',selected[0]);worker.call_method('ReleaseJob',())
stress={'roads':len(roads),'jobs':len(manager.get_editor_property('ActiveJobs')),'selection_seconds':elapsed,'selected':str(selected)}
for w in workers:setp('Bool',w,'AutoWork',True);setp('Double',w,'BaseMoveSpeed',500.);setp('Double',w,'WorkRate',10.)


gm.call_method('SetSimulationSpeed',(4.,))
import time
stress_start=time.time();stress_report={'roads':100,'workers':4,'initial_jobs':800,'completed':0}
def monitor_roads(delta):
 global stress_handle
 try:
  completed=sum(en(b,'BuildState')==2 for b in roads)
  stress_report.update(completed=completed,elapsed=time.time()-stress_start,remaining_jobs=len(manager.get_editor_property('ActiveJobs')))
  if completed==100 or stress_report['elapsed']>180:
   stress_report['passed']=completed==100
   (ROOT/'Saved/Codex/road_stress_results.json').write_text(json.dumps(stress_report,indent=2))
   for w in workers:setp('Bool',w,'AutoWork',False)
   gm.call_method('SetSimulationSpeed',(1.,))
   unreal.unregister_slate_post_tick_callback(stress_handle)
 except Exception:
  stress_report['error']=traceback.format_exc()
  (ROOT/'Saved/Codex/road_stress_results.json').write_text(json.dumps(stress_report,indent=2))
  unreal.unregister_slate_post_tick_callback(stress_handle)
stress_handle=unreal.register_slate_post_tick_callback(monitor_roads)
