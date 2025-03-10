"""Menu bar and menu widgets."""

import re
from typing import Any, Callable

from rich.text import Text
from textual import events
from textual.containers import Container
from textual.dom import NoScreen
from textual.message import Message
from textual.reactive import var
from textual.widgets import Button, Static

from textual_paint.args import args
from textual_paint.localization.i18n import get_direction, get_hotkey, markup_hotkey


def to_snake_case(name: str) -> str:
    """Convert a name to snake_case, for use as an ID."""
    # First remove any hotkey markers (&)
    name = name.replace('&', '')
    # Convert to snake case
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    name = re.sub('__([A-Z])', r'_\1', name)
    name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
    # Replace any remaining non-alphanumeric chars with underscores
    name = re.sub('[^a-zA-Z0-9]', '_', name)
    return name.lower()

class Menu(Container):
    """A menu widget. Note that menus can't be reused in multiple places."""

    class StatusInfo(Message):
        """Sent when hovering over a menu item, or to reset when leaving a menu item or when menu is closed."""
        def __init__(self, description: str|None, closed: bool = False) -> None:
            super().__init__()
            self.description = description
            self.closed = closed

    items: var[list['MenuItem|Separator']] = var([])
    focus_index = var(0)

    def __init__(self, items: list['MenuItem|Separator'], **kwargs: Any) -> None:
        """Initialize a menu."""
        super().__init__(**kwargs)
        self.items = items
        # These are set when opening a submenu
        self.parent_menu: Menu | None = None
        self.parent_menu_item: MenuItem | None = None


    def mount_items(self) -> None:
        """Mount the menu items."""
        # If we're not mounted yet, we'll mount items when we are mounted
        if not self.is_mounted:
            return
        for item in self.items:
            self.mount(item)
            if item.submenu:
                try:
                    self.screen.mount(item.submenu)
                    item.submenu.close()
                except NoScreen:
                    # This can happen during initialization, we'll handle it in on_mount
                    pass
            if isinstance(item, MenuItem):
                item.parent_menu = self

    def compose(self) -> None:
        """Called when the widget is ready to be composed."""
        # This is called before on_mount and ensures we're properly attached to a screen
        yield from ()

    def on_mount(self) -> None:
        """Called when the menu is mounted."""
        self.mount_items()

    def watch_items(self, old_items: list['MenuItem|Separator'], new_items: list['MenuItem|Separator']) -> None:
        """Update the menu items."""
        for item in old_items:
            item.remove()
        if self.is_mounted:
            self.mount_items()
        # If not mounted, items will be mounted when the menu is mounted via on_mount

    def on_key(self, event: events.Key) -> None:
        """Called when the user presses a key."""

        if event.key == "up":
            self.focus_index -= 1
            if self.focus_index < 0:
                self.focus_index = len(self.items) - 1
        elif event.key == "down":
            self.focus_index += 1
            if self.focus_index >= len(self.items):
                self.focus_index = 0
        elif event.key == "escape":
            self.close()
            if self.parent_menu:
                self.parent_menu.focus()
        elif event.is_printable:
            # There doesn't seem to be a way to detect if alt is pressed
            if isinstance(self, MenuBar): #and not event.alt:
                return
            for item in self.items:
                if isinstance(item, MenuItem) and item.hotkey and event.character:
                    if item.hotkey.lower() == event.character.lower():
                        item.press()
                        break


    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Called when a button is clicked or activated with the keyboard."""

        if isinstance(event.button, MenuItem):
            if event.button.has_class("grayed"):
                # TODO: use disabled property once Textual fixes mouse wheel events on disabled buttons
                # and we have a way to listen for the mouse Enter event on disabled buttons
                return
            if event.button.action:
                event.button.action()
                root_menu = self
                while root_menu.parent_menu:
                    root_menu = root_menu.parent_menu
                root_menu.close()
            elif event.button.submenu:
                was_open = event.button.submenu.display
                for item in self.items:
                    if item.submenu:
                        item.submenu.close()
                if not was_open:
                    event.button.submenu.open(self, event.button)

    def open(self, parent_menu: 'Menu', parent_menu_item: 'MenuItem') -> None:
        """Open the menu, and associate it with a parent menu and menu item."""
        self.display = True
        if len(self.items) > 0:
            self.items[0].focus()
        self.parent_menu = parent_menu
        self.parent_menu_item = parent_menu_item
        self.add_class("menu_popup")

        if isinstance(parent_menu, MenuBar):
            y = parent_menu_item.region.y + parent_menu_item.region.height
            self.styles.offset = (parent_menu_item.region.x, y)
            self.styles.max_height = self.screen.size.height - y
        else:
            self.styles.max_height = self.screen.size.height

            # Needed to recompute self.region
            # This makes it much more reliable to open and open in the correct spot,
            # but unfortunately none of these things work to avoid flickering:
            # self.styles.offset = (0, 0)
            # self.refresh(layout=True)
            # self.styles.visibility = "hidden"
            # self.hidden = True
            self.app.refresh(layout=True, repaint=False)
            # self.styles.visibility = "visible"
            # self.hidden = False
            # I also tried call_after_refresh for the below.
            rect = parent_menu_item.region
            self.styles.offset = (
                rect.x - self.region.width if get_direction() == "rtl" else rect.x + rect.width,
                max(0, min(rect.y, self.screen.size.height - self.region.height))
            )
            if get_direction() == "rtl":
                if self.region.x < 0:
                    self.styles.offset = (rect.x + rect.width, rect.y)
                    if self.region.x + self.region.width > self.screen.size.width:
                        self.styles.offset = (self.screen.size.width - self.region.width, rect.y)
            else:
                if self.region.x + self.region.width > self.screen.size.width:
                    self.styles.offset = (rect.x - self.region.width, rect.y)
                    if self.region.x < 0:
                        self.styles.offset = (0, rect.y)

        # Find the widest label
        max_width = 0
        # any_submenus = False
        for item in self.items:
            if isinstance(item, MenuItem):
                assert isinstance(item.label, Text)
                if len(item.label.plain) > max_width:
                    max_width = len(item.label.plain)
                if item.submenu:
                    # any_submenus = True
                    # Add a right pointing triangle to the label
                    # TODO: Make this work generally. Right now I've just spaced it for View > Zoom in English.
                    # Also, all this layout stuff should ideally use the width, not the length, of text.
                    # And it's stupid that this code applies multiple times to the same menu,
                    # and has to be idempotent.
                    # Basically I should rewrite this whole thing.
                    # I'd like to try using the built-in ListView widget for menus.
                    arrow = ">" if args.ascii_only else "▶"
                    if not item.label.plain.endswith(arrow):
                        item.label = item.label.markup + "\t        " + arrow
        # Split on tab character and align the shortcuts
        for item in self.items:
            if isinstance(item, MenuItem):
                assert isinstance(item.label, Text)
                markup_parts = item.label.markup.split("\t")
                plain_parts = item.label.plain.split("\t")
                if len(markup_parts) > 1:
                    item.label = markup_parts[0] + " " * (max_width - len(plain_parts[0])) + markup_parts[1]

    def close(self):
        """Close the menu."""
        for item in self.items:
            if item.submenu:
                item.submenu.close()
        if not isinstance(self, MenuBar):
            self.display = False
        self.post_message(Menu.StatusInfo(None, closed=True))

    def any_menus_open(self) -> bool:
        """Returns whether any submenus are open."""
        for item in self.items:
            if item.submenu and item.submenu.display:
                return True
        return False

class MenuBar(Menu):
    """A menu bar widget."""

    def __init__(self, items: list['MenuItem|Separator'], **kwargs: Any) -> None:
        """Initialize a menu bar."""
        super().__init__(items, **kwargs)


class MenuItem(Button):
    """A menu item widget."""

    def __init__(self,
        name: str,
        action: Callable[[], Any] | None = None,
        id: str | int | None = None,
        submenu: Menu | None = None,
        description: str | None = None,
        grayed: bool = False,
        **kwargs: Any
    ) -> None:
        """Initialize a menu item."""
        super().__init__(markup_hotkey(name), **kwargs)
        self.hotkey: str|None = get_hotkey(name)
        # self.disabled = grayed # This breaks scroll wheel over the menu item, as of Textual 0.20.1
        if grayed:
            self.add_class("grayed")
            self.can_focus = False

        # Prevent menu scrolling down when clicking a menu item,
        # potentially clicking a different menu item, such as Save instead of Open (dangerous!)
        # when the screen is smaller than the menu.
        self.can_focus = False

        self.action = action
        self.submenu = submenu
        self.description = description
        self.parent_menu: Menu | None = None # set when mounted
        if isinstance(id, str):
            self.id = id
        elif id:
            self.id = "rc_" + str(id)
        else:
            self.id = "menu_item_" + to_snake_case(name)

    def on_enter(self, event: events.Enter) -> None:
        """Called when the mouse enters the menu item."""
        if isinstance(self.parent_menu, MenuBar):
            # The message is only reset to the default help text on close, so don't change it while no menu is open.
            # (The top level menus don't have descriptions anyway.)
            return
        self.post_message(Menu.StatusInfo(self.description))
    def on_leave(self, event: events.Leave) -> None:
        """Called when the mouse leaves the menu item."""
        if isinstance(self.parent_menu, MenuBar):
            # The message is only reset to the default help text on close, so don't clear it while no menu is open.
            return
        self.post_message(Menu.StatusInfo(None))


mid_line = ("-" if args.ascii_only else "─") * 100
class Separator(Static):
    """A menu separator widget."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize a separator."""
        super().__init__(mid_line, **kwargs)
        self.hotkey = None
        # self.disabled = True # This breaks scroll wheel over the separator, as of Textual 0.20.1
        self.disabled = False
        self.action = None
        self.submenu = None
