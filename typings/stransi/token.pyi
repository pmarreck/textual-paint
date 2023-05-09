"""
This type stub file was generated by pyright.
"""

from dataclasses import dataclass
from typing import Text

"""The basic unit of ANSI escape sequences."""
@dataclass
class Token:
    r"""
    The basic unit of ANSI escape sequences.

    Examples
    --------
    >>> from stransi import Escape
    >>> list(Escape("\033[38;2;255;0;255m")
    ...      .tokens())  # doctest: +NORMALIZE_WHITESPACE
    [Token(kind='m', data=38),
     Token(kind='m', data=2),
     Token(kind='m', data=255),
     Token(kind='m', data=0),
     Token(kind='m', data=255)]
    """
    kind: Text
    data: int
    def issgr(self) -> bool:
        """
        Return True if this is a SGR escape sequence.

        Examples
        --------
        >>> Token(kind="m", data=0).issgr()
        True
        >>> Token(kind="H", data=0).issgr()
        False
        """
        ...
    


