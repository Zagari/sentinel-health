# Sentinel Health

> Plataforma multimodal de IA para **monitoramento contínuo da saúde da mulher** —
> análise de vídeo cirúrgico, voz, expressões faciais e texto para detecção precoce
> de riscos materno-ginecológicos, violência doméstica e bem-estar psicológico.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Model: HuggingFace](https://img.shields.io/badge/🤗-Model-yellow)](https://huggingface.co/zagari/sentinel-surgical-yolov8m-bleeding)
[![FIAP Tech Challenge](https://img.shields.io/badge/FIAP-Tech_Challenge_Fase_4-ed1c24)](https://github.com/Zagari/sentinel-health)

> ⚠️ **Aviso acadêmico.** Sentinel Health é um **protótipo desenvolvido para fins acadêmicos**
> como parte do Tech Challenge da Fase 4 do curso de Pós-Graduação em Inteligência Artificial
> para Devs da FIAP. **Não é um dispositivo médico** e **não deve ser usado para decisões
> clínicas, diagnóstico, triagem ou suporte a vítimas em situação real.** Os modelos foram
> treinados em datasets de pesquisa com vieses conhecidos. Qualquer interpretação dos
> resultados deve ser feita por profissionais qualificados.

---

## Visão geral

Sentinel Health agrega **dois módulos especialistas** numa plataforma unificada com landing
institucional, página interativa de cobertura do desafio, e infraestrutura de deploy
local + AWS via Terraform:

| Módulo | Foco | Tecnologias principais |
|---|---|---|
| [**Sentinel Surgical**](./modules/surgical/) | Detecção de sangramento anômalo em cirurgias ginecológicas | YOLOv8m fine-tuned · OpenCV · FastAPI · AWS S3 |
| [**Sentinel Insight**](./modules/insight/) | Análise emocional multimodal de consultas (face + voz + LLM) | DeepFace · Whisper-1 · GPT-5.4-nano · Streamlit |

## Cobertura do desafio

Mapeamento item-a-item da proposta do PDF do Tech Challenge:

| Seção | Atendidos | Roadmap | Total |
|---|:---:|:---:|:---:|
| Funcionalidades (mín. 2) | **3** | 1 | 4 |
| Objetivos (mín. 3) | **5** | 0 | 5 |
| Req. 1 — Vídeo | **6** | 1 | 7 |
| Req. 2 — Áudio | **4** | 0 | 4 |
| Entregáveis | **3** | 0 | 3 |
| **Total** | **21** | **2** | **23** |

**21 itens atendidos.** Os 2 em roadmap (Sentinel Motion e Sentinel VitalSigns) estão declarados explicitamente como evolução futura.

📊 **Matriz detalhada:** [`docs/CHALLENGE_COVERAGE.md`](./docs/CHALLENGE_COVERAGE.md) (markdown) ou
[`landing/coverage.html`](./landing/coverage.html) (interativa com filtros).

## Quick start

### Local (Mac · Linux · Windows com Docker Desktop)

```bash
git clone https://github.com/Zagari/sentinel-health.git
cd sentinel-health

# 1. Configurar a key da OpenAI no Insight
cp modules/insight/emotion-recognizer/.env.example \
   modules/insight/emotion-recognizer/.env
$EDITOR modules/insight/emotion-recognizer/.env   # cola sua sk-...

# 2. (Opcional) Se você tem múltiplos profiles AWS sem [default]:
export AWS_PROFILE=<seu-profile>

# 3. Subir os 4 containers
cd deploy
docker compose up -d

# 4. Aguardar ~30s no primeiro boot (entrypoint do surgical baixa
#    best.pt do Hugging Face Hub) e abrir no browser:
open http://localhost/
```

Endpoints disponíveis:

| URL | O que serve |
|---|---|
| `http://localhost/` | Landing institucional |
| `http://localhost/coverage.html` | Matriz interativa de cobertura |
| `http://localhost/surgical/` | UI do Sentinel Surgical |
| `http://localhost/insight/` | UI do Sentinel Insight |

### AWS via Terraform (deploy demonstrativo)

```bash
cd terraform/environments/demo
AWS_PROFILE=<seu-profile> terraform init
AWS_PROFILE=<seu-profile> terraform apply
# Custo estimado: ~$0.04/h (t3.medium). Lembre-se de `terraform destroy` depois.
```

Detalhes em [`terraform/README.md`](./terraform/README.md).

### Behind reverse proxy do host (nginx-sandwich)

```bash
docker compose -f docker-compose.yml -f docker-compose.behind-proxy.yml up -d
# escuta em 127.0.0.1:8100 — para usar atrás de outro nginx no host
sudo cp ../deploy/nginx/host-snippet.conf /etc/nginx/conf.d/sentinel.conf
sudo nginx -t && sudo systemctl reload nginx
```

## Modelo treinado

O modelo de produção (**v3_finetuned**: 91.72% detecção / 13.44% FP) está
publicado publicamente no **Hugging Face Hub** com model card profissional:

🤗 **[zagari/sentinel-surgical-yolov8m-bleeding](https://huggingface.co/zagari/sentinel-surgical-yolov8m-bleeding)**

O container do Surgical **baixa automaticamente** no 1º boot — você não precisa fazer nada.

## Roadmap

Itens identificados como evolução futura (declarados na landing e no relatório técnico):

| Módulo | Descrição |
|---|---|
| 🏃‍♀️ **Sentinel Motion** | Análise de fisioterapia pós-parto via pose estimation (MediaPipe / MoveNet) |
| 📊 **Sentinel VitalSigns** | Detecção de anomalias em sinais vitais (pressão gestacional, batimentos fetais) |
| ⚡ **Sentinel Realtime** | Streaming síncrono ao vivo (hoje: near real-time com latência ≤1 min) |
| 🤲 **Sentinel Pose** | Linguagem corporal indicativa de abuso, complementando análise face+voz |

## Estrutura do repositório

```
sentinel-health/
├── README.md                       # este arquivo
├── LICENSE                         # MIT + Academic Use Notice
├── docs/                           # documentação consolidada
│   ├── CHALLENGE_COVERAGE.md       # matriz item-a-item do desafio
│   ├── ARCHITECTURE.md             # topologia, fluxos, decisões
│   └── DEMO_SCRIPT.md              # roteiro do vídeo de 15 min
├── landing/                        # site institucional + cobertura interativa
│   ├── index.html
│   ├── coverage.html
│   ├── assets/
│   │   ├── coverage-data.json      # FONTE CANÔNICA da matriz
│   │   ├── css/style.css
│   │   └── js/coverage.js
│   └── Dockerfile
├── modules/
│   ├── surgical/                   # Sentinel Surgical (YOLOv8m)
│   │   ├── web/                    # FastAPI + Dockerfile + entrypoint.sh
│   │   ├── src/                    # CLI pipeline alternativa
│   │   ├── scripts/                # treino, validação, ops AWS
│   │   ├── terraform/              # IaC do projeto surgical original (legado)
│   │   └── docs/CODEBASE_ANALYSIS.md
│   └── insight/                    # Sentinel Insight (DeepFace + Whisper + GPT)
│       ├── emotion-recognizer/     # código Streamlit + análise multimodal
│       ├── Dockerfile
│       └── docs/CODEBASE_ANALYSIS.md
├── deploy/                         # hospedagem unificada
│   ├── docker-compose.yml          # 4 containers (nginx + 3 módulos)
│   ├── docker-compose.behind-proxy.yml  # override pra reverse proxy do host
│   ├── nginx/sentinel.conf         # routing interno
│   ├── nginx/host-snippet.conf     # snippet pro nginx do host
│   └── README.md
├── terraform/                      # IaC AWS para Sentinel Health
│   ├── modules/storage/            # S3 buckets (assets + models)
│   ├── modules/runtime/            # EC2 t3.medium + IAM + SG + EIP
│   ├── environments/demo/          # composição
│   └── README.md
└── relatorio/                      # relatório técnico LaTeX (Phase 8)
    └── (em construção)
```

## Documentação

| Documento | Conteúdo |
|---|---|
| [`docs/CHALLENGE_COVERAGE.md`](./docs/CHALLENGE_COVERAGE.md) | Matriz item-a-item da cobertura do desafio (sincronizada com [`landing/assets/coverage-data.json`](./landing/assets/coverage-data.json)) |
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | Topologia, fluxos de dados, decisões arquiteturais, integrações cloud |
| [`docs/DEMO_SCRIPT.md`](./docs/DEMO_SCRIPT.md) | Roteiro completo do vídeo demo de 15 min |
| [`deploy/README.md`](./deploy/README.md) | Como subir local · variante atrás de reverse proxy · troubleshooting |
| [`terraform/README.md`](./terraform/README.md) | Deploy AWS via Terraform · custos · workflow apply→demo→destroy |
| [`modules/surgical/docs/CODEBASE_ANALYSIS.md`](./modules/surgical/docs/CODEBASE_ANALYSIS.md) | Análise técnica detalhada do código do Surgical |
| [`modules/insight/docs/CODEBASE_ANALYSIS.md`](./modules/insight/docs/CODEBASE_ANALYSIS.md) | Análise técnica detalhada do código do Insight |

## Equipe — Grupo Sala 14

- **Adriana Martins de Souza** — RM 368050
- **Diego Oliveira da Silva** — RM 367964
- **Eduardo Nicola F. Zagari** — RM 368021
- **Renan de Assis Torres** — RM 368513

FIAP — Faculdade de Informática e Administração Paulista
Pós-Graduação em Inteligência Artificial para Devs
Tech Challenge — Fase 4 · 2026-05

## Licença

[MIT](./LICENSE) — com [ACADEMIC USE NOTICE](./LICENSE) anexo.

Sentinel Health é distribuído para fins de pesquisa e demonstração acadêmica. Os termos
da MIT autorizam uso, modificação e distribuição amplos, mas o **Aviso de Uso Acadêmico**
no arquivo de licença esclarece que **não é um dispositivo médico** e que **não deve ser
usado em decisões clínicas reais**.
