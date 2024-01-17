from typing import List
from typeguard import typechecked

from .base import ResponderBase
from .logic import BaseLogic
from .constraints import BaseDMConstraint
from .actions import DMResponse
from ..events import EventID

from ..misc.doc import doc_category

import asyncio_event_hub as aeh
import _discord as discord


__all__ = ("DMResponder",)


@doc_category("Auto responder", path="responder")
class DMResponder(ResponderBase):
    __doc__ = "DM responder implementation. " + ResponderBase.__doc__

    @typechecked
    def __init__(
        self,
        condition: BaseLogic,    
        action: DMResponse,
        constraints: List[BaseDMConstraint] = [], 
    ) -> None:
        super().__init__(condition, action, constraints)

    def initialize(self, event_ctrl: aeh.EventController, client: discord.Client):
        event_ctrl.add_listener(
            EventID.discord_message,
            self.handle_message,
            lambda m: isinstance(m.channel, discord.DMChannel)
        )
        self.event_ctrl = event_ctrl
        self.client = client
