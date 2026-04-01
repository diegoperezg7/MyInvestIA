from unittest.mock import patch

from app.services.providers.bloomberg_provider import BloombergProvider


def test_bloomberg_provider_requires_explicit_flag():
    with patch("app.services.providers.bloomberg_provider.BLOOMBERG_AVAILABLE", True), \
         patch("app.services.providers.bloomberg_provider.settings.bloomberg_enabled", False), \
         patch("app.services.providers.bloomberg_provider.settings.bloomberg_host", "localhost"), \
         patch("app.services.providers.bloomberg_provider.settings.bloomberg_port", 8194):
        provider = BloombergProvider()

    assert provider.is_configured is False


def test_bloomberg_provider_disabled_without_sdk():
    with patch("app.services.providers.bloomberg_provider.BLOOMBERG_AVAILABLE", False), \
         patch("app.services.providers.bloomberg_provider.settings.bloomberg_enabled", True), \
         patch("app.services.providers.bloomberg_provider.settings.bloomberg_host", "localhost"), \
         patch("app.services.providers.bloomberg_provider.settings.bloomberg_port", 8194):
        provider = BloombergProvider()

    assert provider.is_configured is False
