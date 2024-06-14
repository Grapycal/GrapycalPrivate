class StoreProxy:
    """
    Proxy the store so when extension reloads and replaced the store instance, the proxy holder will still be able to access the store.
    """

    def __init__(self, name, main_store_):
        self.__dict__["__main_store"] = main_store_
        self.__dict__["__name"] = name

    def __getattr__(self, name):
        obj = self.__dict__["__main_store"].get_real_store(self.__dict__["__name"])
        return getattr(obj, name)

    def __setattr__(self, name, value):
        obj = self.__dict__["__main_store"].get_real_store(self.__dict__["__name"])
        setattr(obj, name, value)
