
import unreal,time,json,traceback
from pathlib import Path
root=Path(unreal.Paths.project_dir())
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
gm=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.load_class(None,'/Game/BP_GridManager.BP_GridManager_C'))[0]
cam=unreal.GameplayStatics.get_player_pawn(world,0)
original_location=cam.get_actor_location()
result={'passed':[],'failed':[],'measurements':{}}
def cases():
 rates=[]
 for factor in [1,8]:
  gm.call_method('SetSimulationSpeed',(float(factor),))
  assert abs(cam.get_editor_property('CustomTimeDilation')-1/factor)<0.00001
  yield time.monotonic()+0.5
  pos=cam.get_actor_location();start=time.monotonic()
  yield start+0.8
  end=cam.get_actor_location()
  rates.append((end-pos).length()/(time.monotonic()-start))
 result['measurements']['camera_units_per_real_second']=rates
 assert rates[0]>1 and 0.85<rates[1]/rates[0]<1.15,str(rates)
 result['passed'].append('Camera movement remains the same at 1x and 8x')
 for factor in [1,2,4,8]:
  gm.call_method('SetSimulationSpeed',(float(factor),))
  assert abs(unreal.GameplayStatics.get_global_time_dilation(world)*cam.get_editor_property('CustomTimeDilation')-1)<0.00001
 result['passed'].append('Camera effective tick time stays normal at all four game speeds')
gen=cases()
deadline=next(gen)
def tick(dt):
 global deadline,handle
 try:
  cam.add_movement_input(unreal.Vector(1,0,0),1,True)
  if time.monotonic()<deadline:return
  deadline=next(gen)
 except StopIteration:finish()
 except Exception:
  result['failed'].append(traceback.format_exc());finish()
def finish():
 unreal.unregister_slate_post_tick_callback(handle)
 gm.call_method('SetSimulationSpeed',(1.0,))
 cam.get_movement_component().stop_movement_immediately()
 cam.set_actor_location(original_location,False,False)
 result['status']='passed' if not result['failed'] else 'failed'
 (root/'Saved/Codex/camera_speed_results.json').write_text(json.dumps(result,indent=2))
handle=unreal.register_slate_post_tick_callback(tick)
