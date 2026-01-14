from pyteal import App


def gget(key):
    """
    global get
    """
    return App.globalGet(key)


def gset(key, value):
    """
    global set
    """
    return App.globalPut(key, value)


def global_decr(key, val):
    """
    decrement numeric global state var
    """
    return App.globalPut(key, App.globalGet(key) - val)


def global_incr(key, val):
    """
    increment numeric global state var
    """
    return App.globalPut(key, val + App.globalGet(key))
