"""Browser Providers Exports and Factory for ZETTA Phase 06."""

from pathlib import Path
from typing import Optional
from core.zetta.browser.providers.base import BrowserProvider
from core.zetta.browser.providers.fake import FakeBrowserProvider
from core.zetta.browser.providers.local import LocalBrowserProvider


def get_browser_provider(
    use_fake: bool = False,
    persist_state: bool = False,
    storage_dir: Optional[Path] = None,
) -> BrowserProvider:
    """Factory creating appropriate BrowserProvider instance."""
    if use_fake:
        return FakeBrowserProvider(persist_state=persist_state, storage_dir=storage_dir)

    local_provider = LocalBrowserProvider(persist_state=persist_state, storage_dir=storage_dir)
    if local_provider.is_available():
        return local_provider

    return FakeBrowserProvider(persist_state=persist_state, storage_dir=storage_dir)


__all__ = [
    "BrowserProvider",
    "FakeBrowserProvider",
    "LocalBrowserProvider",
    "get_browser_provider",
]
