from objectsync import DictTopic, SObject, StringTopic, Topic

class Settings(SObject):
    frontend_type = 'Settings'

    def build(self,old=None):
        self.entries = self.add_attribute('entries',DictTopic,{})
        self.data_path = self.add_attribute('data_path',StringTopic,'./_data')
        self._add_entry('Data/data path',self.data_path,'text',{})

    def _add_entry(self,name,topic:Topic,editor_type:str,editor_args:dict|None=None):
        if editor_args is None:
            editor_args = {}
        editor_args["type"] = editor_type
        self.entries.add(name,{"name": topic.get_name(), "display_name": name, "editor_args": editor_args})
