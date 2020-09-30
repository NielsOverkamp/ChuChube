from threading import RLock

import sys
from itertools import cycle

import chube_search
from channel import Channel
from chube_enums import *
from chube_ws import Resolver, Message, start_server, make_message


class Chueue:
    _lock = RLock()
    _queue = []
    _codes = dict()
    _id_iter = cycle(range(sys.maxsize))

    def add(self, code):
        with self:
            song_id = next(self._id_iter)
            self._queue.append(song_id)
            self._codes[song_id] = code
        return song_id

    def remove(self, song_id):
        with self:
            self._queue.remove(song_id)
            self._codes.pop(song_id)

    def move(self, song_id, displacement):
        with self:
            i = self._queue.index(song_id)
            new_i = min(len(self._queue) - 1, max(0, i + displacement))
            self._queue.pop(i)
            self._queue.insert(new_i, song_id)
            return new_i - i

    def pop(self):
        with self:
            if len(self._queue) > 0:
                song_id = self._queue.pop()
                code = self._codes.pop(song_id)
                return self.as_song(song_id, code)
            else:
                return None

    def as_song(self, song_id, code=None):
        if code is None:
            code = self._codes[song_id]
        return {"id": song_id, "code": code}

    def as_list(self):
        with self:
            res = list(map(self.as_song, self._queue))
        return res

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()

    def __enter__(self):
        self.lock()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unlock()

    def __len__(self):
        return len(self._queue)


class Playback:
    _song = None
    _state: PlayerState = PlayerState.LIST_END
    lock = RLock()

    def set_song(self, song):
        with self.lock:
            self._song = song

    def get_song(self):
        with self.lock:
            return self._song

    def get_song_id(self):
        with self.lock:
            if self._song is not None:
                return self._song["id"]
            else:
                return None

    def get_state(self):
        return self._state

    def set_state(self, state):
        self._state = state


class Room:
    chueue = Chueue()
    channel = Channel()
    controller = None
    controller_lock = RLock()
    playback = Playback()


rooms = {}


async def request_state_processor(ws, data):
    room = rooms["main"]
    await ws.send(make_message(Message.STATE, {
        "list": room.chueue.as_list(),
        "playing": room.playback.get_song(),
        "state": room.playback.get_state().name
    }))


async def request_list_operation_processor(ws, data):
    room = rooms["main"]
    chueue = room.chueue
    op = data["op"]
    message = None
    if op == QueueOp.ADD.name:
        code = data["code"]
        song_id = chueue.add(code)
        with room.playback.lock:
            if room.playback.get_state() == PlayerState.LIST_END:
                room.playback.set_state(PlayerState.PLAYING)
                room.playback.set_song(chueue.pop())
        message = make_message(Message.LIST_OPERATION, {"op": QueueOp.ADD.name, "code": code, "id": song_id})
    elif op == QueueOp.DEL.name:
        song_id = data["id"]
        chueue.remove(song_id)
        message = make_message(Message.LIST_OPERATION, {"op": QueueOp.DEL.name, "id": song_id})
    elif op == QueueOp.MOVE.name:
        song_id = data["id"]
        displacement = data["displacement"]
        actual_displacement = chueue.move(song_id, displacement)
        if actual_displacement != 0:
            message = make_message(Message.LIST_OPERATION,
                                   {"op": QueueOp.MOVE.name, "id": song_id, "displacement": actual_displacement})

    if message is not None:
        await room.channel.send(message)


async def obtain_control_processor(ws, data):
    room = rooms["main"]
    await obtain_control(ws, room)


async def release_control_processor(ws, data):
    room = rooms["main"]
    if len(room.channel.subscribers) > 1:
        await release_control(ws, room)
    else:
        pass
        # TODO error here


async def song_end_processor(ws, data):
    room = rooms["main"]
    old_song_id = data["id"]
    with room.controller_lock, room.playback.lock:
        if ws is room.controller and old_song_id == room.playback.get_song_id():
            new_song = room.chueue.pop()
            room.playback.set_song(new_song)
            if new_song is None:
                room.playback.set_state(PlayerState.LIST_END)
                new_song_id = None
            else:
                new_song_id = new_song["id"]
            await room.channel.send(make_message(Message.SONG_END, {"ended_id": old_song_id, "current_id": new_song_id}))


async def playback_processor(ws, data):
    room = rooms["main"]


# TODO There is some potential concurrent bug here, when the controller loses/releases control right before a song end.
async def obtain_control(ws, room):
    with room.controller_lock:
        if room.controller is not ws:
            prev_controller = room.controller
            room.controller = ws
            await ws.send(make_message(Message.OBTAIN_CONTROL))
            if prev_controller is not None:
                await prev_controller.send(make_message(Message.RELEASE_CONTROL))


async def release_control(ws, room):
    with room.controller_lock:
        if room.controller is ws:
            subs = room.channel.subscribers
            if len(subs) > 0:
                room.controller = subs[0]
                await room.controller.send(make_message(Message.OBTAIN_CONTROL))
            else:
                room.controller = None
            await ws.send(make_message(Message.RELEASE_CONTROL))


async def on_connect(ws, path):
    room = rooms["main"]
    room.channel.subscribe(ws)
    with room.controller_lock:
        if room.controller is None:
            await obtain_control(ws, room)
            # with room.playback.lock:
            #     if room.playback.get_state() == PlayerState.WAITING_FOR_CLIENTS:
            #         room.playback.set_state(PlayerState.PLAYING)
            #         # TODO maybe send a play message on channel.
            #         # await ws.send(make_message(Message.MEDIA_ACTION, {"action": MediaAction.PLAY}))


async def on_disconnect(ws, path):
    room = rooms["main"]
    room.channel.unsubscribe(ws)
    await release_control(ws, room)
    # with room.controller_lock:
    #     if room.controller is None:
    #         room.playback.


def make_resolver():
    resolver = Resolver()
    resolver.register(Message.STATE, request_state_processor)
    resolver.register(Message.LIST_OPERATION, request_list_operation_processor)
    resolver.register(Message.OBTAIN_CONTROL, obtain_control_processor)
    resolver.register(Message.RELEASE_CONTROL, release_control_processor)
    resolver.register(Message.SONG_END, song_end_processor)

    search_resolver = chube_search.make_resolver()

    resolver.add_all(search_resolver)

    return resolver


def init_rooms():
    rooms["main"] = Room()


if __name__ == "__main__":
    player_resolver = make_resolver()

    init_rooms()

    start_server(player_resolver, on_connect, on_disconnect)
