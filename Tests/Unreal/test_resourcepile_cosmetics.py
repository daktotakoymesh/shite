"""Check newly spawned resource visuals in PIE; destroy only this test's own actors."""
import json
import traceback
from pathlib import Path
import unreal

ROOT = Path('D:/shite-visual')
assert Path(unreal.Paths.get_project_file_path()).resolve() == ROOT / 'shite.uproject'
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world
game = unreal.get_default_object(unreal.GameplayStatics)
system = unreal.get_default_object(unreal.SystemLibrary)
spawned = []
report = {'passed': [], 'failed': []}


def cls(name):
    return unreal.load_class(None, '/Game/' + name + '.' + name + '_C')


def spawn(name):
    transform = unreal.Transform(location=unreal.Vector(-9000., -9000., 50.))
    actor = game.call_method('BeginDeferredActorSpawnFromClass', (
        world, cls(name), transform, unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,
        None, unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    actor = game.call_method('FinishSpawningActor', (actor, transform, unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    spawned.append(actor)
    return actor


def setp(kind, actor, name, val):
    system.call_method('Set' + kind + 'PropertyByName', (actor, unreal.Name(name), val))


def check(condition, reason):
    assert condition, reason


def case(name, fn):
    try:
        fn()
        report['passed'].append(name)
    except Exception:
        report['failed'].append({'name': name, 'error': traceback.format_exc()})


try:
    pile = spawn('BP_ResourcePile')
    food_pile = spawn('BP_FoodPile')
    setp('Int', pile, 'Amount', 7)
    root = pile.get_editor_property('StaticMeshComponent')
    presentation = pile.get_editor_property('PilePresentation')
    original_root = unreal.get_default_object(cls('BP_ResourcePile')).get_editor_property('StaticMeshComponent')
    initial_location = pile.get_actor_location()
    initial_scale = root.get_editor_property('relative_scale3d')

    def material_bundle():
        pile.call_method('UpdatePresentation', ())
        check(presentation.static_mesh.get_path_name() == '/Game/Visual/SM_CarryBundle.SM_CarryBundle', 'Expected timber bundle')
        check(presentation.get_editor_property('visible'), 'Bundle hidden')
        check(not root.get_editor_property('visible'), 'Collision cube should not render')
    case('Building material pile renders the timber bundle', material_bundle)

    def original_collision():
        check(root.static_mesh.get_path_name() == '/Engine/BasicShapes/Cube.Cube', 'Original collision mesh replaced')
        check(root.get_collision_profile_name() == original_root.get_collision_profile_name(), 'Collision profile changed')
        check(root.get_collision_enabled() == original_root.get_collision_enabled(), 'Root collision mode changed')
        check(root.get_editor_property('relative_scale3d') == initial_scale, 'Root scale changed')
        check(presentation.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION, 'New visual should not collide')
    case('Original selection and collision root remain intact', original_collision)

    def default_food():
        food_pile.call_method('UpdatePresentation', ())
        visual = food_pile.get_editor_property('PilePresentation')
        check(visual.static_mesh.get_path_name() == '/Game/Visual/SM_FoodCrate.SM_FoodCrate', 'Food subclass is not a crate')
        check(visual.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION, 'Food visual collision enabled')
    case('Food subclass inherits presentation refresh', default_food)

    def switch_food():
        setp('Name', pile, 'ResourceType', 'Food')
        pile.call_method('UpdatePresentation', ())
        check(presentation.static_mesh.get_path_name() == '/Game/Visual/SM_FoodCrate.SM_FoodCrate', 'Runtime food change did not repaint/remesh')
        check(str(pile.get_editor_property('PresentationResourceCache')) == 'Food', 'Resource cache stale')
        check(pile.get_editor_property('Amount') == 7, 'Visual refresh changed stock')
    case('Runtime storage filter changes refresh the appearance', switch_food)

    def switch_back():
        setp('Name', pile, 'ResourceType', 'BuildingMaterial')
        pile.call_method('UpdatePresentation', ())
        check(presentation.static_mesh.get_path_name() == '/Game/Visual/SM_CarryBundle.SM_CarryBundle', 'Timber appearance not restored')
        check(pile.get_editor_property('Amount') == 7, 'Visual refresh changed stock')
        check(pile.get_actor_location() == initial_location, 'Visual refresh moved the resource actor')
    case('Switching back preserves quantity and actor placement', switch_back)

    def colors():
        asset = unreal.load_asset('/Game/Visual/SM_FoodCrate')
        names = [s.material_interface.get_path_name() for s in asset.get_editor_property('static_materials')]
        check(names == ['/Game/Visual/MV_Wood.MV_Wood', '/Game/Visual/MV_Charcoal.MV_Charcoal', '/Game/Visual/MV_Food.MV_Food'], 'Crate material slots wrong')
    case('Food crate has separate wood, binding and produce materials', colors)
finally:
    for actor in spawned:
        actor.destroy_actor()

RESULT = report
(ROOT / 'Saved/Codex/resourcepile_cosmetics_test_results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
assert not report['failed'], report['failed']
