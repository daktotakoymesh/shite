
"""Finite-material construction tests against actual Blueprint functions and live PIE tick."""
import unreal,json,time,traceback
from pathlib import Path
ROOT=Path(unreal.Paths.project_dir())
source=(ROOT/'Tests/Unreal/test_autonomous_builders.py').read_text()
exec(source[:source.index('def unfinished():')],globals())
fixture_spawn=spawn
def spawn(n,x,y):
 a=fixture_spawn(n,x,y)
 if n=='BP_Colonist':setp('Double',a,'BaseMoveSpeed',600.0)
 return a
fixture_reset=reset
def reset():
 fixture_reset()
 setp('Double',worker,'BaseMoveSpeed',600.0)
report={'passed':[],'failed':[],'started':time.time()}
def pile(x,y,amount,resource='BuildingMaterial'):
 p=spawn('BP_ResourcePile',x,y)
 setp('Int',p,'Amount',amount);setp('Name',p,'ResourceType',unreal.Name(resource))
 return p
def supplies():
 return sum(p.get_editor_property('Amount') for p in actors('BP_ResourcePile'))+sum(w.get_editor_property('CarryAmount') for w in actors('BP_Colonist'))+sum(b.get_editor_property('MaterialsDelivered') for b in actors('BP_BuildingBase'))
def job_for(b,worker=None):
 j=unreal.new_object(cls('BP_Job_DeliverMaterials'),outer=manager)
 setp('Object',j,'TargetActor',b)
 if worker:setp('Object',j,'AssignedWorker',worker)
 return j
def waitfor(name,predicate,seconds=30):return name,predicate,seconds
def passed(name):report['passed'].append(name)
def run_tests():
 reset()
 b=place('BP_Building_Dummy2x2',5,5,True);tile(worker,4,5)
 check(b.call_method('WorkOnConstruction',(worker,gm,100.0))==(False,False))
 finish_ready(b);check(not gm.call_method('TryCompleteConstruction',(b,)))
 passed('Direct work and completion cannot bypass unpaid material cost')
 reset()
 b=place('BP_Building_Dummy2x2',7,5,True);p=pile(2,2,10)
 j=job_for(b)
 check(j.call_method('PerformWork',(worker,gm,1.0))==(False,True,True))
 check(p.get_editor_property('Amount')==7 and worker.get_editor_property('CarryAmount')==3)
 tile(worker,6,5)
 check(j.call_method('PerformWork',(worker,gm,1.0))==(True,True,False))
 check(b.get_editor_property('MaterialsDelivered')==3 and worker.get_editor_property('CarryAmount')==0 and supplies()==10)
 passed('Pickup respects capacity and delivery conserves exact quantities')
 reset()
 a=place('BP_Road',7,5,True);b=place('BP_Road',9,5,True);p=pile(2,2,1)
 other=spawn('BP_Colonist',2,2);setp('Bool',other,'AutoWork',False)
 j1=job_for(a);j2=job_for(b)
 check(j1.call_method('PerformWork',(worker,gm,1.0))==(False,True,True))
 check(j2.call_method('PerformWork',(other,gm,1.0))==(False,False,False))
 check(supplies()==1 and worker.get_editor_property('CarryAmount')==1)
 passed('Competing pickups cannot duplicate the last unit of a pile')
 reset()
 b=place('BP_Road',6,5,True);p=pile(2,2,10,'Food');j=job_for(b)
 check(len(j.call_method('GetWorkTiles',(worker,gm)))==0)
 check(j.call_method('PerformWork',(worker,gm,1.0))==(False,False,False))
 passed('A building-material job ignores food piles')
 reset()
 b=place('BP_Road',10,10,True);p=pile(2,2,10);j=job_for(b)
 for x,y in [(9,10),(11,10),(10,9),(10,11)]:cell(x,y,False)
 check(len(j.call_method('GetWorkTiles',(worker,gm)))==0 and supplies()==10)
 passed('No supplies are collected for an unreachable delivery position')
 reset()
 b=place('BP_Road',7,5,True);p=pile(3,2,4);cell(3,2,False);j=job_for(b)
 check(v(2,2) in list(j.call_method('GetWorkTiles',(worker,gm))))
 check(j.call_method('PerformWork',(worker,gm,1.0))==(False,True,True))
 check(worker.get_editor_property('CarryAmount')==1 and supplies()==4)
 passed('A pile on a blocked tile remains collectible from an accessible neighbour')
 reset()
 b=place('BP_Building_Dummy2x2',7,5,True);setp('Double',b,'WorkRequired',0.5)
 pile(3,2,2);setp('Bool',worker,'AutoWork',True)
 yield waitfor('Available partial supplies are delivered',lambda:b.get_editor_property('MaterialsDelivered')==2)
 check(b.get_editor_property('WorkDone')==0 and en(b,'BuildState')==1 and supplies()==2)
 passed('A shortage leaves the site unfinished without free labour or materials')
 pile(3,2,4)
 yield waitfor('New supplies wake waiting construction and finish the site',lambda:en(b,'BuildState')==2,45)
 check(supplies()==6);passed('Multiple trips consume precisely the building cost')
 reset()
 a=place('BP_Building_Dummy2x2',8,5,True);b=place('BP_Building_Dummy2x2',8,10,True)
 for s in [a,b]:setp('Double',s,'WorkRequired',0.5)
 pile(3,2,12);other=spawn('BP_Colonist',3,3)
 setp('Bool',worker,'AutoWork',True);setp('Bool',other,'AutoWork',True)
 yield waitfor('Two workers complete material-funded buildings from shared supplies',lambda:en(a,'BuildState')==2 and en(b,'BuildState')==2,60)
 check(supplies()==12 and all(w.get_editor_property('CarryAmount')==0 for w in actors('BP_Colonist')))
 passed('Concurrent hauling conserves supplies and leaves no stranded cargo')
 reset()
 b=place('BP_Building_Dummy2x2',14,14,True);setp('Double',b,'WorkRequired',0.5)
 pile(3,2,6);setp('Bool',worker,'AutoWork',True)
 yield waitfor('Worker begins carrying a delivery',lambda:worker.get_editor_property('CarryAmount')>0 and worker.get_editor_property('IsMoving'))
 worker.call_method('RequestMove',(v(0,0),))
 yield waitfor('Manual movement drops cargo and releases delivery job',lambda:worker.get_editor_property('CarryAmount')==0 and worker.get_editor_property('CurrentJob') is None,8)
 check(supplies()==6);passed('Manual interruption preserves every unit of cargo')
 yield waitfor('Dropped supplies are collected again and construction resumes',lambda:en(b,'BuildState')==2,60)
 reset()
 b=place('BP_Building_Dummy2x2',14,14,True);pile(3,2,6);setp('Bool',worker,'AutoWork',True)
 yield waitfor('Worker carries supplies before target destruction',lambda:worker.get_editor_property('CarryAmount')>0)
 b.destroy_actor()
 yield waitfor('Destroyed site releases cargo safely',lambda:worker.get_editor_property('CarryAmount')==0 and worker.get_editor_property('CurrentJob') is None,8)
 check(supplies()==6);passed('Target destruction preserves undelivered supplies')
 reset()
 b=place('BP_Building_Dummy2x2',14,14,True);setp('Double',b,'WorkRequired',0.5)
 pile(3,2,6);other=spawn('BP_Colonist',3,3);setp('Bool',other,'AutoWork',True)
 yield waitfor('Temporary worker carries supplies before destruction',lambda:other.get_editor_property('CarryAmount')>0)
 other.destroy_actor()
 check(supplies()==6);passed('Destroying a carrier drops its inventory into the world')
 setp('Bool',worker,'AutoWork',True)
 yield waitfor('Another worker recovers the dropped cargo and completes the site',lambda:en(b,'BuildState')==2,60)
 reset()
runner=run_tests();pending=None;deadline=0
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
  report['finished']=time.time();report['status']='passed';unreal.unregister_slate_post_tick_callback(HANDLE)
 except Exception:
  report['failed'].append(traceback.format_exc());report['status']='failed';unreal.unregister_slate_post_tick_callback(HANDLE)
 finally:
  report['current']=pending[0] if pending else None
  (ROOT/'Saved/Codex/material_runtime_results.json').write_text(json.dumps(report,indent=2))
HANDLE=unreal.register_slate_post_tick_callback(tick_suite)
