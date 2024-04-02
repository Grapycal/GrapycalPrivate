from grapycal import Node

import numpy as np

major_scale = [0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19, 21, 23, 24, 26, 28, 29, 31, 33, 35]

def get_major_mapping():
    rows = 'zxcvbnm,./\nasdfghjkl;\'\nqwertyuiop[]\\\n1234567890-='
    mapping = {}
    for i, row in enumerate(rows.split('\n')):
        for j, char in enumerate(row):
            mapping[char] = 12*i + major_scale[j]
    return mapping

class KeyboardToMidiNode(Node):
    '''
    Convert keyboard events to MIDI notes.
    '''
    def build_node(self):
        self.label.set('Keyboard to MIDI')
        self.note_on_out = self.add_out_port('note_on')
        self.note_off_out = self.add_out_port('note_off')
        self.keyboard_control = self.add_keyboard_control('keyboard')

    def init_node(self):
        self.keyboard_control.keydown += self.keydown
        self.keyboard_control.on_up += self.keyup
        self.base = 36 # C2
        self.mapping = get_major_mapping()

    def key_to_pitch(self, key):
        if key in self.mapping:
            return self.base + self.mapping[key]
        return None
            
    def keydown(self, key):
        pitch = self.key_to_pitch(key)
        if pitch is None:
            return
        self.note_on_out.push({
            'pitch': pitch,
            'velocity': 100
        })

    def keyup(self, key):
        pitch = self.key_to_pitch(key)
        if pitch is None:
            return
        self.note_off_out.push({
            'pitch': pitch
        })
