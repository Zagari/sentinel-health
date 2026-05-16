import json
import logging
import sys

from app.core.logging import JsonFormatter


def test_json_formatter_outputs_structured_extra_fields():
    record = logging.LogRecord(
        name="app.services.ai_analysis_service",
        level=logging.ERROR,
        pathname=__file__,
        lineno=10,
        msg="OpenAI analysis failed; using local fallback",
        args=(),
        exc_info=None,
    )
    record.event = "analysis_failed"
    record.service = "openai"
    record.stage = "llm_analysis"
    record.fallback = "local_rules"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "ERROR"
    assert payload["logger"] == "app.services.ai_analysis_service"
    assert payload["message"] == "OpenAI analysis failed; using local fallback"
    assert payload["event"] == "analysis_failed"
    assert payload["service"] == "openai"
    assert payload["stage"] == "llm_analysis"
    assert payload["fallback"] == "local_rules"


def test_json_formatter_includes_exception_metadata():
    try:
        raise RuntimeError("service unavailable")
    except RuntimeError:
        record = logging.LogRecord(
            name="app.services.azure_transcription_service",
            level=logging.ERROR,
            pathname=__file__,
            lineno=35,
            msg="Azure Speech transcription failed",
            args=(),
            exc_info=sys.exc_info(),
        )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["exception"]["type"] == "RuntimeError"
    assert payload["exception"]["message"] == "service unavailable"
    assert "RuntimeError: service unavailable" in payload["exception"]["stack_trace"]
