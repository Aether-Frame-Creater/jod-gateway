from jod_gateway.core.adapter import ProviderAdapter
from jod_gateway.core.errors import UnknownModelError

_registry: dict[str, ProviderAdapter] = {}


def register(adapter: ProviderAdapter) -> None:
    for model in adapter.models:
        _registry[model] = adapter


def resolve(model: str) -> ProviderAdapter:
    adapter = _registry.get(model)
    if adapter is None:
        raise UnknownModelError(f"Model '{model}' is not registered with any provider.")
    return adapter


def all_models() -> list[dict]:
    seen: set[str] = set()
    models: list[dict] = []
    for adapter in _registry.values():
        for entry in adapter.list_models():
            if entry["id"] not in seen:
                seen.add(entry["id"])
                models.append(entry)
    return models