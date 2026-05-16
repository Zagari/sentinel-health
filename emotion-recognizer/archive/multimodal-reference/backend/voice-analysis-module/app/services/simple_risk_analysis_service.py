import re
import unicodedata


def _normalize(text: str) -> str:
    """Remove acentos e converte para minúsculas para matching robusto."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# Padrões com peso por gravidade do sinal.
# Cada entrada: (padrão_regex_sem_acentos, peso, rótulo_legível)
# O padrão é aplicado sobre o texto já normalizado (sem acentos, minúsculas).
_PATTERNS: list[tuple[str, int, str]] = [
    # Peso 3 — ameaça à vida / suicídio / homicídio
    (r"\bobito\b",                      3, "óbito"),
    (r"\bmorte\b",                      3, "morte"),
    (r"\bmatar\b",                      3, "matar"),
    (r"\bmate\b",                       3, "matar"),
    (r"\bmato\b",                       3, "matar"),
    (r"\bsuicidio\b",                   3, "suicídio"),
    (r"\bsuicidar\b",                   3, "suicídio"),
    (r"\btirar a vida\b",               3, "tirar a vida"),
    (r"\bameaca",                       3, "ameaça"),    # cobre: ameaça, ameaças, ameaçava…
    (r"\bagress[aã]o\b",                3, "agressão"),
    (r"\bviolencia\b",                  3, "violência"),
    (r"\bespancar\b",                   3, "espancar"),
    (r"\bbater\b",                      3, "bater"),
    (r"\bsocar\b",                      3, "socar"),
    (r"\bestupro\b",                    3, "estupro"),

    # Peso 2 — abuso emocional / psicológico
    (r"\bculpa\b",                      2, "culpa"),
    (r"\bnojo\b",                       2, "nojo/desprezo"),
    (r"\bhumilh",                       2, "humilhação"),
    (r"\bofend",                        2, "ofensa"),
    (r"\bxing",                         2, "xingamento"),
    (r"\binsult",                       2, "insulto"),
    (r"\bvergonha\b",                   2, "vergonha induzida"),
    (r"\bcontrol",                      2, "controle"),
    (r"\bpossessiv",                    2, "possessividade"),
    (r"\bciume",                        2, "ciúme excessivo"),
    (r"\bpression",                     2, "pressão"),
    (r"\bmanipul",                      2, "manipulação"),
    (r"\bchantag",                      2, "chantagem"),
    (r"\babusiv",                       2, "comportamento abusivo"),
    (r"\bpsicologica\b",                2, "violência psicológica"),

    # Peso 1 — sinais de alerta / contexto de sofrimento
    (r"\bmedo\b",                       1, "medo"),
    (r"\bsofr",                         1, "sofrimento"),
    (r"\bchoro\b|\bchorando\b|\bchorei\b", 1, "choro"),
    (r"\bdificil\b|\bdificuldade",      1, "dificuldade"),
    (r"\bnao aguento\b|\bnao suporto\b",1, "não aguenta mais"),
    (r"\bfisica\b",                     1, "violência física"),
    (r"\bmachucar\b|\bmachuca\b",       1, "machucado"),
    (r"\bferir\b|\bfere\b",             1, "ferimento"),
    (r"\bproibir\b|\bproibe\b",         1, "proibição"),
    (r"\bisolar\b|\bisolado\b",         1, "isolamento"),
]

# Palavras que, se aparecerem até 4 tokens ANTES do sinal, cancelam o score daquele sinal.
_NEGATORS = re.compile(
    r"\b(nao|nunca|jamais|nem|sequer|nenhum|nenhuma|sem)\b"
)
_NEGATION_WINDOW = 4  # tokens


def _is_negated(tokens: list[str], match_start: int) -> bool:
    """Verifica se há um negador nos _NEGATION_WINDOW tokens que precedem o match."""
    window_start = max(0, match_start - _NEGATION_WINDOW)
    window = tokens[window_start:match_start]
    return any(_NEGATORS.fullmatch(t) for t in window)


def analyze_risk_locally(text: str) -> dict:
    normalized = _normalize(text)
    tokens = re.split(r"\W+", normalized)

    total_score = 0
    detected_signals: list[str] = []

    for pattern, weight, label in _PATTERNS:
        for m in re.finditer(pattern, normalized):
            match_token_idx = len(re.split(r"\W+", normalized[: m.start()]))
            if _is_negated(tokens, match_token_idx):
                continue
            if label not in detected_signals:
                detected_signals.append(label)
                total_score += weight
            break  # conta o sinal uma única vez mesmo se aparecer várias vezes

    if total_score >= 7:
        risk_level = "alto"
    elif total_score >= 3:
        risk_level = "moderado"
    else:
        risk_level = "baixo"

    return {
        "source": "local_rules",
        "risk_level": risk_level,
        "score": total_score,
        "detected_signals": detected_signals,
        "justification": "Análise local baseada em padrões de alerta detectados na transcrição.",
        "recommended_action": (
            "Encaminhar imediatamente para revisão humana qualificada."
            if risk_level == "alto"
            else "Encaminhar para revisão humana se houver sinais relevantes."
        ),
    }