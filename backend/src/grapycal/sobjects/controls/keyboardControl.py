from typing import Any, Dict
from grapycal.sobjects.controls.control import Control
from grapycal.utils.misc import Action
from objectsync import StringTopic, EventTopic


class KeyboardControl(Control):
    '''
    Listen to keyboard events when enabled by the user.

    To add a keyoard control to a node, use the following code in the node:
    ```python
    self.add_keyboard_control(label='keyboard')
    ```
    '''
    frontend_type = 'KeyboardControl'
    def build(self, label:str=''):
        self.label = self.add_attribute('label', StringTopic, label, is_stateful=False)
    
    def init(self):
        self.keydown = Action()
        self.on_up = Action()
        self.register_service('keydown', self._keydown)
        self.register_service('keyup', self.keyup)

    def _keydown(self, key):
        self.keydown.invoke(key)

    def keyup(self, key):
        self.on_up.invoke(key)