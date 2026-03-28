<<<<<<< HEAD
from __future__ import annotations

from .router import LocalRouter


def heal_once(router: LocalRouter) -> int:
    """
    Self-healing analog: detect dead workers and restart them.
    """
    return router.restart_dead()

=======
from __future__ import annotations

from .router import LocalRouter


def heal_once(router: LocalRouter) -> int:
    """
    Self-healing analog: detect dead workers and restart them.
    """
    return router.restart_dead()

>>>>>>> ekta-simulation
