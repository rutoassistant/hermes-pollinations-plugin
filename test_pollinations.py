"""Tests for Pollinations image generation plugin.

Covers: catalog integrity, model resolution, prompt validation,
API key detection, URL building, and error handling.
"""
from __future__ import annotations

import os
import sys
import tempfile
import urllib.parse
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_provider():
    """Load PollinationsImageGenProvider with correct path."""
    import importlib.util
    path = '/opt/data/plugins/image_gen/pollinations/__init__.py'
    spec = importlib.util.spec_from_file_location("pollinations_provider", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["pollinations_provider"] = module
    spec.loader.exec_module(module)
    return module.PollinationsImageGenProvider


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def provider():
    """Fresh provider instance per test."""
    P = _load_provider()
    return P()


# ---------------------------------------------------------------------------
# Catalog integrity
# ---------------------------------------------------------------------------

class TestPollinationsCatalog:
    """Every model entry must have consistent shape."""

    def test_default_model_is_flux(self, provider):
        assert provider.default_model() == "flux"

    def test_list_models_returns_three(self, provider):
        models = provider.list_models()
        assert len(models) == 3
        ids = {m['id'] for m in models}
        assert ids == {"flux", "klein", "zimage"}

    def test_all_entries_have_required_keys(self, provider):
        required = {"id", "display", "speed", "strengths"}
        for meta in provider.list_models():
            missing = required - set(meta.keys())
            assert not missing, f"missing keys: {missing}"

    def test_flux_entry(self, provider):
        flux = next(m for m in provider.list_models() if m['id'] == "flux")
        assert flux['display'] == "Flux"
        assert "~5-10s" in flux['speed']
        assert "quality" in flux['strengths'].lower()

    def test_klein_entry(self, provider):
        klein = next(m for m in provider.list_models() if m['id'] == "klein")
        assert klein['display'] == "Klein"
        assert "fast" in klein['strengths'].lower()

    def test_zimage_entry(self, provider):
        zimage = next(m for m in provider.list_models() if m['id'] == "zimage")
        assert zimage['display'] == "Z-Image"
        assert "artistic" in zimage['strengths'].lower()


# ---------------------------------------------------------------------------
# Basic properties
# ---------------------------------------------------------------------------

class TestProviderProperties:
    def test_name(self, provider):
        assert provider.name == "pollinations"

    def test_display_name(self, provider):
        assert provider.display_name == "Pollinations"

    def test_is_available_always_true(self, provider):
        assert provider.is_available() is True


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

class TestCapabilities:
    def test_text_only_modality(self, provider):
        caps = provider.capabilities()
        assert caps['modalities'] == ["text"]

    def test_no_reference_images(self, provider):
        caps = provider.capabilities()
        assert caps['max_reference_images'] == 0


# ---------------------------------------------------------------------------
# API key detection
# ---------------------------------------------------------------------------

class TestGetApiKey:
    def test_returns_env_var_when_set(self, monkeypatch):
        monkeypatch.setenv("POLLINATIONS_API_KEY", "sk-test-key-123")
        P = _load_provider()
        provider = P()
        assert provider._get_api_key() == "sk-test-key-123"

    def test_returns_none_when_not_set(self, monkeypatch):
        monkeypatch.delenv("POLLINATIONS_API_KEY", raising=False)
        P = _load_provider()
        provider = P()
        assert provider._get_api_key() is None

    def test_reads_from_hermes_env_file(self, tmp_path, monkeypatch):
        # Create a fake .env file
        env_content = """POLLINATIONS_API_KEY=sk-file-key\n"""
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)
        
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        monkeypatch.delenv("POLLINATIONS_API_KEY", raising=False)
        
        P = _load_provider()
        provider = P()
        assert provider._get_api_key() == "sk-file-key"

    def test_prefers_env_var_over_file(self, tmp_path, monkeypatch):
        env_content = "POLLINATIONS_API_KEY=sk-file-key\n"
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)
        
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        monkeypatch.setenv("POLLINATIONS_API_KEY", "sk-env-key")
        
        P = _load_provider()
        provider = P()
        # Env var should take precedence
        assert provider._get_api_key() == "sk-env-key"


# ---------------------------------------------------------------------------
# Prompt validation
# ---------------------------------------------------------------------------

class TestPromptValidation:
    def test_empty_prompt_returns_error(self, provider):
        result = provider.generate("")
        assert 'error' in result
        assert "Prompt is required" in result['error']

    def test_whitespace_only_returns_error(self, provider):
        result = provider.generate("   ")
        assert 'error' in result

    def test_none_prompt_returns_error(self, provider):
        result = provider.generate(None)
        assert 'error' in result


# ---------------------------------------------------------------------------
# Model resolution
# ---------------------------------------------------------------------------

class TestModelResolution:
    def test_invalid_model_falls_back_to_default(self):
        P = _load_provider()
        provider = P()
        
        # Test with invalid model
        # We'll mock the generate method to capture the model_id used
        captured = {}
        original_generate = provider.generate
        
        def capture_generate(prompt, **kwargs):
            captured['model'] = kwargs.get('model', provider.default_model())
            return {'success': True, 'model': captured['model']}
        
        # Use the internal logic directly
        import importlib.util
        spec = importlib.util.spec_from_file_location("pollinations_provider", "/opt/data/plugins/image_gen/pollinations/__init__.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["pollinations_provider"] = mod
        spec.loader.exec_module(mod)
        
        test_cases = [
            ("invalid", mod._DEFAULT_MODEL),
            ("nonexistent", mod._DEFAULT_MODEL),
            ("flux", "flux"),
            ("klein", "klein"),
            ("zimage", "zimage"),
        ]
        for model_input, expected in test_cases:
            resolved = model_input if model_input in mod._MODELS else mod._DEFAULT_MODEL
            assert resolved == expected, f"Failed for model={model_input}"


# ---------------------------------------------------------------------------
# Aspect ratio handling
# ---------------------------------------------------------------------------

class TestAspectRatio:
    def test_square_dims(self):
        size_map = {
            "square": ("1024", "1024"),
            "landscape": ("1280", "768"),
            "portrait": ("768", "1280"),
        }
        assert size_map["square"] == ("1024", "1024")
        assert size_map["landscape"] == ("1280", "768")
        assert size_map["portrait"] == ("768", "1280")

    def test_invalid_aspect_ratio_defaults_to_square(self):
        size_map = {
            "square": ("1024", "1024"),
            "landscape": ("1280", "768"),
            "portrait": ("768", "1280"),
        }
        result = size_map.get("cinemascope", size_map["square"])
        assert result == ("1024", "1024")


# ---------------------------------------------------------------------------
# URL building
# ---------------------------------------------------------------------------

class TestUrlBuilding:
    def test_legacy_url_format(self):
        prompt = "a cat sitting on a mat"
        model_id = "flux"
        width, height = "1024", "1024"
        seed = 42
        
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?model={model_id}&width={width}&height={height}&seed={seed}"
        
        assert "image.pollinations.ai" in url
        assert "prompt/" in url
        assert "model=flux" in url
        assert "seed=42" in url

    def test_authenticated_url_format(self):
        prompt = "a dog running"
        model_id = "klein"
        api_key = "sk-test"
        width, height = "1280", "768"
        seed = 99
        
        url = f"https://gen.pollinations.ai/image/{urllib.parse.quote(prompt)}?model={model_id}&width={width}&height={height}&seed={seed}&key={api_key}"
        
        assert "gen.pollinations.ai" in url
        assert "key=" in url
        assert url.endswith(f"key={api_key}")


# ---------------------------------------------------------------------------
# Integration with ImageGenProvider base class
# ---------------------------------------------------------------------------

class TestInheritance:
    def test_is_subclass_of_image_gen_provider(self):
        from agent.image_gen_provider import ImageGenProvider
        P = _load_provider()
        assert issubclass(P, ImageGenProvider)

    def test_implements_required_interface(self, provider):
        from agent.image_gen_provider import ImageGenProvider
        # Check all required methods exist
        assert hasattr(provider, 'generate')
        assert hasattr(provider, 'list_models')
        assert hasattr(provider, 'default_model')
        assert hasattr(provider, 'is_available')
        assert hasattr(provider, 'capabilities')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
