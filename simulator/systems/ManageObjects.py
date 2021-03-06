from typing import NamedTuple, Tuple
from enum import Enum
from simpy import FilterStore, Store
from esper import World
from pyglet.graphics import Batch

from components.Renderable import Renderable
from components.Inventory import Inventory
from components.Pickable import Pickable

from models.mxCellDecoder import parse_object


class ObjectManagerOps(Enum):
    REMOVE = 'remove'
    RECREATE = 'recreate'


GrabPayload = NamedTuple('GrabPayload', object=str, op=str, reply_channel=Store)
DropPayload = NamedTuple('DropPayload', object=str, op=str, skeleton=any, new_position=Tuple[float, float], reply_channel=Store)

ManagerTag = 'ManagerEventTag'

__event_store: FilterStore
__world: World
__batch: Batch
__window_options = Tuple[Tuple[int, int], int]


def process(kwargs):
    global __world
    global __event_store
    global __batch
    global __window_options
    __event_store = kwargs.get('EVENT_STORE', None)
    __world = kwargs.get('WORLD', None)
    __batch = kwargs.get('BATCH', None)
    __window_options = kwargs.get('WINDOW_OPTIONS', None)
    if __event_store is None:
        raise Exception("Can't find eventStore")

    while True:
        event = yield __event_store.get(lambda ev: ev.type == ManagerTag)
        payload = event.payload
        print(f'Object Manager received event {event}')
        if payload.op == ObjectManagerOps.REMOVE:
            success, msg = remove_entity(payload.object)
            payload.reply_channel.put({'success': success, 'msg': msg})
        if payload.op == ObjectManagerOps.RECREATE:
            success, msg = recreate_entity(payload.object, payload.skeleton, payload.new_position)
            payload.reply_channel.put({'success': success, 'msg': msg})



def remove_entity(obj_name):
    # Remove object from global inventory
    # TODO: restrict access to global_inventory
    # To prevent race conditions if many robots try to pick up the same thing
    global_inventory = __world.component_for_entity(1, Inventory).objects
    if obj_name not in global_inventory:
        return False, 'This object does not belong to the global_inventory.'
    ent = global_inventory[obj_name]
    del global_inventory[obj_name]
    if not __world.has_component(ent, Renderable):
        return True, ''
    r = __world.component_for_entity(ent, Renderable)
    if r.is_primitive:
        r.sprite.delete()
    __world.delete_entity(ent)
    return True, ''


def recreate_entity(obj_name, skeleton, newpos):
    new_obj = parse_object(skeleton, __batch, __window_options)
    components, attributes = new_obj
    # Change position
    pos = components[0]
    pos.x = newpos[0] - (pos.w // 2)
    pos.y = newpos[1] - (pos.h // 2)
    pos.center = newpos
    pos.changed = True
    # Create the pickable component
    pick = Pickable(float(skeleton.attrib['weight']), skeleton.attrib['name'], skeleton)
    components.append(pick)
    new_ent = __world.create_entity()
    for c in components:
        __world.add_component(new_ent, c)
    global_inventory = __world.component_for_entity(1, Inventory).objects
    global_inventory[obj_name] = new_ent
    return True, ''
