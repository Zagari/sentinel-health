# Análise do Codebase: surgical-video-ai

> **Última atualização:** 2026-05-16
> **Commit:** 9f3a32d
> **Branch:** main

## Visão Geral

Sistema de análise de vídeos cirúrgicos baseado em **YOLOv8m** (Ultralytics) para detectar **sangramento anômalo (`blood`)** e **instrumentos cirúrgicos (`grasper`)** em cirurgias ginecológicas laparoscópicas. Estratégia **cross-dataset**: treina em **CholecSeg8k** (colecistectomia, máscaras pixel-level) e valida/fine-tuna em **GynSurg** (cirurgia ginecológica). O modelo de produção é **v3_finetuned** (91.72% detecção / 13.44% FP @ threshold 0.30).

O repositório agrupa três frentes interligadas:
- **Aplicação web** (`web/`): FastAPI + frontend estático que serve a inferência, galeria de clips S3 e interface de anotação para fine-tuning.
- **Pipeline standalone** (`src/`): scripts CLI Python para preparar dataset, processar vídeo com anomalias temporais (sangramento prolongado/excessivo) e gerar relatórios PDF.
- **Operação em nuvem** (`scripts/` + `terraform/`): provisionamento AWS (EC2 GPU, SageMaker, S3) e bash scripts para treinar/validar/comparar versões do modelo no servidor remoto.

Projeto acadêmico — **FIAP Tech Challenge Fase 4**.

## Stack Tecnológico

| Categoria | Tecnologia | Versão (declarada) |
|-----------|------------|--------------------|
| Linguagem | Python | 3.10+ |
| Detecção de objetos | YOLOv8m via Ultralytics | `ultralytics>=8.0.0` |
| Deep learning | PyTorch + torchvision | `torch>=2.0.0`, `torchvision>=0.15.0` |
| Visão computacional | OpenCV (`opencv-python` raiz / `opencv-python-headless` web) | `>=4.8.0` |
| Web framework | FastAPI + uvicorn + python-multipart | `fastapi==0.109.0`, `uvicorn[standard]==0.27.0`, `python-multipart==0.0.6` |
| Validação | Pydantic v2 | `pydantic>=2.0.0` |
| AWS SDK | boto3 + sagemaker SDK | `boto3>=1.28.0`, `sagemaker>=2.200.0` |
| Download de vídeo | `yt-dlp` (instalado no container) | (sem pin) |
| Manipulação de dados | numpy, pandas, scikit-learn, Pillow | `>=1.24.0`, `>=2.0.0`, `>=1.3.0`, `>=10.0.0` |
| Visualização | matplotlib, seaborn | `>=3.7.0`, `>=0.12.0` |
| Relatórios PDF | fpdf2 | `>=2.7.0` |
| Configuração | python-dotenv, pyyaml, click, tqdm | (várias) |
| Testes / qualidade | pytest, pytest-cov, black, isort, flake8 | `>=7.4.0`, `>=4.1.0`, `>=23.0.0`, `>=5.12.0`, `>=6.1.0` |
| Containerização | Docker + docker-compose (variantes GPU e CPU) | — |
| Infraestrutura | Terraform `>= 1.0.0` + provider `hashicorp/aws ~> 5.0` | — |

Dois `requirements.txt` separados: o da raiz é o ambiente completo (ML, scripts, demo, relatórios); o de `web/requirements.txt` é enxuto para o container de inferência.

## Estrutura de Diretórios

```
surgical-video-ai/
├── requirements.txt                # Deps completas (raiz)
├── README.md                       # ~500 linhas: arquitetura, quick start, métricas
├── .gitignore                      # ignora data/, models/, videos/, .env, *.pt, thoughts/, docs/CHECKPOINT*, docs/plano*
│
├── web/                            # APLICAÇÃO WEB (FastAPI + frontend estático)
│   ├── app/
│   │   ├── main.py                 # entry FastAPI: monta routers + /static + /health
│   │   ├── routers/                # video, samples, info, annotation
│   │   ├── services/detector.py    # VideoDetector — wrapper Ultralytics YOLO
│   │   └── static/                 # index.html, annotation.html, js/app.js, css/style.css
│   ├── models/                     # best.pt (montado como volume read-only)
│   ├── Dockerfile                  # python:3.10-slim + ffmpeg + libgl + nodejs + yt-dlp
│   ├── docker-compose.yml          # variante GPU (NVIDIA reservations)
│   ├── docker-compose.cpu.yml      # variante CPU (sem deploy block)
│   ├── requirements.txt            # FastAPI + ultralytics + boto3 (enxuto)
│   └── README.md                   # README específico da app web
│
├── src/                            # PIPELINE STANDALONE CLI (alternativo ao web/)
│   ├── data/prepare_cholecseg8k.py # converte máscaras watershed → bboxes YOLO
│   ├── inference/processor.py      # SurgicalVideoProcessor com anomalias temporais
│   ├── reports/generator.py        # SurgicalReportGenerator (PDF via fpdf2)
│   ├── demo/run_demo.py            # pipeline E2E: processor → JSON → PDF
│   ├── cloud/                      # vazio (só __init__.py)
│   ├── models/                     # vazio (só __init__.py)
│   └── video/                      # vazio (só __init__.py)
│
├── scripts/                        # 16 bash + 2 Python (~2400 linhas) p/ AWS + treino + validação
│   ├── server-setup.sh             # bootstrap da EC2 (deps, venv)
│   ├── server-train.sh             # v1 baseline (yolov8m.pt, 100ep)
│   ├── server-train-v2-classweight.sh   # v2 com cls=3.0
│   ├── finetune-gynsurg.sh         # v3 fine-tuning (30ep, lr=0.001, freeze=10)
│   ├── server-inference.sh
│   ├── generate-validation-set.sh  # cria lista fixa (10 bleeding + 10 non-bleeding)
│   ├── validate-gynsurg.sh         # roda YOLO em validation set + gera JSON
│   ├── validate-all-versions.sh    # valida todas as versões
│   ├── analyze-threshold.sh        # testa thresholds 0.1–0.7
│   ├── compare-validations.sh      # diff entre runs
│   ├── update-web-model.sh         # baixa modelo do S3 p/ web/models/
│   ├── prepare-gynsurg-sample.sh   # sobe clips de amostra ao S3
│   ├── infra-up-training.sh        # terraform apply (training env)
│   ├── infra-down-training.sh      # terraform destroy
│   ├── infra-up-inference.sh
│   ├── infra-down-inference.sh
│   ├── fix_labels.py               # ajustes pontuais em labels YOLO
│   └── prepare_negative_only.py    # gera dataset só com negativos (experimento v5)
│
├── anotacoes-gynsurg/              # ANOTAÇÕES FINE-TUNING v3 (versionado)
│   └── yolo_export/
│       ├── images/                 # frames .jpg
│       ├── labels/                 # labels YOLO .txt (pseudo-bbox 80% centralizado)
│       └── data.yaml
│
├── terraform/                      # IaC AWS
│   ├── modules/
│   │   ├── storage/main.tf         # 3 S3 buckets (datasets, models, results) + versioning + AES256 + lifecycle 90d em results
│   │   ├── training/main.tf        # EC2 + SG (SSH 0.0.0.0/0) + IAM + user_data clona repo
│   │   └── inference/main.tf       # SageMaker model + endpoint config + endpoint
│   └── environments/
│       ├── training/main.tf        # compõe modules storage + training
│       └── inference/main.tf       # compõe module inference
│
├── surgical-training/results/      # SAÍDA LOCAL de treinos (v3_finetuned, v4_finetuned — pesos gitignored)
├── tests/                          # SÓ __init__.py — sem testes implementados
├── notebooks/                      # vazio
├── reports/                        # vazio (PDFs gerados aqui)
├── videos/                         # vazio (input/output gitignored)
├── data/                           # vazio (raw/processed/yolo_format gitignored)
├── models/                         # vazio (trained/exported gitignored)
└── docs/                           # somente CHECKPOINT-SERVIDOR.md e plano-implementacao-video-analysis.md (ambos gitignored)
```

### Responsabilidades por Diretório

| Diretório | Responsabilidade |
|-----------|------------------|
| `web/` | App de inferência exposta ao usuário final. **Único caminho efetivamente "em produção"**. |
| `web/app/routers/` | 4 routers FastAPI sob prefixos `/api/video`, `/api/info`, `/api/samples`, `/api/annotation`. |
| `web/app/services/` | Wrapper YOLO (carrega `.pt` uma vez via lazy `get_detector`). |
| `web/app/static/` | Frontend simples (HTML + Vanilla JS + CSS). |
| `src/` | Pipeline CLI alternativa para preparação de dataset, processamento offline com anomalias temporais e geração de PDF. Não compartilha código com `web/`. |
| `scripts/` | Automação de servidor remoto (treino, validação, comparação). Tudo via `yolo` CLI da Ultralytics. |
| `terraform/modules/` | Módulos reutilizáveis: `storage`, `training`, `inference`. |
| `terraform/environments/` | Composição dos módulos para cada ambiente (training / inference). |
| `anotacoes-gynsurg/` | Dataset YOLO de fine-tuning (1020 frames, classes 0/1). **Está versionado** ao contrário de `data/`. |
| `surgical-training/results/` | Saídas locais do `yolo detect train` (`weights/`, `args.yaml`, plots). Pesos `.pt` gitignored, mas estrutura permanece. |
| `tests/` | Apenas placeholder `__init__.py`. |
| `docs/` | Documentos locais (não versionados via `.gitignore`). |

## Padrões de Arquitetura

### Padrão Principal

**Aplicação web em camadas (FastAPI) + pipeline CLI paralela + automação shell-first**. Não é monorepo de pacotes Python instaláveis; cada subprojeto roda no seu próprio `cwd`:

- `web/` é containerizada e roda `uvicorn app.main:app` com `cwd=/app`.
- `src/` é invocada via `python src/<modulo>/<arquivo>.py --args ...` (ou via `run_demo.py` que ajusta `sys.path`).
- `scripts/*.sh` rodam direto no servidor (não dependem de venv local).

### Convenções de Código

| Aspecto | Convenção |
|---------|-----------|
| Linguagem | Python 3.10+, type hints modernos (`list[dict]`, `str \| None`) |
| Nomenclatura de arquivos | `snake_case.py`; bash `kebab-case.sh` |
| Nomenclatura de funções/variáveis | `snake_case`; classes em `PascalCase` |
| Privacidade | Helpers privados com `_` prefix (`_load_model`, `_get_class_color`) |
| Docstrings | Triple-quote em PT-BR, com Args/Returns; comum no topo do módulo |
| Pydantic | `BaseModel` para request/response (`URLRequest`, `SampleClip`, `ClassInfo`, etc.) |
| Logs | `logging.getLogger(__name__)` no `web/`, `print()` direto em `src/` e bash scripts |
| Comentários | Cabeçalhos visuais com `# === Section ===` ou `# -- Section --` |
| Bash | `set -e`, blocos numerados `[N/M]`, mensagens com ✅/❌/⚠️, `aws s3 sync ... --only-show-errors` |
| Terraform | Variáveis no topo, recursos, outputs no fim; `tags = { Project, Environment, Name }` |
| Idioma | PT-BR predominante em mensagens, docstrings, comentários e endpoints |

### Padrões Identificados

1. **Lazy loading do detector via singleton de módulo**
   - Onde: `web/app/routers/video.py:get_detector`
   - Variável global `detector = None`; primeira request cria a instância. Modelo carregado uma única vez por processo.

2. **Job tracker in-memory**
   - Onde: `web/app/routers/video.py:50` (`jobs: Dict[str, Dict] = {}`)
   - Background tasks atualizam o dicionário; status consultado em `/api/video/status/{job_id}`. Comentário explícito: *"em produção, usar Redis ou DB"*. Não persiste entre restarts.

3. **Background processing com `BackgroundTasks` do FastAPI**
   - Onde: `video.py:upload_video`, `video.py:process_url`, `samples.py:process_sample`
   - Upload retorna `job_id` imediatamente; processamento real ocorre em task async.

4. **Cross-router reuse**
   - Onde: `samples.py:128` importa `jobs`, `process_video`, `UPLOAD_DIR` de `app.routers.video`
   - O router de samples reaproveita o pipeline de processamento do router de video, só baixando do S3 antes.

5. **Constantes "info" hard-coded em router**
   - Onde: `web/app/routers/info.py` — `MODEL_INFO`, `DATASET_INFO`, `TRAINING_METRICS`, `PROJECT_INFO`
   - Dicionários estáticos em nível de módulo servidos via endpoints `/api/info/*`. Sem leitura dinâmica de metadados do modelo.

6. **Frame caching em `/tmp` para anotação**
   - Onde: `annotation.py` — `FRAMES_CACHE = "/tmp/frames_cache"`, `ANNOTATIONS_PATH = "/tmp/annotations"`
   - Frames extraídos de clips GynSurg são redimensionados para 1280 px de largura e salvos em disco; anotações vão para `annotations.json` (lista com `annotated_ids`, `skipped_ids`).

7. **Pseudo-bounding box centralizado para fine-tuning**
   - Onde: `annotation.py:export_for_training:266`
   - Frames classificados como `bleeding` recebem uma única bbox em `(0.5, 0.5, 0.8, 0.8)` — classe 1 (blood). Negativos recebem arquivo de label vazio.

8. **Dataclasses tipadas no pipeline CLI**
   - Onde: `src/inference/processor.py` — `@dataclass Detection`, `@dataclass VideoAnalysis`
   - `field(default_factory=list)` para listas, `field(default_factory=lambda: datetime.now().isoformat())` para timestamps.

9. **Detecção de anomalias temporal (apenas no pipeline CLI)**
   - Onde: `src/inference/processor.py:218-251`
   - Sangramento prolongado (`> BLOOD_DURATION_THRESHOLD=5s`) e excessivo (`> BLOOD_AREA_THRESHOLD=0.05 da área`). Web não tem esta lógica.

10. **Reprodutibilidade via validation set fixo**
    - Onde: `scripts/validate-gynsurg.sh:135-152`
    - Suporta 3 modos: `--fixed` (lê arquivos `.txt` gerados por `generate-validation-set.sh`), `--seed` (`shuf --random-source=<(yes 42)`), random. Garante comparações reproduzíveis entre versões.

11. **Versionamento de modelo via flag `--version`**
    - Onde: `validate-gynsurg.sh`, `validate-all-versions.sh`, `analyze-threshold.sh`
    - Tag (`v1_baseline`, `v2_classweight`, `v3_finetuned`, etc.) propagada para o `validation_report.json` e diretório de saída.

12. **Bootstrap via `user_data` no Terraform**
    - Onde: `terraform/modules/training/main.tf:167-246`
    - `aws_instance.training` clona o repo GitHub no `user_data`, cria venv, instala deps, monta script `train.sh` de conveniência. Nada é injetado por SCP/SSM.

## Componentes Principais

### `web/app/main.py` — Bootstrap FastAPI
- **Localização:** `web/app/main.py`
- **Responsabilidade:** instancia `FastAPI(title="Surgical Video AI", version="1.0.0")`, registra CORS aberto (`*`), monta os 4 routers e arquivos estáticos.
- **Rotas próprias:** `GET /` (serve `index.html`), `GET /annotation` (serve `annotation.html`), `GET /health`.
- **Container:** servido por `uvicorn app.main:app --host 0.0.0.0 --port 8000`, exposto pelo compose na porta host **8100**.

### `web/app/services/detector.py` — VideoDetector
- **Localização:** `web/app/services/detector.py`
- **Classe:** `VideoDetector(model_path)`
- **API:**
  - `process_video(video_path, output_dir, job_id, progress_callback, conf_threshold=0.3)` → `dict` com `video`, `json`, `summary`.
  - `detect_frame(frame, conf_threshold=0.3)` → `{detections, annotated_frame}` (não usado pelo backend atualmente).
- **Lê classes do `model.names`** (não hard-coded) — herda do `.pt`.
- **Output JSON por job:** `{summary: {…}, detections: [{frame, timestamp, class, confidence, bbox}, …]}` em `<output>/<job_id>_detections.json`.
- **Codec de vídeo de saída:** `mp4v` (MP4).

### `web/app/routers/video.py` — Upload e processamento de vídeo
- **Endpoints:**
  - `POST /api/video/upload` — multipart, valida `.mp4|.avi|.mov|.mkv|.webm`, gera UUID, salva em `/tmp/surgical-uploads`, agenda task.
  - `POST /api/video/url` — `{url: HttpUrl}`, baixa com `yt-dlp -f "best[height<=720]"` (timeout 300s), depois processa.
  - `GET /api/video/status/{job_id}` — devolve `ProcessingStatus`.
  - `GET /api/video/result/{job_id}/video` — `FileResponse` do MP4 anotado.
  - `GET /api/video/result/{job_id}/report` — `FileResponse` do JSON.
- **Diretórios fixos:** `UPLOAD_DIR=/tmp/surgical-uploads`, `RESULTS_DIR=/tmp/surgical-results` (volumes do compose).

### `web/app/routers/samples.py` — Galeria S3
- **Endpoints:**
  - `GET /api/samples/metadata` — cacheia `s3://{S3_BUCKET}/gynsurg_sample/metadata.json` em variável de módulo.
  - `GET /api/samples/list?category=` — lista objetos `.mp4` em `gynsurg_sample/{bleeding|non_bleeding}/`.
  - `GET /api/samples/stream/{category}/{filename}` — `StreamingResponse` direto do S3.
  - `POST /api/samples/process/{category}/{filename}` — baixa S3 → agenda processamento (reutiliza `jobs` e `process_video` do video.py).
  - `GET /api/samples/stats` — contagens e tamanhos por categoria.
- **Variável de ambiente:** `S3_BUCKET` (default `surgical-detection-datasets-dev`), prefixo fixo `gynsurg_sample`.

### `web/app/routers/info.py` — Metadados
- **Endpoints:** `GET /api/info/{model|dataset|metrics|classes|project|strategy}`
- **Conteúdo estático** — dicionários `MODEL_INFO`, `DATASET_INFO`, `TRAINING_METRICS`, `PROJECT_INFO` no próprio módulo.
- **Valores fixados:** versão `v3_finetuned`, threshold `0.30`, detection rate `91.72%`, FP rate `13.44%`.

### `web/app/routers/annotation.py` — Anotação para fine-tuning
- **Endpoints:**
  - `GET /api/annotation/frame/random` — sorteia clip não anotado, extrai frame do meio (`total_frames // 2`), redimensiona para máx. 1280 px, cacheia em disco, retorna `{frame_id, frame_url, ground_truth_label}`.
  - `GET /api/annotation/frame/{frame_id}/image` — serve JPG do cache.
  - `POST /api/annotation/annotate` — grava em `annotations.json` (com `has_bleeding`, `confidence`).
  - `POST /api/annotation/skip/{frame_id}` — adiciona ao `skipped_ids`.
  - `GET /api/annotation/stats` — contadores.
  - `GET /api/annotation/export` — gera diretório YOLO (`images/train`, `labels/train`, `data.yaml`) com pseudo-bbox central para `bleeding`, label vazio para `non_bleeding`.
  - `DELETE /api/annotation/reset` — backup + delete do `annotations.json`.
- **Dependência externa:** dataset GynSurg montado em `GYNSURG_PATH` (default `/data/GynSurg_Action_3sec`).

### `src/inference/processor.py` — `SurgicalVideoProcessor`
- **Pipeline CLI alternativa** ao `VideoDetector` do `web/`.
- **3 classes** hard-coded: `{0: "grasper", 1: "blood", 2: "electrocautery"}`.
- **Threshold padrão diferente:** `CONFIDENCE_THRESHOLD = 0.5` (vs. 0.30 no web).
- **Anomalias temporais:** `excessive_bleeding` (área > 5%), `prolonged_bleeding` (duração > 5s).
- **Dataclasses:** `Detection`, `VideoAnalysis` (com `summary`, `anomalies`, `detections`).
- **Output:** JSON via `save_analysis()` — schema **distinto** do `VideoDetector`.

### `src/reports/generator.py` — `SurgicalReportGenerator`
- **Geração de PDF via `fpdf2`** com 5 seções: capa, resumo executivo, estatísticas, anomalias por severidade, linha do tempo (buckets 30s) e recomendações.
- **Consome o JSON do `src/inference/processor.py`** (não o JSON do `web/`). Procura por `anomalies` e `detections` no formato do processor CLI.
- **Cores por severidade:** vermelho/laranja/amarelo. Status: `ATENCAO NECESSARIA` / `REVISAO RECOMENDADA` / `PROCEDIMENTO NORMAL`.

### `src/data/prepare_cholecseg8k.py` — Conversor de dataset
- **Entrada:** estrutura `CholecSeg8k/video*/video*_frame_*/`*_endo.png` + `*_watershed_mask.png`.
- **Mapping de IDs de máscara watershed → YOLO:** `{50: 0 (grasper), 23: 1 (blood)}`.
- **`mask_to_bbox()`:** `findContours` + `boundingRect`, filtra contornos com área < 100 px.
- **Split:** `train_test_split(test_size=0.2, random_state=42)`.
- **Saída:** estrutura YOLO `train/images`, `train/labels`, `val/images`, `val/labels`, `data.yaml` com `nc=2`.

### `src/demo/run_demo.py` — Pipeline E2E offline
- **Encadeia:** `SurgicalVideoProcessor.process_video` → `save_analysis` → `SurgicalReportGenerator.generate_report`.
- **Gera 3 artefatos:** `*_analyzed_<ts>.mp4`, `*_analysis_<ts>.json`, `*_report_<ts>.pdf`.
- **CLI:** `--video --model --output --preview --cpu`.

### `scripts/*.sh` — Operação remota
Todos seguem o mesmo padrão (`set -e`, etapas numeradas, sync com S3). Pontos-chave:
- `server-train.sh`: `yolo detect train data=… model=yolov8m.pt epochs=100 imgsz=640 batch=16 patience=20` → upload `best.pt` para `s3://surgical-detection-models-dev/trained/`.
- `server-train-v2-classweight.sh`: igual ao v1 + `cls=3.0` (peso da loss de classificação).
- `finetune-gynsurg.sh`: `epochs=30 lr0=0.001 batch=8 freeze=10`, modelo base = `~/surgical-training/models/best.pt`, gera `best_v3_finetuned.pt`.
- `validate-gynsurg.sh`: 363 linhas — roda `yolo detect predict` em 10 bleeding + 10 non-bleeding, conta frames com blood via parsing dos `labels/*.txt`, usa `ffprobe` para contar frames totais, gera `validation_report.json` com `blood_detection_rate` e `false_positive_rate`.

### Terraform — `terraform/modules/`
- **`storage/main.tf`:** 3 S3 buckets (`{project}-{datasets|models|results}-{env}`), versioning + AES256 em datasets e models, lifecycle de 90 dias em results.
- **`training/main.tf`:** AMI `Deep Learning OSS Nvidia Driver AMI GPU PyTorch*Ubuntu*` (filtro `data.aws_ami`), instance type **default `t3.xlarge`** (comentário marca como temporário), `key_name = "castellabate-key"` no env de training, SG permitindo SSH `0.0.0.0/0`, IAM com `s3:Get/Put/List/Delete` nos 3 buckets, `user_data` clona `https://github.com/Zagari/surgical-video-ai.git`.
- **`inference/main.tf`:** SageMaker model usando imagem oficial `pytorch-inference:2.0.1-gpu-py310-cu118-ubuntu20.04-sagemaker` apontando para `s3://{bucket}/trained/model.tar.gz`; endpoint config `ml.g4dn.xlarge`; envs `MODEL_VERSION`, `CONFIDENCE_THRESHOLD`.

## Fluxos de Dados

### Fluxo 1 — Upload de vídeo via Web UI

```
POST /api/video/upload (multipart .mp4/.avi/.mov/.mkv/.webm)
  ↓
generate uuid → salva em /tmp/surgical-uploads/{uuid}_{filename}
  ↓
jobs[uuid] = {status: "pending"}
BackgroundTasks → process_video(uuid, path)
  ↓
VideoDetector (lazy singleton) lê classes do .pt → cv2.VideoCapture loop:
   self.model(frame, conf=0.3) → desenha bboxes → writer.write(annotated)
   acumula detections[], class_counts, frames_with_{blood,grasper}
  ↓
escreve /tmp/surgical-results/{uuid}_annotated.mp4 + {uuid}_detections.json
  ↓
jobs[uuid] = {status: "completed", result_url, report_url, detections: summary}
  ↓
Frontend faz polling em GET /api/video/status/{uuid}
  ↓ (quando completed)
GET /api/video/result/{uuid}/video  +  GET /api/video/result/{uuid}/report
```

### Fluxo 2 — Processar URL (YouTube etc.)

```
POST /api/video/url {url}
  ↓
subprocess yt-dlp -f "best[height<=720]" -o /tmp/surgical-uploads/{uuid}_video.mp4
  ↓ (timeout 300s)
mesmo fluxo de processamento do Fluxo 1
```

### Fluxo 3 — Galeria de samples (S3)

```
GET /api/samples/list?category=bleeding
  ↓
boto3 list_objects_v2 em s3://{S3_BUCKET}/gynsurg_sample/bleeding/
  ↓
frontend mostra grid → user escolhe
  ↓
POST /api/samples/process/{category}/{filename}
  ↓
s3.download_file → /tmp/surgical-uploads/{uuid}_{filename}
  ↓
jobs[uuid] = {…, source: {type: "sample", category, ground_truth}}
  ↓
process_video (reusa pipeline do router video)
```

### Fluxo 4 — Anotação para fine-tuning

```
GET /api/annotation/frame/random
  ↓
embaralha clips em $GYNSURG_PATH/GynSurg_bleeding_dataset/{Bleeding,Non_bleeding}/*.mp4
escolhe primeiro não anotado/pulado → cv2 lê frame do meio
  ↓
redimensiona para ≤1280 px de largura → /tmp/frames_cache/{frame_id}.jpg
retorna {frame_id, frame_url, ground_truth_label}
  ↓
user pressiona S/N/Espaço no /annotation
POST /api/annotation/annotate  ou  POST /api/annotation/skip/{frame_id}
  ↓ (acumula em /tmp/annotations/annotations.json)
GET /api/annotation/export
  ↓
gera /tmp/annotations/yolo_export/{images,labels}/train + data.yaml
labels: pseudo-bbox "1 0.5 0.5 0.8 0.8" para bleeding, vazio para non_bleeding
  ↓
servidor: scripts/finetune-gynsurg.sh /tmp/annotations/yolo_export
  ↓
yolo detect train (30ep, lr=0.001, freeze=10) → best_v3_finetuned.pt
  ↓
aws s3 cp para s3://surgical-detection-models-dev/trained/
  ↓
local: scripts/update-web-model.sh → web/models/best.pt
```

### Fluxo 5 — Pipeline standalone CLI (offline, sem web)

```
prepare_cholecseg8k.py --input CholecSeg8k/ --output data/yolo_format
  ↓
(treina offline com Ultralytics YOLO CLI ou scripts)
  ↓
run_demo.py --video --model
  ├─→ SurgicalVideoProcessor.process_video
  │     (3 classes, threshold 0.5, detecta excessive/prolonged bleeding)
  │     → VideoAnalysis dataclass
  ├─→ save_analysis → JSON (schema com anomalies)
  └─→ SurgicalReportGenerator.generate_report → PDF (fpdf2)
```

### Fluxo 6 — Treinamento em AWS (Terraform)

```
terraform apply (terraform/environments/training/)
  ├─→ module.storage → 3 S3 buckets
  └─→ module.training → EC2 (Deep Learning AMI) + IAM + SG
                       user_data: clona repo, cria venv, instala deps
ssh ubuntu@<ip>
  ↓
./scripts/server-train.sh             → v1 baseline → s3://.../trained/best.pt
./scripts/server-train-v2-classweight.sh → v2
./scripts/finetune-gynsurg.sh         → v3 (best_v3_finetuned.pt)
./scripts/validate-gynsurg.sh <path> --fixed --version vN [--upload]
terraform destroy
```

## Integrações Externas

| Sistema | Tipo | Configuração | Onde |
|---------|------|--------------|------|
| AWS S3 (datasets) | boto3 / `aws s3` CLI | `surgical-detection-datasets-dev` — dataset YOLO + `gynsurg_sample/` | `samples.py`, scripts |
| AWS S3 (models) | boto3 / `aws s3` CLI | `surgical-detection-models-dev/trained/best*.pt` + `model.tar.gz` | scripts, terraform |
| AWS S3 (results) | `aws s3 sync` | `surgical-detection-results-dev/validation_gynsurg_*/` | `validate-gynsurg.sh` |
| AWS EC2 | Terraform `aws_instance` | Deep Learning AMI Ubuntu, default `t3.xlarge` (comentário diz "trocar por g4dn.xlarge") | `terraform/modules/training/` |
| AWS SageMaker | Terraform `aws_sagemaker_{model,endpoint_configuration,endpoint}` | `ml.g4dn.xlarge`, image `pytorch-inference:2.0.1-gpu-py310-cu118` | `terraform/modules/inference/` |
| AWS IAM | Terraform | Roles para EC2 (`s3:GetPutListDelete`) e SageMaker (`AmazonSageMakerFullAccess` + S3 GetObject/ListBucket) | terraform modules |
| YouTube / web | `yt-dlp -f "best[height<=720]"` | subprocess no container; binário instalado via `pip install yt-dlp` no Dockerfile | `video.py:process_url` |
| GitHub | `git clone` no `user_data` | URL hard-coded `https://github.com/Zagari/surgical-video-ai.git` | `terraform/modules/training/main.tf:178` |
| Ultralytics Hub | Implícito (download de `yolov8m.pt`) | Faz download automático no primeiro `yolo` call | scripts de treino |
| ffmpeg / ffprobe | CLI | Conta frames de vídeos AVI gerados pelo YOLO (`validate-gynsurg.sh:228-242`); container instala via `apt-get install ffmpeg` | scripts, Dockerfile |

## Banco de Dados

**Não há banco de dados.** Toda persistência é:
- **Em memória do processo:** dicionário `jobs` em `video.py:50` (perdido ao reiniciar).
- **No filesystem do container:** `/tmp/surgical-uploads`, `/tmp/surgical-results`, `/tmp/annotations`, `/tmp/frames_cache` — montados como **named volumes** Docker (`surgical-uploads`, `surgical-results`, `surgical-annotations`).
- **No S3:** datasets, modelos, resultados de validação.
- **Arquivos JSON em disco:** `annotations.json` (estado da anotação), `*_detections.json` (output por job), `validation_report.json` (output de validação).

O `video.py` deixa um TODO explícito: *"em produção, usar Redis ou DB"*.

## Testes

| Tipo | Localização | Comando | Estado |
|------|-------------|---------|--------|
| Unitários | `tests/` | `pytest` | **Apenas `__init__.py` — nenhum teste implementado** |

`pytest>=7.4.0` e `pytest-cov>=4.1.0` estão em `requirements.txt` mas não há suíte. Não há CI configurado.

## Scripts Úteis

### Aplicação web
| Comando | Descrição |
|---------|-----------|
| `cd web && docker-compose up -d` | Sobe API com GPU NVIDIA |
| `cd web && docker-compose -f docker-compose.cpu.yml up -d` | Sobe API só com CPU |
| `curl http://localhost:8100/health` | Health check |

### Pipeline CLI (raiz)
| Comando | Descrição |
|---------|-----------|
| `python src/data/prepare_cholecseg8k.py -i CholecSeg8k -o data/yolo_format` | Converte CholecSeg8k → YOLO |
| `python src/demo/run_demo.py -v video.mp4 -m models/best.pt [--cpu] [--preview]` | Pipeline E2E offline (vídeo + JSON + PDF) |
| `python src/inference/processor.py -v video.mp4 -m models/best.pt -o out.mp4 -j out.json` | Só processamento (sem PDF) |
| `python src/reports/generator.py -j analysis.json -o report.pdf` | Só PDF |

### Operação em servidor
| Comando | Descrição |
|---------|-----------|
| `./scripts/server-setup.sh` | Instala deps no EC2 (Ubuntu Deep Learning AMI) |
| `./scripts/server-train.sh` | Treino v1 baseline (100 ep, batch 16) |
| `./scripts/server-train-v2-classweight.sh` | v2 com `cls=3.0` |
| `./scripts/finetune-gynsurg.sh [yolo_export_dir] [base_model]` | v3 fine-tuning (30 ep, freeze=10, lr=0.001) |
| `./scripts/generate-validation-set.sh /path/to/GynSurg [N]` | Gera lista fixa (default N=10) |
| `./scripts/validate-gynsurg.sh /path/to/GynSurg --fixed --version vX [--upload]` | Valida uma versão |
| `./scripts/validate-all-versions.sh /path/to/GynSurg` | Valida todas as versões |
| `./scripts/analyze-threshold.sh /path/to/GynSurg --version v3_finetuned [--thresholds 0.1,0.2,…]` | Sweep de thresholds |
| `./scripts/compare-validations.sh [run1 run2]` | Diff entre relatórios |
| `./scripts/update-web-model.sh` | Baixa `best.pt` do S3 para `web/models/` |

### Infra
| Comando | Descrição |
|---------|-----------|
| `./scripts/infra-up-training.sh` | `terraform apply` no env training |
| `./scripts/infra-down-training.sh` | `terraform destroy` |
| `./scripts/infra-up-inference.sh` / `infra-down-inference.sh` | Idem para SageMaker |

## Variáveis de Ambiente

| Variável | Onde é lida | Default | Obrigatória |
|----------|-------------|---------|:-----------:|
| `MODEL_PATH` | `video.py:30` (lazy detector) | `models/best.pt` (compose: `/app/models/best.pt`) | Recomendada |
| `S3_BUCKET` | `samples.py:15` | `surgical-detection-datasets-dev` | Recomendada |
| `AWS_DEFAULT_REGION` | boto3 + AWS CLI | `us-east-1` (compose) | Sim (para S3) |
| `GYNSURG_PATH` | `annotation.py:19` | `/data/GynSurg_Action_3sec` | Só se usar `/annotation` |
| `ANNOTATIONS_PATH` | `annotation.py:20` | `/tmp/annotations` | Não |
| `PYTHONUNBUFFERED` | Dockerfile | `1` | — |
| `aws_region`, `environment`, `project_name`, `key_name`, `model_version`, `confidence_threshold` | Terraform vars | (ver `terraform/environments/*/main.tf`) | Sim no Terraform |

Credenciais AWS são montadas via volume read-only `~/.aws:/root/.aws:ro` no `docker-compose.yml`.

## Pontos de Extensão

1. **Novo endpoint na API:** criar arquivo em `web/app/routers/`, instanciar `router = APIRouter()`, registrar em `web/app/main.py` com `app.include_router(novo.router, prefix="/api/novo", tags=["novo"])`.
2. **Nova classe detectada:** treinar com `nc>2` (ajustar `data.yaml`), atualizar `MODEL_INFO["classes"]` em `info.py`, ajustar `_get_class_color` em `src/inference/processor.py` (se for usar o pipeline CLI).
3. **Persistência de jobs:** substituir `jobs: Dict` em `video.py:50` por Redis/DB. Refatorar `process_video` para escrever status fora da memória.
4. **Novo modo de input de vídeo:** adicionar endpoint em `video.py` ou novo router; reaproveitar `process_video` background task.
5. **Novo modelo / versão:** subir `.pt` para `s3://surgical-detection-models-dev/trained/best_<nome>.pt`; atualizar Terraform `var.model_version` para SageMaker; rodar `scripts/update-web-model.sh` para a app web.
6. **Nova métrica de validação:** estender `count_detections()` no Python embutido de `validate-gynsurg.sh:245-291` e o `report` JSON.
7. **Frontend novo:** editar `web/app/static/index.html` / `js/app.js` (vanilla JS — sem build step).
8. **Anomalia temporal nova (CLI):** ampliar a lógica em `src/inference/processor.py:218-251` e refletir no `SurgicalReportGenerator._add_anomalies_section`.
9. **Novo bucket S3 / IAM:** adicionar em `terraform/modules/storage/main.tf`, exportar no `outputs`, consumir em `modules/training` ou `modules/inference`.
10. **CI/CD:** não existe. Para adicionar, criar `.github/workflows/` (repo está no GitHub conforme `info.py`).

## Notas e Observações Factuais

Pontos que são úteis lembrar ao trabalhar no projeto:

- **`web/` e `src/inference/processor.py` são pipelines paralelas e divergentes:**
  - `web/app/services/detector.py` é o caminho de produção: 2 classes (`grasper`, `blood`) lidas dinamicamente do `.pt`, threshold 0.30, sem anomalias temporais.
  - `src/inference/processor.py` é a versão CLI offline: hard-coded com **3 classes** (`+ electrocautery`), threshold padrão **0.5**, detecta `excessive_bleeding` e `prolonged_bleeding`. O schema JSON é diferente e só o `SurgicalReportGenerator` consome esse formato.
- **Threshold default difere entre componentes:** `web` → 0.30, `src/inference/processor.py` → 0.50, Terraform inference var → 0.30, scripts de validação → 0.3 (via `--conf`).
- **README desatualizado em alguns detalhes:** menciona apenas `src/data/prepare_cholecseg8k.py`, `src/inference/processor.py`, `src/reports/generator.py` mas omite `src/demo/run_demo.py`; não cita `surgical-training/`, `anotacoes-gynsurg/`, `tests/`, `thoughts/`. O Terraform da raiz é referenciado com `g4dn.xlarge`, mas o default no módulo é `t3.xlarge` (comentário marca como temporário); env do training tem comentário antigo `p3.2xlarge ~$3.06/hora`.
- **Repo GitHub hard-coded no Terraform:** `user_data` em `terraform/modules/training/main.tf:178` clona `https://github.com/Zagari/surgical-video-ai.git`. Forks precisam editar essa URL.
- **Key SSH hard-coded:** `var.key_name = "castellabate-key"` em `terraform/environments/training/main.tf:55`.
- **SG do training expõe SSH para `0.0.0.0/0`** (`terraform/modules/training/main.tf:79`).
- **`tests/` só tem `__init__.py`** — nenhum teste implementado, embora pytest esteja nas deps.
- **`docs/CHECKPOINT-SERVIDOR.md` e `docs/plano-implementacao-video-analysis.md` estão gitignored** (`.gitignore:138-139`): documentação local-only. `thoughts/` inteira também é ignorada (`.gitignore:137`).
- **Job storage in-memory:** restart do container limpa todos os jobs em andamento (`video.py:50`).
- **`/api/info/*` são dicionários estáticos:** valores (versão, métricas) não são lidos do modelo nem de S3 — refletem o estado documentado no momento do código.
- **Pseudo-bbox de fine-tuning:** clips bleeding viram apenas uma bbox `(0.5, 0.5, 0.8, 0.8)` classe 1 (`annotation.py:267`). Não há localização real do sangramento — o fine-tuning trata o frame inteiro como contendo blood ou não.
- **CORS aberto:** `allow_origins=["*"]` em `web/app/main.py:23`.
- **Pacote SageMaker (`model.tar.gz`) referenciado em terraform/modules/inference/main.tf:128 mas não há script no repo que crie esse tarball** — comentário no arquivo descreve o passo manual necessário.
- **`opencv-python` vs `opencv-python-headless`:** raiz usa a versão completa (com GUI), `web/requirements.txt` usa headless (correto para container).
- **`yt-dlp` no compose web:** o Dockerfile instala via `pip install yt-dlp` e também instala `nodejs/npm` (não usado diretamente pelo Python — comentário sugere ser para `yt-dlp`).
- **Git remoto:** repositório com pacote git levemente danificado localmente (erro de pack file em `git log --since=...`); usar `--no-walk` ou `git log --oneline` para evitar.
- **`surgical-training/results/`** ainda contém `surgical_detection_v3_finetuned/` e `surgical_detection_v4_finetuned/`, mas os pesos `*.pt` estão gitignored — só as estruturas e arquivos auxiliares ficam versionados (ex.: `args.yaml`, plots).

## Referências

- README principal: [`../README.md`](../README.md)
- README web: [`../web/README.md`](../web/README.md)
- Repositório: https://github.com/Zagari/surgical-video-ai (URL referenciada em `info.py` e Terraform)
- Datasets:
  - CholecSeg8k (Kaggle) — treino
  - GynSurg Action Recognition (Medical University of Vienna / Toronto) — validação e fine-tuning (CC BY-NC-ND 4.0)
- Documentos locais (gitignored): `docs/CHECKPOINT-SERVIDOR.md`, `docs/plano-implementacao-video-analysis.md`, `thoughts/`
- Relatório técnico mencionado no README: `docs/relatorio_.pdf` (não presente no repo no commit atual)

---

*Este documento é gerado automaticamente. Rodar `/asp-analyze-codebase` novamente atualiza apenas o que mudou (delta). Para recriar do zero, use `/asp-analyze-codebase --recreate`.*
