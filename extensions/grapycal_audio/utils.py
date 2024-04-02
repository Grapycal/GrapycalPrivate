import threading
from grapycal.utils.misc import Action
import asyncio
import time

import numpy as np


class byteFIFO:
    """ byte FIFO buffer """
    def __init__(self):
        self._buf = bytearray()
        self.lock = threading.Lock()

    def put(self, data):
        with self.lock:
            self._buf.extend(data)

    def get(self, size):
        with self.lock:
            data = self._buf[:size]
            self._buf[:size] = b''
            return data

    def peek(self, size):
        return self._buf[:size]

    def getvalue(self):
        return self._buf

    def __len__(self):
        return len(self._buf)
    
class Clock:
    def __init__(self, interval: float):
        self.interval = interval
        self.on_tick = Action()
        self.start_time = time.time()

    async def run(self):
        i = 0
        while True:
            await asyncio.sleep(self.interval)
            rel_t = time.time() - self.start_time
            self.on_tick.invoke(rel_t)
            i += 1

def midi2Freq(pitch):
    return 440 * 2 ** ((pitch - 69) / 12)

import os
import wave
from wave import Wave_read

class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache: dict[str,Wave_read] = {}
        self.lru = []
    def get(self, key) -> Wave_read:
        if key in self.cache:
            self.lru.remove(key)
            self.lru.append(key)
            return self.cache[key]
        raise KeyError(key)
    def put(self, key, value):
        if key in self.cache:
            return
        if len(self.cache) >= self.capacity:
            del self.cache[self.lru.pop(0)]
        self.cache[key] = value
        self.lru.append(key)

    def __contains__(self, key):
        return key in self.cache

class Instrument:
    def __init__(self,root:str):
        self._root = root
        self._cache = LRUCache(20)

    def files_exist(self):
        for i in range(264):
            name = f'{i:03d}.wav'
            path = os.path.join(self._root,name)
            if not os.path.exists(path):
                print(f'file not found: {path}')
                return False
        return True
    
    def get_file(self,name)-> Wave_read:
        path = os.path.join(self._root,name)
        if path in self._cache:
            return self._cache.get(path)
        data = wave.open(path,'rb')
        self._cache.put(path,data)
        return data

    def get(self,pitch,velocity) -> Wave_read:
        assert 21 <= pitch <= 108
        assert 0 <= velocity <= 2 # 0,1,2
        name = pitch-21 + velocity*88
        name = f'{name:03d}.wav'
        return self.get_file(name)
    
    def get_frames(self,pitch:int,velocity:int,start:int,length:int) -> np.ndarray:
        file = self.get(pitch,velocity)
        file.setpos(start)
        frames = file.readframes(length)
        frames = np.frombuffer(frames,dtype='int16').astype('float32') / 32768
        # stereo to mono
        frames = frames.reshape(-1,2)
        frames = frames.mean(axis=1)
        # pad with zeros if necessary
        if len(frames) < length:
            frames = np.pad(frames,(0,length-len(frames)))
        return frames