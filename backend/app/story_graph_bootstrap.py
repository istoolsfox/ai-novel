_BOOTSTRAPPED = False


def bootstrap_story_graph() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    from . import database
    from .story_graph_runtime import (
        install_story_graph_api,
        patch_contract_runtime,
        patch_memory_compiler,
    )
    from .story_graph_schema import (
        init_story_graph_cleanup_triggers,
        init_story_graph_schema,
    )

    original_init_db = database.init_db

    def init_db_with_story_graph() -> None:
        init_story_graph_schema()
        patch_memory_compiler()
        original_init_db()
        patch_contract_runtime()
        init_story_graph_cleanup_triggers()
        install_story_graph_api()

    database.init_db = init_db_with_story_graph
    _BOOTSTRAPPED = True
