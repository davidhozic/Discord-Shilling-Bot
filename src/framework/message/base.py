"""
    Contains base definitions for different message classes."""

from typing import Any, Dict, Iterable, Set, Tuple, Union
from datetime import timedelta, datetime
from typeguard import check_type

from ..dtypes import *
from ..tracing import *
from ..timing import *
from ..exceptions import *
from .. import misc

import random
import _discord as discord
import asyncio


__all__ = (
    "BaseMESSAGE",
)


@misc._enforce_annotations
class BaseMESSAGE:
    """
    This is the base class for all the different classes that
    represent a message you want to be sent into discord.

    .. deprecated:: 2.1
        (start_now) - Using bool value to dictate whether the message should be sent at framework start.

        Use ``timedelta`` object instead describing the delay before first send.
    
    Parameters
    -----------------
    start_period: Union[int, timedelta, None]
        If this this is not None, then it dictates the bottom limit for range of the randomized period. Set this to None
                                         for a fixed sending period.
    end_period: Union[int, timedelta],
        If start_period is not None, this dictates the upper limit for range of the randomized period. If start_period is None, then this
                            dictates a fixed sending period in SECONDS, eg. if you pass the value `5`, that means the message will be sent every 5 seconds.
    data: inherited class dependant
        The data to be sent to discord.
    start_in: timedelta
        Dictates when, the first send should be


    Raises
    ----------------
    DAFParameterError(code=DAF_INVALID_TYPE)
        The parameter end_period cannot be None.
    """
    __slots__ = (
        "period",
        "start_period",
        "force_retry",
        "end_period",
        "next_send_time",
        "data",
        "update_semaphore",
        "_deleted"
    )

    __logname__: str = "" # Used for registering SQL types and to get the message type for saving the log

    def __init__(self,
                start_period: Union[int, timedelta, None],
                end_period: Union[int, timedelta],
                data: Any,
                start_in: Union[timedelta, bool]):
        
        # Data parameter checks
        if isinstance(data, Iterable):
            if not len(data):
                raise TypeError(f"data parameter cannot be an empty iterable. Got: '{data}'")
            
            annots = self.__init__.__annotations__["data"]  
            for element in data:
                if isinstance(element, _FunctionBaseCLASS): # Check if function is being used standalone
                    raise TypeError(f"The function can only be used on the data parameter directly, not in a iterable. Function: '{element})'")
                
                # Check if the list elements are of correct type (typeguard does not protect iterable's elements)
                check_type("data", element, annots)

        # Deprecated int, use timedelta
        if isinstance(start_period, int):
            trace("Using int on start_period is deprecated, use timedelta object instead", TraceLEVELS.WARNING)
            start_period = timedelta(seconds=start_period)

        if isinstance(end_period, int):
            trace("Using int on end_period is deprecated, use timedelta object instead", TraceLEVELS.WARNING)
            end_period = timedelta(seconds=end_period)
        
        if start_period is None:
            self.period = end_period    # Fixed period is used, equal to end_period
        else:
            range = map(int, [start_period.total_seconds(), end_period.total_seconds()])
            self.period = random.randrange(*range) # Randomized period is used
            
        if isinstance(start_in, bool): # Deprecated since 2.1
            self.next_send_time = datetime.now() if start_in else datetime.now() + self.period
            trace("Using bool value for 'start_in' ('start_now') parameter is deprecated. Use timedelta object instead.", TraceLEVELS.WARNING)
        else:
            self.next_send_time = datetime.now() + start_in


        self.force_retry = {"ENABLED" : False, "TIMESTAMP" : None}
        self.data = data
        self.start_period = start_period
        self.end_period = end_period

        # Attributes created with this function will not be re-referenced to a different object
        # if the function is called again, ensuring safety (.update_method)
        misc._write_attr_once(self, "_deleted", False)
        misc._write_attr_once(self, "update_semaphore", asyncio.Semaphore(1))

    @property
    def deleted(self) -> bool:
        """
        Property that indicates if an object has been deleted from the shilling list.

        If this is True, you should dereference this object from any variables.
        """
        return self._deleted

    def _delete(self):
        """
        Sets the deleted flag to True, indicating the user should stop
        using this message.
        """
        self._deleted = True

    def _generate_exception(self,
                           status: int,
                           code: int,
                           description: str,
                           cls: discord.HTTPException) -> discord.HTTPException:
        """
        Generates a discord.HTTPException inherited class exception object.
        This is used for generating dummy exceptions that are then raised inside the `._send_channel()`
        method to simulate what would be the result of a API call, without actually having to call the API (reduces the number of bad responses).

        Parameters
        -------------
        status: int
            Discord status code of the exception.
        code: int
            Discord error code.
        description: str
            The textual description of the error.
        cls: discord.HTTPException
            Inherited class from discord.HTTPException to make exception from.
        """
        resp = Exception()
        resp.status = status
        resp.status_code = status
        resp.reason = cls.__name__
        resp = cls(resp, {"message" : description, "code" : code})
        return resp

    def _generate_log_context(self):
        """
        This method is used for generating a dictionary (later converted to json) of the
        data that is to be included in the message log. This is to be implemented inside the
        inherited classes.
        """
        raise NotImplementedError

    def _get_data(self) -> dict:
        """
        Returns a dictionary of keyword arguments that is then expanded
        into other functions (_send_channel, generate_log)
        This is to be implemented in inherited classes due to different data_types
        """
        raise NotImplementedError

    def _handle_error(self) -> bool:
        """
        This method handles the error that occurred during the execution of the function.
        Returns ``True`` if error was handled.
        """
        raise NotImplementedError

    def is_ready(self) -> bool:
        """
        This method returns bool indicating if message is ready to be sent.
        """
        return (datetime.now() >= self.force_retry["TIMESTAMP"] if self.force_retry["ENABLED"]
                else datetime.now() >= self.next_send_time)

    def reset_timer(self) -> None:
        """
        Resets internal timer
        """
        self.force_retry["ENABLED"] = False
        if self.start_period is not None:
            range = map(int, [self.start_period.total_seconds(), self.end_period.total_seconds()])
            self.period = timedelta(seconds=random.randrange(*range))

        # Absolute timing instead of relative to prevent time slippage due to missed timer reset.
        current_stamp = datetime.now()
        while self.next_send_time < current_stamp:
            self.next_send_time += self.period

    async def _send_channel(self) -> dict:
        """
        Sends data to a specific channel, this is separate from send
        for easier implementation of similar inherited classes
        The method returns a dictionary: `{"success": bool, "reason": discord.HTTPException}` where
        `"reason"` is only present if `"success"` `is False`
        """
        raise NotImplementedError

    async def send(self) -> dict:
        """
        Sends a message to all the channels.
        Returns a dictionary generated by the `._generate_log_context` method
        """
        raise NotImplementedError

    async def _initialize_channels(self):
        """
        This method initializes the implementation specific
        api objects and checks for the correct channel input context.
        """
        raise NotImplementedError

    async def update(self, init_options: dict={}, **kwargs):
        """
        Used for changing the initialization parameters the object was initialized with.

        .. warning::
            Upon updating, the internal state of objects get's reset, meaning you basically have a brand new created object.

        Parameters
        -------------
        init_options: dict
            Contains the initialization options used in .initialize() method for re-initializing certain objects.
            This is implementation specific and not necessarily available.
        original_params:
            The allowed parameters are the initialization parameters first used on creation of the object AND

        Raises
        ------------
        DAFParameterError(code=DAF_UPDATE_PARAMETER_ERROR)
            Invalid keyword argument was passed
        Other
            Raised from .initialize() method

        .. versionadded::
            v2.0
        """

        raise NotImplementedError

    async def initialize(self, **options):
        """
        The initialize method initializes the message object.

        Parameters
        -------------
        - options - keyword arguments sent to _initialize_channels() from an inherited (from _BaseGUILD) class, contains extra init options.

        Raises
        -------------
        - Exceptions raised from ._initialize_channels() and .initialize_data() methods
        """
        await self._initialize_channels(**options)
