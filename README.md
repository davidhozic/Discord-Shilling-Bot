
# **Shilling Framework Documentation**
The Discord Shilling/Advertising/Self-Promotion Framework allows you to periodically (absolute or in a random time range)  send messages to discord servers and channels.
It supports sending normal text, discord embeds(you are required to run on an actual bot) , files and can even accept user defined functions that will be called to get the data you want to send. 
The framework also supports formatted logging which tells you what messages succeeded in which channels and failed in which channels(and why they failed).

You can also build an additional layer on top of the framework, because when run, the framework can call a user defined function before starting shilling, allowing you to eg. make an asyncio task that runs parallel to the shilling framework.


The below documentation describes everything you need to start shilling, thank you for reading it. If you don't like to read you can skip to the [Getting Started](#getting_started) section or see [Examples](#code_examples).
***

<a id="code_examples"> </a>
##  **Examples** :
Because I believe reading documention can be a bit boring, I prepaired some examples in the Examples folder which should show everying you might want to do.<br>
Examples folder: [Examples folder](Examples).
***
<br>

##  **Creatable objects** :
- <a id="framework_embed"> </a>framework.**EMBED** (available to use if running on a **bot account**):
    - The **EMBED** class is an inherited class from discord.Embed meaning it has the same methods as [discord.Embed](https://docs.pycord.dev/en/master/api.html?highlight=discord%20embed#discord.Embed) but you can create a full embed without actually having to call those methods. 
    - <u>Parameters</u>:
        - Author name  (author_name)        : str   - Name of the embed author
        - Author Image (author_image_url)   : str   - URL to author's image
        - Image (image)                     : str   - URL to image that will be placed **at the end** of the embed.
        - Thumbnail (thumbnail)             : str   - URL to image that will be placed **at top right** of the embed.
        - Embedded Fields (fields)          : list  - List of [framework.**EMBED_FIELD**](#framework_embed_field)<br>

        <image alt="framework.EMBED" src="DOC_src\framework_EMBED_obj_1.png">
        <br><br>

- <a id="framework_embed_field"> </a>framework.**EMBED_FIELD** (available to use if running on a **bot account**):
    - The **EMBED_FIELD** is used with combination of [framework.**EMBED**:](#framework_embed) as one of it's parameters that represents one of the fields inside the embedded message.
    - <u>Parameters</u>:
        - Field name (name)         : str  -  Name of the field
        - Field content (content)   : str  -  Text that is placed inside the embedded field
        - Inline (inline)           : bool -  If True and the previous or next embed field also have inline set to true, it will place this field in the same line as the previous or next field
<br><br>
- <a id="framework_file"> </a>framework.**FILE**:
    - The **FILE** objects represents a file you want to send to discord. 
    - <u>Parameters</u>:
        - File name (filename)  - path to the file you want to send to discord
        <br><br>
- <a id="framework_guild"> </a>framework.**GUILD**:
    - The **GUILD** object represents a server to which messages will be sent.
    - <u>Parameters</u>:
        - **Guild ID** - identificator which can be obtain by enabling [developer mode](https://techswift.org/2020/09/17/how-to-enable-developer-mode-in-discord/) in discord's settings and afterwards right-clicking on the server/guild icon in the server list and clicking **"Copy ID"**,
        - **List of <u>MESSAGE</u> objects** - Python list or tuple contating **MESSAGE** objects.
        - <a id="framework_guild_gen_file_log"></a>**Generate file log** - bool variable, if True it will generate a file log for each message send attempt.<br>

    <image alt="framework.GUILD" src="DOC_src\framework_GUILD_obj_1.png">
    <br><br>
<a id="framework_message"></a>
-  framework.**MESSAGE** 
    - The **MESSAGE** object containts parameters which describe behaviour and data that will be sent to the channels.
    - <u>Parameters</u>:
        - **Start Period** , **End Period** (start_period, end_period) - These 2 parameters specify the period on which the messages will be sent.
            - **Start Period** can be either:
              - None - Messages will be sent on intervals specified by **End period**,
              - Integer  >= 0 - Messages will be sent on intervals **randomly** chosen between **<u>Start period** and **End period</u>**, where the randomly chosen intervals will be re-randomized after each sent message.<br><br>
        <a id="framework_message_data"></a>
        - **Data** (data) - The data parameter is the actual data that will be sent using discord's API. The **data types** of this parameter can be:
          - **String** (normal text),
          - [framework.**EMBED**](#framework_embed),
          - [framework.**FILE**](#framework_file),
          - **List/Tuple** containing any of the above arguments (There can up to **1** string, up to **1** embed and up to **10** [framework.FILE](#framework_file) objects, if more than 1 string or embeds are sent, the framework will only consider the last found).
          - Function that accepts any amount of parameters and returns any of the above types. To pass a function, <u>**YOU MUST USE THE [framework.FUNCTION decorator](#framework_decorators_function)**</u> on the function before passing the function to the framework.<br>
          Then when you pass the function to the data parameter, pass it in the next format:
            ```python
            data=function_name(parameter_1, parameter_2, ...., parameter_n)
            ```
            **NOTE**: If you don't use [framework.FUNCTION](framework_decorators_function) decorator the function will only get called once(when you pass it to the data) and will not be called by the framework dynamically.<br>
            Example:<br>
            <image alt="Function parameter" src="DOC_src\function_as_data_parameter_1.png" width=500>
        <br><br>
        - **Channel IDs** (channel_ids) - List of IDs of all the channels you want data to be sent into.
        - **Clear Previous** (clear_previous) - A bool variable that can be either True of False. If True, then before sending a new message to the channels, the framework will delete all previous messages sent to discord that originated from this message object.
        - **Start Now** (start_now) - A bool variable that can be either True or False. If True, then the framework will send the message as soon as it is run and then wait it's period before trying again. If False, then the message will not be sent immediatly after framework is ready, but will instead wait for the period to elapse.<br>
        <image alt="framework.MESSAGE" src="DOC_src\framework_MESSAGE_obj_1.png">
***
<br>

##  **Decorators** :
Python decorators are essentially functions/classes that accept a function or a class as their parameter and add extra functionality on them.<br>
<u>In our case</u> there is only one decorator:<br>
<a id="framework_decorators_function"></a>
- framework.FUNCTION:
    - This decorator accepts a function as it's parameter and then returns a class which's objects will be called by the framework. To use an user defined function as parameter to the [framework.MESSAGE data parameter](#framework_message_data), you must use this decorator beforehand. Please see the **Examples** folder.
    - Usage:<br>
    <img src="DOC_src\function_decorator_1.png" alt="drawing" width="600"/>
***
<br>

##  **Functions** :
The framework only gives you one function to call making it easy to use:
- <a id="framework_framework_run"></a>framework.**run**:
    - <u> Parameters</u>:
        - token             : str       = access token for account
        - is_user           : bool      = Set to True if token is from an user account and not a bot account
        - user_callback     : function  = User callback function (gets called after framework is ran)
        - server_log_output : str       = Path where the server log files will be created
    -   ```py
        framework.run(  token="your_token_here",        # MANDATORY
                        is_user=False,                  # OPTIONAL
                        user_callback=None,             # OPTIONAL
                        server_log_output="Logging")    # OPTIONAL
        ```
***
<br>

##  **Logging** :

### <a id="logging_sent_msgs"></a>**LOG OF SENT MESSAGES**
The framework can keep a log of sent messages for **each guild/server**. To enable file logging of sent messages, set the parameter [**Generate file log**](#framework_guild_gen_file_log) to True inside each [GUILD OBJECT](#framework_guild).<br> 
Inside the log you will find data of what was sent (text, embed, files), a channel list it succeeded to send this message and a channel list of the ones it failed (If it failed due to slow mode, the message will be sent as soon as possible, overwriting the default period) <br>
All of these file logs will be Markdown files.<br>
<image alt="Server Log" src="DOC_src\framework_server_log_1.png" width=1920>
(Left is raw Markdown code, to the right is rendered Markdown)

<br>

***

## **Getting started**:
### <u> Install requirements:</u>
To use the Shilling Framework, you need to first install **aiohttp**.

### <u> Sending messages </u>

To start sending messages you must first create a python file, e.g <u>*main.py*</u> and import <u>**framework**</u>.<br>
I recommend you take a look at <u>**Examples folder**</u>.


Then define the server list:
```py
framework.GUILD.server_list = [
]
```
and in that server list, define **GUILD** objects.
```py
framework.GUILD.server_list = [
    # GUILD 1
    framework.GUILD(
        123456789,       # ID of server (guild)
        [                # List MESSAGE objects 
            framework.MESSAGE(start_period=None, end_period=0, data="", channel_ids=[123456789, 123456789], clear_previous=False, start_now=True),
            framework.MESSAGE(start_period=None, end_period=0, data="", channel_ids=[123456789, 123456789], clear_previous=False, start_now=True),
        ],
        generate_log=True            # Create file log of sent messages for this server
    ),

    # GUILD 2
    framework.GUILD(
        123456789,       # ID of server (guild)
        [                # List MESSAGE objects 
            framework.MESSAGE(start_period=None, end_period=0, data="", channel_ids=[123456789, 123456789], clear_previous=False, start_now=True),
            framework.MESSAGE(start_period=None, end_period=0, data="", channel_ids=[123456789, 123456789], clear_previous=False, start_now=True),
        ],
        generate_log=True            # Create file log of sent messages for this server
    ),

    # GUILD n
    framework.GUILD(
        123456789,       # ID of server (guild)
        [                # List MESSAGE objects 
            framework.MESSAGE(start_period=None, end_period=0, data="", channel_ids=[123456789, 123456789], clear_previous=False, start_now=True),
            framework.MESSAGE(start_period=None, end_period=0, data="", channel_ids=[123456789, 123456789], clear_previous=False, start_now=True),
        ],
        generate_log=True            # Create file log of sent messages for this server
    )
]
```

Now start the framework by calling the [**framework.run()**](#framework_framework_run) function. The function can accept one parameter which is a function to be called after framework has started.

```python

def callback():
    print("Framework is now running")

framework.run(token="your_token_here",      
              user_callback=callback)         

```

That's it, your framework is now running and messages will be periodicaly sent.
