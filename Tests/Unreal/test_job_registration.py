"""Exercise the actual RegisterJob Blueprint in the editor; restore all CDO state."""
import json
import traceback
from pathlib import Path
import unreal

report = {'passed': [], 'failed': []}
restores = []
keep_alive = []
system = unreal.get_default_object(unreal.SystemLibrary)

def runtime_set(kind, obj, name, value):
    system.call_method('Set' + kind + 'PropertyByName', (obj, unreal.Name(name), value))

def remember(obj, names):
    values = {}
    for name in names:
        value = obj.get_editor_property(name)
        values[name] = list(value) if name == 'ActiveJobs' else value
    restores.append((obj, values))

def check(name, condition):
    if not condition:
        raise AssertionError(name)
    report['passed'].append(name)

try:
    manager_class = unreal.load_class(None, '/Game/BP_JobManager.BP_JobManager_C')
    job_class = unreal.load_class(None, '/Game/BP_Job_Construction.BP_Job_Construction_C')
    base_class = unreal.load_class(None, '/Game/BP_JobBase.BP_JobBase_C')
    building_class = unreal.load_class(None, '/Game/BP_BuildingBase.BP_BuildingBase_C')
    road_class = unreal.load_class(None, '/Game/BP_Road.BP_Road_C')
    manager = unreal.get_default_object(manager_class)
    building = unreal.get_default_object(building_class)
    road = unreal.get_default_object(road_class)
    remember(manager, ['ActiveJobs', 'NextJobID'])
    remember(building, ['BuildState'])
    remember(road, ['BuildState'])
    build_enum = type(building.get_editor_property('BuildState'))
    state_enum = type(unreal.get_default_object(job_class).get_editor_property('State'))
    manager.set_editor_property('ActiveJobs', [])
    manager.set_editor_property('NextJobID', 1)

    def make(target=building, key='Construction', cls=job_class, job_id=-1):
        obj = unreal.new_object(cls)
        keep_alive.append(obj)
        runtime_set('Object', obj, 'TargetActor', target)
        runtime_set('Name', obj, 'JobKey', unreal.Name(key))
        runtime_set('Int', obj, 'JobID', job_id)
        return obj

    def register(job):
        return manager.call_method('RegisterJob', (job,))

    def rejected(name, job):
        before_id = manager.get_editor_property('NextJobID')
        before_jobs = list(manager.get_editor_property('ActiveJobs'))
        result, accepted = register(job)
        check(name, not accepted and result is None
              and manager.get_editor_property('NextJobID') == before_id
              and list(manager.get_editor_property('ActiveJobs')) == before_jobs)

    rejected('null job rejected without changing registry', None)
    rejected('missing target rejected', make(target=None))
    rejected('None job key rejected', make(key='None'))
    rejected('foreign assigned ID rejected', make(job_id=99))
    building.set_editor_property('BuildState', build_enum.cast(0))
    rejected('preview building rejected', make())
    building.set_editor_property('BuildState', build_enum.cast(2))
    rejected('completed building rejected', make())
    building.set_editor_property('BuildState', build_enum.cast(1))
    road.set_editor_property('BuildState', build_enum.cast(1))
    rejected('base job fallback rejected', make(cls=base_class))
    rejected('non-building target rejected', make(target=manager))

    first = make()
    result, accepted = register(first)
    check('new construction job gets ID 1 and Available state',
          accepted and result == first and first.get_editor_property('JobID') == 1
          and first.get_editor_property('State') == state_enum.cast(1)
          and list(manager.get_editor_property('ActiveJobs')) == [first]
          and manager.get_editor_property('NextJobID') == 2)
    result, accepted = register(first)
    check('same-object registration is idempotent', accepted and result == first
          and len(manager.get_editor_property('ActiveJobs')) == 1
          and manager.get_editor_property('NextJobID') == 2)

    for state, name in enumerate(['Waiting', 'Available', 'Reserved', 'InProgress']):
        runtime_set('Byte', first, 'State', state)
        duplicate = make()
        result, accepted = register(duplicate)
        check('duplicate reuses existing ' + name + ' job',
              accepted and result == first and duplicate.get_editor_property('JobID') == -1
              and first.get_editor_property('State') == state_enum.cast(state)
              and len(manager.get_editor_property('ActiveJobs')) == 1
              and manager.get_editor_property('NextJobID') == 2)

    different_key = make(key='ConstructionAlternative')
    result, accepted = register(different_key)
    check('different key on same target is distinct', accepted and result == different_key
          and different_key.get_editor_property('JobID') == 2)
    different_target = make(target=road)
    result, accepted = register(different_target)
    check('same key on different target is distinct', accepted and result == different_target
          and different_target.get_editor_property('JobID') == 3)

    for state, name in [(4, 'Completed'), (5, 'Cancelled'), (6, 'Failed')]:
        runtime_set('Byte', first, 'State', state)
        manager.set_editor_property('ActiveJobs', [None, first])
        candidate = make()
        before_id = manager.get_editor_property('NextJobID')
        result, accepted = register(candidate)
        check(name + ' entries and null entries do not block a new job',
              accepted and result == candidate and candidate.get_editor_property('JobID') == before_id
              and manager.get_editor_property('NextJobID') == before_id + 1)

    rejected('rejection after success does not leak previous return object', None)
except Exception:
    report['failed'].append(traceback.format_exc())
finally:
    for obj, values in reversed(restores):
        try:
            for name, value in values.items():
                obj.set_editor_property(name, value)
        except Exception:
            report['failed'].append('restore: ' + traceback.format_exc())
    output = Path(unreal.Paths.project_saved_dir()) / 'Codex' / 'job_registration_test_results.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2))
    unreal.log('RegisterJob tests: {} passed, {} failed'.format(len(report['passed']), len(report['failed'])))
