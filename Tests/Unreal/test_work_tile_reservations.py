"""Work-tile reservations: actual Blueprint calls and live PIE workers."""
import unreal,json,time,traceback
from pathlib import Path
ROOT=Path(unreal.Paths.project_dir())
source=(ROOT/'Tests/Unreal/test_autonomous_builders.py').read_text()
exec(source[:source.index('def unfinished():')],globals())
report={'passed':[],'failed':[]}
def available(t,w):return gm.call_method('IsWorkTileAvailable',(t,w))
def other_at(x,y):
 w=spawn('BP_Colonist',x,y);setp('Bool',w,'AutoWork',False);setp('Double',w,'BaseMoveSpeed',600.0)
 return w
def reserve(w):
 j,t=manager.call_method('FindJobForWorker',(w,))
 if j:setp('Object',w,'CurrentJob',j)
 return j,t
def shared():
 a=place('BP_Road',5,4);b=place('BP_Road',4,5)
 for x,y in [(5,3),(6,4),(5,5),(3,5),(4,6)]:cell(x,y,False)
 tile(worker,3,4);other=other_at(2,4)
 manager.call_method('RefreshJobs',())
 return a,b,other
def exclusivity():
 a,b,other=shared()
 j,t=manager.call_method('FindJobForWorker',(worker,))
 check(j is not None and t==v(4,4),'first work tile')
 check(worker.get_editor_property('HasWorkTileReservation'))
 check(not available(t,other),'reservation must apply before caller assigns CurrentJob')
 check(available(t,worker),'owner can reuse its spot')
 j2,t2=reserve(other);check(j2 is None,'second worker must wait')
 setp('Object',worker,'CurrentJob',j);worker.call_method('ReleaseJob',())
 check(not worker.get_editor_property('HasWorkTileReservation'))
 check(available(t,other),'released tile')
 j2,t2=reserve(other);check(j2 is not None and t2==t,'waiting worker can acquire released tile')
case('Shared sole work tile is claimed atomically, released, and reused',exclusivity)
def occupied():
 other=other_at(4,4)
 check(not available(v(4,4),worker) and available(v(4,4),other))
 other.call_method('RequestMove',(v(5,4),))
 check(other.get_editor_property('IsMoving'))
 check(not available(other.get_editor_property('NextTile'),worker))
case('Occupied tiles and incoming movement tiles are excluded',occupied)
def destruction():
 a,b,other=shared();j,t=reserve(other)
 check(j is not None and not available(t,worker))
 other.destroy_actor()
 check(available(t,worker),'destroyed worker leaves no claim')
case('Destroyed workers leave no stale work-tile reservation',destruction)
def alternatives():
 a=place('BP_Road',5,4);b=place('BP_Road',4,5)
 other=other_at(3,3);manager.call_method('RefreshJobs',())
 j,t=reserve(worker);j2,t2=reserve(other)
 check(j is not None and j2 is not None and t!=t2)
case('Nearby jobs choose different work positions when alternatives exist',alternatives)
def arrival():
 a=place('BP_Road',8,8);other=other_at(1,1);manager.call_method('RefreshJobs',())
 j,t=reserve(worker)
 # Re-evaluating a journey must stop targeting a spot newly occupied by another pawn.
 tile(other,int(t.x),int(t.y))
 worker.call_method('TravelToCurrentJob',())
 check(worker.get_editor_property('CurrentJob') is not None)
 check(worker.get_editor_property('JobWorkTile')!=t)
 check(worker.get_editor_property('HasWorkTileReservation'))
case('Travel re-evaluation replaces a newly occupied work position',arrival)

def enable(w):
 setp('Double',w,'BaseMoveSpeed',600.0);setp('Bool',w,'AutoWork',True)
def assert_unique():
 claimed=[];working=[]
 for w in actors('BP_Colonist'):
  if w.get_editor_property('HasWorkTileReservation'):
   t=w.get_editor_property('JobWorkTile');claimed.append((t.x,t.y))
  if en(w,'WorkerActivity')==2:
   t=w.get_editor_property('CurrentTile');working.append((t.x,t.y))
 check(len(claimed)==len(set(claimed)),'duplicate claimed work tiles')
 check(len(working)==len(set(working)),'builders working on the same tile')
def live():
 reset();a,b,other=shared()
 for site in [a,b]:setp('Double',site,'WorkRequired',2.0)
 enable(worker);enable(other)
 yield ('Both sites finish when only one shared work position exists',lambda:en(a,'BuildState')==2 and en(b,'BuildState')==2,30)
 yield ('Completed work releases all tile reservations',lambda:all(not w.get_editor_property('HasWorkTileReservation') for w in actors('BP_Colonist')),8)
 reset()
 a=place('BP_Road',5,4);b=place('BP_Road',4,5);other=other_at(3,3)
 for site in [a,b]:setp('Double',site,'WorkRequired',3.0)
 enable(worker);enable(other)
 yield ('Two builders work simultaneously from different positions',lambda:en(worker,'WorkerActivity')==2 and en(other,'WorkerActivity')==2,20)
 yield ('Both simultaneous construction jobs complete',lambda:en(a,'BuildState')==2 and en(b,'BuildState')==2,20)
 reset()
base_live=live
def live():
 yield from base_live()
 a=place('BP_Road',10,10);setp('Double',a,'WorkRequired',1.0);other=other_at(1,1)
 enable(worker)
 yield ('Worker reserves its destination before arrival',lambda:worker.get_editor_property('HasWorkTileReservation') and worker.get_editor_property('IsMoving'),12)
 current=worker.get_editor_property('JobWorkTile')
 original=v(current.x,current.y)  # Snapshot: reflected struct properties alias mutable Blueprint storage.
 tile(other,int(original.x),int(original.y))
 yield ('Occupied destination at arrival triggers a different work position',lambda:worker.get_editor_property('HasWorkTileReservation') and worker.get_editor_property('JobWorkTile')!=original,15)
 yield ('Construction finishes after arrival reselects a work position',lambda:en(a,'BuildState')==2,15)
 reset()
runner=live();pending=None;deadline=0
def tick_suite(delta):
 global pending,deadline,HANDLE
 try:
  assert_unique()
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
  (ROOT/'Saved/Codex/work_tile_reservation_results.json').write_text(json.dumps(report,indent=2))
HANDLE=unreal.register_slate_post_tick_callback(tick_suite)
