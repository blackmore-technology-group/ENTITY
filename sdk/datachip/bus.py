"""Experimental ENTITY Data Processor (EDP) typed dispatcher.

This in-process bus never listens on a network. Host-supplied local paths
are distinct from archive members. Signing/authority are external.
"""
from __future__ import annotations
from collections.abc import Callable
from typing import Any
from .processor import DataChipError, export_chip, inspect_chip, verify_chip

BUS_SCHEMA = "entity-edp-request-v0.1"
SUPPORTED_OPS = frozenset({"edc.inspect", "edc.verify", "edc.export"})


class DataChipProcessor:
    """Minimal embeddable stateless, fail-closed reference I/O interface."""

    def __init__(self, authorize: Callable[[str, dict[str, Any]], bool] | None = None):
        self._authorize = authorize

    @staticmethod
    def capabilities() -> dict[str, Any]:
        return {
            "schema": "entity-edp-capabilities-v0.1",
            "operations": sorted(SUPPORTED_OPS),
            "signing": False,
            "rights_verification": False,
            "formula_execution": False,
            "transport": "in-process",
            "offline": True,
        }

    def dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        if type(request) is not dict:
            raise DataChipError("request must be a JSON-style object")
        if request.get("schema") != BUS_SCHEMA:
            raise DataChipError("unsupported EDP bus schema")
        op = request.get("operation")
        if type(op) is not str or op not in SUPPORTED_OPS:
            raise DataChipError("unsupported EDP bus operation")
        keys = {"schema", "operation", "chip"}
        if op == "edc.export":
            keys.add("destination")
        if set(request) != keys:
            raise DataChipError("unexpected or missing bus request fields")
        chip = request["chip"]
        if not isinstance(chip, str) or not (1 <= len(chip) <= 4096):
            raise DataChipError("invalid chip path")
        if op == "edc.inspect":
            result = inspect_chip(chip)
        elif op == "edc.verify":
            result = verify_chip(chip)
        else:
            dest = request["destination"]
            if not isinstance(dest, str) or not (1 <= len(dest) <= 4096):
                raise DataChipError("invalid destination path")
            if self._authorize is None:
                raise PermissionError("external host authorization required")
            result = export_chip(chip, dest, authorize=self._authorize)
        return {"schema": "entity-edp-response-v0.1",
                "operation": op, "result": result}
