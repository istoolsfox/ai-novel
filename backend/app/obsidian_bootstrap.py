_BOOTSTRAPPED = False


def bootstrap_obsidian_export() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    from . import database
    from .obsidian_runtime import install_obsidian_api
    from .obsidian_schema import init_obsidian_cleanup_triggers, init_obsidian_schema

    original_init_db = database.init_db

    def init_db_with_obsidian() -> None:
        init_obsidian_schema()
        original_init_db()
        init_obsidian_cleanup_triggers()
        install_obsidian_api()

    database.init_db = init_db_with_obsidian
    _BOOTSTRAPPED = True
