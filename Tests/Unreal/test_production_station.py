"""Production table geometry, job lifecycle, finite output, and construction integration."""
import unreal,json,time,traceback
from pathlib import Path
ROOT=Path(unreal.Paths.project_dir())
source=(ROOT/'Tests/Unreal/test_autonomous_builders.py').read_text()
exec(source[:source.index('def unfinished():')],globals())
report={'passed':[],'failed':[]}
def built(x=5,y=5):
 s=place('BP_ProductionStation',x,y);finish_ready(s)
 check(gm.call_method('TryCompleteConstruction',(s,)),'station did not complete')
 return s
def produce(s,amount=5):
 return s.call_method('WorkOnProduction',(worker,gm,float(amount)))
def menu():
 lib=unreal.get_default_object(unreal.load_class(None,'/Script/UMG.WidgetBlueprintLibrary'))
 widgets=lib.call_method('GetAllWidgetsOfClass',(world,cls('WBP_BuildEntry'),False))
 check(sum(w.get_editor_property('BuildingClass')==cls('BP_ProductionStation') for w in widgets)==1)
case('Production structure appears automatically once in the building menu',menu)
def footprint():
 s=built()
 expected={(0,0),(2,0),(0,1),(2,1),(0,2),(1,2),(2,2)}
 check({(int(t.x),int(t.y)) for t in s.get_editor_property('FootprintOffsets')}==expected)
 check(all(not gm.call_method('IsTileWalkable',(v(5+x,5+y),)) for x,y in expected))
 check(all(gm.call_method('IsTileWalkable',(v(6,y),)) for y in [5,6]))
 check(list(s.call_method('GetProductionWorkTiles',(gm,)))==[v(6,6)])
 check(gm.call_method('FindPath',(v(6,4),v(6,6),100.0))[0])
 check(s.get_editor_property('BuildingMesh').get_editor_property('StaticMesh').get_path_name()=='/Game/Meshes/SM_ProductionTable_P.SM_ProductionTable_P')
case('P-shaped 3x3 table blocks seven cells while preserving entrance and inner work tile',footprint)
def unfinished():
 s=place('BP_ProductionStation',5,5);tile(worker,6,6)
 check(not s.call_method('CanProduce',()) and produce(s,100)==(False,False))
 check(s.get_editor_property('OutputPile') is None)
case('Unfinished workstations cannot produce resources',unfinished)
def positions():
 s=built();tile(worker,6,5)
 check(produce(s)==(False,False))
 tile(worker,6,6);setp('Bool',worker,'IsMoving',True)
 check(produce(s)==(False,False));setp('Bool',worker,'IsMoving',False)
 check(produce(s,2)==(False,True))
 worker.call_method('ReleaseJob',())
 check(abs(s.get_editor_property('ProductionProgress')-2)<0.001)
 produce(s,-5);check(abs(s.get_editor_property('ProductionProgress')-2)<0.001)
 check(produce(s,3)==(True,True))
 check(s.get_editor_property('OutputPile').get_editor_property('Amount')==2)
case('Only a stationary worker inside can produce, and interruption preserves partial labour',positions)
def capacity():
 s=built();tile(worker,6,6);setp('Int',s,'OutputCapacity',5)
 for i in range(2):check(produce(s)==(True,True))
 p=s.get_editor_property('OutputPile');check(p.get_editor_property('Amount')==4)
 check(not s.call_method('CanProduce',()) and produce(s)==(False,False))
 setp('Int',p,'Amount',0);p.set_actor_hidden_in_game(True)
 check(produce(s)==(True,True));check(s.get_editor_property('OutputPile')==p and p.get_editor_property('Amount')==2)
 check(not p.get_editor_property('hidden'))
case('Full batches respect output capacity and depleted output is replenished in the same pile',capacity)
def disabled():
 s=built();tile(worker,6,6)
 setp('Bool',s,'ProductionEnabled',False);check(produce(s)==(False,False))
 setp('Bool',s,'ProductionEnabled',True);setp('Double',s,'ProductionWorkRequired',0);check(not s.call_method('CanProduce',()))
 setp('Double',s,'ProductionWorkRequired',5);setp('Int',s,'OutputPerBatch',0);check(not s.call_method('CanProduce',()))
case('Disabled production and invalid zero-work or zero-output recipes do not generate free resources',disabled)
def resource():
 s=built();tile(worker,6,6);produce(s);p=s.get_editor_property('OutputPile')
 setp('Name',s,'OutputResource',unreal.Name('Food'))
 check(not s.call_method('CanProduce',()),'must not mix resource types')
 setp('Int',p,'Amount',0);check(produce(s)==(True,True))
 check(str(p.get_editor_property('ResourceType'))=='Food' and p.get_editor_property('Amount')==2)
case('Generic output settings support another resource without mixing existing contents',resource)
def destroy():
 s=built();tile(worker,6,6);produce(s);p=s.get_editor_property('OutputPile')
 s.destroy_actor();manager.call_method('RefreshJobs',())
 check(p in actors('BP_ResourcePile') and p.get_editor_property('Amount')==2)
case('Destroying a workstation leaves already produced supplies intact',destroy)
def enable(w):setp('Double',w,'BaseMoveSpeed',600.0);setp('Bool',w,'AutoWork',True)
def other(x,y):
 w=spawn('BP_Colonist',x,y);enable(w);return w
def active_production(s):
 return [j for j in manager.get_editor_property('ActiveJobs') if j.get_editor_property('TargetActor')==s and str(j.get_editor_property('JobKey')).startswith('Production_') and en(j,'State')<4]
def live():
 reset()
 s=place('BP_ProductionStation',5,5,True);setp('Double',s,'WorkRequired',0.5);setp('Double',s,'ProductionWorkRequired',0.5);setp('Int',s,'OutputCapacity',4)
 p=spawn('BP_ResourcePile',2,2);setp('Int',p,'Amount',6);enable(worker)
 yield ('Colonist delivers construction cost and builds the workbench',lambda:en(s,'BuildState')==2,30)
 check(s.get_editor_property('MaterialsDelivered')==6)
 yield ('Finished workstation is discovered and autonomously fills its output buffer',lambda:s.get_editor_property('OutputPile') is not None and s.get_editor_property('OutputPile').get_editor_property('Amount')==4,15)
 yield ('Full output releases the producer instead of continuing free work',lambda:worker.get_editor_property('CurrentJob') is None,8)
 manager.call_method('RefreshJobs',())
 check(len(active_production(s))==1 and en(active_production(s)[0],'State')==0)
 report['passed'].append('Periodic discovery keeps one waiting production slot without duplicates')
 output=s.get_editor_property('OutputPile');setp('Int',output,'Amount',2)
 yield ('Removing stock wakes the waiting production job',lambda:output.get_editor_property('Amount')==4,12)
 setp('Int',output,'Amount',2);setp('Double',s,'ProductionWorkRequired',100);setp('Bool',s,'ProductionEnabled',False)
 yield ('Production toggle disables and releases its active job',lambda:worker.get_editor_property('CurrentJob') is None,8)
 check(output.get_editor_property('Amount')==2)
 reset()
 s=built(5,5);setp('Double',s,'ProductionWorkRequired',0.5)
 target=place('BP_Building_Dummy2x2',12,8,True);setp('Double',target,'WorkRequired',0.5)
 check(len(actors('BP_ResourcePile'))==0)
 enable(worker);w2=other(3,2)
 yield ('Produced supplies are hauled to an unpaid construction site',lambda:target.get_editor_property('MaterialsDelivered')>0,25)
 yield ('Production sustains construction with no starting resource piles',lambda:en(target,'BuildState')==2,35)
 check(target.get_editor_property('MaterialsDelivered')==6)
 report['passed'].append('Construction consumes exactly its cost from workstation output')
 reset()
runner=live();pending=None;deadline=0
def tick_suite(delta):
 global pending,deadline,HANDLE
 try:
  if pending:
   name,predicate,seconds=pending
   if predicate():report['passed'].append(name);pending=None
   elif time.monotonic()>deadline:raise AssertionError('Timed out: '+name)
   else:return
  pending=next(runner);deadline=time.monotonic()+pending[2]
 except StopIteration:
  report['status']='failed' if report['failed'] else 'passed';unreal.unregister_slate_post_tick_callback(HANDLE)
 except Exception:
  report['failed'].append(traceback.format_exc());report['status']='failed';unreal.unregister_slate_post_tick_callback(HANDLE)
 finally:
  report['current']=pending[0] if pending else None
  (ROOT/'Saved/Codex/production_results.json').write_text(json.dumps(report,indent=2))
HANDLE=unreal.register_slate_post_tick_callback(tick_suite)
