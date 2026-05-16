import json
import logging
import re

from openai import OpenAI, OpenAIError

from app.core.config import settings
from app.services.simple_risk_analysis_service import analyze_risk_locally

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """\
Você é um assistente de apoio à triagem clínica.

Analise a transcrição abaixo e retorne SOMENTE um JSON válido.

Não faça diagnóstico.
Não afirme que houve violência.
Indique apenas sinais de alerta para revisão humana.

Campos obrigatórios:
- sentiment: positivo, neutro ou negativo
- risk_level: baixo, moderado ou alto
- score: número de 0 a 10
- summary: resumo curto da fala
- keywords: lista de palavras-chave relevantes
- detected_signals: lista de sinais percebidos
- justification: explicação curta
- recommended_action: ação recomendada

Transcrição:
\"\"\"<<TRANSCRIPTION>>\"\"\"
"""

# Erros considerados recuperáveis: a aplicação cai no fallback local em vez de propagar.
_RECOVERABLE_LLM_ERRORS: tuple[type[Exception], ...] = (
    OpenAIError,
    ValueError,
    json.JSONDecodeError,
)
_JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)
_client: OpenAI | None = None


def _get_openai_client() -> OpenAI:
    """Instancia o client da OpenAI sob demanda e o reaproveita entre chamadas."""
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise OpenAIError("OPENAI_API_KEY não configurada.")
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def analyze_transcription_with_ai(transcription: str) -> dict:
    try:
        result = _analyze_with_openai(transcription)
        result.setdefault("source", "openai_llm")
        return result
    except _RECOVERABLE_LLM_ERRORS as error:
        logger.exception(
            "Falha na análise com OpenAI; usando fallback local",
            extra={
                "event": "analysis_failed",
                "service": "openai",
                "stage": "llm_analysis",
                "fallback": "local_rules",
                "transcription_length": len(transcription),
            },
        )
        return _build_local_fallback_result(transcription, error)


def _analyze_with_openai(transcription: str) -> dict:
    client = _get_openai_client()
    prompt = PROMPT_TEMPLATE.replace("<<TRANSCRIPTION>>", transcription)

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content or ""
    return _parse_json_response(content)


def _parse_json_response(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = _JSON_OBJECT_PATTERN.search(content)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Resposta do modelo não é JSON válido: {content[:200]}")


def _build_local_fallback_result(transcription: str, error: Exception) -> dict:
    local_result = analyze_risk_locally(transcription)
    return {
        "source": "local_fallback",
        "sentiment": "indefinido",
        "risk_level": local_result["risk_level"],
        "score": local_result["score"],
        "summary": "Análise feita localmente porque a IA externa não respondeu.",
        "keywords": [],
        "detected_signals": local_result["detected_signals"],
        "justification": local_result["justification"],
        "recommended_action": local_result["recommended_action"],
        "llm_error": str(error),
    }
