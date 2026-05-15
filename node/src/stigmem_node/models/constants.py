"""Shared model constants."""

VALID_VALUE_TYPES = {"string", "text", "number", "boolean", "datetime", "ref", "null"}
VALID_SCOPES = {"local", "team", "company", "public"}
VALID_GARDEN_ROLES = {"admin", "writer", "reader", "quarantine:moderator"}

# Quarantine statuses written to facts.quarantine_status
QUARANTINE_PENDING = "pending"
QUARANTINE_PROMOTED = "promoted"
QUARANTINE_REJECTED = "rejected"
