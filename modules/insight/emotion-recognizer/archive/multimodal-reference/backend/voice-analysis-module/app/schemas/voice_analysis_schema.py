from pydantic import BaseModel, Field

class AnalysisResult(BaseModel):
    source: str
    risk_level: str
    score: int
    justification: str
    recommended_action: str
    sentiment: str | None = None
    summary: str | None = None
    keywords: list[str] = Field(default_factory=list)
    detected_signals: list[str] = Field(default_factory=list)
    llm_error: str | None = None

class VoiceAnalysisResponse(BaseModel):
    original_filename: str
    saved_filename: str
    saved_path: str
    transcription: str
    analysis: AnalysisResult
    message: str
