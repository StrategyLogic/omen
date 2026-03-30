"""Actor OSS insight capability surface.

Only persona generation remains publicly available in actor OSS flow.
"""

from __future__ import annotations

from typing import Any

from omen.analysis.case.insight import generate_persona_insight as _generate_persona_insight


def generate_persona_insight(
    *,
    case_id: str,
    founder_ontology: dict[str, Any],
    strategy_ontology: dict[str, Any] | None = None,
    llm_client: Any = None,
    config_path: str | None = None,
    output_language: str = "en",
) -> dict[str, Any]:
    return _generate_persona_insight(
        case_id=case_id,
        founder_ontology=founder_ontology,
        strategy_ontology=strategy_ontology,
        llm_client=llm_client,
        config_path=config_path,
        output_language=output_language,
    )
