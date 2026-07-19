_BOOTSTRAPPED = False


def bootstrap_layered_memory() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    from . import database
    from .memory_runtime import install_memory_api, patch_continuity_runtime
    from .memory_schema import init_memory_cleanup_triggers, init_memory_schema

    original_init_db = database.init_db

    def init_db_with_layered_memory() -> None:
        init_memory_schema()
        patch_continuity_runtime()
        original_init_db()
        init_memory_cleanup_triggers()
        install_memory_api()

    database.init_db = init_db_with_layered_memory
    _BOOTSTRAPPED = True
