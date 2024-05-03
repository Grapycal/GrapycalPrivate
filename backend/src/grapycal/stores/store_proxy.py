class StoreProxy:
    '''
    Proxy the store so when extension reloads and replaced the store instance, the proxy holder will still be able to access the store.
    '''
    def __init__(self, name, main_store_):
        self.__dict__['name'] = name

    def __getattr__(self, name):
        from grapycal.stores.main_store import main_store
        obj = main_store.get_real_store(self.__dict__['name'])
        return getattr(obj, name)

    def __setattr__(self, name, value):
        from grapycal.stores.main_store import main_store
        obj = main_store.get_real_store(self.__dict__['name'])
        setattr(obj, name, value)