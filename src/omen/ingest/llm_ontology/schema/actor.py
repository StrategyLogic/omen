"""Shared actor schema constants for ingest runtime and validation."""

from __future__ import annotations

VERSION = "v0.1.0-actor"
QUERY_TYPES = ("status", "persona")
REDACTION_MARKER = {"redacted": True}
BACKGROUND_FACT_FIELDS = (
	"birth_year",
	"origin",
	"education",
	"career_trajectory",
	"key_experiences",
)

PRODUCT_TYPES = {"product", "platform", "tool", "saas", "app", "system"}
ACTOR_TYPE_ALIAS = {
	"company": "organization",
	"startup": "organization",
	"enterprise": "organization",
	"business": "organization",
	"org": "organization",
	"department": "team",
	"squad": "team",
	"group": "team",
	"top management": "top_management",
	"top-management": "top_management",
	"executive": "top_management",
	"management": "top_management",
}
STRATEGIC_ROLE_TOKENS = {"founder", "ceo", "top management"}
ALLOWED_ACTOR_TYPES = {
	"founder",
	"ceo",
	"top_management",
	"team",
	"organization",
	"customer",
	"competitor",
	"regulator",
	"investor",
	"partner",
	"supplier",
	"government",
	"other",
}
STRATEGIC_ACTOR_TYPES = {"founder", "ceo", "top_management"}
STRATEGIC_STYLE_FIELDS = (
	"decision_style",
	"value_proposition",
	"decision_preferences",
	"non_negotiables",
)
