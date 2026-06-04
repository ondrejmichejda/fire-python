from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any, Callable

from .engine import (
    CalculationError,
    assess_etics,
    assess_roof,
    calculate_full_assessment,
    calculate_opening_distance,
    calculate_opening_group,
    calculate_opening_percentage,
    check_individual_opening_spacing,
    roof_distance_table_15,
)


RouteHandler = Callable[[dict[str, Any]], dict[str, Any]]


def _schema() -> dict[str, Any]:
    return {
        "service": "fire-separation-api",
        "version": "1.0.0",
        "endpoints": {
            "GET /health": "Liveness check",
            "GET /schema": "Supported endpoints and payload hints",
            "POST /v1/opening-group": {
                "required": ["openings", "layout", "gaps_m"],
            },
            "POST /v1/opening-distance": {
                "required": ["width_m", "height_m", "pv_kg_m2"],
                "optional": [
                    "structural_system",
                    "radiation_percentage",
                    "emissivity",
                    "falling_parts_risk",
                    "fall_height_m",
                    "opening_id",
                ],
            },
            "POST /v1/opening-percentage": {
                "required": ["openings"],
                "optional": ["bounding_width_m", "bounding_height_m", "layout", "gaps_m"],
            },
            "POST /v1/spacing-check": {
                "required": ["openings_edge_distance_m", "distance_opening_1_m", "distance_opening_2_m"],
                "optional": ["p0_percent", "gap_m", "distance_1_m", "distance_2_m"],
            },
            "POST /v1/roof-assessment": {
                "optional": [
                    "pv_kg_m2",
                    "fire_safety_level",
                    "roof_requirement_status",
                    "roof_classification",
                    "roof_structure_above_fire_ceiling",
                    "fire_resistance_required",
                    "fire_resistance_met",
                    "coefficient_c",
                    "supporting_construction_type",
                    "required_fire_resistance_met",
                    "released_heat_mj_m2",
                    "heat_release_rate_mw_m2",
                    "average_distance_to_dp1_m",
                    "roof_edge_heat_flux_kw_m2",
                    "hu_m",
                    "width_m",
                ],
            },
            "POST /v1/roof-distance-table15": {
                "required": ["hu_m", "width_m"],
            },
            "POST /v1/etics-assessment": {
                "required": ["insulation_thickness_mm", "insulation_reaction_class"],
            },
            "POST /v1/full-assessment": {
                "optional": [
                    "roof",
                    "etics",
                    "openings",
                    "group",
                    "layout",
                    "gaps_m",
                    "spacing_checks",
                    "pv_kg_m2",
                    "structural_system",
                ],
            },
        },
    }


ROUTES: dict[str, RouteHandler] = {
    "/v1/opening-group": calculate_opening_group,
    "/v1/opening-distance": calculate_opening_distance,
    "/v1/opening-percentage": calculate_opening_percentage,
    "/v1/spacing-check": check_individual_opening_spacing,
    "/v1/roof-assessment": assess_roof,
    "/v1/roof-distance-table15": lambda payload: roof_distance_table_15(
        payload.get("hu_m"),
        payload.get("width_m"),
    ),
    "/v1/etics-assessment": assess_etics,
    "/v1/full-assessment": calculate_full_assessment,
}


class FireRequestHandler(BaseHTTPRequestHandler):
    server_version = "FireSeparationAPI/1.0"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._write_json(HTTPStatus.OK, {"status": "ok"})
            return
        if self.path == "/schema":
            self._write_json(HTTPStatus.OK, _schema())
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        handler = ROUTES.get(self.path)
        if handler is None:
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        try:
            body = self._read_json_body()
            response = handler(body)
        except CalculationError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except json.JSONDecodeError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": f"Invalid JSON: {exc.msg}"})
            return
        except Exception as exc:  # pragma: no cover
            self._write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Internal error: {exc}"})
            return
        self._write_json(HTTPStatus.OK, response)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise CalculationError("JSON body must be an object.")
        return data

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), FireRequestHandler)
    print(f"Fire separation API listening on http://{host}:{port}")
    server.serve_forever()
