_BOOTSTRAPPED = False


def bootstrap_worldlines() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    from . import database
    from .worldline_runtime import install_worldline_api
    from .worldline_schema import init_worldline_cleanup_triggers, init_worldline_schema

    original_init_db = database.init_db

    def init_db_with_worldlines() -> None:
        init_worldline_schema()
        original_init_db()
        init_worldline_cleanup_triggers()
        install_worldline_api()

    database.init_db = init_db_with_worldlines
    _BOOTSTRAPPED = True
