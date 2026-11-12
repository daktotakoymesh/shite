"""PIE checks for the compact inspector. Restores worker/selection state.

Temporary buildings/piles are spawned outside the grid and destroyed afterwards.
Tests exercise actual widget functions, reflected gameplay data and storage rules.
No Blueprint assets are edited or saved by this test.
"""
import json
import math
import traceback
from pathlib import Path
import unreal

ROOT = Path('D:/shite-visual')
assert Path(unreal.Paths.get_project_file_path()).resolve() == ROOT / 'shite.uproject'
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world, 'Run this test in PIE'
game = unreal.get_default_object(unreal.GameplayStatics)
system = unreal.get_default_object(unreal.SystemLibrary)
report = {'passed': [], 'failed': []}
spawned = []


def cls(name):
    result = unreal.load_class(None, '/Game/' + name + '.' + name + '_C')
    assert result, name
    return result


def get(obj, name):
    return obj.get_editor_property(name)


def setp(kind, obj, name, value):
    system.call_method('Set' + kind + 'PropertyByName', (obj, unreal.Name(name), value))


def spawn(name):
    transform = unreal.Transform(location=unreal.Vector(-9000., -9000., 50.))
    actor = game.call_method('BeginDeferredActorSpawnFromClass', (
        world, cls(name), transform, unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,
        None, unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    assert actor, name
    actor = game.call_method('FinishSpawningActor', (actor, transform, unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    spawned.append(actor)
    return actor


def check(condition, message):
    assert condition, message


def case(name, fn):
    try:
        fn()
        report['passed'].append(name)
    except Exception:
        report['failed'].append({'name': name, 'error': traceback.format_exc()})


grids = unreal.GameplayStatics.get_all_actors_of_class(world, cls('BP_GridManager'))
workers = unreal.GameplayStatics.get_all_actors_of_class(world, cls('BP_Colonist'))
assert grids and workers, 'Expected the normal test level with grid and colonists'
inspector = get(grids[0], 'InspectorWidget')
worker = workers[0]
assert inspector, 'Inspector was not created'
old_selected = get(inspector, 'SelectedActor')
fields = {'AutoWork': 'Bool', 'NeedsEnabled': 'Bool', 'IsMoving': 'Bool',
          'CarryAmount': 'Int', 'CarryResource': 'Name', 'CurrentJob': 'Object'}
saved = {key: get(worker, key) for key in fields}
need_saved = [(need, get(need, 'Level')) for need in get(worker, 'Needs') if need]
before_location = worker.get_actor_location()
before_path_index = get(worker, 'PathIndex')


def widget(name):
    return get(inspector, name)


def text(name):
    return str(get(widget(name), 'text'))


def visibility(name):
    return get(widget(name), 'visibility')


def select(actor, update_tag=False):
    setp('Object', inspector, 'SelectedActor', actor)
    inspector.call_method('RefreshInspection', ())
    if update_tag:
        inspector.call_method('UI_UpdateSelectionTag', ())


def meter(index, value, label):
    check(visibility('MeterRow' + str(index)) != unreal.SlateVisibility.COLLAPSED, 'Meter row is hidden')
    percent = float(get(widget('MeterBar' + str(index)), 'percent'))
    check(math.isclose(percent, value, abs_tol=1e-4), f'{label}: expected {value}, got {percent}')
    check(label in text('MeterCaption' + str(index)), f'Meter label missing: {label}')


try:
    setp('Bool', worker, 'AutoWork', False)
    setp('Bool', worker, 'NeedsEnabled', False)
    setp('Bool', worker, 'IsMoving', False)
    setp('Int', worker, 'CarryAmount', 3)
    setp('Name', worker, 'CarryResource', unreal.Name('Food'))
    job = unreal.new_object(cls('BP_Job_Construction'), outer=worker)
    setp('String', job, 'JobDisplayName', 'Test construction')
    setp('Object', worker, 'CurrentJob', job)
    for need, unused in need_saved:
        n = str(get(need, 'NeedName'))
        if n in ('Nutrition', 'Rest'):
            setp('Double', need, 'Level', 25. if n == 'Nutrition' else 80.)

    def colonist():
        select(worker)
        check(text('InspectionTitle') == str(get(worker, 'ColonistName')), 'Colonist name is wrong')
        body = text('InspectorText')
        check('Test construction' in body and 'Food' in body and 'Carrying 3' in body, 'Task/cargo summary missing')
        check('Work rate' in body and 'Speed' in body, 'Worker stats missing')
        meter(1, .25, 'Nutrition'); meter(2, .80, 'Rest')
        check(visibility('StorageControls') == unreal.SlateVisibility.COLLAPSED, 'Stock controls visible on colonist')
    case('Selected colonist shows name, task, cargo, stats and live needs', colonist)

    wall = spawn('BP_Wall')
    setp('Byte', wall, 'BuildState', 1)
    setp('Int', wall, 'MaterialCost', 12)
    setp('Int', wall, 'MaterialsDelivered', 3)
    setp('Double', wall, 'WorkRequired', 20.)
    setp('Double', wall, 'WorkDone', 5.)

    def construction():
        select(wall)
        check('Under construction' in text('InspectorText'), 'Construction status missing')
        meter(1, .25, 'Materials'); meter(2, .25, 'Construction')
        check('3 / 12' in text('MeterCaption1'), 'Material counts wrong')
        check(get(wall, 'MaterialsDelivered') == 3 and get(wall, 'WorkDone') == 5., 'Inspector changed construction state')
    case('Construction shows separate delivered-material and labour progress', construction)

    station = spawn('BP_ProductionStation')
    output = spawn('BP_ResourcePile')
    setp('Byte', station, 'BuildState', 2)
    setp('Double', station, 'ProductionWorkRequired', 10.)
    setp('Double', station, 'ProductionProgress', 5.)
    setp('Bool', station, 'ProductionEnabled', True)
    setp('Int', station, 'OutputPerBatch', 2)
    setp('Int', station, 'OutputCapacity', 20)
    setp('Int', output, 'Amount', 3)
    setp('Object', station, 'OutputPile', output)

    def production():
        select(station)
        meter(1, .5, 'Production'); meter(2, .15, 'Output')
        check('Building materials' in text('InspectorText'), 'Friendly output name missing')
        setp('Int', output, 'Amount', 20)
        select(station)
        check('Output full' in text('InspectorText'), 'Full-output status missing')
        meter(2, 1., 'Output')
        setp('Bool', station, 'ProductionEnabled', False)
        select(station)
        check('paused' in text('InspectorText').lower(), 'Paused production status missing')
        check(get(output, 'Amount') == 20, 'Inspection changed output inventory')
    case('Production and output meters follow live state and show full/paused status', production)

    shelf = spawn('BP_Stockpile')
    stock = spawn('BP_ResourcePile')
    setp('Byte', shelf, 'BuildState', 2)
    setp('Int', shelf, 'StorageCapacity', 100)
    setp('Name', shelf, 'AcceptedResource', unreal.Name('BuildingMaterial'))
    setp('Object', shelf, 'StoredPile', stock)
    setp('Object', stock, 'StorageOwner', shelf)
    setp('Name', stock, 'ResourceType', unreal.Name('BuildingMaterial'))
    setp('Int', stock, 'Amount', 40)

    def storage():
        select(shelf)
        meter(1, .4, 'Stored')
        check(visibility('MeterRow2') == unreal.SlateVisibility.COLLAPSED, 'Irrelevant second storage meter visible')
        check(visibility('StorageControls') != unreal.SlateVisibility.COLLAPSED, 'Storage controls missing')
        inspector.call_method('SelectStoredResource', (unreal.Name('Food'),))
        check(str(get(shelf, 'AcceptedResource')) == 'BuildingMaterial', 'Filter changed while storage contained materials')
        check(get(stock, 'Amount') == 40, 'Rejected filter change altered inventory')
        check('Cannot switch' in text('StorageHint'), 'Rejected-filter hint missing')
        setp('Int', stock, 'Amount', 0)
        inspector.call_method('SelectStoredResource', (unreal.Name('Food'),))
        check(str(get(shelf, 'AcceptedResource')) == 'Food', 'Empty shelf could not change resource')
    case('Storage meter and existing empty-only filter change rules are preserved', storage)

    def completed_and_pile():
        setp('Byte', wall, 'BuildState', 2)
        select(wall)
        check(text('InspectorText') == 'Completed', 'Completed building status wrong')
        check(all(visibility('MeterRow' + str(i)) == unreal.SlateVisibility.COLLAPSED for i in (1, 2)), 'Completed wall retained meters')
        setp('Name', output, 'ResourceType', unreal.Name('Food'))
        setp('Int', output, 'Amount', 17)
        select(output)
        check(text('InspectionTitle') == 'Food' and '17' in text('InspectorText'), 'Stack identity/count wrong')
        check(visibility('StorageControls') == unreal.SlateVisibility.COLLAPSED, 'Stack retained storage controls')
    case('Changing selection hides irrelevant meters and retains stack counts', completed_and_pile)

    def clamps():
        for value, maximum, expected in [(12., 10., 1.), (-4., 10., 0.), (0., 0., 1.)]:
            inspector.call_method('UI_SetMeter', (widget('MeterRow1'), widget('MeterCaption1'),
                                                 widget('MeterBar1'), 'Clamp check', value, maximum))
            meter(1, expected, 'Clamp check')
    case('Progress is clamped and zero-cost targets are complete without division by zero', clamps)

    def selected_tag():
        camera = unreal.GameplayStatics.get_player_camera_manager(world, 0)
        location = camera.get_camera_location()
        forward = unreal.MathLibrary.get_forward_vector(camera.get_camera_rotation())
        output.set_actor_location(location + forward * 1000., False, True)
        select(output, True)
        check(visibility('SelectionTag') == unreal.SlateVisibility.HIT_TEST_INVISIBLE, 'Selected label should be visible without capturing input')
        check('Food' in text('SelectionTagText'), 'Selected label does not match inspector')
        slot = get(widget('SelectionTag'), 'slot')
        position = slot.get_position()
        check(math.isfinite(position.x) and math.isfinite(position.y), 'Projected label position is not finite')
        select(None, True)
        check(visibility('SelectionTag') == unreal.SlateVisibility.COLLAPSED, 'Label visible with no selection')
        check(all(visibility('MeterRow' + str(i)) == unreal.SlateVisibility.COLLAPSED for i in (1, 2)), 'Meters visible with no selection')
        check(visibility('StorageControls') == unreal.SlateVisibility.COLLAPSED, 'Storage controls visible with no selection')
    case('Only the selected object has a projected label and empty selection collapses contextual UI', selected_tag)

    def no_gameplay_changes():
        check(worker.get_actor_location() == before_location, 'Inspector moved the colonist')
        check(get(worker, 'PathIndex') == before_path_index, 'Inspector changed path state')
        check(get(worker, 'CarryAmount') == 3, 'Inspector consumed carried food')
    case('Inspector refreshes do not alter colonist movement or inventory', no_gameplay_changes)
finally:
    for name, kind in fields.items():
        setp(kind, worker, name, saved[name])
    for need, value in need_saved:
        setp('Double', need, 'Level', value)
    for actor in spawned:
        actor.destroy_actor()
    setp('Object', inspector, 'SelectedActor', old_selected)
    inspector.call_method('RefreshInspection', ())
    inspector.call_method('UI_UpdateSelectionTag', ())

RESULT = report
(ROOT / 'Saved/Codex/ui_cosmetics_test_results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
assert not report['failed'], report['failed']
