"""Run inside the copied project's PIE world; all edited worker fields are restored."""
import json
import traceback
from pathlib import Path
import unreal

ROOT = Path('D:/shite-visual')
assert Path(unreal.Paths.get_project_file_path()).resolve() == ROOT / 'shite.uproject'
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world, 'Run this smoke test in PIE.'
klass = unreal.load_class(None, '/Game/BP_Colonist.BP_Colonist_C')
workers = unreal.GameplayStatics.get_all_actors_of_class(world, klass)
assert workers
worker = workers[0]
system = unreal.get_default_object(unreal.SystemLibrary)
body = worker.get_editor_property('Body')
carry = worker.get_editor_property('CarryVisual')
dust = worker.get_editor_property('WorkDust')
status = worker.get_editor_property('NeedStatus')


def setp(kind, name, val):
    system.call_method('Set' + kind + 'PropertyByName', (worker, unreal.Name(name), val))


def get(name):
    return worker.get_editor_property(name)


def tick(seconds=.16):
    worker.call_method('UpdatePresentation', (seconds,))


def visible(component):
    return component.get_editor_property('visible')


def check(condition, message):
    assert condition, message


fields = {
    'AutoWork': 'Bool', 'NeedsEnabled': 'Bool', 'IsMoving': 'Bool',
    'CarryAmount': 'Int', 'CarryResource': 'Name', 'CurrentJob': 'Object',
    'WorkerActivity': 'Byte', 'bPresentationEnabled': 'Bool',
    'PresentationTime': 'Double', 'PresentationStatusCache': 'String',
}
saved = {n: get(n) for n in fields}
actor_location = worker.get_actor_location()
actor_rotation = worker.get_actor_rotation()
current_tile = get('CurrentTile')
path_index = get('PathIndex')
report = {'passed': [], 'failed': []}


def case(name, fn):
    try:
        fn()
        report['passed'].append(name)
    except Exception:
        report['failed'].append({'name': name, 'error': traceback.format_exc()})


try:
    setp('Bool', 'AutoWork', False)
    setp('Bool', 'NeedsEnabled', False)
    setp('Bool', 'bPresentationEnabled', True)
    setp('Bool', 'IsMoving', False)
    setp('Byte', 'WorkerActivity', 0)
    setp('Object', 'CurrentJob', None)
    setp('Int', 'CarryAmount', 0)

    def idle():
        tick()
        check(not visible(carry) and not visible(dust) and not visible(status), 'Idle visual components should all be hidden')
        check(body.get_editor_property('relative_location') == get('PresentationBodyLocation'), 'Idle Body offset changed')
    case('Idle colonist has no cargo, work puff or need label', idle)

    def wood():
        setp('Int', 'CarryAmount', 3)
        setp('Name', 'CarryResource', 'BuildingMaterial')
        tick()
        check(visible(carry), 'Cargo is hidden')
        check(carry.get_material(0).get_path_name() == '/Game/Visual/MV_Wood.MV_Wood', 'Wood cargo material wrong')
        check(get('CarryAmount') == 3, 'Visual update consumed cargo')
    case('Building material cargo is visible without changing inventory', wood)

    def food():
        setp('Name', 'CarryResource', 'Food')
        tick()
        check(visible(carry), 'Food cargo is hidden')
        check(carry.get_material(0).get_path_name() == '/Game/Visual/MV_Food.MV_Food', 'Food cargo material wrong')
        check(get('CarryAmount') == 3, 'Visual update consumed food')
    case('Food cargo uses its own appearance', food)

    def moving():
        setp('Bool', 'IsMoving', True)
        setp('Double', 'PresentationTime', .1)
        tick(.1)
        loc = body.get_editor_property('relative_location')
        base = get('PresentationBodyLocation')
        check(0.01 < loc.z - base.z <= 2.21, 'Walk bob should be small and positive')
        check(loc.x == base.x and loc.y == base.y, 'Bob must not change horizontal mesh alignment')
    case('Walk bob affects only the mesh', moving)

    def sleep():
        setp('Bool', 'IsMoving', False)
        setp('Byte', 'WorkerActivity', 2)
        need = unreal.new_object(unreal.load_class(None, '/Game/BP_Need_Sleep.BP_Need_Sleep_C'), outer=worker)
        setp('Object', 'CurrentJob', need)
        tick()
        check(visible(status), 'Sleep status hidden')
        check(str(status.get_editor_property('text')) == 'Z z z', 'Sleep text wrong')
        check(not visible(dust), 'Sleeping must not create work dust')
    case('Active sleep shows a sleep label without work dust', sleep)

    def eating():
        need = unreal.new_object(unreal.load_class(None, '/Game/BP_Need_Hunger.BP_Need_Hunger_C'), outer=worker)
        setp('Object', 'CurrentJob', need)
        tick()
        check(visible(status), 'Eating status hidden')
        check(str(status.get_editor_property('text')) == 'EATING', 'Eating text wrong')
        check(not visible(dust), 'Eating must not create work dust')
    case('Active hunger job shows eating instead of work effects', eating)

    def working():
        job = unreal.new_object(unreal.load_class(None, '/Game/BP_Job_Construction.BP_Job_Construction_C'), outer=worker)
        setp('Object', 'CurrentJob', job)
        setp('Double', 'PresentationTime', 0.)
        tick(.1)
        check(visible(dust), 'Work pulse should be visible at the chosen phase')
        check(not visible(status), 'Construction must hide need text')
    case('Construction uses work pulse and hides need text', working)

    def disabled():
        setp('Bool', 'bPresentationEnabled', False)
        tick()
        check(not visible(carry) and not visible(dust) and not visible(status), 'Disabled visuals remain visible')
        check(body.get_editor_property('relative_location') == get('PresentationBodyLocation'), 'Disabled Body location not restored')
        check(body.get_editor_property('relative_rotation') == get('PresentationBodyRotation'), 'Disabled Body rotation not restored')
        check(body.get_editor_property('relative_scale3d') == get('PresentationBodyScale'), 'Disabled Body scale not restored')
    case('Opt-out restores the authored Body transform and hides additions', disabled)

    def no_gameplay_changes():
        check(worker.get_actor_location() == actor_location, 'Actor position changed')
        check(worker.get_actor_rotation() == actor_rotation, 'Actor facing changed')
        check(get('CurrentTile') == current_tile and get('PathIndex') == path_index, 'Grid path state changed')
        check(get('CarryAmount') == 3 and str(get('CarryResource')) == 'Food', 'Inventory changed during cosmetic calls')
        for component in [carry, dust, status]:
            check(component.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION, 'Cosmetic collision is enabled')
    case('Presentation leaves actor motion, path state and inventory untouched', no_gameplay_changes)
finally:
    for name, kind in fields.items():
        val = saved[name]
        if kind == 'Byte':
            val = val.value if hasattr(val, 'value') else int(val)
        setp(kind, name, val)
    tick(0.)

RESULT = report
(ROOT / 'Saved/Codex/colonist_cosmetics_test_results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
assert not report['failed'], report['failed']
