_BOOTSTRAPPED = False


def bootstrap_impact_planning() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    from . import database
    from .impact_planning_runtime import (
        install_impact_planning_api,
        patch_impact_planning_runtime,
    )
    from .impact_planning_schema import (
        init_impact_planning_cleanup_triggers,
        init_impact_planning_schema,
    )

    original_init_db = database.init_db

    def init_db_with_impact_planning() -> None:
        init_impact_planning_schema()
        original_init_db()
        patch_impact_planning_runtime()
        init_impact_planning_cleanup_triggers()
        install_impact_planning_api()

    database.init_db = init_db_with_impact_planning
    _BOOTSTRAPPED = True
