
"""Asynchronous PIE tests: real game tick, movement, cancellation and multiple builders."""
import unreal,json,traceback,time
from pathlib import Path
ROOT=Path(unreal.Paths.project_dir())
# Execute reusable fixture definitions only, without rerunning static cases.
source=(ROOT/'Tests/Unreal/test_autonomous_builders.py').read_text()
exec(source[:source.index("def unfinished():")],globals())
report={'passed':[],'failed':[],'started':time.time()}
def waitfor(name,predicate,seconds=30):return (name,predicate,seconds)
def run_tests():
 reset()
 a=place('BP_Road',4,4);b=place('BP_Building_Dummy2x2',7,4)
 for site in [a,b]:setp('Double',site,'WorkRequired',0.5)
 setp('Bool',worker,'AutoWork',True)
 yield waitfor('Worker completes road and solid building autonomously',lambda:en(a,'BuildState')==2 and en(b,'BuildState')==2,35)
 check(worker.get_editor_property('CurrentJob') is None)
 report['passed'].append('Completed job leaves worker available')
 reset()
 a=place('BP_Road',5,5);b=place('BP_Road',12,5);c=place('BP_Road',8,10)
 for site in [a,b,c]:setp('Double',site,'WorkRequired',1.0)
 second=spawn('BP_Colonist',13,4)
 setp('Bool',worker,'AutoWork',True);setp('Bool',second,'AutoWork',True)
 yield waitfor('Two workers hold distinct live reservations',lambda:worker.get_editor_property('CurrentJob') is not None and second.get_editor_property('CurrentJob') is not None and worker.get_editor_property('CurrentJob')!=second.get_editor_property('CurrentJob'))
 yield waitfor('Two autonomous workers finish a shared job queue',lambda:all(en(s,'BuildState')==2 for s in [a,b,c]),45)
 reset()
 site=place('BP_Road',12,12);setp('Double',site,'WorkRequired',0.5);setp('Bool',worker,'AutoWork',True)
 yield waitfor('Worker begins travelling to a construction job',lambda:en(worker,'WorkerActivity')==1 and worker.get_editor_property('IsMoving'))
 abandoned=worker.get_editor_property('CurrentJob')
 manual_id=worker.call_method('RequestMove',(v(0,0),))
 yield waitfor('Manual command releases construction reservation',lambda:worker.get_editor_property('CurrentJob') is None and abandoned.get_editor_property('AssignedWorker') is None,5)
 check(worker.get_editor_property('CurrentMoveRequestID')==manual_id)
 report['passed'].append('Old job cancellation does not cancel newer manual movement')
 yield waitfor('Manual movement reaches its requested destination',lambda:worker.get_editor_property('CurrentTile')==v(0,0),20)
 yield waitfor('Worker resumes construction after manual movement',lambda:en(site,'BuildState')==2,45)
 reset()
 site=place('BP_Road',3,2);setp('Double',site,'WorkRequired',2.0);setp('Bool',worker,'AutoWork',True)
 yield waitfor('Worker starts adding construction labour',lambda:site.get_editor_property('WorkDone')>0.1)
 prior=site.get_editor_property('WorkDone');worker.call_method('RequestMove',(v(0,0),))
 yield waitfor('Manual movement interrupts active labour',lambda:worker.get_editor_property('CurrentJob') is None,5)
 check(site.get_editor_property('WorkDone')>=prior)
 report['passed'].append('Interrupted work preserves accumulated labour')
 yield waitfor('Interrupted building is eventually resumed and completed',lambda:en(site,'BuildState')==2,25)
 reset()
 site=place('BP_Road',13,13);setp('Bool',worker,'AutoWork',True)
 yield waitfor('Worker reserves site before target destruction',lambda:worker.get_editor_property('CurrentJob') is not None)
 job=worker.get_editor_property('CurrentJob');site.destroy_actor()
 yield waitfor('Destroyed target releases travelling worker',lambda:worker.get_editor_property('CurrentJob') is None and not worker.get_editor_property('IsMoving'),8)
 check(en(job,'State')==5);report['passed'].append('Destroyed target job is cancelled')
 reset()
 site=place('BP_Road',13,13);setp('Double',site,'WorkRequired',0.5);setp('Bool',worker,'AutoWork',True)
 yield waitfor('Worker has a multi-step path before obstacle insertion',lambda:len(worker.get_editor_property('ActivePath'))>5 and worker.get_editor_property('IsMoving'))
 route=list(worker.get_editor_property('ActivePath'));index=worker.get_editor_property('PathIndex')
 obstacle=route[min(index+2,len(route)-2)];cell(int(obstacle.x),int(obstacle.y),False)
 yield waitfor('Worker replans around a new obstacle and finishes',lambda:en(site,'BuildState')==2,45)
 reset()
 site=place('BP_Road',10,10);setp('Double',site,'WorkRequired',0.5)
 temporary=spawn('BP_Colonist',9,9);setp('Bool',temporary,'AutoWork',True)
 yield waitfor('Temporary worker reserves a site',lambda:temporary.get_editor_property('CurrentJob') is not None)
 temporary.destroy_actor();setp('Bool',worker,'AutoWork',True)
 yield waitfor('Surviving worker recovers abandoned job and completes it',lambda:en(site,'BuildState')==2,35)
 reset()
runner=run_tests();pending=None;deadline=0
def tick_suite(delta):
 global pending,deadline,HANDLE
 try:
  if pending:
   name,predicate,seconds=pending
   if predicate():report['passed'].append(name);pending=None
   elif time.monotonic()>deadline:raise AssertionError('Timed out: '+name)
   else:return
  pending=next(runner)
  deadline=time.monotonic()+pending[2]
 except StopIteration:
  report['finished']=time.time();report['status']='passed'
  unreal.unregister_slate_post_tick_callback(HANDLE)
 except Exception:
  report['failed'].append(traceback.format_exc());report['status']='failed'
  unreal.unregister_slate_post_tick_callback(HANDLE)
 finally:
  report['current']=pending[0] if pending else None
  (ROOT/'Saved/Codex/autonomous_runtime_results.json').write_text(json.dumps(report,indent=2))
HANDLE=unreal.register_slate_post_tick_callback(tick_suite)
