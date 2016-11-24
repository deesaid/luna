# Stubs for gamecontextmenu (Python 2)
#
# NOTE: This dynamically typed stub was automatically generated by stubgen.

import xbmcgui
from resources.lib.manager.gamemanager import GameManager
from resources.lib.model.game import Game
from resources.lib.model.hostdetails import HostDetails
from resources.lib.views.gamecontextmenu import GameContextMenu as GameContextMenuType
from xbmcgui import ControlList


class GameContextMenu(xbmcgui.WindowXMLDialog):
    def __new__(cls:GameContextMenuType, *args, **kwargs): ...
    host = ... # type: HostDetails
    list_item = ... # type: xbmcgui.ListItem
    game_manger = ... # type: GameManager
    list = ... # type: ControlList
    refresh_required = False
    def __init__(self:GameContextMenuType, host:HostDetails, list_item: xbmcgui.ListItem) -> GameContextMenuType: ...
    def onInit(self): ...
    def build_list(self): ...
    def onAction(self, action:xbmcgui.Action): ...