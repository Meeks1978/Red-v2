from __future__ import annotations

import time

from app.services.container import ServiceContainer
from app.world.types import WorldFact, Source, new_id


def main() -> None:
    c = ServiceContainer()

    src = Source(source_id=new_id("src"), kind="sensor", trust=0.9)

    fact = WorldFact(
        fact_id=new_id("fact"),
        key="user_available",
        value=True,
        observed_at_ms=int(time.time() * 1000) - 4000,
        source=src,
        ttl_ms=2000,  # already stale
    )

    c.world_engine.observe(fact)

    analysis = c.world_engine.analyze(
        expected={"user_available": False}
    )

    print("FACTS:", len(analysis["facts"]))
    print("STALE:", [f.key for f in analysis["stale"]])
    print("DRIFT:", analysis["drift"])


if __name__ == "__main__":
    main()
