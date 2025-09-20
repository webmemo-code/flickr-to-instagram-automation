"""
Orchestration modules for breaking up complex automation workflows.

This package provides modular orchestration components that separate concerns
and enable better testing, maintainability, and future enhancements.
"""

from .photo_selection import (
    PhotoSelector,
    PhotoValidator,
    PhotoSelectionResult,
    create_photo_selector,
    create_photo_validator
)

from .caption_orchestration import (
    CaptionOrchestrator,
    CaptionPreprocessor,
    CaptionResult,
    create_caption_orchestrator,
    create_caption_preprocessor
)

from .posting_orchestration import (
    InstagramPoster,
    ProgressTracker,
    PostingOrchestrator,
    PostingResult,
    create_instagram_poster,
    create_progress_tracker,
    create_posting_orchestrator
)

from .state_orchestration import (
    StateOrchestrator,
    ValidationStateHandler,
    StateResult,
    create_state_orchestrator,
    create_validation_state_handler
)

__all__ = [
    # Photo Selection
    'PhotoSelector',
    'PhotoValidator',
    'PhotoSelectionResult',
    'create_photo_selector',
    'create_photo_validator',

    # Caption Orchestration
    'CaptionOrchestrator',
    'CaptionPreprocessor',
    'CaptionResult',
    'create_caption_orchestrator',
    'create_caption_preprocessor',

    # Posting Orchestration
    'InstagramPoster',
    'ProgressTracker',
    'PostingOrchestrator',
    'PostingResult',
    'create_instagram_poster',
    'create_progress_tracker',
    'create_posting_orchestrator',

    # State Orchestration
    'StateOrchestrator',
    'ValidationStateHandler',
    'StateResult',
    'create_state_orchestrator',
    'create_validation_state_handler'
]