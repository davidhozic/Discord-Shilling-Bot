# Import the necessary items
from daf.logging.logger_json import LoggerJSON

from daf.guild.autoguild import AutoGUILD
from daf.logic import or_
from daf.messagedata.textdata import TextMessageData
from datetime import timedelta
from daf.message.autochannel import AutoCHANNEL
from daf.message.messageperiod import FixedDurationPeriod
from daf.message.text_based import TextMESSAGE
from daf.logic import contains
from daf.client import ACCOUNT
from daf.logging.tracing import TraceLEVELS
import daf

# Define the logger
logger = LoggerJSON(
    path="C:\\Users\\david\\daf\\History",
)

# Define remote control context


# Defined accounts
accounts = [
    ACCOUNT(
        token="TOKEN_HERE",
        is_user=True,
        servers=[
            AutoGUILD(
                include_pattern=or_(
                    operands=[
                        contains(keyword="shill"),
                        contains(keyword="NFT"),
                        contains(keyword="dragon"),
                        contains(keyword="promo"),
                    ],
                ),
                messages=[
                    TextMESSAGE(
                        data=TextMessageData(content="Checkout my  new Red Dragon NFT! Additionaly, we also have the Golden Dragon - limited time only!"),
                        channels=AutoCHANNEL(
                            include_pattern=or_(
                                operands=[
                                    contains(keyword="nft"),
                                    contains(keyword="shill"),
                                    contains(keyword="self-promo"),
                                    contains(keyword="projects"),
                                    contains(keyword="marketing"),
                                ],
                            ),
                        ),
                        period=FixedDurationPeriod(duration=timedelta(seconds=5.0)),
                    ),
                ],
                logging=True,
            ),
        ],
    ),
]

# Run the framework (blocking)
daf.run(
    accounts=accounts,
    logger=logger,
    debug=TraceLEVELS.NORMAL,
    save_to_file=False
)
