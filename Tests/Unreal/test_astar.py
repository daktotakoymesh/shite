"""Run through Unreal's Python console during PIE; restores all test state."""
import unreal
import heapq
import json
import math
import random
import traceback
from pathlib import Path

REPORT = Path(unreal.Paths.project_saved_dir()) / 'Codex' / 'astar_test_results.json'
REPORT.parent.mkdir(parents=True, exist_ok=True)
TYPE = 'TileType_3_D82FE0704557242E4FB850ACCC61C7E7'
WALK = 'IsWalkable_4_7DA75FFE4686E7B63764E2B74B1FBD1C'
report = {'passed': [], 'failed': []}
actor = None
original = {}

def reference(cells, start, goal, diagonal, ground, road, size, speed):
    def multiplier(tile):
        return road if cells.get(tile) == 'road' else ground
    def walk(tile):
        return tile in cells and cells[tile] != 'wall'
    def edges(tile):
        x, y = tile
        offsets = [(1,0),(-1,0),(0,1),(0,-1)]
        if diagonal:
            offsets += [(1,1),(1,-1),(-1,1),(-1,-1)]
        for dx, dy in offsets:
            dest = x+dx, y+dy
            if not walk(dest) or multiplier(dest) <= 0:
                continue
            if dx and dy and (not walk((x+dx,y)) or not walk((x,y+dy))):
                continue
            distance = size * math.hypot(dx, dy)
            yield dest, distance * 0.5 / speed * (1/multiplier(tile) + 1/multiplier(dest))
    if size <= 0 or speed <= 0 or not walk(start) or not walk(goal):
        return math.inf, edges
    if multiplier(start) <= 0 or multiplier(goal) <= 0:
        return math.inf, edges
    costs, queue = {start:0.0}, [(0.0,start)]
    while queue:
        cost, tile = heapq.heappop(queue)
        if cost != costs[tile]:
            continue
        if tile == goal:
            return cost, edges
        for dest, edge in edges(tile):
            alt = cost + edge
            if alt < costs.get(dest, math.inf):
                costs[dest] = alt
                heapq.heappush(queue, (alt,dest))
    return math.inf, edges

try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    cls = unreal.load_class(None, '/Game/BP_GridManager.BP_GridManager_C')
    runtime_actor = unreal.GameplayStatics.get_all_actors_of_class(world, cls)[0]
    sample = next(iter(runtime_actor.get_editor_property('Gridmap').values())).copy()
    actor = unreal.get_default_object(cls)
    for prop in ('Gridmap','AllowDiagonalMovement','GroundSpeedMultiplier','RoadSpeedMultiplier','TileZize'):
        value = actor.get_editor_property(prop)
        original[prop] = value.copy() if prop == 'Gridmap' else value
    enum = type(sample.get_editor_property(TYPE))
    templates = {}
    for name, value, walk in [('ground',0,True),('road',1,True),('wall',2,False)]:
        row = sample.copy()
        row.set_editor_property(TYPE, enum.cast(value))
        row.set_editor_property(WALK, walk)
        templates[name] = row

    def test(name, cells, start, goal, diagonal=True, ground=1.0, road=1.5, size=100.0, speed=100.0, require_road=False):
        actor.set_editor_property('Gridmap', {unreal.Vector2D(*p):templates[t] for p,t in cells.items()})
        actor.set_editor_property('AllowDiagonalMovement', diagonal)
        actor.set_editor_property('GroundSpeedMultiplier', ground)
        actor.set_editor_property('RoadSpeedMultiplier', road)
        actor.set_editor_property('TileZize', size)
        expected, edges = reference(cells,start,goal,diagonal,ground,road,size,speed)
        ok, path, cost = actor.call_method('FindPath', (unreal.Vector2D(*start), unreal.Vector2D(*goal), speed))
        route = [(p.x,p.y) for p in path]
        assert ok == math.isfinite(expected), (name,ok,expected,route,cost)
        if ok:
            assert route[0] == start and route[-1] == goal, (name,route)
            assert len(route) == len(set(route)), (name,'cycle',route)
            summed = 0.0
            for a,b in zip(route,route[1:]):
                choices = dict(edges(a))
                assert b in choices, (name,'illegal step',a,b)
                summed += choices[b]
            assert math.isclose(cost,expected,rel_tol=1e-7,abs_tol=1e-7), (name,cost,expected,route)
            assert math.isclose(cost,summed,rel_tol=1e-7,abs_tol=1e-7), (name,cost,summed)
            if require_road:
                assert sum(cells[p]=='road' for p in route) >= 2, (name,route)
        else:
            assert not route and cost == 0, (name,'stale result',route,cost)
        report['passed'].append({'name':name,'success':ok,'path_length':len(route),'travel_time':cost})

    def grid(w,h):
        return {(x,y):'ground' for x in range(w) for y in range(h)}

    small = grid(4,4)
    test('diagonal open grid',small,(0,0),(3,3))
    test('four-direction open grid',small,(0,0),(3,3),diagonal=False)
    test('already at goal',small,(2,2),(2,2))
    test('goal out of bounds',small,(0,0),(4,3))
    test('start out of bounds',small,(-1,0),(3,3))
    test('fractional coordinate rejected',small,(0.5,0),(3,3))
    test('empty grid',{},(0,0),(0,0))
    test('zero movement speed',small,(0,0),(3,3),speed=0.0)
    test('negative movement speed',small,(0,0),(3,3),speed=-10.0)
    test('zero tile size',small,(0,0),(3,3),size=0.0)
    test('zero terrain speed',small,(0,0),(3,3),ground=0.0)
    blocked = dict(small)
    blocked[(0,0)] = 'wall'
    test('blocked origin',blocked,(0,0),(3,3))
    test('blocked goal',blocked,(3,3),(0,0))
    corner = grid(2,2)
    corner[(1,0)] = 'wall'
    test('one blocked side forbids shortcut',corner,(0,0),(1,1))
    corner[(0,1)] = 'wall'
    test('two blocked sides unreachable',corner,(0,0),(1,1))
    separated = grid(8,8)
    for y in range(8): separated[(4,y)] = 'wall'
    test('full wall unreachable',separated,(0,0),(7,7))
    separated[(4,5)] = 'ground'
    test('wall with single gap',separated,(0,0),(7,7))
    roads = grid(9,3)
    for x in range(9): roads[(x,1)] = 'road'
    test('faster road detour selected',roads,(0,0),(8,0),require_road=True)
    test('four-direction road detour',roads,(0,0),(8,0),diagonal=False,road=2.0,require_road=True)
    test('slower roads avoided',roads,(0,0),(8,0),road=0.5)
    test('ground faster than road',roads,(0,0),(8,0),ground=2.0,road=1.0)
    test('tile size and movement speed scaling',roads,(0,0),(8,0),size=75.0,speed=180.0)
    test('half ground half road transition',{(0,0):'ground',(1,0):'road'},(0,0),(1,0))
    test('repeated search after failure',small,(3,3),(0,0))
    for seed in range(32):
        rng = random.Random(seed)
        cells = {(x,y):rng.choices(['ground','road','wall'],[0.48,0.28,0.24])[0] for x in range(10) for y in range(10)}
        cells[(0,0)],cells[(9,9)] = 'ground','ground'
        test('random map '+str(seed),cells,(0,0),(9,9),diagonal=bool(seed%2),road=[0.65,1.5,3.0][seed%3])
    large = grid(20,20)
    test('current map size 20x20',large,(0,0),(19,19))
    test('current map size cardinal',large,(0,0),(19,19),diagonal=False)
    for p in [(18,19),(19,18),(18,18)]: large[p] = 'wall'
    test('20x20 exhausted frontier',large,(0,0),(19,19))
except Exception:
    report['failed'].append(traceback.format_exc())
finally:
    if actor:
        for prop,value in original.items():
            try:
                actor.set_editor_property(prop,value)
            except Exception:
                report['failed'].append('RESTORE '+prop+': '+traceback.format_exc())
    report['pass_count'] = len(report['passed'])
    REPORT.write_text(json.dumps(report,indent=2))
    unreal.log('A* TESTS: '+str(report['pass_count'])+' passed; '+str(len(report['failed']))+' failed. '+str(REPORT))
