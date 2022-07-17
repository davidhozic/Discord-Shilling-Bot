""" ~ exceptions ~
- @Added in v1.9.5
- @Info: This module contains the definitons related to errors
         that can be raised inside the framework."""

# TODO: Documentation

class DAFError(Exception):
    """~ class ~
    @Info: Base exception class for all DAF exceptions."""
    def __init__(self, message: str, code: int):
        self.code = code # Error code
        super().__init__(message)

class DAFParameterError(DAFError):
    """~ class ~
    @Info: Raised when theres an parameter exception."""
    pass

class DAFNotFoundError(DAFError):
    """~ class ~
    @Info: Raised when an object is not found."""
    pass

class DAFSQLError(DAFError):
    """~ class ~
    @Info: Raised whenever there's an error with SQL."""
    pass

# Error Codes
## Guild codes
DAF_GUILD_ALREADY_ADDED         = 0     # Guild with specified snowflake is already added.
DAF_GUILD_ID_REQUIRED           = 1     # Guild ID is required but was not passed.    
DAF_GUILD_ID_NOT_FOUND          = 2     # Guild with specified snowflake was not found (or user).
DAF_USER_CREATE_DM              = 3
## Data type codes
DAF_INVALID_TYPE                = 4     # Object of invalid type was given.
DAF_YOUTUBE_STREAM_ERROR        = 5     # The given youtube link could not be streamed (AUDIO, VoiceMESSAGE).
DAF_FILE_NOT_FOUND              = 6     # The given file was not found.
## Parameter specific errors
DAF_UPDATE_PARAMETER_ERROR      = 7     # The update method only accepts the following keyword arguments.
DAF_MISSING_PARAMETER           = 8     # The parameter(s) is(are) missing.
## SQL Exceptions
DAF_SQL_CREATE_TABLES_ERROR     = 9     # Unable to create all the tables.
DAF_SQL_LOOKUPTABLE_NOT_FOUND   = 10    # The lookup table was not found.
DAF_SQL_BEGIN_ENGINE_ERROR      = 11    # Unable to start engine.
DAF_SQL_CR_LT_VALUES_ERROR      = 12    # Unable to create lookuptables' rows.
DAF_SQL_CREATE_DT_ERROR         = 13    # Unable to create SQL data types.
DAF_SQL_CREATE_VPF_ERROR        = 14    # Unable to create views, procedures and functions.
DAF_SQL_CURSOR_CONN_ERROR       = 15    # Unable to connect the cursor.