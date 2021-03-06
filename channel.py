from typing import Dict

from websockets import WebSocketServerProtocol


class Subscriber:
    player_enabled = False
    ws: WebSocketServerProtocol

    def __init__(self, ws):
        self.ws = ws


class Channel:
    subscribers: Dict[WebSocketServerProtocol, Subscriber]

    def __init__(self):
        self.subscribers = dict()

    def subscribe(self, ws: WebSocketServerProtocol):
        if ws not in self.subscribers:
            self.subscribers[ws] = (Subscriber(ws))

    def unsubscribe(self, ws: WebSocketServerProtocol):
        if ws in self.subscribers:
            self.subscribers.pop(ws)

    def get_player_enabled_subscribers(self):
        return filter(lambda s: s.player_enabled, self.subscribers.values())

    async def send(self, message):
        for sub in list(self.subscribers.values()):
            if sub.ws.open:
                await sub.ws.send(message)
            else:
                print("closed ws still in channel")
                self.unsubscribe(sub.ws)
