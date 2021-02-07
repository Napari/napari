from __future__ import annotations

from typing import TYPE_CHECKING, Generator

if TYPE_CHECKING:
    from .group import Group


class Node:
    def __init__(self, name: str = "Node"):
        self.parent: Group | None = None
        self.name = name

    def is_group(self) -> bool:
        return False

    def index_in_parent(self) -> int:
        if self.parent is not None:
            return self.parent.index(self)
        # TODO: check if this can be None?
        return 0

    def index_from_root(self) -> tuple[int, ...]:
        item = self
        indices: list[int] = []
        while item.parent is not None:
            indices.insert(0, item.index_in_parent())
            item = item.parent
        return tuple(indices)

    def traverse(self, leaves_only=False) -> Generator[Node, None, None]:
        yield self

    def __str__(self):
        """Render ascii tree string representation of this node"""
        return "\n".join(self._render())

    def _render(self) -> list[str]:
        """Return list of strings that can render ascii tree.

        For ``Node``, we just return the name of this specific node.
        """
        return [self.name]

    def unparent(self):
        if self.parent is not None:
            self.parent.remove(self)
            return self
        raise IndexError("Cannot unparent orphaned Node: {self!r}")
