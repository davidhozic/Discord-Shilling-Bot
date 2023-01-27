"""
    This modules contains definitions related to the client (for API)
"""
from typing import Optional, Union, Optional, List
from contextlib import suppress
from random import random

from . import misc
from . import guild
from . import misc
from . import web

from .logging.tracing import *

from typeguard import typechecked

import _discord as discord
import asyncio


#######################################################################
# Globals
#######################################################################
LOGIN_TIMEOUT_S = 30
TOKEN_MAX_PRINT_LEN = 5
TASK_SLEEP_DELAY_S = 0.100
TASK_STARTUP_DELAY_S = 2


__all__ = (
    "ACCOUNT",
    "get_client"
)


class GLOBALS:
    "Storage class used for storing global variables"
    proxy_installed = False


# ----------------- OPTIONAL ----------------- #
try:
    from aiohttp_socks import ProxyConnector
    GLOBALS.proxy_installed = True
except ImportError:
    GLOBALS.proxy_installed = False
# -------------------------------------------- #


@misc.doc_category("Clients")
class ACCOUNT:
    """
    .. versionadded:: v2.4

    .. versionchanged:: v2.5
        Added ``username`` and ``password`` parameters.
        For logging in automatically

    Represents an individual Discord account.
    
    Each ACCOUNT instance runs it's own shilling task.

    Parameters
    -----------
    token : str
        The Discord account's token
    is_user : Optional[bool] =False
        Declares that the ``token`` is a user account token ("self-bot")
    intents: Optional[discord.Intents]=discord.Intents.default()
        Discord Intents (settings of events that the client will subscribe to)
    proxy: Optional[str]=None
        The proxy to use when connecting to Discord.

        .. IMPORTANT::
            It is **RECOMMENDED** to use a proxy if you are running **MULTIPLE** accounts.
            Running multiple accounts from the same IP address, can result in Discord
            detecting self-bots. 

            Running multiple bot accounts on the other hand is perfectly fine without 
            a proxy.
    servers: Optional[List[guild.GUILD | guild.USER | guild.AutoGUILD]]=[]
        Predefined list of servers (guilds, users, auto-guilds).
    username: Optional[str]
        The username to login with. 
    password: Optional[str]
        The password to login with.
    auto_join: Optional[List[web.GuildDiscoveryCLIENT]]
        List of :class:`~daf.web.GuildDiscoveryCLIENT` though which, the
        account will auto discover and join new guilds.

    .. Caution::
        Do not provide ``token`` parameter if you've provided username and password.
        An exception will be raised to prevent token being used that does not belong
        to the provided account.

    Raises
    ---------------
    ModuleNotFoundError
        'proxy' parameter was provided but requirements are not installed.
    ValueError
        'token' is not allowed if 'username' is provided and vice versa.
    ValueError
        'username' and 'password' must be set if you want the framework to auto-join the guilds (thru the browser)
    """
    @typechecked
    def __init__(self,
                 token : Optional[str]=None,
                 is_user : Optional[bool] =False,
                 intents: Optional[discord.Intents]=None,
                 proxy: Optional[str]=None,
                 servers: Optional[List[Union[guild.GUILD, guild.USER, guild.AutoGUILD]]]=None,
                 username: Optional[str]=None,
                 password: Optional[str]=None,
                 auto_join: Optional[List[web.GuildDiscoveryCLIENT]]=None) -> None:
        connector = None
        if proxy is not None:
            if not GLOBALS.proxy_installed:
                raise ModuleNotFoundError("You need to install extra requirements: pip install discord-advert-framework[proxy]")
        
            connector = ProxyConnector.from_url(proxy)

        if token is not None and username is not None: # Only one parameter of these at a time
            raise ValueError("'token' parameter not allowed if 'username' is given.")
        
        if token is None and username is None: # At least one of these
            raise ValueError("At lest one parameter of these is required: 'token' OR 'username' + 'password'")

        if auto_join is not None and (username is None or password is None):
            raise ValueError("Error with 'auto_join' parameter: 'username' and 'password' must be set"
                             " if you want the framework to auto-join the guilds (thru the browser).")

        self._token = token
        self.is_user = is_user
        self.proxy = proxy
        # If intents not passed, enable default
        if intents == None:
            intents = discord.Intents.default()

        self.intents = intents

        self._running = False
        self.tasks: List[asyncio.Task] = []
        self._servers: List[guild._BaseGUILD] = []
        self._autoguilds: List[guild.AutoGUILD] = [] # To prevent __eq__ issues, use 2 lists
        self._selenium = web.SeleniumCLIENT(username, password, proxy) if username is not None else None

        if servers is None:
            servers = []

        self._uiservers = servers
        """Temporary list of uninitialized servers
        servers parameter gets stored into _servers to prevent the
        update method from re-initializing initializes objects.
        This gets deleted in the initialize method"""

        if auto_join is None:
            auto_join = []
        
        self.auto_join = auto_join

        self._client = discord.Client(intents=intents, connector=connector)
        self._deleted = False
        misc._write_attr_once(self, "_update_sem", asyncio.Semaphore(2))

    def __eq__(self, other):
        if isinstance(other, ACCOUNT):
            return self._token == other._token

        raise NotImplementedError("Only comparison between 2 ACCOUNTs is supported")

    @property
    def selenium(self) -> web.SeleniumCLIENT:
        """
        .. versionadded:: v2.5

        Returns the, bound to account, Selenium client
        """
        return self._selenium

    @property
    def running(self) -> bool:
        """
        Is the account still running?

        Returns
        -----------
        True
            The account is logged in and shilling is active.
        False
            The shilling has ended or not begun.
        """
        return self._running
    
    @property
    def deleted(self) -> bool:
        """
        Returns
        -----------
        True
            The object is no longer in the framework and should no longer
            be used.
        False
            Object is in the framework in normal operation.
        """
        return self._deleted

    @property
    def servers(self):
        """
        Returns all guild like objects inside the account's s
        shilling list. This also includes :class:`~daf.guild.AutoGUILD`
        """
        return self._servers + self._autoguilds
    
    @property
    def client(self) -> discord.Client:
        "Returns the API wrapper client"
        return self._client
    
    def _delete(self):
        """
        Sets the internal _deleted flag to True,
        indicating the object should not be used.
        """
        self._deleted = True
        for server in self.servers:
            server._delete()


    async def initialize(self):
        """
        Initializes the API wrapper client layer.

        Raises
        ------------
        RuntimeError
            Unable to login to Discord.
        """
        # Obtain token if it is not provided
        if self._selenium is not None:
            trace("Logging in thru browser and obtaining token")
            self._token = await self._selenium.initialize()
            self.is_user = True

        # Login
        trace("Logging in...")
        _client_task: asyncio.Future = asyncio.gather(asyncio.create_task(self._client.start(self._token, bot=not self.is_user)), return_exceptions=True)
        try:
            await self._client.wait_for("ready", timeout=LOGIN_TIMEOUT_S)
            trace(f"Logged in as {self._client.user.display_name}")
        except asyncio.TimeoutError as exc:
            exc = _client_task.exception() if _client_task.done() else exc
            raise RuntimeError(f"Error logging in to Discord. (Token {self._token[:TOKEN_MAX_PRINT_LEN]}...)") from exc
        
        for server in self._uiservers:
            try:
                await self.add_server(server)
            except Exception as exc:
                trace("Unable to add server.", TraceLEVELS.WARNING, exc)

        for discovery_client in self.auto_join:
            await discovery_client.initialize(self._selenium)

        del self._uiservers # Only needed for predefined initialization
        self.tasks.append(asyncio.create_task(self._loop()))
        self.tasks.append(asyncio.create_task(self._guild_join_loop()))
        self._running = True

    @typechecked
    async def add_server(self, server: Union[guild.GUILD, guild.USER, guild.AutoGUILD]):
        """
        Initializes a guild like object and
        adds it to the internal account shill list.

        Parameters
        --------------
        server: guild.GUILD | guild.USER | guild.AutoGUILD
            The guild like object to add

        Raises
        --------
        Any
            Raised in 
            :py:meth:`daf.guild.GUILD.initialize()` | :py:meth:`daf.guild.USER.initialize()` | :py:meth:`daf.guild.AutoGUILD.initialize()`
        """
        await server.initialize(parent=self)
        if isinstance(server, guild._BaseGUILD):
            self._servers.append(server)
        else:
            self._autoguilds.append(server)

    @typechecked
    def remove_server(self, server: Union[guild.GUILD, guild.USER, guild.AutoGUILD]):
        """
        Removes a guild like object from the shilling list.

        Parameters
        --------------
        server: guild.GUILD | guild.USER | guild.AutoGUILD
            The guild like object to remove
        
        Raises
        -----------
        ValueError
            ``server`` is not in the shilling list.
        """
        if isinstance(server, guild._BaseGUILD):
            server._delete()
            self._servers.remove(server)
        else:
            self._autoguilds.remove(server)

    @typechecked
    def get_server(self, snowflake: Union[int, discord.Guild, discord.User, discord.Object]) -> Union[guild.GUILD, guild.USER, None]:
        """
        Retrieves the server based on the snowflake id or discord API object.

        Parameters
        -------------
        snowflake: Union[int, discord.Guild, discord.User, discord.Object]
            Snowflake ID or Discord API object.
        
        Returns
        ---------
        Union[guild.GUILD, guild.USER]
            The DAF server object.
        None
            The object was not found.
        """
        if isinstance(snowflake, int):
            snowflake = discord.Object(snowflake)

        for server in self._servers:
            if server.snowflake == snowflake.id:
                return server

        return None

    async def _close(self):
        """
        Signals the tasks of this account to finish and
        waits for them.
        """
        trace(f"Logging out of {self.client.user.display_name}...")
        self._running = False
        self._delete()
        for exc in await asyncio.gather(*self.tasks, return_exceptions=True):
            if exc is not None:
                trace(f"Exception occurred in a task for account {self.client.user.display_name} (Token: {self._token[:TOKEN_MAX_PRINT_LEN]})",
                    TraceLEVELS.ERROR, exc)

        selenium = self.selenium
        if selenium is not None:
            selenium._close()

        await self._client.close()

    async def _loop(self):
        """
        Main task loop for advertising thru each guild.

        Runs while _running is set to True and afterwards
        closes the connection to Discord.
        """
        while self._running:
            ###############################################################
            @misc._async_safe(self._update_sem)
            async def __loop():
                to_remove = []
                to_await = []
                for server in self.servers:
                    if server._check_state():
                        to_remove.append(server)
                    else:
                        to_await.append( server._advertise() )

                for server in to_remove:
                    self.remove_server(server)

                for coro in to_await:
                    status = await coro
                    if status == guild.GUILD_ADVERT_STATUS_ERROR_REMOVE_ACCOUNT:
                        self._running = False
                    # If loop stop has been requested, stop asap
                    if not self._running:
                        return
            ###############################################################
            await __loop()
            await asyncio.sleep(TASK_SLEEP_DELAY_S)
    
    async def _guild_join_loop(self):
        """
        Task used for joining to new guilds.

        Runs while _running is set to True.
        """
        result: web.QueryResult
        while self._running:
            for discovery_client in self.auto_join:
                async for result in discovery_client._query():
                    if not self._running:
                        break

                    if (self.client.get_guild(result.id)) is None:
                        try:
                            await self._selenium.join_guild(result.invite)
                            await self._selenium.random_sleep(2, 4)
                        except Exception as exc:
                            trace("Could not join a guild.", TraceLEVELS.ERROR, exc)

            await asyncio.sleep(TASK_SLEEP_DELAY_S)

    async def update(self, **kwargs):
        """
        Updates the object with new parameters and afterwards updates all lower layers (GUILD->MESSAGE->CHANNEL).

        .. WARNING::
            After calling this method the entire object is reset.
        """
        @misc._async_safe("_update_sem", 2)
        async def update_servers(self_):
            for server in self.servers:
                await server.update(init_options={"parent": self})

        if "token" not in kwargs:
            kwargs["token"] = self._token

        await self._close()
        await misc._update(self, **kwargs)

        await update_servers(self)


def get_client() -> discord.Client:
    """
    TODO: remove in v2.5

    .. deprecated:: v2.4

    Returns the `CLIENT` object used for communicating with Discord.
    """
    trace("DEPRECATED! Function daf.client.get_client is deprecated since v2.4 and is planned for removal. Please use ACCOUNT.client attribute instead.",
          TraceLEVELS.DEPRECATED)
    from . import core
    return core.GLOBALS.accounts[0].client
