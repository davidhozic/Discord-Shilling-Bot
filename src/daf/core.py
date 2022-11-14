"""
    This module contains the essential definitions
    and functions needed for the framework to run,
    as well as user function to control the framework
"""
from __future__ import annotations
from typing import Callable, Coroutine, List, Optional, Union, overload
from typeguard import typechecked

from .exceptions import *
from .logging.tracing import *
from .logging import sql, logging, tracing

from . import guild
from . import client
from . import misc
from . import message
from . import gen

import asyncio
import _discord as dc

#######################################################################
# Configuration
#######################################################################
C_TASK_SLEEP_DELAY = 0.010 # Advertiser task sleep
EVENT_LOOP_CLOSE_DELAY = 1

#######################################################################
# Exports
#######################################################################
__all__ = (
    "run",
    "shutdown",
    "add_object",
    "remove_object",
    "get_guild_user",
    "initialize"
)

#######################################################################
# Globals   (These are all set in the daf.run function)
#######################################################################
class GLOBALS:
    """
    Storage class used for holding global variables.
    """
    server_list: List[guild._BaseGUILD, gen.AutoGUILD] = [] # Guild/User objects 
    awaiting_removal: List[guild._BaseGUILD, gen.AutoGUILD] = [] # Guild/User objects 
    awaiting_addition: List[guild._BaseGUILD, gen.AutoGUILD] = [] # Guild/User objects 


#######################################################################
# Coroutines
#######################################################################
async def _advertiser(message_type: guild.AdvertiseTaskType) -> None:
    """
    The task that is responsible for shilling to channels.
    This is the most top level task.

    Parameters
    ------------
    message_type: str
        Two tasks advertising tasks are created, this variable tells the guild objects which
        task is requesting to shill, so it knows what type of messages to actually send.
    """
    while True:
        await asyncio.sleep(C_TASK_SLEEP_DELAY)
        
        # TODO: This will not work due to 2 tasks, find a better solution.
        #       This also doesn't work with AutoGUILD and GUILD added at the same time (__eq__ method).

        # Add new objects that were added
        GLOBALS.server_list.extend(GLOBALS.awaiting_addition)
        GLOBALS.awaiting_addition.clear()

        # Remove objects that were removed
        for o in GLOBALS.awaiting_removal:
            GLOBALS.server_list.remove(o)
        
        GLOBALS.awaiting_removal.clear()

        for guild_user in GLOBALS.server_list:
            # Remove guild
            if guild_user._check_state():
                trace(f"[GUILD:] Removing {guild_user}")
                remove_object(guild_user)

            await guild_user._advertise(message_type)


@misc.doc_category("Core control")
async def initialize(token : str,
                     server_list : Optional[List[Union[guild.GUILD, guild.USER]]]=[],
                     is_user : Optional[bool] =False,
                     user_callback : Optional[Union[Callable, Coroutine]]=None,
                     server_log_output : Optional[str] =None,
                     sql_manager: Optional[sql.LoggerSQL]=None,
                     intents: Optional[dc.Intents]=None,
                     debug : Optional[ TraceLEVELS | int | str | bool ] = TraceLEVELS.NORMAL,
                     proxy: Optional[str]=None,
                     logger: Optional[logging.LoggerBASE]=None) -> None:
    """
    The main initialization function.
    It initializes all the other modules, creates advertising tasks
    and initializes all the core functionality.
    If you want to control your own event loop, use this instead of run.

    Parameters
    ---------------
    Any: Any
        Parameters are the same as in :func:`daf.core.run`.
    """
    loop = asyncio.get_event_loop()
    
    if isinstance(debug, bool):
        trace("Using bool for debug parameter is DEPRECATED. Use daf.logging.TraceLEVELS", TraceLEVELS.DEPRECATED)
        debug = TraceLEVELS.NORMAL if debug else TraceLEVELS.DEPRECATED
    
    tracing.initialize(debug) # Print trace messages to the console for debugging purposes
    
    if intents is None: # Sphinx doesn't like if this is directly in the declaration
        intents = dc.Intents.default()

    # Initialize discord client
    trace("[CORE:] Logging in...")
    await client._initialize(token, bot=not is_user, intents=intents, proxy=proxy)

    # Initialize logging
    # --------------- DEPRECATED -------------------- #
    if server_log_output is not None:
        if logger is None:
            trace("DEPRECATED! Using this parameter is deprecated and scheduled for removal\nIt is implicitly converted to logger=LoggerJSON(path=\"History\")",
                  TraceLEVELS.DEPRECATED)
            logger = logging.LoggerJSON(path=server_log_output)
        else:
            trace("logger parameter was passed, ignoring server_log_output", TraceLEVELS.WARNING)
    
    if sql_manager is not None:
        if logger is None:
            trace("DEPRECATED! Using this parameter is deprecated and scheduled for removal\nIt is implicitly converted to logger=LoggerSQL(...)",
                  TraceLEVELS.DEPRECATED)
            logger = sql_manager
        else:
            trace("logger parameter was passed, ignoring sql_manager", TraceLEVELS.WARNING)
    # ----------------------------------------------- #
    if logger is None:
        logger = logging.LoggerJSON(path="History")

    await logging.initialize(logger)

    # Initialize the servers (and their message objects)
    trace("[CORE]: Initializing servers", TraceLEVELS.NORMAL)
    for server in server_list:
        try:
            await add_object(server) # Add each guild to the shilling list
        except (DAFError, ValueError, TypeError) as ex:
            trace(ex)
    
    # Create advertiser tasks
    trace("[CORE]: Creating advertiser tasks", TraceLEVELS.NORMAL)
    loop.create_task(_advertiser(guild.AdvertiseTaskType.TEXT_ISH))
    loop.create_task(_advertiser(guild.AdvertiseTaskType.VOICE))

    # Create the user callback task
    if user_callback is not None:
        trace("[CORE]: Starting user callback function", TraceLEVELS.NORMAL)
        user_callback = user_callback()
        if isinstance(user_callback, Coroutine):
            loop.create_task(user_callback)

    trace("[CORE]: Initialization complete.", TraceLEVELS.NORMAL)


#######################################################################
# Functions
#######################################################################

@overload
@misc.doc_category("Shilling list modification", True)
async def add_object(obj: Union[guild.USER, guild.GUILD]) -> None:
    """

    Adds a guild or an user to the daf.

    Parameters
    -----------
    obj: Union[guild.USER, guild.GUILD]
        The guild object to add into the daf.

    Raises
    ----------
    ValueError
        The guild/user is already added to the daf.
    TypeError
        The object provided is not supported for addition.
    TypeError
        Invalid parameter type.
    Other
        Raised in the obj.initialize() method
    """
    ...
@overload
@misc.doc_category("Shilling list modification", True)
async def add_object(obj: Union[message.DirectMESSAGE, message.TextMESSAGE, message.VoiceMESSAGE],
                     snowflake: Union[int, guild.GUILD, guild.USER, dc.Guild, dc.User, dc.Object]) -> None:
    """
    Adds a message to the daf.

    Parameters
    -----------
    obj: Union[message.DirectMESSAGE, message.TextMESSAGE, message.VoiceMESSAGE]
        The message object to add into the daf.
    snowflake: Union[int, guild.GUILD, guild.USER, discord.Guild, discord.User]
        Which guild/user to add it to (can be snowflake id or a framework _BaseGUILD object or a discord API wrapper object).

    Raises
    ----------
    ValueError
        guild_id wasn't provided when adding a message object (to which guild should it add)
    TypeError
        The object provided is not supported for addition.
    TypeError
        Missing snowflake parameter.
    DAFNotFoundError(code=DAF_SNOWFLAKE_NOT_FOUND)
        Could not find guild with that id.
    Other
        Raised in the obj.add_message() method
    """
    ...
@overload
@misc.doc_category("Shilling list modification", True)
async def add_object(obj: gen.AutoGUILD) -> None:
    """
    Adds a AutoGUILD to the shilling list.

    Parameters
    -----------
    obj: daf.gen.AutoGUILD
        AutoGUILD object that automatically finds guilds to shill in.

    Raises
    ----------
    TypeError
        The object provided is not supported for addition.
    Other
        From :py:meth`~daf.gen.AutoGUILD.initialize` method.
    """
    ...

async def add_object(obj, snowflake=None):
    object_type_name = type(obj).__name__
    # Convert the `snowflake` object into a discord snowflake ID (only if adding a message to guild)
    if isinstance(snowflake, (dc.Guild, dc.User, dc.Object)):
        snowflake = snowflake.id
    elif isinstance(snowflake, guild._BaseGUILD):
        snowflake = snowflake.snowflake

    # Add the object
    if isinstance(obj, guild._BaseGUILD):
        if obj in GLOBALS.server_list + GLOBALS.awaiting_addition:
            raise ValueError(f"{object_type_name} with snowflake `{obj.snowflake}` is already added to the daf.")

        await obj.initialize()
        GLOBALS.awaiting_addition.append(obj)

    elif isinstance(obj, gen.AutoGUILD):
        await obj.initialize()
        GLOBALS.awaiting_addition.append(obj)

    elif isinstance(obj, message.BaseMESSAGE):
        if snowflake is None:
            raise TypeError(f"`snowflake` is required to add a message. Only the {object_type_name} object was provided.")

        for guild_user in GLOBALS.server_list:
            if guild_user.snowflake == snowflake:
                await guild_user.add_message(obj)
                return

        raise DAFNotFoundError(f"Guild or user with snowflake `{snowflake}` was not found in the daf.", DAF_SNOWFLAKE_NOT_FOUND)

    else:
        raise TypeError(f"Invalid object type `{object_type_name}`.")


@misc.doc_category("Shilling list modification")
def remove_object(snowflake: Union[int, dc.Object, dc.Guild, dc.User, dc.Object, guild._BaseGUILD, message.BaseMESSAGE, gen.AutoGUILD]) -> None:
    """
    Removes an object from the daf.

    Parameters
    -------------
    snowflake: Union[int, dc.Object, dc.Guild, dc.User, dc.Object, guild._BaseGUILD, message.BaseMESSAGE, gen.AutoGUILD]
        The GUILD/USER object to remove/snowflake of GUILD/USER
        or a xMESSAGE object or AutoGUILD object.

    Raises
    --------------
    DAFNotFoundError(code=DAF_SNOWFLAKE_NOT_FOUND)
         Could not find guild with that id.
    TypeError
        Invalid argument."""    
    if isinstance(snowflake, message.BaseMESSAGE):
        for _guild in GLOBALS.server_list:
            if snowflake in _guild.messages:
                _guild.remove_message(snowflake)
                break
    elif isinstance(snowflake, gen.AutoGUILD):
        GLOBALS.awaiting_removal.append(snowflake)
    else:
        if not isinstance(snowflake, guild._BaseGUILD):
            snowflake = get_guild_user(snowflake)

        if snowflake is not None and snowflake in GLOBALS.server_list + GLOBALS.awaiting_removal:
            GLOBALS.awaiting_removal.remove(snowflake)
        else:
            raise DAFNotFoundError(f"GUILD/USER not in the shilling list.", DAF_SNOWFLAKE_NOT_FOUND)


@misc.doc_category("Getters")
def get_guild_user(snowflake: Union[int, dc.Object, dc.Guild, dc.User, dc.Object]) -> Union[guild.GUILD, guild.USER, None]:
    """
    Retrieves the GUILD/USER object that has the ``snowflake`` ID from the shilling list. 

    Parameters
    -------------
    snowflake: Union[int, discord.Object, discord.Guild, discord.User, discord.Object]
        Snowflake ID or discord objects containing snowflake id of the GUILD.
    
    Raises
    ---------------
    TypeError
        Incorrect snowflake type

    Returns
    ---------------
    :class:`daf.guild.GUILD` | :class:`daf.guild.USER`
        The object requested.
    None
        If not guild/user not in the shilling list.
    """
    if isinstance(snowflake, int):
        snowflake = dc.Object(snowflake)

    for guild in GLOBALS.server_list:
        if guild.snowflake == snowflake.id:
            return guild

    return None


@misc.doc_category("Core control")
async def shutdown(loop: Optional[asyncio.AbstractEventLoop]=None) -> None:
    """
    Stops the framework.

    .. versionchanged:: v2.1
        Made the function non async and shutdown everything.

    Parameters
    ----------
    loop: Optional[asyncio.AbstractEventLoop]
        The loop everything is running in.
        Leave empty for default loop.
    """
    if loop is None:
        loop = asyncio.get_event_loop()
    
    loop.stop()


def _shutdown_clean(loop: asyncio.AbstractEventLoop) -> None:
    """
    Fully stops all the tasks and then closes the event loop

    Parameters
    ---------------
    loop: asyncio.AbstractEventLoop
        The loop to stop.
    """
    cl = client.get_client()
    loop.run_until_complete(cl.close())
    # Cancel all tasks
    tasks = asyncio.all_tasks(loop)
    for task in tasks:
        if not task.done():
            task.cancel()

    loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
    loop.run_until_complete(asyncio.sleep(EVENT_LOOP_CLOSE_DELAY)) # Yield for one second to allow aiohttp cleanup


@misc.doc_category("Getters")
def get_shill_list() -> List[Union[guild.GUILD, guild.USER]]:
    """
    .. versionadded:: v2.1

    Returns
    -----------
    List[Union[guild.GUILD, guild.USER]]
        The shilling list.
    """
    return GLOBALS.server_list.copy()


@typechecked
@misc.doc_category("Core control")
def run(token : str,
        server_list : Optional[List[Union[guild.GUILD, guild.USER]]]=[],
        is_user : Optional[bool] =False,
        user_callback : Optional[Union[Callable, Coroutine]]=None,
        server_log_output : Optional[str] =None,
        sql_manager: Optional[sql.LoggerSQL]=None,
        intents: Optional[dc.Intents]=None,
        debug : Optional[ TraceLEVELS | int | str | bool ] = TraceLEVELS.NORMAL,
        proxy: Optional[str]=None,
        logger: Optional[logging.LoggerBASE]=None) -> None:
    """
    Runs the framework and does not return until the framework is stopped (:func:`daf.core.shutdown`).
    After stopping, it returns None.

    .. warning::
        This will block until the framework is stopped, if you want manual control over the
        asyncio event loop, eg. you want to start the framework as a task, use
        the :func:`daf.core.initialize` coroutine.

    .. versionchanged:: v2.2

        .. card::
        
            - Added ``logger`` parameter
            - ``user_callback`` can now be a regular function as well as async
        

    .. deprecated:: v2.2

        .. card::

            These parameters are replaced with ``logger`` parameter.
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            - sql_manager
            - server_log_output
            

    Parameters
    ---------------
    token: str
        Discord's access token for account.
    server_list: Optional[List[Union[:ref:`GUILD`, :ref:`USER`]]
        Predefined server list (guild list) to shill.
    is_user: Optional[bool]
        Set to True if the token is for an user account.
    user_callback: Optional[Union[Callable, Coroutine]]
        Function or async function to call after the framework has been started.
    server_log_output: Optional[str]
        Path where the server log files will be created.
    sql_manager: Optional[:ref:`LoggerSQL`]
        SQL manager object that will save logs into the database.
    intents: Optional[discord.Intents]
        Discord Intents object (represents settings to which events it will be listened to).
    debug : Optional[TraceLEVELS | int | str] = TraceLEVELS.NORMAL
        .. versionchanged:: v2.3
            Deprecate use of bool (assume TraceLEVELS.NORMAL).
            Add support for TraceLEVELS or int or str that converts to TraceLEVELS.

        The level of trace for trace function to display.
        The higher value this option is, the more will be displayed.
    proxy: Optional[str]
        URL of a proxy you want the framework to use.
    logger: Optional[loggers.LoggerBASE]
        The logging class to use.
        If this is not provided, JSON is automatically used.

    Raises
    ---------------
    ModuleNotFoundError
        Missing modules for the wanted functionality, install with ``pip install discord-advert-framework[optional-group]``.
    ValueError
        Invalid proxy url.
    """
    _params = locals().copy()
    loop = asyncio.get_event_loop()
    try:
        loop.create_task(initialize(**_params))
        loop.run_forever()
    except asyncio.CancelledError as exc:
        trace(exc, TraceLEVELS.ERROR)
    except KeyboardInterrupt:
        trace("Received a cancellation event. Stopping..", TraceLEVELS.WARNING)
    finally:
        _shutdown_clean(loop)
        asyncio.set_event_loop(None)
        loop.close()