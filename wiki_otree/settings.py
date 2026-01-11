import os
import warnings
#import custom_python.get_config as cf

SESSION_CONFIGS = [
     dict(
         name='shellproject',
         display_name='Shell Project',
         app_sequence=['wiki'],
         num_demo_participants=3,
     ),
]

ROOMS = [
    # dict(
    #     name='PolVer',
    #     display_name='Political Science class',
    #     participant_label_file='_rooms/code_list.txt',
    # )
]

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, participation_fee=0.00, doc=""
)

PARTICIPANT_FIELDS = []
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True

ADMIN_USERNAME = "admin"
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = os.environ.get("OTREE_ADMIN_PASSWORD")

OTREE_AUTH_LEVEL = os.environ.get('OTREE_AUTH_LEVEL', None)


match os.environ.get("OTREE_REST_KEY"):
    case "" | None:
        SECRET_KEY = "5903222485487"
        warnings.warn(
            "Environmental variable for REST key not set. Using default.",
            stacklevel=1,
        )
    case _:
        SECRET_KEY = os.environ.get("OTREE_REST_KEY")

# Database credentials
if (
    os.environ.get("POSTGRES_PASSWORD")
    and os.environ.get("POSTGRES_USER")
    and os.environ.get("POSTGRES_DB")
):
    os.environ["DATABASE_URL"] = (
        "postgres://"
        + os.environ.get("POSTGRES_USER")
        + ":"
        + os.environ.get("POSTGRES_PASSWORD")
        + "@db/"
        + os.environ.get("POSTGRES_DB")
    )
elif (
    os.environ.get("POSTGRES_PASSWORD")
    or os.environ.get("POSTGRES_USER")
    or os.environ.get("POSTGRES_DB")
):
    warnings.warn(
        """To use Postgres, the environmental variables DATABASE_URL,
        POSTGRES_USER, and POSTGRES_DB must all be set""",
        stacklevel=1,
    )
elif os.environ.get("DATABASE_URL"):
    pass
else:
    warnings.warn(
        """Using SQLite, because no Postgres credentials are specified. This is
        fine for local use, but can lead to performance degradation in
        production.""",
        stacklevel=1,
    )
