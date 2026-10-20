"""Shared-site worker slots, finite material claims, and live cooperative construction."""
import unreal,json,time,traceback
from pathlib import Path
ROOT=Path(unreal.Paths.project_dir())
source=(ROOT/'Tests/Unreal/test_autonomous_builders.py').read_text()
exec(source[:source.index('def unfinished():')],globals())
report={'passed':[],'failed':[]}
def newworker(x,y):
 w=spawn('BP_Colonist',x,y);setp('Bool',w,'AutoWork',False);setp('Double',w,'BaseMoveSpeed',600.0)
 return w
def site(x=10,y=10,cost=6,builders=4,haulers=4):
 gm.call_method('StartPlacement',(cls('BP_Building_Dummy2x2'),))
 b=gm.get_editor_property('CurrentGhostBuilding')
 for n,value in [('MaterialCost',cost),('MaxConstructionWorkers',builders),('MaxDeliveryWorkers',haulers)]:setp('Int',b,n,value)
 harness.call_method('SetHoveredTile',(gm,v(x,y)));b.set_actor_location(gm.call_method('GridToWorld',(v(x,y),)),False,False)
 gm.call_method('ConfrimPlacement',());return b
def pile(x,y,amount):
 p=spawn('BP_ResourcePile',x,y);setp('Int',p,'Amount',amount);return p
def assign(w):
 j,t=manager.call_method('FindJobForWorker',(w,))
 if j:setp('Object',w,'CurrentJob',j)
 return j,v(t.x,t.y)
def claims(b):
 return sum(w.get_editor_property('ReservedDeliveryAmount') for w in actors('BP_Colonist') if w.get_editor_property('ReservedDeliveryTarget')==b)
def supply():
 return sum(p.get_editor_property('Amount') for p in actors('BP_ResourcePile'))+sum(w.get_editor_property('CarryAmount') for w in actors('BP_Colonist'))+sum(b.get_editor_property('MaterialsDelivered') for b in actors('BP_BuildingBase'))
def reservation_case():
 b=site(cost=5);pile(2,2,20);other=newworker(3,2);third=newworker(4,2)
 manager.call_method('RefreshJobs',())
 j,t=assign(worker);j2,t2=assign(other);j3,t3=assign(third)
 check(j is not None and j2 is not None and j!=j2 and j3 is None)
 check(j.get_editor_property('TargetActor')==b and j2.get_editor_property('TargetActor')==b)
 check([worker.get_editor_property('ReservedDeliveryAmount'),other.get_editor_property('ReservedDeliveryAmount')]==[3,2])
 check(t!=t2 and claims(b)==5)
 worker.call_method('ReleaseJob',())
 check(claims(b)==2 and b.call_method('GetUnreservedMaterialAmount',(None,))==3)
 j3,t3=assign(third);check(j3 is not None and claims(b)==5)
case('Shared delivery claims split a five-unit cost into 3+2 and release on cancellation',reservation_case)
def scarcity():
 b=site(cost=1);pile(2,2,30);other=newworker(3,2)
 manager.call_method('RefreshJobs',());j,t=assign(worker);j2,t2=assign(other)
 check(j is not None and j2 is None and claims(b)==1)
case('A one-unit remainder never recruits a redundant second hauler',scarcity)
def slots():
 b=site(cost=0,builders=2,haulers=0)
 for i in range(5):manager.call_method('RefreshJobs',())
 jobs=list(manager.get_editor_property('ActiveJobs'))
 check(len(jobs)==2 and len(set(str(j.get_editor_property('JobKey')) for j in jobs))==2)
 other=newworker(3,2);third=newworker(4,2)
 j,t=assign(worker);j2,t2=assign(other);j3,t3=assign(third)
 check(j is not None and j2 is not None and j3 is None)
case('Configured site worker limit is respected and repeated refresh does not duplicate slots',slots)
def destruction():
 b=site();pile(2,2,20);other=newworker(3,2)
 manager.call_method('RefreshJobs',());j,t=assign(other)
 check(claims(b)==3);other.destroy_actor()
 check(claims(b)==0 and b.call_method('GetUnreservedMaterialAmount',(None,))==6)
case('Destroying a reserved hauler immediately frees its quantity claim',destruction)
def shortage():
 b=site();p=pile(2,2,1);other=newworker(3,2)
 manager.call_method('RefreshJobs',());j,t=assign(worker);j2,t2=assign(other)
 tile(worker,int(t.x),int(t.y))
 result=j.call_method('PerformWork',(worker,gm,1.0))
 check(result==(False,True,True) and worker.get_editor_property('ReservedDeliveryAmount')==1)
 check(claims(b)==4 and b.call_method('GetUnreservedMaterialAmount',(None,))==2)
 check(supply()==1)
case('Partial pickup reduces the claim to actual cargo without losing materials',shortage)
def enable(w):setp('Double',w,'BaseMoveSpeed',600.0);setp('Bool',w,'AutoWork',True)
def working(w,b):
 j=w.get_editor_property('CurrentJob')
 return j is not None and j.get_editor_property('TargetActor')==b and en(w,'WorkerActivity')==2 and w.get_editor_property('CarryAmount')==0
def invariant():
 used=[]
 for w in actors('BP_Colonist'):
  if w.get_editor_property('HasWorkTileReservation'):
   t=w.get_editor_property('JobWorkTile');used.append((t.x,t.y))
 check(len(used)==len(set(used)),'work tile claimed twice')
 for b in actors('BP_BuildingBase'):
  check(claims(b)+b.get_editor_property('MaterialsDelivered')<=b.get_editor_property('MaterialCost'),'material demand overcommitted')
def live():
 reset()
 b=site(8,8,cost=0);setp('Double',b,'WorkRequired',100.0);other=newworker(3,2)
 enable(worker);enable(other)
 yield ('Two builders perform labour on the same building simultaneously',lambda:working(worker,b) and working(other,b),20)
 before=b.get_editor_property('WorkDone')
 worker.call_method('UpdateJob',(0.5,));other.call_method('UpdateJob',(0.5,))
 check(abs(b.get_editor_property('WorkDone')-before-1.0)<0.0001)
 report['passed'].append('Both builders add labour to the same shared progress total')
 setp('Double',b,'WorkRequired',b.get_editor_property('WorkDone')+1.0)
 yield ('Cooperative construction completes exactly once',lambda:en(b,'BuildState')==2,10)
 yield ('All builders release their claims after shared completion',lambda:all(w.get_editor_property('CurrentJob') is None and not w.get_editor_property('HasWorkTileReservation') for w in actors('BP_Colonist')),8)
 reset()
 b=site(14,14,cost=5);setp('Double',b,'WorkRequired',3.0);pile(2,2,20);other=newworker(3,2);third=newworker(4,2)
 enable(worker);enable(other);enable(third)
 yield ('Two colonists carry materials to the same site concurrently',lambda:sum(w.get_editor_property('CarryAmount')>0 and w.get_editor_property('ReservedDeliveryTarget')==b for w in actors('BP_Colonist'))>=2,20)
 yield ('Concurrent hauling funds and completes the building',lambda:en(b,'BuildState')==2,30)
 check(b.get_editor_property('MaterialsDelivered')==5 and supply()==20)
 check(sum(p.get_editor_property('Amount') for p in actors('BP_ResourcePile'))==15)
 report['passed'].append('Concurrent deliveries consume exactly five materials with no excess cargo')
 reset()
 b=site(14,14,cost=6);setp('Double',b,'WorkRequired',1.0);pile(2,2,6);other=newworker(3,2)
 enable(worker);enable(other)
 yield ('Both haulers carry before one is manually interrupted',lambda:worker.get_editor_property('CarryAmount')>0 and other.get_editor_property('CarryAmount')>0,20)
 worker.call_method('RequestMove',(v(0,0),))
 yield ('Manual interruption releases material and work-position reservations',lambda:worker.get_editor_property('CurrentJob') is None and worker.get_editor_property('ReservedDeliveryAmount')==0 and not worker.get_editor_property('HasWorkTileReservation'),8)
 check(supply()==6)
 yield ('Remaining and recovered deliveries complete the shared site',lambda:en(b,'BuildState')==2,40)
 check(supply()==6 and claims(b)==0)
 report['passed'].append('Interrupted concurrent delivery preserves every material')
 reset()
runner=live();pending=None;deadline=0
def tick_suite(delta):
 global pending,deadline,HANDLE
 try:
  invariant()
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
  (ROOT/'Saved/Codex/multiworker_site_results.json').write_text(json.dumps(report,indent=2))
HANDLE=unreal.register_slate_post_tick_callback(tick_suite)
