"""Run in the visual copy's disposable PIE world after building_cosmetics.py.

This resets the test colony using its existing harness. It never saves assets.
"""
import json
from pathlib import Path
import unreal

assert Path(unreal.Paths.get_project_file_path()).resolve() == Path('D:/shite-visual/shite.uproject')
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'PIE is required.'
source = (Path(unreal.Paths.project_dir()) / 'Tests/Unreal/test_autonomous_builders.py').read_text()
exec(source[:source.index('def unfinished():')], globals())
COMPONENTS = ('CompletionPuffA', 'CompletionPuffB', 'CompletionPuffC', 'ActivityIndicator')


def presentation(actor, seconds=.01):
    actor.call_method('UpdatePresentation', (float(seconds),))


def fx(actor):
    return [actor.get_editor_property(name) for name in COMPONENTS]


def gameplay_snapshot(actor):
    result = {name: str(actor.get_editor_property(name)) for name in
              ('BuildState', 'WorkDone', 'WorkRequired', 'MaterialCost', 'MaterialsDelivered')}
    anchor = actor.get_editor_property('AnchorTIle')
    location = actor.get_actor_location()
    rotation = actor.get_actor_rotation()
    result['anchor'] = (anchor.x, anchor.y)
    result['location'] = (location.x, location.y, location.z)
    result['rotation'] = (rotation.pitch, rotation.yaw, rotation.roll)
    if unreal.MathLibrary.class_is_child_of(actor.get_class(), cls('BP_ProductionStation')):
        for name in ('ProductionProgress', 'ProductionWorkRequired', 'OutputResource', 'OutputPerBatch', 'OutputCapacity'):
            result[name] = str(actor.get_editor_property(name))
        pile = actor.get_editor_property('OutputPile')
        result['output_amount'] = pile.get_editor_property('Amount') if pile else None
    return result


def complete(actor):
    presentation(actor)
    finish_ready(actor)
    check(gm.call_method('TryCompleteConstruction', (actor,)), 'Completion failed')
    return actor


def preview_and_collision():
    gm.call_method('StartPlacement', (cls('BP_Wall'),))
    actor = gm.get_editor_property('CurrentGhostBuilding')
    before = gameplay_snapshot(actor)
    presentation(actor)
    check(all(not comp.is_visible() for comp in fx(actor)), 'Preview shows feedback')
    check(gameplay_snapshot(actor) == before, 'Presentation changed preview state')
    for comp in fx(actor):
        check(str(comp.get_collision_profile_name()) == 'NoCollision', comp.get_name())
        check(comp.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION, comp.get_name())
        check(not comp.get_editor_property('generate_overlap_events'), comp.get_name())
        check(not comp.get_editor_property('can_ever_affect_navigation'), comp.get_name())


case('Preview has no effects and every added mesh uses persistent NoCollision', preview_and_collision)


def construction_feedback():
    actor = complete(place('BP_Wall', 5, 5))
    before = gameplay_snapshot(actor)
    presentation(actor)
    check(actor.get_editor_property('PresentationPulseRemaining') > .5, 'Missing completion pulse')
    check(all(comp.is_visible() for comp in fx(actor)), 'Completion shapes or amber indicator hidden')
    check(gameplay_snapshot(actor) == before, 'Presentation changed construction state')
    presentation(actor, 1.)
    check(all(not comp.is_visible() for comp in fx(actor)), 'Completion effects did not expire')
    check(actor.get_editor_property('PresentationPulseRemaining') == 0)
    check(gameplay_snapshot(actor) == before, 'Decay changed construction state')


case('Finishing construction produces a short pulse then cleanly expires without gameplay writes', construction_feedback)


def finish_materials():
    for index, (name, material_name) in enumerate((('BP_Road', 'MV_Road'), ('BP_Wall', 'MV_Stone'), ('BP_Building_Dummy2x2', 'MV_Wood'))):
        actor = place(name, 5 + index * 3, 5)
        expected = unreal.load_asset('/Game/Visual/' + material_name)
        check(actor.get_editor_property('OriginalMaterials')[0] == expected, name + ' captured wrong finish')
        complete(actor)
        check(actor.get_editor_property('BuildingMesh').get_material(0) == expected, name + ' restored wrong finish')


case('Road, wall and building finish materials are captured before ghost/construction material changes', finish_materials)


def production_feedback():
    station = complete(place('BP_ProductionStation', 5, 5))
    presentation(station, 1.)
    presentation(station, 1.)
    tile(worker, 6, 6)
    check(station.call_method('WorkOnProduction', (worker, gm, 1.)) == (False, True))
    before = gameplay_snapshot(station)
    presentation(station)
    check(station.get_editor_property('PresentationWorkRemaining') > .25, 'Work timer not refreshed')
    presentation(station)
    check(station.get_editor_property('ActivityIndicator').is_visible(), 'Working indicator hidden')
    check(gameplay_snapshot(station) == before, 'Work feedback changed recipe/output')
    check(station.call_method('WorkOnProduction', (worker, gm, 4.)) == (True, True))
    before_batch_fx = gameplay_snapshot(station)
    presentation(station)
    check(station.get_editor_property('PresentationPulseRemaining') > .5, 'Batch reset did not trigger pulse')
    presentation(station)
    check(all(comp.is_visible() for comp in fx(station)), 'Batch completion effects hidden')
    check(gameplay_snapshot(station) == before_batch_fx, 'Batch feedback changed output')
    presentation(station, 1.)
    check(all(not comp.is_visible() for comp in fx(station)), 'Idle station keeps feedback visible')


case('Production override retains parent effects, shows work and completed batches, and preserves output', production_feedback)


def opt_out():
    station = complete(place('BP_ProductionStation', 5, 5))
    tile(worker, 6, 6)
    station.call_method('WorkOnProduction', (worker, gm, 1.))
    presentation(station)
    presentation(station)
    setp('Bool', station, 'bPresentationEnabled', False)
    before = gameplay_snapshot(station)
    presentation(station)
    check(all(not comp.is_visible() for comp in fx(station)))
    check(station.get_editor_property('PresentationPulseRemaining') == 0)
    check(station.get_editor_property('PresentationWorkRemaining') == 0)
    check(gameplay_snapshot(station) == before)


case('Disabling presentation hides additions and clears only cosmetic state', opt_out)
reset()
report['status'] = 'failed' if report['failed'] else 'passed'
result_path = Path(unreal.Paths.project_saved_dir()) / 'Codex/building_cosmetics_tests.json'
result_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
RESULT = report
