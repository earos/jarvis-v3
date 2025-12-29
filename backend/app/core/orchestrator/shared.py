"""
Shared orchestrator instance to prevent multiple initializations
"""
from app.core.orchestrator.agent import JarvisOrchestrator

# Single shared orchestrator instance
_orchestrator = None

def get_orchestrator() -> JarvisOrchestrator:
    """Get the shared orchestrator instance (singleton pattern)"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = JarvisOrchestrator()
    return _orchestrator
