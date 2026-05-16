# Análise do Codebase: emotion-detector

> **Última atualização:** 2026-05-16
> **Commit:** 1ed7e96
> **Branch:** main

## Visão Geral

Aplicação **Streamlit** mono-repositório em Python que combina **detecção de emoções faciais em vídeo** (OpenCV + DeepFace) com **análise emocional da fala** (Whisper + LLM) para apoiar a identificação de sinais de sofrimento emocional ligados a possível violência doméstica. Pensada para integração com sistemas de telemedicina. Toda a inteligência LLM (Whisper, GPT-5) é consumida via **apiGPTeal** (proxy interno Merck sobre Azure OpenAI), com uma única chave `XMerckAPIKey`.

## Stack Tecnológico

| Categoria | Tecnologia | Versão |
|-----------|------------|--------|
| Linguagem | Python | 3.12+ |
| UI / App framework | Streamlit | (sem pin) |
| Visão computacional | OpenCV (`opencv-python`) | (sem pin) |
| Classificação de emoções | DeepFace + `tf-keras` (TensorFlow) | (sem pin) |
| Transcrição de fala | Whisper (`whisper-1`) via apiGPTeal | API REST |
| LLM (sumarização / voz) | Azure OpenAI `gpt-5-2025-08-07` via apiGPTeal | API REST |
| Download YouTube | `yt-dlp` (CLI) | (sem pin) |
| Extração de áudio | `ffmpeg` (sistema) com fallback `imageio-ffmpeg` | — |
| Manipulação de dados | `pandas`, `numpy` | (sem pin) |
| Imagens | `Pillow` | (sem pin) |
| Cliente HTTP | `requests`, `openai` (SDK ≥1.0) | (sem pin) |
| Config | `python-dotenv` (lê `.env`) | (sem pin) |
| Testes | `pytest` | (sem pin) |

Todas as deps estão em `requirements.txt` (raiz, 13 pacotes, **sem versões fixadas**).

## Estrutura de Diretórios

```
emotion-detector/
├── requirements.txt                # Python deps (sem pin)
├── README.md                       # README extenso (arquitetura + uso)
├── .gitignore                      # ignora .env, modelos .h5/.pb, mídias
└── emotion-recognizer/             # raiz da aplicação Python
    ├── app.py                      # entry point Streamlit (wiring de tudo)
    ├── .env                        # apenas XMerckAPIKey (não commitado)
    ├── README.md                   # cópia local do README do projeto
    │
    ├── analysis/                   # pipeline de vídeo + LLM
    │   ├── __init__.py
    │   ├── analyzer.py             # Haar cascade + DeepFace.analyze
    │   ├── summarizer.py           # GPT-5 sumarização multimodal
    │   └── visualizer.py           # componentes Streamlit (tabela, chart, previews)
    │
    ├── audio/                      # pipeline de áudio
    │   ├── __init__.py
    │   ├── extractor.py            # ffmpeg → WAV 16kHz mono PCM 16-bit
    │   ├── transcriber.py          # Whisper API (apiGPTeal)
    │   └── voice_analyzer.py       # LLM → JSON, fallback keyword local
    │
    ├── video/                      # fontes de vídeo
    │   ├── __init__.py
    │   ├── recorder.py             # webcam (cv2.VideoCapture(0))
    │   └── youtube.py              # yt-dlp subprocess
    │
    ├── utils/
    │   ├── __init__.py
    │   └── export.py               # JSON export + NumpyEncoder + UI controls
    │
    ├── tests/                      # pytest (sem __init__.py)
    │   ├── test_api_key.py         # live test contra apiGPTeal
    │   ├── test_extractor.py       # ffmpeg mockado
    │   ├── test_transcriber.py     # Whisper mockado
    │   ├── test_voice_analyzer.py  # LLM + fallback keyword
    │   ├── test_summarizer.py      # payload, tokens, live test
    │   └── test_multimodal.py      # integração video+voice
    │
    └── archive/                    # NÃO usado em runtime — referência apenas
        ├── audio_whisper.py        # implementação Whisper original
        ├── llm-response.py         # script de exploração LLM
        ├── emotion_results.json    # output de exemplo
        ├── test.py                 # script standalone original (base do analyzer.py)
        └── multimodal-reference/   # projeto FastAPI separado (health monitoring)
            └── backend/voice-analysis-module/   # FastAPI + serviços
```

### Responsabilidades por Diretório

| Diretório | Responsabilidade |
|-----------|------------------|
| `emotion-recognizer/` | Raiz da aplicação. Todos os imports são feitos a partir daqui (Streamlit roda com cwd = repo root, mas resolve módulos relativos à pasta do `app.py`). |
| `analysis/` | Lógica de análise visual e geração de sumário LLM. Reúne pipeline de detecção de emoção + componentes Streamlit + integração GPT. |
| `audio/` | Pipeline áudio fim-a-fim: extração via ffmpeg → transcrição Whisper → análise emocional LLM/fallback. |
| `video/` | Aquisição de mídia: webcam local e download YouTube. |
| `utils/` | Helpers transversais (atualmente só export JSON). |
| `tests/` | Suíte pytest. Sem `__init__.py`; descoberta automática. `test_api_key.py` e `test_summarizer.py` têm casos *live* contra apiGPTeal. |
| `archive/` | Código-base de referência. **Não é importado pela aplicação.** Inclui um projeto FastAPI completo (`multimodal-reference/`) que serviu de inspiração. |

## Padrões de Arquitetura

### Padrão Principal

**Pipeline funcional modular** orquestrado pela UI Streamlit. Sem classes de domínio, sem injeção de dependência, sem camadas formais (controller/service/repo). Cada módulo expõe uma **API pública pequena** (1–3 funções de alto nível) consumida diretamente por `app.py` ou por outro módulo.

Fluxo geral:

```
Streamlit UI (app.py)
   ↓ (orquestração condicional por modo)
video/ ── recorder | youtube ──→ video_path
   ↓
analysis/analyzer.analyze_video(video_path)  ──→ list[dict] de detecções
   ↓
audio/extractor → audio/transcriber → audio/voice_analyzer ──→ voice_result
   ↓
analysis/summarizer.summarize_emotions(video_results, voice_result) ──→ str
   ↓
analysis/visualizer + utils/export ──→ renderiza no Streamlit
```

### Convenções de Código

| Aspecto | Convenção |
|---------|-----------|
| Nomenclatura de arquivos | `snake_case.py` |
| Nomenclatura de funções/variáveis | `snake_case` |
| Privacidade | Prefixo `_` para helpers/constantes privadas (`_FACE_CASCADE`, `_resolve_ffmpeg`) |
| Type hints | Usados em assinaturas públicas, sintaxe moderna 3.10+ (`str \| None`, `list[dict]`) |
| Docstrings | Triple-quoted no topo de módulo + por função pública. Frequentemente longas e didáticas. |
| Imports | Absolutos a partir da raiz `emotion-recognizer/` (ex.: `from analysis.summarizer import ...`) |
| Comentários | Cabeçalhos visuais com `# ── Section ──` para separar seções dentro de arquivos |
| UI strings | Português opcional / inglês predominante, com emojis nos rótulos Streamlit (🎬 🎥 🎤 ⚠️) |
| Erros | `raise RuntimeError(...) from err` para falhas de subprocess; `st.error/warning/info` para feedback ao usuário |

### Padrões Identificados

1. **Carregamento preguiçoso de `.env` por módulo**
   - Onde: `analysis/summarizer.py:setup_openai_api`, `audio/transcriber.py:_load_api_key`
   - Cada módulo que usa LLM resolve `os.path.join(os.path.dirname(__file__), os.pardir, ".env")` e chama `load_dotenv` na demanda. O arquivo `.env` vive em `emotion-recognizer/.env`.

2. **Reuso da config OpenAI entre módulos**
   - Onde: `audio/voice_analyzer.py:17-21` importa `setup_openai_api`, `estimate_tokens`, `compute_max_completion_tokens` de `analysis.summarizer`.
   - Após `setup_openai_api()`, lê `openai.azure_endpoint`/`openai.api_key`/`openai.api_version` como variáveis globais do módulo `openai`.

3. **Fallback local para LLM**
   - Onde: `audio/voice_analyzer.py:_analyze_with_llm` (primário) + `analyze_risk_locally` (fallback).
   - Se a chamada Azure OpenAI falha por qualquer motivo, regex de keywords ponderadas (pesos 1/2/3) calcula `score`, `risk_level`, `sentiment`. Resultado fica marcado com `source: "local_rules"` e `llm_error: <str>`.

4. **Compactação de payload + estimativa de tokens**
   - Onde: `analysis/summarizer.py:compact_payload`, `estimate_tokens`, `compute_max_completion_tokens`
   - Drop de `all_emotions` e `bbox` antes de enviar ao LLM (~70% de redução). Heurística `len(text)/3.5` para estimar tokens; `max_completion_tokens` é calculado para caber em `_MODEL_MAX_TOKENS=8192`.

5. **Pre-warm de modelo**
   - Onde: `analysis/analyzer.py:_prewarm_models`
   - Faz `DeepFace.analyze` num array 48×48 zerado antes do loop, para amortizar o custo de carregamento de pesos.

6. **Persistência via `st.session_state`**
   - Onde: `app.py:_run_audio_only_mode` (`audio_only_path`, `audio_only_result`)
   - Resultados de áudio sobrevivem a reruns do Streamlit; vídeo+áudio é recomputado a cada interação.

7. **Constantes de configuração no topo do módulo**
   - Onde: `analyzer.py` (`_MAX_WIDTH`, `_MIN_FACE_PX`), `extractor.py` (`_FFMPEG_BASE_ARGS`, `_FFMPEG_TARGET_ARGS`, `_CONVERSION_TIMEOUT_SECONDS`), `summarizer.py` (`_MODEL_MAX_TOKENS`, `_RESPONSE_TOKENS_RESERVE`).

## Componentes Principais

### `app.py` — Orquestrador Streamlit
- **Localização:** `emotion-recognizer/app.py`
- **Responsabilidade:** Wiring entre módulos, controle de modo de análise, gestão de arquivos temporários.
- **Funções principais:**
  - `main()` — page config, sidebar, seleção de modo
  - `_run_audio_only_mode()` — fluxo áudio-only com session_state
  - `_run_voice_pipeline(video_path)` — extração + transcrição + análise dentro do modo Video+Audio
  - `_cleanup(path)` — `os.remove` silencioso de temps
- **Modos:** `🎬 Video + Audio` (default), `🎥 Video Only`, `🎤 Audio Only`
- **Dependências:** todos os outros módulos do projeto

### `analysis/analyzer.py` — Pipeline de Visão
- **Localização:** `emotion-recognizer/analysis/analyzer.py`
- **Responsabilidade:** Detecção facial (Haar cascade) + classificação de emoção (DeepFace) frame-a-frame.
- **API pública:** `analyze_video(video_path: str, every_n: int = 5) -> list[dict]`
- **Detalhes técnicos:**
  - Modelo Haar: `haarcascade_frontalface_default.xml` (carregado uma vez no nível do módulo)
  - `scaleFactor=1.1, minNeighbors=5, minSize=(30,30)`
  - Frames redimensionados para no máx. 960 px de largura antes do processamento
  - DeepFace recebe BGR → cinza → RGB (`enforce_detection=False`)
  - Leitura sequencial de frames (mais confiável para AVI/webcam que seek aleatório)
  - **Single-threaded** (modelo TF não é totalmente thread-safe)
- **Output:** lista de dicts ordenados por `(frame, face)` com: `frame, timestamp_s, face, dominant_emotion, confidence, all_emotions, bbox, frame_image`

### `analysis/summarizer.py` — Sumarização LLM
- **Localização:** `emotion-recognizer/analysis/summarizer.py`
- **Responsabilidade:** Combina detecções de vídeo + análise de voz e gera resumo natural-language via GPT-5.
- **API pública:** `summarize_emotions(export_data, voice_result) -> str | None`
- **Endpoint:** `https://iapi-test.merck.com/gpt/libsupport` (Azure OpenAI proxy)
- **Modelo:** `gpt-5-2025-08-07`, `api_version=2024-10-21`
- **System prompt:** instrui o LLM a agir como psicólogo comportamental e responder **somente em texto natural** (sem JSON/bullets/headings).
- **Funções auxiliares públicas:** `setup_openai_api`, `compact_payload`, `estimate_tokens`, `compute_max_completion_tokens`, `create_chat_completion`, `extract_message_content` — reutilizadas pelo `voice_analyzer`.
- **Observação:** contém `print(...)` de diagnóstico em `create_chat_completion` (linhas 171–175).

### `analysis/visualizer.py` — UI Streamlit
- **Localização:** `emotion-recognizer/analysis/visualizer.py`
- **Responsabilidade:** Render dos componentes visuais a partir dos dicts produzidos pelo analyzer/voice_analyzer.
- **API pública:**
  - `show_summary_table(results)` — DataFrame com Frame/Time/Face/Emotion/Confidence
  - `show_emotion_chart(results)` — `st.line_chart` com seletor de face
  - `show_frame_previews(results, max_previews)` — grid 4-col com bounding boxes coloridos por emoção (`EMOTION_COLORS`)
  - `show_voice_analysis(voice_result)` — 4 métricas (sentiment, risk, score, source) + signals + keywords + expanders
  - `show_llm_summary(results, voice_result)` — invoca `summarize_emotions` e renderiza
- **`EMOTION_COLORS`:** mapa fixo emoção → BGR (note: usado como RGB no `_draw_bboxes`).

### `audio/extractor.py` — Extração de Áudio
- **Localização:** `emotion-recognizer/audio/extractor.py`
- **API pública:** `extract_audio(video_path: str) -> str | None`
- **Saída:** WAV PCM 16-bit, mono, 16 kHz em `tempfile.mkstemp(suffix=".wav")`
- **Resolução de ffmpeg:** `shutil.which("ffmpeg")` → fallback `imageio_ffmpeg.get_ffmpeg_exe()` → `RuntimeError`
- **Timeout:** 120 s. Em timeout/erro remove o arquivo temp e levanta `RuntimeError`.

### `audio/transcriber.py` — Whisper
- **Localização:** `emotion-recognizer/audio/transcriber.py`
- **API pública:** `transcribe_audio(audio_path: str, language: str = "en") -> str`
- **Endpoint:** `https://iapi-test.merck.com/gpt/v2/whisper-1/audio/transcriptions` (note: caminho **diferente** do summarizer)
- **Header:** `X-Merck-APIKey: <XMerckAPIKey>`
- **Params:** `api-version=2024-10-21`, `response_format=verbose_json`
- **Formatos aceitos:** mp3, mp4, mpeg, mpga, m4a, wav, webm (máx. 25 MB — limite do endpoint)
- **Timeout:** 120 s.

### `audio/voice_analyzer.py` — Análise Emocional da Fala
- **Localização:** `emotion-recognizer/audio/voice_analyzer.py`
- **API pública:** `analyze_voice_emotions(transcription: str) -> dict`
- **Comportamento:** tenta LLM (`_analyze_with_llm`), em falha cai para `analyze_risk_locally` (keywords regex).
- **LLM:** mesmo `gpt-5-2025-08-07`, retorna JSON com `sentiment, risk_level, score, summary, keywords, detected_signals, justification, "domestic violence signals"`. Parser tolera markdown wrappers (`_JSON_OBJECT_PATTERN`).
- **Fallback local:** 27 padrões regex em inglês com pesos 1/2/3, negação por janela de 4 tokens (`_NEGATORS`), score capped em 10. Saída marcada com `source: "local_rules"`.
- **Output keys:** `source, sentiment, risk_level, score, summary, keywords, detected_signals, justification, recommended_action` (opcional `llm_error`).

### `video/recorder.py` — Webcam
- **Localização:** `emotion-recognizer/video/recorder.py`
- **API pública:** `record_webcam(duration_sec: int = 10) -> str | None`
- **Saída:** AVI XVID em `tempfile.NamedTemporaryFile(suffix=".avi")`
- **UI:** preview ao vivo via `st.image` atualizado a cada frame + cronômetro + progress bar.

### `video/youtube.py` — Download YouTube
- **Localização:** `emotion-recognizer/video/youtube.py`
- **API pública:** `download_youtube(url: str) -> str | None`
- **Implementação:** chama `yt-dlp` como subprocess; resolução do binário tenta `sys.executable` dir → user Scripts (Windows) → `shutil.which`.
- **Args:** `-f worst[ext=mp4] --no-playlist --no-check-certificates --js-runtimes node:C:/Program Files/nodejs/node.exe`
- **Nota:** o flag `--js-runtimes` aponta para caminho Windows hard-coded — chamadas em macOS/Linux precisam ajustar ou remover esse flag.

### `utils/export.py` — Export JSON
- **Localização:** `emotion-recognizer/utils/export.py`
- **API pública:** `prepare_export_data(results)`, `show_export_controls(results)`
- **`_NumpyEncoder`:** lida com `np.floating`, `np.integer`, `np.ndarray`. `prepare_export_data` remove o campo `frame_image` (não serializável).

## Fluxos de Dados

### Fluxo 1 — Video + Audio (modo default)

```
Webcam ou YouTube URL
  → video/{recorder|youtube} → video_path (.avi/.mp4 temp)
       ├──→ analysis/analyzer.analyze_video(video_path)
       │       ↓ cv2.VideoCapture → sampled frames
       │       ↓ Haar cascade → face boxes
       │       ↓ DeepFace.analyze → emotion dict
       │       └──→ list[dict] (results)
       │
       └──→ audio/extractor.extract_audio → .wav temp
              ↓
              audio/transcriber.transcribe_audio (Whisper REST)
              ↓ transcription (str)
              audio/voice_analyzer.analyze_voice_emotions
                  ├─ try _analyze_with_llm (Azure OpenAI)
                  └─ except → analyze_risk_locally (regex keywords)
              └──→ voice_result (dict)

  → analysis/visualizer: tabela, chart, frame previews, voice metrics
  → analysis/summarizer.summarize_emotions(results, voice_result)
       ↓ compact_payload + JSON serialize + token budget
       ↓ AzureOpenAI.chat.completions.create (gpt-5)
       └──→ summary (str)  →  st.info(summary)
  → utils/export.show_export_controls(results)
  → _cleanup(video_path), _cleanup(wav_path)
```

### Fluxo 2 — Video Only

Mesmo fluxo do Video+Audio, mas `voice_result = None` e o pipeline de áudio é pulado. `summarize_emotions` recebe somente `video_emotions` no payload.

### Fluxo 3 — Audio Only

```
Upload de arquivo OU YouTube URL
  → (se YouTube) download_youtube → extract_audio → cleanup do video
  → audio_path persistido em st.session_state.audio_only_path
  → [botão] Analyse Audio
       → transcribe_audio → analyze_voice_emotions
       → resultado em st.session_state.audio_only_result
  → visualizer.show_voice_analysis + show_llm_summary(results=None, voice_result=…)
  → download_button com voice_analysis.json
```

## Integrações Externas

| Sistema | Tipo | Configuração / Endpoint | Auth |
|---------|------|-------------------------|------|
| apiGPTeal — Whisper | REST POST multipart | `https://iapi-test.merck.com/gpt/v2/whisper-1/audio/transcriptions?api-version=2024-10-21` | Header `X-Merck-APIKey` |
| apiGPTeal — Azure OpenAI (GPT-5) | OpenAI SDK (Azure) | `azure_endpoint="https://iapi-test.merck.com/gpt/libsupport"`, `api_version="2024-10-21"`, modelo `gpt-5-2025-08-07` | `openai.api_key = XMerckAPIKey` |
| YouTube | CLI (`yt-dlp`) via subprocess | `video/youtube.py` | sem auth |
| ffmpeg / imageio-ffmpeg | CLI subprocess | `audio/extractor.py` | local |
| DeepFace / TensorFlow | Lib Python | Pesos baixados sob demanda em `~/.deepface/` | local |

> Mais info sobre `XMerckAPIKey`: https://share.merck.com/spaces/EG/pages/1759994187/apiGPTeal+Onboarding (link presente no código).

## Banco de Dados

**Não há.** Toda persistência é em memória (`st.session_state`) ou em arquivos temporários (`tempfile`). Resultados são exportados sob demanda como JSON.

## Testes

| Tipo | Localização | Comando |
|------|-------------|---------|
| Unitários + integração mockada | `emotion-recognizer/tests/` | `pytest emotion-recognizer/tests/ --ignore=emotion-recognizer/tests/test_api_key.py -v` |
| Live (chama apiGPTeal de verdade) | `tests/test_api_key.py`, parte de `test_summarizer.py` | `pytest emotion-recognizer/tests/test_api_key.py -v` |

Cobertura declarada (do README, confirmada pela existência dos arquivos):

| Arquivo | Testes | Foco |
|---|---|---|
| `test_transcriber.py` | 6 | Whisper: key loading, sucesso/erro/empty, missing key |
| `test_extractor.py` | 5 | ffmpeg: resolução, file-not-found, mock, falha, sem ffmpeg |
| `test_voice_analyzer.py` | 11 | Fallback keyword (6), parse JSON (3), input vazio, mock LLM, fallback LLM |
| `test_summarizer.py` | 8 | env loading, payloads, mock LLM, missing key, content extraction, live |
| `test_multimodal.py` | 4 | Video-only, multimodal, voice vazia, compact keys |
| `test_api_key.py` | 2 | Validação live da key + chat completion |

`tests/` **não tem `__init__.py`** — pytest descobre direto.

## Scripts Úteis

| Comando | Descrição |
|---------|-----------|
| `streamlit run emotion-recognizer/app.py` | Sobe a UI em `http://localhost:8501` (executar a partir da raiz do repo) |
| `pip install -r requirements.txt` | Instala dependências |
| `pytest emotion-recognizer/tests/ --ignore=emotion-recognizer/tests/test_api_key.py -v` | Suíte sem chamar API externa |
| `pytest emotion-recognizer/tests/test_api_key.py -v` | Smoke test live |

Não há `Makefile`, `pyproject.toml`, `setup.py` nem CI configurado no repo.

## Variáveis de Ambiente

| Variável | Descrição | Obrigatória |
|----------|-----------|:-----------:|
| `XMerckAPIKey` | Chave única apiGPTeal — usada por Whisper, voice_analyzer e summarizer | ✓ |

Localização esperada do `.env`: `emotion-recognizer/.env` (lido por `analysis/summarizer.py:setup_openai_api` e `audio/transcriber.py:_load_api_key` com path relativo ao módulo).

## Pontos de Extensão

Quando precisar adicionar funcionalidade:

1. **Nova fonte de mídia (ex.: arquivo de vídeo upload):** criar módulo em `video/` retornando um path de arquivo; ligar em `app.py:main()` como nova opção de `st.radio`.
2. **Nova análise no pipeline de áudio:** criar função em `audio/` consumindo o resultado de `transcribe_audio`; chamar de `_run_voice_pipeline` ou `_run_audio_only_mode`.
3. **Novo modo de análise:** adicionar opção em `analysis_mode = st.radio(...)` em `app.py:42` e branch correspondente no `main()`.
4. **Nova métrica visual:** criar função `show_*` em `analysis/visualizer.py`, invocar em `app.py` após o bloco de análise.
5. **Trocar provider de LLM:** ajustar `setup_openai_api` e `create_chat_completion` em `analysis/summarizer.py`; o `voice_analyzer` herda automaticamente (reusa as funções).
6. **Adicionar campo no output do voice_analyzer:** estender `_VOICE_SYSTEM_PROMPT` + `analyze_risk_locally` (manter paridade entre LLM e fallback) + render em `visualizer.show_voice_analysis`.
7. **Persistir resultados (banco):** atualmente não há camada de persistência — adicionar em `utils/` seguindo o padrão funcional dos demais módulos.

## Notas e Observações Factuais

Pontos do código que valem ser lembrados ao trabalhar nele:

- **README inconsistente em alguns detalhes:** o documento principal omite o tag de data do modelo (`gpt-5-2025-08-07` no código) e descreve `endpoint` como apenas `libsupport`, mas o Whisper na verdade usa o caminho `/gpt/v2/whisper-1/...` (path diferente do summarizer).
- **Caminho Windows hard-coded em `video/youtube.py:55`:** `--js-runtimes node:C:/Program Files/nodejs/node.exe`. Em macOS/Linux a flag falha; ajustar antes de rodar fora do Windows.
- **Typo em `app.py:34`:** título exibe "Multimodal Domestice Violence Recognizer".
- **Typos no prompt LLM em `voice_analyzer.py:39`:** chave `"domestic violence signals"` (com espaços) e palavra `"likelyhood"`.
- **Debug `print` em produção:** `analysis/summarizer.py:171-175` imprime contagem de tokens e finish_reason no stdout — não vai para `logger`.
- **Comportamentos divergentes para "sem fala":** `_run_voice_pipeline` retorna um dict `source="none"` estruturado; `_run_audio_only_mode` exibe `st.error` e zera o estado. Ambos são intencionais, mas a UX difere.
- **Tests dependem de `.env` para parte dos casos:** `test_api_key.py` e o caso live de `test_summarizer.py` precisam de `XMerckAPIKey` válida e rede.
- **`archive/` não é importado pela app em runtime**, mas contém um projeto FastAPI completo (`multimodal-reference/`) que foi a base inspiracional do `voice_analyzer` (vide cabeçalho do arquivo).

## Referências

- README principal: [`README.md`](../README.md)
- apiGPTeal Onboarding (link interno Merck): https://share.merck.com/spaces/EG/pages/1759994187/apiGPTeal+Onboarding
- Vídeo de exemplo (README): https://www.youtube.com/watch?v=O-xjW_ig1KI
- Projeto de referência arquivado: `emotion-recognizer/archive/multimodal-reference/`

---

*Este documento é gerado automaticamente. Rodar `/asp-analyze-codebase` novamente atualiza apenas o que mudou (delta). Para recriar do zero, use `/asp-analyze-codebase --recreate`.*
