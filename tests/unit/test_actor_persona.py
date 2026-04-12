from __future__ import annotations

from omen.analysis.actor.insight import generate_persona_insight


def test_generate_persona_insight_zh_uses_profile_and_events() -> None:
  payload = {
    "actors": [
      {
        "id": "a1",
        "name": "Chen Jiaxing",
        "type": "StrategicActor",
        "role": "founder",
        "profile": {
          "background_facts": {
            "birth_year": None,
            "origin": "中国",
            "education": ["经济学"],
            "career_trajectory": ["持续创业"],
            "key_experiences": ["研发效能实践"],
          },
          "strategic_style": {
            "decision_style": "数据驱动",
            "value_proposition": "用数据洞察替代流程驱动",
            "decision_preferences": ["先验证再扩张"],
            "non_negotiables": ["不增加研发人员手工填报负担"],
          },
        },
      }
    ],
    "events": [
      {
        "id": "e1",
        "name": "X-Developer Platform Launch",
        "date": "2019-10",
        "description": "平台发布并提供社区版。",
        "actors_involved": ["a1"],
      },
      {
        "id": "e2",
        "name": "Pricing Model Announcement",
        "date": "2019-10",
        "description": "公布免费社区版与商业版。",
        "actors_involved": ["a1"],
      },
    ],
  }

  class _Response:
    content = (
      '{"persona_insight": {'
      '"narrative": "这是一段用于测试的战略画像叙事，围绕背景、决策风格与关键事件形成一致闭环，并解释行动背后的内在动力与资源配置逻辑。'
      '为了满足长度约束，这里补充战略取舍、执行节奏与阶段性验证机制，强调其通过事件链条推进价值主张并在约束中保持稳定判断。'
      '同时，叙事进一步说明其如何在外部压力下通过连续试错与反馈回路校正路径，使每次关键行动都服务于同一长期目标。'
      '并且，该行动逻辑并不是一次性决策，而是在多轮验证中逐步稳定，最终形成从问题识别到价值兑现的闭环能力。", '
      '"key_traits": ['
      '{"trait": "目标牵引", "evidence_summary": "以关键事件持续验证方向。"},'
      '{"trait": "风格一致", "evidence_summary": "决策风格与行动路径一致。"},'
      '{"trait": "边界清晰", "evidence_summary": "在约束下保持非妥协项。"}'
      '],'
      '"consistency_score": 0.9}}'
    )

  class _Chat:
    def invoke(self, _prompt: str):
      return _Response()

  result = generate_persona_insight(
    case_id="chen-jiaxing",
    actor_ontology=payload,
    llm_client=_Chat(),
    output_language="zh",
  )
  insight = result["persona_insight"]
  narrative = insight["narrative"]

  assert 200 <= len(narrative) <= 300
  assert "战略画像" in narrative
  assert isinstance(insight["key_traits"], list)
  assert len(insight["key_traits"]) >= 3
  assert result["run_meta"]["mode"] == "skeleton-deterministic"


def test_generate_persona_insight_traits_have_evidence() -> None:
  payload = {
    "actors": [
      {
        "id": "a1",
        "name": "Elon Musk",
        "type": "StrategicActor",
        "profile": {
          "background_facts": {
            "origin": "South Africa",
            "education": ["UPenn"],
            "career_trajectory": ["Serial founder"],
            "key_experiences": ["Aerospace and EV"],
          },
          "strategic_style": {
            "decision_style": "first-principles",
            "value_proposition": "sustainable energy and multiplanetary civilization",
            "non_negotiables": ["engineering reality over convenience"],
          },
        },
      }
    ],
    "events": [
      {
        "id": "e1",
        "name": "Founding of SpaceX",
        "date": "2002",
        "actors_involved": ["a1"],
      }
    ],
  }

  class _Response:
    content = (
      '{"persona_insight": {'
      '"narrative": "Elon Musk demonstrates a thesis-driven strategic persona where background, decision style, and event choices remain tightly coupled across high-uncertainty contexts.", '
      '"key_traits": ['
      '{"trait": "First-principles", "evidence_summary": "Frames key decisions from underlying constraints."},'
      '{"trait": "Execution speed", "evidence_summary": "Uses events to validate and scale quickly."},'
      '{"trait": "Boundary discipline", "evidence_summary": "Maintains non-negotiables under pressure."}'
      '],'
      '"consistency_score": 0.88}}'
    )

  class _Chat:
    def invoke(self, _prompt: str):
      return _Response()

  result = generate_persona_insight(
    case_id="elon-musk",
    actor_ontology=payload,
    llm_client=_Chat(),
    output_language="en",
  )
  traits = result["persona_insight"]["key_traits"]

  assert len(traits) >= 3
  assert all("trait" in item and "evidence_summary" in item for item in traits)
  assert all(str(item["evidence_summary"]).strip() for item in traits)


def test_generate_persona_insight_prefers_llm_when_available() -> None:
  payload = {
    "actors": [
      {
        "id": "a1",
        "name": "Chen Jiaxing",
        "type": "StrategicActor",
        "profile": {
          "background_facts": {},
          "strategic_style": {},
        },
      }
    ],
    "events": [
      {
        "id": "e1",
        "name": "Launch",
        "date": "2019-10",
        "actors_involved": ["a1"],
      }
    ],
  }

  class _Response:
    content = (
      '{"persona_insight": {'
      '"narrative": "这是一段用于测试的战略画像叙事，围绕背景、决策风格与事件驱动形成闭环，并通过连续行动验证长期价值主张。'
      '为了满足长度约束，这里继续补充动因、边界与执行节奏，强调其在关键节点上的取舍逻辑与组织资源配置方式。'
      '最终文本强调关键事件如何塑造战略行动的因果链条，并体现出稳定的价值主线与执行一致性。", '
      '"key_traits": ['
      '{"trait": "目标牵引", "evidence_summary": "以关键事件验证战略方向。"},'
      '{"trait": "风格一致", "evidence_summary": "决策偏好与行动路径一致。"},'
      '{"trait": "边界清晰", "evidence_summary": "在冲突中坚持非妥协项。"}'
      '],"consistency_score": 0.87}}'
    )

  class _Chat:
    def invoke(self, _prompt: str):
      return _Response()

  result = generate_persona_insight(
    case_id="chen-jiaxing",
    actor_ontology=payload,
    llm_client=_Chat(),
    output_language="zh",
  )

  assert result["run_meta"]["mode"] == "skeleton-deterministic"
  assert len(result["persona_insight"]["key_traits"]) >= 3


def test_generate_persona_insight_falls_back_when_llm_payload_is_empty() -> None:
  payload = {
    "actors": [
      {
        "id": "a1",
        "name": "Muhammad Alam",
        "type": "StrategicActor",
        "profile": {
          "background_facts": {
            "key_experiences": ["Led acquisition decisions for platform adoption."],
          },
          "strategic_style": {
            "decision_style": "platform-centric acquisition",
            "value_proposition": "integrated data foundation for AI adoption",
            "decision_preferences": ["alliances", "external data integration"],
            "non_negotiables": ["must improve adoption outcomes"],
          },
        },
      }
    ],
    "events": [
      {
        "id": "e1",
        "name": "SAP announces acquisition of Reltio",
        "date": "2026-03",
        "actors_involved": ["a1"],
      }
    ],
  }

  strategy_payload = {
    "meta": {
      "case_id": "sap_reltio_acquisition",
      "domain": "enterprise_software_ai_platforms",
      "strategy": "acquisition_to_overcome_adoption_resistance",
    },
    "known_outcome": "SAP acquires Reltio to address BDC adoption resistance",
  }

  class _Response:
    content = '{"persona_insight": {"narrative": "", "key_traits": [], "consistency_score": 0.0}}'

  class _Chat:
    def invoke(self, _prompt: str):
      return _Response()

  result = generate_persona_insight(
    case_id="sap_reltio_acquisition",
    actor_ontology=payload,
    strategy_ontology=strategy_payload,
    llm_client=_Chat(),
    output_language="en",
  )

  insight = result["persona_insight"]
  assert str(insight["narrative"]).strip()
  assert len(list(insight["key_traits"])) >= 1
  assert float(insight["consistency_score"]) > 0
