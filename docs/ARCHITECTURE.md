# Arquitetura — Sentinel Health

Visão geral da plataforma multimodal de monitoramento da saúde da mulher.

## Topologia de runtime

```
                          ┌──────────────────────────────────────────────────────┐
                          │  Host (Mac local · VPS · AWS EC2 · qualquer Docker)  │
                          │                                                      │
                          │  ┌────────────────────────────────────────────────┐  │
   browser ── HTTP(S) ────┼──┤  nginx (sentinel-nginx)                        │  │
                          │  │     │                                          │  │
                          │  │     ├── /             → landing :80            │  │
                          │  │     ├── /coverage.html → landing :80           │  │
                          │  │     ├── /surgical/*   → surgical :8000         │  │
                          │  │     ├── /static/*     → surgical :8000         │  │
                          │  │     ├── /api/*        → surgical :8000         │  │
                          │  │     └── /insight/*    → insight  :8501         │  │
                          │  └────────────────────────────────────────────────┘  │
                          │                                                      │
                          │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
                          │  │ sentinel-    │  │ sentinel-    │  │ sentinel-  │  │
                          │  │  landing     │  │  surgical    │  │  insight   │  │
                          │  │ (nginx       │  │ (FastAPI)    │  │ (Streamlit)│  │
                          │  │  static)     │  │  YOLOv8m     │  │  DeepFace  │  │
                          │  │              │  │              │  │  Whisper   │  │
                          │  └──────────────┘  └──────┬───────┘  └─────┬──────┘  │
                          │                           │                │         │
                          │   docker network: sentinel-net (bridge)    │         │
                          │                           │                │         │
                          └───────────────────────────┼────────────────┼─────────┘
                                                      │                │
                                                      ▼                ▼
                                       ┌──────────────────┐   ┌────────────────┐
                                       │  Hugging Face    │   │  OpenAI API    │
                                       │  Hub (model)     │   │  - chat        │
                                       │  pull best.pt    │   │  - whisper-1   │
                                       │  no 1º boot      │   │                │
                                       └──────────────────┘   └────────────────┘
                                                ▲
                                       AWS S3 (samples) ◄─── boto3 com IAM/profile
                                       AWS EC2/SSM (deploy via Terraform)
```

## Serviços e portas

| Service | Container name | Imagem | Porta interna | Path do nginx |
|---|---|---|:---:|---|
| `nginx` | `sentinel-nginx` | `nginx:alpine` | 80 | reverse proxy de tudo |
| `landing` | `sentinel-landing` | `sentinel-landing:latest` | 80 | `/`, `/coverage.html`, `/assets/*` |
| `surgical` | `sentinel-surgical` | `sentinel-surgical:latest` | 8000 | `/surgical/*`, `/static/*`, `/api/*` |
| `insight` | `sentinel-insight` | `sentinel-insight:latest` | 8501 | `/insight/*` |

Porta exposta ao host:
- **Default:** `0.0.0.0:80 → nginx:80` (`docker-compose.yml`)
- **Behind host reverse proxy:** `127.0.0.1:8100 → nginx:80` (`docker-compose.yml + docker-compose.behind-proxy.yml`)

## Fluxos de dados

### Fluxo 1 — Upload de vídeo no Surgical

```
Browser
   │ POST /api/video/upload (multipart .mp4/.avi/.mov)
   ▼
nginx (porta 80)
   │ proxy_pass http://surgical/api/video/upload
   ▼
sentinel-surgical (FastAPI)
   │ uuid = create_job()
   │ background_task → process_video(uuid, path)
   │
   ├─ get_detector() ── lazy-load YOLO(best.pt)
   │                    └─ best.pt vem do volume montado de
   │                       modules/surgical/web/models/, baixado
   │                       pelo entrypoint.sh do Hugging Face Hub
   │                       no primeiro boot do container
   │
   ├─ cv2.VideoCapture → frame loop
   │   └─ YOLO inference (conf=0.30) → bboxes + classes
   │
   ├─ writer (mp4v) → .mp4 anotado
   ├─ jobs[uuid] = {status: "completed", detections, ...}
   └─ JSON com summary em RESULTS_DIR

Browser (polling)
   ▼ GET /api/video/status/{uuid} → 200 quando completed
   ▼ GET /api/video/result/{uuid}/video → FileResponse mp4
   ▼ GET /api/video/result/{uuid}/report → FileResponse JSON
```

### Fluxo 2 — Análise de áudio no Insight

```
Browser (Streamlit UI)
   │ Upload audio (WAV/MP3/M4A)
   ▼
sentinel-insight (Streamlit)
   │ st.session_state.audio_only_path = tmp_path
   │
   │ [user clica "Analyse Audio"]
   │
   ├─ audio/transcriber.transcribe_audio(path)
   │    └─ OpenAI() client → audio.transcriptions.create(model="whisper-1")
   │       ◄─── chama OpenAI API (text-based, returns text + language)
   │
   ├─ audio/voice_analyzer.analyze_voice_emotions(transcription)
   │    ├─ try setup_openai_api() + _analyze_with_llm()
   │    │    └─ OpenAI() → chat.completions.create(model="gpt-5.4-nano")
   │    │       ◄─── prompt psicológico retornando JSON com:
   │    │              sentiment / risk_level / score 0-10 /
   │    │              detected_signals / domestic_violence_signals /
   │    │              recommended_action
   │    │
   │    └─ except → analyze_risk_locally(text)
   │         └─ regex sobre 27 padrões com pesos 1/2/3 (fallback,
   │            independente de rede ou key)
   │
   └─ render no Streamlit:
        - 4 métricas (sentiment, risk, score, source)
        - signals (badges)
        - keywords (badges)
        - transcription completa (expander)
        - summary LLM (st.info)
        - botão download voice_analysis.json
```

### Fluxo 3 — Galeria S3 de clips GynSurg (Surgical)

```
Browser
   ▼ GET /api/samples/list
   ▼
nginx → sentinel-surgical
   │ boto3 client (credenciais via ~/.aws montado + AWS_PROFILE env)
   │ s3.list_objects_v2(Bucket="surgical-detection-datasets-dev",
   │                    Prefix="gynsurg_sample/bleeding/")
   ▼
S3 (us-east-1)
   ▲ retorna lista de objetos
   │ [SampleClip{name, category, url, size_mb}, ...]
   ▼
JSON response (50 bleeding + 54 non_bleeding clips disponíveis)
```

## Integrações externas

| Serviço | Quem chama | Como | Auth |
|---|---|---|---|
| **OpenAI API** (`api.openai.com`) | `sentinel-insight` | SDK `openai>=1.0` chat completions + Whisper | `OPENAI_API_KEY` em `.env` mountado no container |
| **Hugging Face Hub** (`huggingface.co`) | entrypoint do `sentinel-surgical` | `curl -fL` do `best.pt` no 1º boot | Público — sem auth |
| **AWS S3** (`surgical-detection-datasets-dev`) | `sentinel-surgical` (galeria de samples) | `boto3` | `~/.aws/credentials` (montado RO) + `AWS_PROFILE` env |
| **AWS EC2 + Terraform** (deploy demo) | `terraform apply` | `aws-cli` + `gh` clone do repo no `user_data` | IAM Role na instância |
| **AWS SSM Parameter Store** (deploy) | EC2 boot script | `aws ssm get-parameter` | IAM Role |

## Decisões arquiteturais

### Por que monorepo (não polyrepo)

- **Avaliador acadêmico** abre 1 URL e tem tudo.
- Histórico do `surgical-video-ai` e `emotion-detector` preservado via `git subtree`.
- Versionamento conjunto da plataforma.
- Trade-off: 2 stacks Python conviventes em pastas distintas — sem conflito real porque cada uma vive em seu container.

### Por que modelo no Hugging Face Hub (não git LFS, não bake na imagem)

- **Free unlimited bandwidth** para modelos públicos.
- Model card profissional documenta v1→v2→v3, datasets, métricas, limitações.
- Discoverability (indexado pelo HF).
- Container baixa no 1º boot via `entrypoint.sh` — same code path para Mac local, servidor remoto, AWS EC2.
- Volume RW persiste o download entre restarts.

### Por que **near** real-time, não streaming síncrono

- Custo de implementação alto (websocket bidirecional + GPU dedicada + backpressure handling) para o ganho marginal num demo acadêmico.
- Latência fim-a-fim de upload → response em ~1 min satisfaz "tempo real" no contexto clínico de pós-procedimento.
- Streaming síncrono (sub-segundo) está em **Sentinel Realtime** (roadmap).

### Por que job tracker in-memory (não Redis/DB)

- Plataforma de demonstração; tráfego concorrente é 1 usuário (avaliador).
- Trade-off explícito: jobs em andamento se perdem em restart do container.
- Pronto para evolução: o `jobs: Dict` em `video.py:50` é o único ponto a migrar.

### Por que múltiplas nuvens (não 100% AWS)

- AWS: bom para infraestrutura (S3, EC2, Terraform).
- OpenAI API: GPT-5.4-nano + Whisper-1 estão **só** na OpenAI; Azure OpenAI seria caminho equivalente mas com setup extra (apiGPTeal Merck era assim e migramos).
- Hugging Face Hub: **padrão da indústria de ML** pra distribuição pública de modelos.
- A combinação demonstra ao avaliador competência multi-cloud sem amarrar a uma vendor única.

## Variantes de deploy

| Variante | Como subir | Quando usar |
|---|---|---|
| **Default** | `docker compose up -d` | Mac local, host dedicado, AWS EC2 com porta 80 livre |
| **Behind reverse proxy do host** | `docker compose -f docker-compose.yml -f docker-compose.behind-proxy.yml up -d` | Host com nginx/Apache já na 80; binda em `127.0.0.1:8100` |
| **AWS Terraform** | `cd terraform/environments/demo && terraform apply` | Provisioning automatizado num EC2 t3.medium com IAM Role |

Detalhes em [`deploy/README.md`](../deploy/README.md) e [`terraform/README.md`](../terraform/README.md).

## Privacidade e LGPD

- **Volumes locais** para uploads/results (`/tmp/surgical-uploads`, `/tmp/surgical-results`) — dados não vão para a nuvem default.
- **Transito criptografado** quando atrás de nginx com TLS (snippet pronto em `deploy/nginx/host-snippet.conf`).
- **SSM Parameter Store** para a `OPENAI_API_KEY` no deploy AWS — secret nunca aparece no Terraform state.
- **SSH desabilitado** no SG do EC2 (SG só abre 80/443); acesso administrativo via **SSM Session Manager** (IAM-controlled, auditado em CloudTrail).
- **S3 buckets bloqueados** com `public_access_block` em todas as 4 dimensões.
- **Sem persistência centralizada de dados de paciente** — design assumindo que o uso real exigiria EHR integration via API, fora do escopo do demo.

## Referências de análise técnica detalhada

| Documento | O que cobre |
|---|---|
| [`modules/surgical/docs/CODEBASE_ANALYSIS.md`](../modules/surgical/docs/CODEBASE_ANALYSIS.md) | Análise completa do código do Surgical (estrutura, padrões, decisões, observações factuais) |
| [`modules/insight/docs/CODEBASE_ANALYSIS.md`](../modules/insight/docs/CODEBASE_ANALYSIS.md) | Análise completa do código do Insight (pré-migração; aviso de obsolescência no header) |
| [`thoughts/shared/research/2026-05-16-merck-wrapper-locations-in-insight.md`](../../thoughts/shared/research/2026-05-16-merck-wrapper-locations-in-insight.md) | Inventário da migração apiGPTeal → OpenAI standard (research mode) |
| [`thoughts/shared/plans/2026-05-16-sentinel-health-platform.md`](../../thoughts/shared/plans/2026-05-16-sentinel-health-platform.md) | Plano de implementação master da plataforma (9 phases) |
