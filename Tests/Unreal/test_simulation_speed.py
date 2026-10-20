"""Global simulation speed and front-right workstation output tests in PIE."""
import unreal,json,time,traceback
from pathlib import Path
ROOT=Path(unreal.Paths.project_dir())
source=(ROOT/'Tests/Unreal/test_autonomous_builders.py').read_text()
exec(source[:source.index('def unfinished():')],globals())
report={'passed':[],'failed':[],'measurements':{}}
def speed(n):gm.call_method('SetSimulationSpeed',(float(n),))
def actual():return unreal.GameplayStatics.get_global_time_dilation(world)
def passed(n):report['passed'].append(n)
def clockwait(seconds):
 end=time.monotonic()+seconds
 return lambda:time.monotonic()>=end
def live():
 reset()
 check(abs(actual()-1)<0.001);passed('A fresh Play session starts at normal speed')
 for expected in [2,4,8,1]:
  gm.call_method('CycleSimulationSpeed',())
  check(abs(actual()-expected)<0.001 and abs(gm.get_editor_property('SimulationSpeed')-expected)<0.001)
 passed('Speed cycles through 1x, 2x, 4x and 8x and returns to normal')
 speed(0);check(actual()==1);speed(100);check(actual()==8);speed(1)
 passed('Speed setter clamps unsupported rates to the supported range')
 s=place('BP_ProductionStation',5,5);finish_ready(s);check(gm.call_method('TryCompleteConstruction',(s,)))
 tile(worker,6,6)
 check(s.call_method('WorkOnProduction',(worker,gm,5.0))==(True,True))
 p=s.get_editor_property('OutputPile')
 check(p.get_editor_property('Amount')==2)
 check(gm.call_method('WorldToGrid',(p.get_actor_location(),))==v(7,5))
 check(s.get_editor_property('OutputTileOffset')==v(2,0))
 passed('New output is stored on the front-right occupied tile beside the entrance')
 setp('Double',s,'ProductionWorkRequired',1000)
 setp('Bool',worker,'AutoWork',True)
 yield ('Worker starts producing for the speed measurement',lambda:en(worker,'WorkerActivity')==2,8)
 rates=[]
 for factor in [1,4]:
  speed(factor)
  start=time.monotonic();progress=s.get_editor_property('ProductionProgress')
  yield ('Measure production at '+str(factor)+'x',clockwait(0.75),4)
  rates.append((s.get_editor_property('ProductionProgress')-progress)/(time.monotonic()-start))
 report['measurements']['production_labour_per_real_second']=rates
 check(2.8<rates[1]/rates[0]<5.2,str(rates))
 passed('Global 4x speed accelerates actual production labour approximately fourfold')
 reset()
 rates=[]
 for factor in [1,4]:
  speed(factor);tile(worker,2,2)
  setp('Double',worker,'BaseMoveSpeed',100.0)
  worker.call_method('RequestMove',(v(15,2),))
  start=time.monotonic();x=worker.get_actor_location().x
  yield ('Measure movement at '+str(factor)+'x',clockwait(0.65),4)
  rates.append((worker.get_actor_location().x-x)/(time.monotonic()-start))
  reset()
 report['measurements']['movement_units_per_real_second']=rates
 check(2.8<rates[1]/rates[0]<5.2,str(rates))
 passed('Global 4x speed accelerates actual colonist movement approximately fourfold')
 reset();speed(8)
 s=place('BP_ProductionStation',5,5);finish_ready(s);check(gm.call_method('TryCompleteConstruction',(s,)))
 setp('Double',s,'ProductionWorkRequired',0.5)
 target=place('BP_Building_Dummy2x2',12,8,True);setp('Double',target,'WorkRequired',0.5)
 other=spawn('BP_Colonist',3,2);setp('Bool',other,'AutoWork',True);setp('Bool',worker,'AutoWork',True)
 yield ('Production, hauling, and construction finish correctly at 8x',lambda:en(target,'BuildState')==2,20)
 check(target.get_editor_property('MaterialsDelivered')==6)
 passed('Fast construction still consumes exactly the required resources')
 speed(1);reset()
 check(actual()==1);passed('Returning to normal restores the global rate')
runner=live();pending=None;deadline=0
def tick_suite(delta):
 global pending,deadline,HANDLE
 try:
  if pending:
   name,predicate,seconds=pending
   if predicate():passed(name);pending=None
   elif time.monotonic()>deadline:raise AssertionError('Timed out: '+name)
   else:return
  pending=next(runner);deadline=time.monotonic()+pending[2]
 except StopIteration:
  report['status']='passed';unreal.unregister_slate_post_tick_callback(HANDLE)
 except Exception:
  report['failed'].append(traceback.format_exc());report['status']='failed'
  try:speed(1)
  except Exception:pass
  unreal.unregister_slate_post_tick_callback(HANDLE)
 finally:
  report['current']=pending[0] if pending else None
  (ROOT/'Saved/Codex/simulation_speed_results.json').write_text(json.dumps(report,indent=2))
HANDLE=unreal.register_slate_post_tick_callback(tick_suite)
