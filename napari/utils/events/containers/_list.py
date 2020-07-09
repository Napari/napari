from __future__ import annotations

from collections import defaultdict
from typing import (
    DefaultDict,
    Iterable,
    List,
    MutableSequence,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
    overload,
)

from napari.utils.events import EmitterGroup, Event

T = TypeVar('T')
NestedIndex = Tuple[int, ...]


class EventedList(MutableSequence[T]):
    """Mutable Sequence that emits events when altered

    Parameters
    ----------
    data : Iterable, optional
        Initil data, by default None

    Events
    ------
    inserting (index: int)
        emitted before an item is inserted at ``index``
    inserted (index: int, value: T)
        emitted after ``value`` is inserted at ``index``
    removing (index: int)
        emitted before an item is removed at ``index``
    removed (index: int, value: T)
        emitted after ``value`` is removed at ``index``
    moving (index: int, new_index: int)
        emitted before an item is moved from ``index`` to ``new_index``
    moved (index: int, new_index: int, value: T)
        emitted after ``value`` is moved from ``index`` to ``new_index``
    changed (index: int, old_value: T, new_value: T)
        emitted when ``index`` is set from ``old_value`` to ``new_value``
    reordered (value: self)
        emitted when the list is reordered (eg. moved/reversed).
    """

    def __init__(self, data: Iterable[T] = None):
        self._list: List[T] = []
        self.events: EmitterGroup

        _events = {
            'inserting': None,  # int
            'inserted': None,  # Tuple[int, Any] - (idx, value)
            'removing': None,  # int
            'removed': None,  # Tuple[int, Any] - (idx, value)
            'moving': None,  # Tuple[int, int]
            'moved': None,  # Tuple[Tuple[int, int], Any]
            'changed': None,  # Tuple[int, Any, Any] - (idx, old, new)
            'reordered': None,  # None
        }
        # For multiple inheritance
        if hasattr(self, 'events') and isinstance(self.events, EmitterGroup):
            self.events.add(**_events)
        else:
            self.events = EmitterGroup(source=self, **_events)

        if data is not None:
            self.extend(data)

    # fmt: off
    @overload
    def __getitem__(self, key: int) -> T: ...  # noqa: E704

    @overload
    def __getitem__(self, key: slice) -> List[T]: ...  # noqa

    def __getitem__(self, key):  # noqa: F811
        return self._list[key]

    @overload
    def __setitem__(self, key: int, value: T): ...  # noqa: E704

    @overload
    def __setitem__(self, key: slice, value: Iterable[T]): ...  # noqa
    # fmt: on

    def __setitem__(self, key, value):  # noqa: F811
        old = self._list[key]
        self._list[key] = value
        if value != old:
            self.events.changed(index=key, old_value=old, new_value=value)

    def _delitem_indices(
        self, key: Union[int, slice]
    ) -> Iterable[Tuple[EventedList, int]]:
        # returning List[(self, int)] allows subclasses to pass nested members
        if isinstance(key, int):
            return [(self, key if key >= 0 else key + len(self))]
        elif isinstance(key, slice):
            _start = key.start or 0
            _stop = key.stop or len(self)
            _step = key.step or 1
            if _start < 0:
                _start = len(self) + _start
            if _stop < 0:
                _stop = len(self) + _stop
            return [(self, i) for i in range(_start, _stop, _step)]
        raise TypeError("Deletion index must be int, or slice")

    def __delitem__(self, key: Union[int, slice]):
        # delete from the end
        for parent, index in sorted(self._delitem_indices(key), reverse=True):
            parent.events.removing(index=index)
            item = parent._list.pop(index)
            parent.events.removed(index=index, value=item)

    def __len__(self) -> int:
        return len(self._list)

    def __repr__(self) -> str:
        return repr(self._list)

    def insert(self, index: int, value: T):
        self.events.inserting(index=index)
        self._list.insert(index, value)
        self.events.inserted(index=index, value=value)

    def move(self, old_index: int, new_index: int,) -> bool:
        if new_index > old_index:
            new_index -= 1

        self.events.moving(index=old_index, new_index=new_index)
        item = self._list.pop(old_index)
        self._list.insert(new_index, item)
        self.events.moved(index=old_index, new_index=new_index, value=item)
        self.events.reordered(value=self)
        return True

    def reverse(self) -> None:
        # reimplementing to emit a change event
        # If this method were removed, it would just emit a "changed" event
        # for each moved index in the list
        self._list.reverse()
        self.events.reordered(value=self)

    def copy(self) -> EventedList:
        return self.__class__(self._list)


class NestableEventedList(EventedList[T]):
    """Nestable Mutable Sequence that emits recursive events when altered.

    A key property of this class is that when new mutable sequences are added
    to the list, they are themselves converted to a ``NestableEventedList``,
    and all of the ``EventEmitter`` objects in the child are connect to the
    parent object's ``_bubble_event`` method. When ``_bubble_event`` receives
    an event from a child object, it remits the event, but changes any
    ``index`` keys in the event to a ``NestedIndex`` (a tuple of ``int``) such
    that indices emitted by any given ``NestableEventedList`` are always
    relative to itself.

    ``NestableEventedList`` instances can be indexed with a ``tuple`` of
    ``int`` (e.g. ``mylist[0, 2, 1]``) to retrieve nested child objects.

    Parameters
    ----------
    data : Iterable, optional
        Initil data, by default None

    Events
    ------
    types used:
        Index = Union[int, Tuple[int, ...]]

    inserting (index: Index)
        emitted before an item is inserted at ``index``
    inserted (index: Index, value: T)
        emitted after ``value`` is inserted at ``index``
    removing (index: Index)
        emitted before an item is removed at ``index``
    removed (index: Index, value: T)
        emitted after ``value`` is removed at ``index``
    moving (index: Index, new_index: Index)
        emitted before an item is moved from ``index`` to ``new_index``
    moved (index: Index, new_index: Index, value: T)
        emitted after ``value`` is moved from ``index`` to ``new_index``
    changed (index: Index, old_value: T, new_value: T)
        emitted when ``index`` is set from ``old_value`` to ``new_value``
    reordered (value: self)
        emitted when the list is reordered (eg. moved/reversed).
    """

    # fmt: off
    @overload
    def __getitem__(self, key: Union[int, NestedIndex]) -> T: ...  # noqa: E704

    @overload
    def __getitem__(self, key: slice) -> List[T]: ...  # noqa

    def __getitem__(self, key):  # noqa: F811
        if isinstance(key, tuple):
            item = self
            for idx in key:
                item = item[idx]
            return item
        return super().__getitem__(key)

    @overload
    def __setitem__(self, key: Union[int, NestedIndex], value: T): ...  # noqa

    @overload
    def __setitem__(self, key: slice, value: Iterable[T]): ...  # noqa
    # fmt: on

    def __setitem__(self, key, value):  # noqa: F811
        if isinstance(value, MutableSequence):
            value = NestableEventedList(value)
        if isinstance(key, tuple):
            parent_i, index = self._split_nested_index(key)
            self[parent_i].__setitem__(index, value)
            return
        self._connect_child_emitters(value)
        EventedList.__setitem__(self, key, value)

    def _delitem_indices(
        self, key: Union[int, slice, NestedIndex]
    ) -> Iterable[Tuple[EventedList, int]]:
        if isinstance(key, tuple):
            parent_i, index = self._split_nested_index(key)
            return [(cast(NestableEventedList, self[parent_i]), index)]
        elif isinstance(key, (int, slice)):
            return super()._delitem_indices(key)
        raise TypeError("Deletion index must be int, slice, or tuple")

    def __delitem__(self, key: Union[int, slice]):
        # delete from the end
        for parent, index in self._delitem_indices(key):
            self._disconnect_child_emitters(parent[index])
        super().__delitem__(key)

    def insert(self, index: int, value: T):
        if isinstance(value, list):
            value = NestableEventedList(value)  # type: ignore
        super().insert(index, value)
        self._connect_child_emitters(value)

    def _bubble_event(self, event: Event):
        if event.source == self:
            return
        emitter = getattr(self.events, event.type, None)
        if not emitter:
            return

        for attr in ('index', 'new_index'):
            if hasattr(event, attr):
                cur_index = self._ensure_tuple_index(event.index)
                source_index = self.index(event.source)
                setattr(event, attr, (source_index,) + cur_index)

        emitter(event)

    def _disconnect_child_emitters(self, child: T):
        if isinstance(child, EventedList):
            for emitter in child.events.emitters.values():
                emitter.disconnect(self._bubble_event)

    def _connect_child_emitters(self, child: T):
        if isinstance(child, EventedList):
            for emitter in child.events.emitters.values():
                emitter.connect(self._bubble_event)

    def _ensure_tuple_index(
        self, index: Union[NestedIndex, int]
    ) -> NestedIndex:
        if isinstance(index, int):
            return (index,)  # single integer inserts to self
        elif isinstance(index, tuple):
            return index
        raise TypeError(
            f"Invalid nested index: {index}. Must be an int or tuple"
        )

    def _split_nested_index(
        self, index: Union[NestedIndex, int]
    ) -> Tuple[NestedIndex, int]:
        """Given a nested index, return (nested_parent_index, row)."""
        index = self._ensure_tuple_index(index)
        if index:
            *par, i = index
            return tuple(par), i
        return (), -1  # empty tuple appends to self

    def move_multiple(
        self, sources: Sequence[NestedIndex], dest_index: NestedIndex,
    ) -> int:
        """Move a batch of nested indices, to a single destination."""
        dest_par, dest_i = self._split_nested_index(dest_index)

        destination_group = cast(NestableEventedList, self[dest_par])
        if dest_i < 0:
            dest_i += len(destination_group) + 1
        else:
            dest_i = min(dest_i, len(destination_group))

        self.events.reordered.block()
        moved = 0
        # more complicated when moving multiple objects.
        # don't assume index adjacency ... so move one at a time
        # need to update indices as we pop, so we keep track of the indices
        # we have previously popped
        popped: DefaultDict[NestedIndex, List[int]] = defaultdict(list)
        # we iterate indices from the end first, so pop() always works
        for i, idx in enumerate(sorted(sources, reverse=True)):
            if idx == ():
                raise IndexError("Group cannot move itself")
            src_par, src_i = self._split_nested_index(idx)

            if src_i < 0:
                src_i += len(cast(NestableEventedList, self[src_par]))

            # we need to decrement the src_i by 1 for each time we have
            # previously pulled items out from in front of the src_i
            src_i -= sum(map(lambda x: x <= src_i, popped.get(src_par, [])))
            # we need to decrement the dest_i by 1 for each time we have
            # previously pulled items out from in front of the dest_i
            ddec = sum(map(lambda x: x <= dest_i, popped.get(dest_par, [])))

            # if item is being moved within the same parent,
            # we need to increase the src_i by 1 for each time we have
            # previously inserted items in front of the src_i
            if src_par == dest_par:
                src_i += (dest_i <= src_i) * i
                if src_i == dest_i - ddec:
                    # skip noop
                    continue
            moved += self.move(src_par + (src_i,), dest_par + (dest_i - ddec,))
            popped[src_par].append(src_i)
        self.events.reordered.unblock()
        return moved

    def move(
        self,
        old_index: Union[int, NestedIndex],
        new_index: Union[int, NestedIndex],
    ) -> bool:
        src_par, src_i = self._split_nested_index(old_index)
        dest_par, dest_i = self._split_nested_index(new_index)

        if src_par == dest_par:
            if dest_i > src_i:
                dest_i -= 1
            if src_i == dest_i:
                return False

        self.events.moving(index=old_index, new_index=new_index)

        silenced = ['removed', 'removing', 'inserted', 'inserting']
        for event_name in silenced:
            getattr(self.events, event_name).block()
        value = self[src_par].pop(src_i)  # type: ignore
        self[dest_par].insert(dest_i, value)  # type: ignore
        for event_name in silenced:
            getattr(self.events, event_name).unblock()

        self.events.moved(index=old_index, new_index=new_index, value=value)
        self.events.reordered()
        return True
