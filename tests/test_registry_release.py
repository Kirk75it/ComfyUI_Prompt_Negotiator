from ComfyUI_Prompt_Negotiator.registry import RuntimeRegistry
from ComfyUI_Prompt_Negotiator.models import ClipIdentity


def test_registry_replace_drops_previous_reference_without_unloading():
    registry = RuntimeRegistry()
    a = object(); b = object()
    registry.bind("1", a, ClipIdentity(), image=None)
    registry.bind("1", b, ClipIdentity(), image=None)
    assert registry.get("1").clip is b


def test_registry_invalidate_does_not_release_model():
    registry = RuntimeRegistry()
    clip = object()
    registry.bind("1", clip, ClipIdentity())
    registry.invalidate("1")
    assert registry.get("1") is None
    assert not hasattr(RuntimeRegistry, "_release_clip")


def test_nodes_refresh_request_roundtrip():
    registry = RuntimeRegistry()
    clip = object()
    registry.bind("1", clip, ClipIdentity(), image=None)
    registry.request_nodes_refresh("1")
    assert registry.nodes_refresh_requested("1") is True
    registry.clear_nodes_refresh("1")
    assert registry.nodes_refresh_requested("1") is False


def test_image_refresh_alias_still_maps_to_nodes_refresh():
    registry = RuntimeRegistry()
    clip = object()
    registry.bind("1", clip, ClipIdentity(), image=None)
    registry.request_image_refresh("1")
    assert registry.image_refresh_requested("1") is True
    registry.clear_image_refresh("1")
    assert registry.image_refresh_requested("1") is False


def test_bind_preserves_image_when_lazy_input_not_evaluated():
    registry = RuntimeRegistry()
    clip = object()
    first = object()
    registry.bind("1", clip, ClipIdentity(), image=first)
    entry = registry.bind("1", clip, ClipIdentity(), image=None)
    assert entry.image is first


def test_bind_updates_empty_external_values_instead_of_preserving_stale_values():
    registry = RuntimeRegistry()
    clip = object()
    registry.bind("1", clip, ClipIdentity(), system_prompt="old", approved_prompt="old-final")
    entry = registry.bind("1", clip, ClipIdentity(), system_prompt="", approved_prompt="")
    assert entry.system_prompt == ""
    assert entry.approved_prompt == ""

