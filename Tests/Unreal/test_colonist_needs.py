"""Food, configurable storage, personal needs and furniture integration checks."""

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


base_reset=reset
def reset():
 base_reset()
 setp('Bool',worker,'NeedsEnabled',True)
 worker.call_method('InitializeNeeds',())
 for n in worker.get_editor_property('Needs'):
  setp('Double',n,'DecayPerSecond',0.08 if str(n.get_editor_property('NeedName'))=='Nutrition' else 0.04);setp('Double',n,'Level',85.);setp('Bool',n,'NeedActive',False);setp('Double',n,'NutritionRemaining',0.)
  setp('Object',n,'SelectedFurniture',None)
  setp('Int',n,'JobID',-1);manager.call_method('RegisterJob',(n,))
 setp('Int',worker,'CarryAmount',0)
def need(kind='Nutrition',w=None):
 return next(n for n in (w or worker).get_editor_property('Needs') if str(n.get_editor_property('NeedName'))==kind)
def built(kind,x,y):
 b=place(kind,x,y);finish_ready(b);check(gm.call_method('TryCompleteConstruction',(b,)));return b
def nwork(n,seconds=1.):return n.call_method('PerformWork',(worker,gm,seconds))
def hunger_pickup():
 p=spawn('BP_FoodPile',2,3);setp('Int',p,'Amount',3)
 n=need();setp('Double',n,'Level',20);setp('Bool',n,'NeedActive',True)
 check(nwork(n)==(False,True,True))
 check(p.get_editor_property('Amount')==2 and worker.get_editor_property('CarryAmount')==1)
 check(n.get_editor_property('Level')==20)
 check(nwork(n)==(False,True,False))
 check(worker.get_editor_property('CarryAmount')==0 and n.get_editor_property('Level')==30)
 check(n.get_editor_property('NutritionRemaining')==30)
case('Meal transfers exactly one food and restores nutrition over time',hunger_pickup)
def nofood():
 p=spawn('BP_ResourcePile',2,3);setp('Int',p,'Amount',10);setp('Name',p,'ResourceType','BuildingMaterial')
 n=need();setp('Double',n,'Level',20)
 check(not n.call_method('GetWorkTiles',(worker,gm)))
 check(nwork(n)==(False,False,False));check(p.get_editor_property('Amount')==10)
case('Building materials cannot be eaten; no food yields no eating destination',nofood)
def sleepground():
 n=need('Rest');setp('Double',n,'Level',20);setp('Bool',n,'NeedActive',True)
 t=n.call_method('GetWorkTiles',(worker,gm));check(len(t)==1 and t[0]==v(2,2))
 nwork(n);check(abs(n.get_editor_property('Level')-24)<0.01)
case('Colonist can sleep on current ground tile',sleepground)
def bedbonus():
 bed=built('BP_Bed',4,4);n=need('Rest');setp('Double',n,'Level',20)
 t=n.call_method('GetWorkTiles',(worker,gm));check(t==[v(5,4)],str(t));tile(worker,5,4)
 nwork(n);check(n.get_editor_property('Level')==28)
 check(not gm.call_method('IsTileWalkable',(v(4,4),)))
case('Completed bed provides twofold recovery from its free use tile',bedbonus)
def tablebonus():
 b=built('BP_DiningTable',4,4);n=need();setp('Double',n,'Level',20)
 setp('Int',worker,'CarryAmount',1);setp('Name',worker,'CarryResource','Food')
 t=n.call_method('GetWorkTiles',(worker,gm));check(len(t)==1 and n.get_editor_property('SelectedFurniture')==b)
 tile(worker,t[0].x,t[0].y);nwork(n)
 check(n.get_editor_property('Level')==40 and worker.get_editor_property('CarryAmount')==0)
case('Table doubles eating recovery and consumes actual carried food',tablebonus)
def unfinished():
 b=place('BP_Bed',4,4);n=need('Rest')
 check(n.call_method('GetWorkTiles',(worker,gm))==[v(2,2)])
 check(n.get_editor_property('SelectedFurniture') is None)
case('Unfinished furniture gives no use destination or bonus',unfinished)
def unreachable():
 b=built('BP_Bed',6,6);cell(7,6,False);n=need('Rest')
 check(n.call_method('GetWorkTiles',(worker,gm))==[v(2,2)])
case('Blocked bed falls back to ground',unreachable)
def destroyed():
 b=built('BP_Bed',4,4);n=need('Rest');setp('Double',n,'Level',20)
 n.call_method('GetWorkTiles',(worker,gm));tile(worker,5,4);b.destroy_actor();nwork(n)
 check(n.get_editor_property('Level')==24)
case('Destroyed furniture loses bonus without breaking recovery',destroyed)
def reservation():
 b=built('BP_Bed',4,4);n=need('Rest')
 second=spawn('BP_Colonist',5,4);setp('Bool',second,'AutoWork',False)
 check(n.call_method('GetWorkTiles',(worker,gm))==[v(2,2)])
case('Another colonist occupying the bed use tile prevents selection',reservation)
def switchstorage():
 b=built('BP_Stockpile',6,6);p=b.call_method('EnsureStoredPile',(gm,))
 check(b.call_method('TrySetResource',('Food',)))
 setp('Name',p,'ResourceType','Food');setp('Int',p,'Amount',2)
 check(not b.call_method('TrySetResource',('BuildingMaterial',)))
 setp('Int',p,'Amount',0);setp('Object',worker,'ReservedDeliveryTarget',b);setp('Int',worker,'ReservedDeliveryAmount',2)
 check(not b.call_method('TrySetResource',('BuildingMaterial',)))
 setp('Int',worker,'ReservedDeliveryAmount',0)
 check(b.call_method('TrySetResource',('BuildingMaterial',)))
case('Storage filter refuses existing stock and in-flight claims',switchstorage)
def owned():
 second=spawn('BP_Colonist',3,2);setp('Bool',second,'AutoWork',False)
 n=need();check(not n.call_method('TryReserveWorker',(second,)))
 check(not n.call_method('GetWorkTiles',(second,gm)))
 check(n.call_method('TryReserveWorker',(worker,)))
case('Personal need jobs cannot be taken by another colonist',owned)
def activation():
 n=need();setp('Double',n,'Level',30.01);check(n.call_method('UpdateNeed',(1.,)))
 check(not n.call_method('UpdateNeed',(1.,)))
 check(en(n,'State')<4);check(en(n,'State')<4)
 setp('Double',n,'Level',89.);setp('Double',n,'NutritionRemaining',10.)
 check(nwork(n)==(True,True,False));check(n.get_editor_property('Level')==90 and not n.get_editor_property('NeedActive'))
case('Need activation uses hysteresis and completes at target without overshoot',activation)
def cancelmeal():
 p=spawn('BP_FoodPile',2,3);setp('Int',p,'Amount',3);n=need();setp('Double',n,'Level',20)
 nwork(n);setp('Object',worker,'CurrentJob',n);setp('Object',n,'AssignedWorker',worker);worker.call_method('ReleaseJob',())
 total=sum(a.get_editor_property('Amount') for a in actors('BP_ResourcePile') if str(a.get_editor_property('ResourceType'))=='Food')
 check(total==3 and worker.get_editor_property('CarryAmount')==0,str(total))
case('Cancel before eating returns carried food to inventory',cancelmeal)
def mealprogress():
 n=need();setp('Double',n,'Level',20);setp('Int',worker,'CarryAmount',1);setp('Name',worker,'CarryResource','Food')
 nwork(n);setp('Object',worker,'CurrentJob',n);setp('Object',n,'AssignedWorker',worker);worker.call_method('ReleaseJob',())
 check(n.get_editor_property('NutritionRemaining')==30 and n.get_editor_property('Level')==30)
 nwork(n);check(n.get_editor_property('Level')==40 and n.get_editor_property('NutritionRemaining')==20)
case('Consumed meal progress survives interruption without consuming twice',mealprogress)
def ui():
 b=built('BP_Stockpile',6,6);b.call_method('EnsureStoredPile',(gm,))
 gm.call_method('InspectTile',(v(6,6),));ui=gm.get_editor_property('InspectorWidget')
 ui.call_method('SelectStoredResource',('Food',));check(str(b.get_editor_property('AcceptedResource'))=='Food')
 check('Food' in b.call_method('GetInspectionText',()))
 check('Nutrition' in worker.call_method('GetInspectionText',()) and 'Rest' in worker.call_method('GetInspectionText',()))
case('Inspector controls change storage filter and show both needs',ui)

def kitchen():
 b=built('BP_FoodKitchen',5,5);tile(worker,6,5)
 check(b.call_method('WorkOnProduction',(worker,gm,4.))==(True,True))
 p=b.get_editor_property('OutputPile');check(p.get_editor_property('Amount')==2 and str(p.get_editor_property('ResourceType'))=='Food')
 check(list(b.call_method('GetProductionWorkTiles',(gm,)))==[v(6,5)])
 check(abs(p.get_actor_location().z-gm.call_method('GetTileCenter',(v(6,6),)).z-77.)<0.01)
case('Compact food kitchen produces real food at the configured output position',kitchen)
def menus():
 lib=unreal.get_default_object(unreal.load_class(None,'/Script/UMG.WidgetBlueprintLibrary'))
 entries=lib.call_method('GetAllWidgetsOfClass',(world,cls('WBP_BuildEntry'),False))
 classes=[e.get_editor_property('BuildingClass') for e in entries]
 for name in ['BP_Bed','BP_DiningTable','BP_FoodGarden','BP_FoodKitchen','BP_Stockpile']:check(classes.count(cls(name))==1,name)
 check(cls('BP_NeedsFurniture') not in classes)
case('All usable new buildings appear once; abstract furniture definition is hidden',menus)
def guards():
 n=need('Rest');setp('Double',n,'Level',20.);nwork(n,-10.);check(n.get_editor_property('Level')==20.)
 n=need();setp('Double',n,'Level',20.);p=spawn('BP_FoodPile',2,3)
 setp('Int',worker,'CarryAmount',2);setp('Name',worker,'CarryResource','BuildingMaterial')
 check(nwork(n)==(False,False,False))
 check(worker.get_editor_property('CarryAmount')==2 and p.get_editor_property('Amount')==10)
case('Negative work cannot drain needs and eating cannot overwrite other cargo',guards)
def manualdecay():
 n=need();setp('Double',n,'Level',85.);setp('Bool',worker,'AutoWork',False)
 worker.call_method('UpdateNeeds',(10.,));check(abs(n.get_editor_property('Level')-84.2)<0.01)
 setp('Bool',worker,'NeedsEnabled',False);worker.call_method('UpdateNeeds',(10.,));check(abs(n.get_editor_property('Level')-84.2)<0.01)
case('Needs decay during manual control and freeze only when explicitly disabled',manualdecay)
def color():
 p=spawn('BP_FoodPile',2,3);c=p.get_components_by_class(unreal.StaticMeshComponent)[0]
 check(c.get_material(0).get_path_name()=='/Game/M_Food.M_Food')
case('Food resource stacks have a distinct green material',color)

reset()

(ROOT/'Saved/Codex/needs_static_results.json').write_text(json.dumps(report,indent=2))
assert not report['failed'], report['failed']

import time
live_report={'passed':[],'failed':[]}
def stat(n,p):return n.get_editor_property(p)
def configure(w):
 setp('Double',w,'BaseMoveSpeed',400.);setp('Bool',w,'NeedsEnabled',True);setp('Double',w,'JobSearchDelay',0.)
 w.call_method('InitializeNeeds',())
 for n in w.get_editor_property('Needs'):
  setp('Double',n,'DecayPerSecond',0.)
  manager.call_method('RegisterJob',(n,))
def run_cases():
 reset();configure(worker);gm.call_method('SetSimulationSpeed',(4.,))
 garden=built('BP_FoodGarden',5,5)
 setp('Double',garden,'ProductionWorkRequired',1.)
 n=need();setp('Double',n,'Level',20.);setp('Double',n,'DecayPerSecond',0.001)
 manager.call_method('RefreshJobs',());setp('Bool',worker,'AutoWork',True)
 yield 'Hungry colonist with no food operates the garden and then eats its real output',lambda:stat(n,'Level')>=89.,45
 check(stat(garden,'OutputPile') is not None and str(stat(stat(garden,'OutputPile'),'ResourceType'))=='Food')
 yield 'Recovered colonist resumes food production',lambda:stat(worker,'CurrentJob') is not None and stat(stat(worker,'CurrentJob'),'JobDisplayName')=='Produce resources',15
 setp('Bool',worker,'AutoWork',False);worker.call_method('ReleaseJob',())
 reset();configure(worker);gm.call_method('SetSimulationSpeed',(4.,))
 bed=built('BP_Bed',5,5);n=need('Rest');setp('Double',n,'Level',20.)
 setp('Bool',worker,'AutoWork',True)
 yield 'Tired colonist autonomously reaches the bed and recovers',lambda:stat(n,'Level')>=90.,25
 check(stat(n,'SelectedFurniture')==bed)
 yield 'Sleeping finishes and releases work-position reservation',lambda:stat(worker,'CurrentJob') is None and not stat(worker,'HasWorkTileReservation'),10
 setp('Bool',worker,'AutoWork',False);worker.call_method('ReleaseJob',())
 reset();configure(worker);gm.call_method('SetSimulationSpeed',(4.,))
 table=built('BP_DiningTable',6,6);food=spawn('BP_FoodPile',4,4);setp('Int',food,'Amount',10)
 second=spawn('BP_Colonist',3,2);configure(second)
 for w in [worker,second]:
  setp('Double',need(w=w),'Level',20.);setp('Bool',w,'AutoWork',True)
 manager.call_method('RefreshJobs',())
 observed={'separate':False}
 def bothfed():
  n1=need();n2=need(w=second)
  if stat(worker,'HasWorkTileReservation') and stat(second,'HasWorkTileReservation') and stat(n1,'SelectedFurniture')==table and stat(n2,'SelectedFurniture')==table:
   check(stat(worker,'JobWorkTile')!=stat(second,'JobWorkTile'),'Shared table reservations overlapped')
   observed['separate']=True
  return stat(n1,'Level')>=90 and stat(n2,'Level')>=90
 yield 'Two colonists eat concurrently at distinct table places',bothfed,35
 check(observed['separate'],'Never observed independent table reservations')
 check(sum(stat(p,'Amount') for p in actors('BP_ResourcePile') if str(stat(p,'ResourceType'))=='Food')==6,'Expected two food units per hungry worker')
 live_report['passed'].append('Concurrent eating consumed exactly four food, without duplication')
 for w in [worker,second]:setp('Bool',w,'AutoWork',False);w.call_method('ReleaseJob',())
 reset();configure(worker);gm.call_method('SetSimulationSpeed',(4.,))
 storage=built('BP_Stockpile',5,5);pile=storage.call_method('EnsureStoredPile',(gm,));check(storage.call_method('TrySetResource',('Food',)))
 setp('Name',pile,'ResourceType','Food');setp('Int',pile,'Amount',4);pile.set_actor_hidden_in_game(False)
 n=need();setp('Double',n,'Level',20.);setp('Bool',worker,'AutoWork',True);manager.call_method('RefreshJobs',())
 yield 'Hungry colonist withdraws food from solid storage and eats without a table',lambda:stat(n,'Level')>=90.,35
 check(stat(pile,'Amount')==2)
 setp('Bool',worker,'AutoWork',False);worker.call_method('ReleaseJob',())
 reset();gm.call_method('SetSimulationSpeed',(1.,))
steps=iter(run_cases());pending=None;started=0.;handle=None
def tick_needs(dt):
 global pending,started,handle
 try:
  if pending is None:pending=next(steps);started=time.monotonic()
  label,condition,timeout=pending
  if condition():
   live_report['passed'].append(label);pending=None
  elif time.monotonic()-started>timeout:raise AssertionError('Timed out: '+label)
 except StopIteration:
  unreal.unregister_slate_post_tick_callback(handle)
  (ROOT/'Saved/Codex/needs_live_results.json').write_text(json.dumps(live_report,indent=2))
 except Exception:
  live_report['failed'].append(traceback.format_exc())
  unreal.unregister_slate_post_tick_callback(handle)
  (ROOT/'Saved/Codex/needs_live_results.json').write_text(json.dumps(live_report,indent=2))
handle=unreal.register_slate_post_tick_callback(tick_needs)
