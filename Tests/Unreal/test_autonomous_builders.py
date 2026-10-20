
"""Run in PIE through Unreal Python. Tests actual Blueprint functions in a disposable play world."""
import unreal,json,traceback
from pathlib import Path
ROOT=Path(unreal.Paths.project_dir())
REPORT=Path(unreal.Paths.project_saved_dir())/'Codex/autonomous_static_results.json'
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def cls(n):return unreal.load_class(None,'/Game/'+n+'.'+n+'_C')
def actors(n):return list(unreal.GameplayStatics.get_all_actors_of_class(world,cls(n)))
gm=actors('BP_GridManager')[0]; manager=actors('BP_JobManager')[0]; worker=actors('BP_Colonist')[0]
harness=unreal.new_object(cls('BP_AutonomousTestHarness'))
sys=unreal.get_default_object(unreal.SystemLibrary); game=unreal.get_default_object(unreal.GameplayStatics)
def setp(kind,o,n,v):sys.call_method('Set'+kind+'PropertyByName',(o,unreal.Name(n),v))
def v(x,y):return unreal.Vector2D(x,y)
def en(o,n):return o.get_editor_property(n).value
def cell(x,y,walk=True,occupant=None):harness.call_method('SetGridCell',(gm,v(x,y),walk,occupant))
def tile(w,x,y):
 harness.call_method('SetWorkerTile',(w,v(x,y)))
 w.set_actor_location(gm.call_method('GetTileCenter',(v(x,y),)),False,False)
def spawn(n,x,y):
 tr=unreal.Transform(location=gm.call_method('GetTileCenter',(v(x,y),)))
 a=game.call_method('BeginDeferredActorSpawnFromClass',(world,cls(n),tr,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
 return game.call_method('FinishSpawningActor',(a,tr,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
def reset():
 for w in actors('BP_Colonist'):
  setp('Bool',w,'AutoWork',False);w.call_method('ReleaseJob',())
  setp('Bool',w,'IsMoving',False);setp('Bool',w,'HasActiveMoveRequest',False);setp('Bool',w,'StopAtNextTile',False)
  harness.call_method('ClearMoveResults',(w,))
  if w!=worker:w.destroy_actor()
 for b in actors('BP_BuildingBase'):b.destroy_actor()
 for p in actors('BP_ResourcePile'):p.destroy_actor()
 harness.call_method('ClearJobs',(manager,))
 for x in range(20):
  for y in range(20):cell(x,y)
 tile(worker,2,2)
def place(n,x,y,materials=False):
 gm.call_method('StartPlacement',(cls(n),));b=gm.get_editor_property('CurrentGhostBuilding')
 harness.call_method('SetHoveredTile',(gm,v(x,y)))
 b.set_actor_location(gm.call_method('GridToWorld',(v(x,y),)),False,False)
 gm.call_method('ConfrimPlacement',())
 if not materials:setp('Int',b,'MaterialCost',0)
 return b
def finish_ready(b):setp('Double',b,'WorkDone',b.get_editor_property('WorkRequired'))
def check(ok,detail=''):
 if not ok:raise AssertionError(detail)
report={'passed':[],'failed':[]}
def case(name,fn):
 try:reset();fn();report['passed'].append(name)
 except Exception:report['failed'].append({'name':name,'error':traceback.format_exc()})
def unfinished():
 b=place('BP_Building_Dummy2x2',5,5)
 check(en(b,'BuildState')==1)
 check(all(gm.call_method('IsTileWalkable',(v(x,y),)) for x in [5,6] for y in [5,6]))
 check(not gm.call_method('CheckFootprint',(v(5,5),[v(0,0)]))[-1])
case('Unfinished footprint stays walkable but rejects overlapping placement',unfinished)
def partial():
 b=place('BP_Building_Dummy2x2',5,5);tile(worker,4,5)
 finished,cont=b.call_method('WorkOnConstruction',(worker,gm,1.25))
 check(not finished and cont and abs(b.get_editor_property('WorkDone')-1.25)<1e-6)
 worker.call_method('ReleaseJob',());check(abs(b.get_editor_property('WorkDone')-1.25)<1e-6)
 b.call_method('WorkOnConstruction',(worker,gm,-10.0));check(abs(b.get_editor_property('WorkDone')-1.25)<1e-6)
case('Partial progress survives release and negative work cannot erase it',partial)
def badposition():
 b=place('BP_Building_Dummy2x2',5,5);tile(worker,5,5)
 check(b.call_method('WorkOnConstruction',(worker,gm,10.0))==(False,False))
 check(b.get_editor_property('WorkDone')==0)
case('A worker cannot build from inside the footprint',badposition)
def safe_finish():
 b=place('BP_Building_Dummy2x2',5,5);finish_ready(b)
 check(gm.call_method('TryCompleteConstruction',(b,)))
 check(en(b,'BuildState')==2)
 check(not gm.call_method('TryCompleteConstruction',(b,)))
case('Safe completion commits once',safe_finish)
def occupant():
 b=place('BP_Building_Dummy2x2',5,5);finish_ready(b);tile(worker,5,5)
 check(not gm.call_method('TryCompleteConstruction',(b,)))
 check(en(b,'BuildState')==1 and gm.call_method('IsTileWalkable',(v(5,5),)))
 tile(worker,4,5);check(gm.call_method('TryCompleteConstruction',(b,)))
case('Solid completion waits for a pawn inside and succeeds after it leaves',occupant)
def transit():
 b=place('BP_Building_Dummy2x2',5,5);finish_ready(b);tile(worker,4,5)
 harness.call_method('SetWorkerTile',(worker,v(5,5)))
 # SetWorkerTile sets both; retain NextTile inside but set CurrentTile via mutable harness input below.
 worker.call_method('RequestMove',(v(4,5),))
 check(not gm.call_method('TryCompleteConstruction',(b,)))
case('Completion refuses a pawn departing an occupied footprint',transit)
def road_under_pawn():
 b=place('BP_Road',5,5);finish_ready(b);tile(worker,5,5)
 check(gm.call_method('TryCompleteConstruction',(b,)))
 check(gm.call_method('IsTileWalkable',(v(5,5),)))
case('Road may finish under a pawn and remains walkable',road_under_pawn)
def blocked_exit():
 for x in range(3,9):
  for y in [3,8]:
   if (x,y) not in [(5,3),(6,3)]:cell(x,y,False)
 for y in range(4,8):
  for x in [3,8]:cell(x,y,False)
 b=place('BP_Building_Dummy2x2',5,3);finish_ready(b);tile(worker,5,6)
 check(not gm.call_method('HasExitAfterConstruction',(v(5,6),b)))
 check(not gm.call_method('TryCompleteConstruction',(b,)))
 cell(3,6,True)
 check(gm.call_method('HasExitAfterConstruction',(v(5,6),b)))
 check(gm.call_method('TryCompleteConstruction',(b,)))
case('Closing the only exit is deferred until another exit opens',blocked_exit)
def unreachable():
 b=place('BP_Building_Dummy2x2',10,10)
 for x in range(9,13):
  for y in [9,12]:cell(x,y,False)
 for y in [10,11]:
  for x in [9,12]:cell(x,y,False)
 manager.call_method('RefreshJobs',())
 check(manager.call_method('FindJobForWorker',(worker,))[0] is None)
 cell(9,10,True)
 job,wt=manager.call_method('FindJobForWorker',(worker,))
 check(job is not None and job.get_editor_property('TargetActor')==b)
case('Unreachable sites are skipped and become assignable after access opens',unreachable)
def priority():
 near=place('BP_Road',3,2);far=place('BP_Road',9,9);manager.call_method('RefreshJobs',())
 for j in manager.get_editor_property('ActiveJobs'):
  if j.get_editor_property('TargetActor')==far:setp('Int',j,'Priority',100)
 j,t=manager.call_method('FindJobForWorker',(worker,));check(j.get_editor_property('TargetActor')==far)
case('Higher job priority wins over travel distance',priority)
def nearest():
 near=place('BP_Road',3,2);far=place('BP_Road',9,9);manager.call_method('RefreshJobs',())
 j,t=manager.call_method('FindJobForWorker',(worker,));check(j.get_editor_property('TargetActor')==near)
case('Equal priority chooses least travel time',nearest)
def two_workers():
 a=place('BP_Road',4,4);b=place('BP_Road',8,8);manager.call_method('RefreshJobs',())
 second=spawn('BP_Colonist',3,2);setp('Bool',second,'AutoWork',False)
 j1,t1=manager.call_method('FindJobForWorker',(worker,));setp('Object',worker,'CurrentJob',j1)
 j2,t2=manager.call_method('FindJobForWorker',(second,));setp('Object',second,'CurrentJob',j2)
 check(j1 is not None and j2 is not None and j1!=j2)
 check(j1.get_editor_property('AssignedWorker')==worker and j2.get_editor_property('AssignedWorker')==second)
case('Two workers reserve different jobs',two_workers)
def abandoned():
 b=place('BP_Road',4,4);manager.call_method('RefreshJobs',())
 second=spawn('BP_Colonist',3,2);setp('Bool',second,'AutoWork',False)
 job,t=manager.call_method('FindJobForWorker',(second,));setp('Object',second,'CurrentJob',job)
 second.destroy_actor();manager.call_method('RefreshJobs',())
 check(en(job,'State')==1 and job.get_editor_property('AssignedWorker') is None)
 replacement,t=manager.call_method('FindJobForWorker',(worker,));check(replacement==job)
case('Destroyed worker releases reservation for another worker',abandoned)
def destroyed_target():
 b=place('BP_Road',4,4);manager.call_method('RefreshJobs',())
 job,t=manager.call_method('FindJobForWorker',(worker,));setp('Object',worker,'CurrentJob',job)
 b.destroy_actor();manager.call_method('RefreshJobs',());worker.call_method('UpdateJob',(0.1,))
 check(worker.get_editor_property('CurrentJob') is None and en(job,'State')==5)
case('Destroyed construction target cancels job and releases worker',destroyed_target)
def duplicate():
 b=place('BP_Road',4,4)
 for i in range(5):manager.call_method('RefreshJobs',())
 jobs=list(manager.get_editor_property('ActiveJobs'))
 check(len(jobs)==b.get_editor_property('MaxConstructionWorkers'))
 check(len(set(str(j.get_editor_property('JobKey')) for j in jobs))==len(jobs))
case('Repeated discovery does not duplicate site jobs',duplicate)
reset()
REPORT.write_text(json.dumps(report,indent=2))
