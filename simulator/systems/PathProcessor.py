import esper
from typing import NamedTuple
from simpy import FilterStore

from main import EVENT
from components.Path import Path
from components.Position import Position
from components.Velocity import Velocity


EndOfPathPayload = NamedTuple('EndOfPathPayload', [('ent', int), ('timestamp', str)])
EndOfPathTag = 'EndOfPath'


class PathProcessor(esper.Processor):
    def __init__(self):
        super().__init__()

    def process(self, kwargs):
        event_store: FilterStore = kwargs.get('EVENT_STORE', None)
        env = kwargs.get('ENV', None)
        for ent, (pos, path, vel) in self.world.get_components(Position, Path, Velocity):
            # print(f"Processing {ent}")
            point = path.points[path.curr_point]
            pos_center = pos.center
            # print(f"[Path] Point {point} is {path.curr_point}th point")
            if pos_center[0] == point[0] and pos_center[1] == point[1]:
                # print("Going to next point")
                path.curr_point += 1
                if path.curr_point == len(path.points):
                    # end of path
                    vel.x = 0
                    vel.y = 0
                    # print("Removing Path component from", ent)
                    pos.changed = False or pos.changed
                    self.world.remove_component(ent, Path)
                    # Adds an EndOfPath event, in case anyone is listening
                    end_of_path = EVENT(EndOfPathTag, EndOfPathPayload(ent, env.now))
                    # print(f'[{env.now}] PathProcessor adding EndOfPath event {end_of_path}')
                    event_store.put(end_of_path)
                    return
                point = path.points[path.curr_point]
                # print(f"Point {point} is {path.curr_point}th point")

            dx = point[0] - pos_center[0]
            if dx > 0:
                vel.x = min(path.speed, dx)
            else:
                vel.x = max(- path.speed, dx)
            dy = point[1] - pos_center[1]
            if dy > 0:
                vel.y = min(path.speed, dy)
            else:
                vel.y = max(- path.speed, dy)

