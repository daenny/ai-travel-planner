"""UI components for the travel planner app."""

from .diff_preview import (
    render_diff_preview,
    render_diff_actions,
    render_update_request_form,
)

from .config import (
    PROVIDERS,
    PROVIDER_MODELS,
    SUPPORTED_LANGUAGES,
    PLANS_DIR,
    EXPORTS_DIR,
    IMAGES_DIR,
    DEBUG_DIR,
)

from .api_keys import (
    get_api_key,
    save_api_key,
    delete_api_key,
    auto_detect_provider,
    get_agent,
)

from .state import init_session_state

from .helpers import (
    get_app_title,
    get_chat_placeholder,
    render_settings_prompt,
    save_debug_output,
)

from .tabs import (
    render_settings,
    render_sidebar,
    render_chat,
    render_itinerary_builder,
    render_blog_tips,
)

__all__ = [
    # diff_preview
    "render_diff_preview",
    "render_diff_actions",
    "render_update_request_form",
    # config
    "PROVIDERS",
    "PROVIDER_MODELS",
    "SUPPORTED_LANGUAGES",
    "PLANS_DIR",
    "EXPORTS_DIR",
    "IMAGES_DIR",
    "DEBUG_DIR",
    # api_keys
    "get_api_key",
    "save_api_key",
    "delete_api_key",
    "auto_detect_provider",
    "get_agent",
    # state
    "init_session_state",
    # helpers
    "get_app_title",
    "get_chat_placeholder",
    "render_settings_prompt",
    "save_debug_output",
    # tabs
    "render_settings",
    "render_sidebar",
    "render_chat",
    "render_itinerary_builder",
    "render_blog_tips",
]
