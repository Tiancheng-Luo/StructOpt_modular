import sys as _sys
from collections import _OrderedDictKeysView, _OrderedDictItemsView, _OrderedDictValuesView, _Link
from _collections_abc import MutableMapping
from _weakref import proxy as _proxy
from reprlib import recursive_repr as _recursive_repr
from operator import eq as _eq


class SortedDict(dict):
    'Dictionary that preserves order by key'
    # An inherited dict maps keys to values.
    # The inherited dict provides __getitem__, __len__, __contains__, and get.
    # The remaining methods are order-aware.
    # Big-O running times for all methods are the same as regular dictionaries.

    # The internal self.__map dict maps keys to links in a doubly linked list.
    # The circular doubly linked list starts and ends with a sentinel element.
    # The sentinel element never gets deleted (this simplifies the algorithm).
    # The sentinel is in self.__hardroot with a weakref proxy in self.__root.
    # The prev links are weakref proxies (to prevent circular references).
    # Individual links are kept alive by the hard reference in self.__map.
    # Those hard references disappear when a key is deleted from an OrderedDict.

    def __init__(*args, **kwds):
        '''Initialize an ordered dictionary.  The signature is the same as
        regular dictionaries, but keyword arguments are not recommended because
        their insertion order is arbitrary.

        '''
        if not args:
            raise TypeError("descriptor '__init__' of 'OrderedDict' object "
                            "needs an argument")
        self, *args = args
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__root
        except AttributeError:
            self.__hardroot = _Link()
            self.__root = root = _proxy(self.__hardroot)
            root.prev = root.next = root
            root.key = -float('inf')
            self.__map = {}
        self.__update(*args, **kwds)

    def __setitem__(self, key, value,
                    dict_setitem=dict.__setitem__, proxy=_proxy, Link=_Link):
        'od.__setitem__(i, y) <==> od[i]=y'
        # Setting a new item creates a new link at the end of the linked list,
        # and the inherited dictionary is updated with the new key/value pair.
        if key not in self:
            self.__map[key] = link = Link()
            root = self.__root
            # Find the correct spot
            after = root.next
            while (after is not root) and (after.key < key):
                after = after.next
                continue
            before = after.prev
            #print("Before: {}, Key: {}, After: {}, List: {}".format(before.key, key, after.key, [root.key] + [l for l in self]))
            link.prev, link.next, link.key = before, after, key
            after.prev = proxy(link)
            before.next = proxy(link)
        dict_setitem(self, key, value)

    def __delitem__(self, key, dict_delitem=dict.__delitem__):
        'od.__delitem__(y) <==> del od[y]'
        # Deleting an existing item uses self.__map to find the link which gets
        # removed by updating the links in the predecessor and successor nodes.
        dict_delitem(self, key)
        link = self.__map.pop(key)
        link_prev = link.prev
        link_next = link.next
        link_prev.next = link_next
        link_next.prev = link_prev
        link.prev = None
        link.next = None

    def __iter__(self):
        'od.__iter__() <==> iter(od)'
        # Traverse the linked list in order.
        root = self.__root
        curr = root.next
        while curr is not root:
            yield curr.key
            curr = curr.next

    def __reversed__(self):
        'od.__reversed__() <==> reversed(od)'
        # Traverse the linked list in reverse order.
        root = self.__root
        curr = root.prev
        while curr is not root:
            yield curr.key
            curr = curr.prev

    def clear(self):
        'od.clear() -> None.  Remove all items from od.'
        root = self.__root
        root.prev = root.next = root
        self.__map.clear()
        dict.clear(self)

    def popitem(self, last=True):
        '''od.popitem() -> (k, v), return and remove a (key, value) pair.
        Pairs are returned in LIFO order if last is true or FIFO order if false.

        '''
        if not self:
            raise KeyError('dictionary is empty')
        root = self.__root
        if last:
            link = root.prev
            link_prev = link.prev
            link_prev.next = root
            root.prev = link_prev
        else:
            link = root.next
            link_next = link.next
            root.next = link_next
            link_next.prev = root
        key = link.key
        del self.__map[key]
        value = dict.pop(self, key)
        return key, value

    def __sizeof__(self):
        sizeof = _sys.getsizeof
        n = len(self) + 1                       # number of links including root
        size = sizeof(self.__dict__)            # instance dictionary
        size += sizeof(self.__map) * 2          # internal dict and inherited dict
        size += sizeof(self.__hardroot) * n     # link objects
        size += sizeof(self.__root) * n         # proxy objects
        return size

    update = __update = MutableMapping.update

    def keys(self):
        "D.keys() -> a set-like object providing a view on D's keys"
        return _OrderedDictKeysView(self)

    def items(self):
        "D.items() -> a set-like object providing a view on D's items"
        return _OrderedDictItemsView(self)

    def values(self):
        "D.values() -> an object providing a view on D's values"
        return _OrderedDictValuesView(self)

    __ne__ = MutableMapping.__ne__

    __marker = object()

    def pop(self, key, default=__marker):
        '''od.pop(k[,d]) -> v, remove specified key and return the corresponding
        value.  If key is not found, d is returned if given, otherwise KeyError
        is raised.

        '''
        if key in self:
            result = self[key]
            del self[key]
            return result
        if default is self.__marker:
            raise KeyError(key)
        return default

    def setdefault(self, key, default=None):
        'od.setdefault(k[,d]) -> od.get(k,d), also set od[k]=d if k not in od'
        if key in self:
            return self[key]
        self[key] = default
        return default

    @_recursive_repr()
    def __repr__(self):
        'od.__repr__() <==> repr(od)'
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self.items()))

    def __reduce__(self):
        'Return state information for pickling'
        inst_dict = vars(self).copy()
        for k in vars(SortedDict()):
            inst_dict.pop(k, None)
        return self.__class__, (), inst_dict or None, None, iter(self.items())

    def copy(self):
        'od.copy() -> a shallow copy of od'
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        '''OD.fromkeys(S[, v]) -> New ordered dictionary with keys from S.
        If not specified, the value defaults to None.

        '''
        self = cls()
        for key in iterable:
            self[key] = value
        return self

    def __eq__(self, other):
        '''od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
        while comparison to a regular mapping is order-insensitive.

        '''
        if isinstance(other, SortedDict):
            return dict.__eq__(self, other) and all(map(_eq, self, other))
        return dict.__eq__(self, other)

