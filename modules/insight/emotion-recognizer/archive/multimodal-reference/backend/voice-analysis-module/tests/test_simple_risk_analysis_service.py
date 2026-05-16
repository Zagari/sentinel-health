from app.services.simple_risk_analysis_service import analyze_risk_locally


def test_analyze_risk_locally_returns_low_risk_when_no_signal_is_detected():
    result = analyze_risk_locally("Hoje foi um dia tranquilo e consegui descansar.")

    assert result["source"] == "local_rules"
    assert result["risk_level"] == "baixo"
    assert result["score"] == 0
    assert result["detected_signals"] == []


def test_analyze_risk_locally_detects_high_risk_signals():
    result = analyze_risk_locally(
        "Sinto medo, sofro humilhação, recebi ameaça de morte e violência física."
    )

    assert result["risk_level"] == "alto"
    assert result["score"] >= 7
    assert "medo" in result["detected_signals"]
    assert "ameaça" in result["detected_signals"]
    assert "morte" in result["detected_signals"]


def test_analyze_risk_locally_ignores_negated_signals():
    result = analyze_risk_locally("Não sinto medo e nunca sofri ameaça.")

    assert result["risk_level"] == "baixo"
    assert result["score"] == 0
    assert result["detected_signals"] == []
