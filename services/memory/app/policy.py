from .models import MemoryPut

def enforce_phase5_policy(item: MemoryPut) -> None:
    # Canonical writes require explicit approval
    if item.scope == "canonical":
        if not item.approval_ref:
            raise ValueError("canonical writes require approval_ref (Phase-5)")
        if item.source not in ("user", "doc", "import"):
            raise ValueError("canonical source must be user/doc/import")

    # Prevent accidental secret embedding
    if item.scope == "semantic" and item.key:
        if any(x in item.key.lower() for x in ("token", "secret", "key", "password")):
            raise ValueError("semantic memory may not store secrets")
