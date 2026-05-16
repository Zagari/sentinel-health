<!-- .slide: class="cover" -->

<span class="tag">FIAP Tech Challenge · Fase 4</span>

# Sentinel Health

### Plataforma multimodal de IA para monitoramento contínuo da saúde da mulher

<div class="team">
  Adriana M. Souza · Diego O. Silva · Eduardo N. F. Zagari · Renan A. Torres<br>
  <strong>Grupo Sala 14</strong> · Pós-Graduação em IA para Devs · FIAP · 2026
</div>

Note:
Saudação inicial (~10s). Apresentar o grupo e o título. Click pro próximo slide quando começar a contextualizar.

---

## O Problema

> *"Com a IA integrada aos processos médicos, a rede hospitalar deseja
> monitorar continuamente as pacientes por meio de dados multimodais
> — áudio, vídeo e texto — para identificar sinais precoces de risco
> específicos da saúde e segurança feminina."*

— FIAP Tech Challenge, Fase 4

<div style="margin-top: 1.5em; font-size: 0.7em; color: #666;">
Saúde da mulher = saúde materna · risco cirúrgico · violência doméstica · bem-estar psicológico
</div>

Note:
30s. Citar o trecho exato do PDF. Reforçar que escolhemos atender 3 das 4 funcionalidades e os 5 objetivos.

---

## A Proposta — Sentinel Health

Plataforma com **2 módulos especialistas** orquestrados:

<div class="metrics">
  <div class="metric blue">
    <div class="num">Surgical</div>
    <div class="lbl">YOLOv8m · OpenCV · FastAPI</div>
  </div>
  <div class="metric">
    <div class="num">Insight</div>
    <div class="lbl">DeepFace · Whisper · GPT</div>
  </div>
  <div class="metric">
    <div class="num">Landing</div>
    <div class="lbl">Coverage interativa</div>
  </div>
</div>

Atrás de **nginx reverse proxy**, deployable via `docker compose` ou Terraform na AWS.

Note:
30s. Explica que é uma plataforma multi-módulo, cada um com foco específico. A landing e a página de cobertura interativa fazem parte do entregável.

---

## Cobertura do Desafio

<div class="coverage-rows">
  <div class="row ok-section">
    <div class="label">Funcionalidades</div>
    <div class="met">3</div>
    <div class="min">mín. 2 ✓</div>
    <div class="road">+1 roadmap</div>
  </div>
  <div class="row ok-section">
    <div class="label">Objetivos</div>
    <div class="met">5</div>
    <div class="min">mín. 3 ✓</div>
    <div class="road">—</div>
  </div>
  <div class="row ok-section">
    <div class="label">Req. 1 — Análise de Vídeo</div>
    <div class="met">6</div>
    <div class="min">de 7</div>
    <div class="road">+1 roadmap</div>
  </div>
  <div class="row ok-section">
    <div class="label">Req. 2 — Análise de Áudio</div>
    <div class="met">4</div>
    <div class="min">de 4 ✓</div>
    <div class="road">—</div>
  </div>
  <div class="row ok-section">
    <div class="label">Entregáveis</div>
    <div class="met">3</div>
    <div class="min">de 3 ✓</div>
    <div class="road">—</div>
  </div>
</div>

<div style="text-align: center; margin-top: 1em; font-size: 0.85em;">
  <strong>21 itens atendidos · 2 em roadmap declarado · /coverage.html</strong>
</div>

Note:
60s — slide-chave. Falar: "Excedemos os mínimos nas duas seções com opção (funcionalidades e objetivos). Cobrimos 100% do requisito de áudio. No vídeo, 6 de 7 atendidos com 1 deixado em roadmap (fisioterapia, que requer pose estimation). Os entregáveis estão completos. Página coverage.html tem a matriz interativa com filtros."

---

## Arquitetura

```
┌──────────────────────────────────────────────────────┐
│  Host (qualquer Docker — Mac · VPS · EC2)            │
│                                                      │
│   nginx → /              → landing                   │
│        → /surgical/      → FastAPI (YOLOv8m)         │
│        → /insight/       → Streamlit (DeepFace+LLM)  │
│        → /coverage.html  → matriz interativa         │
│                                                      │
└────────┬──────────────────────────────┬──────────────┘
         │                              │
         ▼                              ▼
  AWS S3 + EC2 + SSM           OpenAI API + 🤗 HF Hub
  (deploy Terraform IaC)       (LLM + Whisper + model)
```

<div style="font-size: 0.65em; margin-top: 1em; color: #666;">
Variantes: <strong>local</strong> · <strong>behind reverse proxy do host</strong> · <strong>AWS via Terraform</strong>
</div>

Note:
30s. Mostrar o diagrama. Destacar: roda em qualquer Docker host, IaC pronto pra AWS, integra 2 clouds (AWS para infra + OpenAI para LLM + HF Hub para distribuição do modelo).

---

<!-- .slide: class="surgical" -->

## Sentinel Surgical

Detecção de **sangramento anômalo em cirurgias ginecológicas**.

<div class="metrics">
  <div class="metric blue">
    <div class="num">91.72%</div>
    <div class="lbl">Taxa de detecção</div>
  </div>
  <div class="metric blue">
    <div class="num">13.44%</div>
    <div class="lbl">Falsos positivos</div>
  </div>
  <div class="metric blue">
    <div class="num">YOLOv8m</div>
    <div class="lbl">v3_finetuned</div>
  </div>
</div>

**Pipeline de treino em 3 fases:** CholecSeg8k (baseline) → class weights → fine-tuning com 1020 frames GynSurg.

Note:
30s. Explicar que escolhemos sangramento anômalo (item 3 das 4 opções de YOLO listadas no PDF). 3 fases de treino cross-dataset. Modelo público no HF Hub.

---

<!-- .slide: class="live-demo-slide" -->

## 🎬 Live Demo · Surgical

<div class="big-arrow">↓</div>

### http://&lt;servidor&gt;/surgical/

<div class="hint">
  Tab para a UI · upload de clip GynSurg da galeria · análise YOLO em ~30s<br>
  Mostrar JSON exportável + vídeo anotado com bboxes
</div>

Note:
4 minutos de demo ao vivo. Alt-tab pra UI do Surgical. Mostrar a galeria S3 (com source: s3 ou local), escolher um clip de bleeding, processar (~30s), mostrar JSON + vídeo anotado. Voltar pra apresentação clicando aqui.

---

## Surgical · Evolução do modelo

| Versão | Treino | Detecção | FP |
|---|---|---:|---:|
| v1 (baseline) | CholecSeg8k, 100 ep | 5.41% | 76.11% |
| v2 (class weight) | + cls=3.0 | 12.14% | 46.89% |
| **v3 (fine-tuned)** | **+ 1020 frames GynSurg** | **91.72%** ✅ | **13.44%** ✅ |

### Threshold sweep (v3_finetuned)

| Threshold | Detecção | FP |
|:---:|---:|---:|
| 0.10 | 94.48% | 19.33% |
| 0.20 | 93.05% | 14.78% |
| **0.30** (default) | **91.72%** | **13.44%** |
| 0.50 | 88.96% | 9.33% |
| 0.70 | 85.76% | 4.89% |

Note:
30s. Mostrar a evolução. Threshold 0.30 escolhido como balanço — em contexto cirúrgico, mais FP é menos pior que perder bleeding real.

---

## Sentinel Insight

Análise emocional multimodal de consultas.

<div class="metrics">
  <div class="metric">
    <div class="num">Face</div>
    <div class="lbl">DeepFace · frame-a-frame</div>
  </div>
  <div class="metric">
    <div class="num">Voz</div>
    <div class="lbl">Whisper-1 · STT</div>
  </div>
  <div class="metric">
    <div class="num">LLM</div>
    <div class="lbl">gpt-5.4-nano</div>
  </div>
</div>

Cobre **100% do Requisito de Áudio:** consultas ginecológicas · pré-natal · pós-parto · vítimas de violência.

Fallback **keyword-based** (27 regex com pesos 1/2/3) quando LLM indisponível.

Note:
30s. Insight cobre face + voz + texto. 4 casos de áudio do PDF: ginecológicas, pré-natal (ansiedade), pós-parto (depressão), violência. Fallback rule-based garante degradação graciosa.

---

<!-- .slide: class="live-demo-slide" -->

## 🎬 Live Demo · Insight

<div class="big-arrow">↓</div>

### http://&lt;servidor&gt;/insight/

<div class="hint">
  Tab para a UI Streamlit · modo "Audio Only"<br>
  Upload de WAV/MP3 · transcrição via Whisper · análise LLM<br>
  Mostrar sentiment + risk_level + signals + recommended_action
</div>

Note:
4 minutos de demo. Alt-tab pra Streamlit. Audio Only mode. Upload áudio (use texto que mencione violência/ansiedade pra ativar o detector). Mostrar as 4 métricas no topo, signals, recommended_action. Voltar.

---

## Insight · O que detectamos

Exemplo de output JSON de uma análise de áudio:

```json
{
  "sentiment": "negative",
  "risk_level": "high",
  "score": 8,
  "detected_signals": ["fear", "crying", "physical harm"],
  "keywords": ["scared", "hurt", "help"],
  "domestic violence signals": "strong indicators",
  "recommended_action": "Review with qualified professional",
  "source": "openai_llm"
}
```

→ Em produção, este JSON dispararia **alerta na EHR** e na escala da equipe especializada.

Note:
30s. Exemplo real do que o Insight devolve. Em produção, plugado num EHR/sistema hospitalar, esses campos viram alerta acionável. Fluxo final do alerta à equipe médica.

---

## Multi-cloud

<div class="metrics">
  <div class="metric blue">
    <div class="num">AWS</div>
    <div class="lbl">S3 · EC2 · SSM · SageMaker · Terraform</div>
  </div>
  <div class="metric">
    <div class="num">OpenAI</div>
    <div class="lbl">GPT-5.4-nano · Whisper-1</div>
  </div>
  <div class="metric">
    <div class="num">🤗 HF Hub</div>
    <div class="lbl">Modelo público + Model Card</div>
  </div>
</div>

🤗 **`huggingface.co/zagari/sentinel-surgical-yolov8m-bleeding`**

Container baixa o modelo do HF no 1º boot (via `entrypoint.sh`) — sem credenciais, sem `aws s3 cp`, sem `git lfs`.

Note:
30s. AWS para infra (IaC com Terraform), OpenAI para LLM/STT, HF Hub para distribuir o modelo publicamente com model card profissional. Tudo automatizado — o container baixa o modelo sozinho.

---

## Privacidade & LGPD

- 🔒 **Volumes locais** para uploads/resultados — dados sensíveis fora da nuvem default
- 🔐 **TLS** quando atrás de nginx do host (snippet pronto no repo)
- 🔑 **SSM Parameter Store** para `OPENAI_API_KEY` — secret nunca no Terraform state
- 🚫 **SSH desabilitado** no SG do EC2 — acesso administrativo só via SSM Session Manager (IAM + CloudTrail audit)
- 🪣 **S3 buckets bloqueados** (`public_access_block` em todas as dimensões)
- 📋 **Sem persistência centralizada** de dados de paciente — design para integração futura via EHR API

Note:
30s. Sabemos que estamos lidando com dados sensíveis. Resumir as 6 práticas — não vai dar tempo pra detalhar cada uma, mas listar dá a impressão de seriedade.

---

## Roadmap

<div class="roadmap-grid">
  <div class="item">
    <div class="emoji">🏃‍♀️</div>
    <div class="title">Sentinel Motion</div>
    <div class="desc">Fisioterapia pós-parto via pose estimation (MediaPipe / MoveNet)</div>
  </div>
  <div class="item">
    <div class="emoji">📊</div>
    <div class="title">Sentinel VitalSigns</div>
    <div class="desc">Sinais vitais: pressão gestacional, batimentos fetais</div>
  </div>
  <div class="item">
    <div class="emoji">⚡</div>
    <div class="title">Sentinel Realtime</div>
    <div class="desc">Streaming síncrono ao vivo (hoje: near real-time ≤1 min)</div>
  </div>
  <div class="item">
    <div class="emoji">🤲</div>
    <div class="title">Sentinel Pose</div>
    <div class="desc">Linguagem corporal indicativa de abuso, complementando face+voz</div>
  </div>
</div>

Note:
30s. Quatro frentes declaradas explicitamente como evolução. Transparência: 2 estão na matriz como 🚀 roadmap, 2 são extensões propostas.

---

<!-- .slide: class="cover" -->

# Obrigado!

### 🔗 github.com/Zagari/sentinel-health

### 🤗 huggingface.co/zagari/sentinel-surgical-yolov8m-bleeding

<div class="disclaimer-box">
⚠️ <strong>Aviso acadêmico.</strong>
Sentinel Health é um <strong>protótipo desenvolvido para fins acadêmicos</strong> como parte do Tech Challenge da Fase 4 do curso de Pós-Graduação em IA para Devs da FIAP.
<strong>Não é um dispositivo médico.</strong> Não deve ser usado para decisões clínicas, diagnóstico, triagem ou suporte a vítimas em situação real.
</div>

<div class="team">
  Adriana M. Souza · Diego O. Silva · Eduardo N. F. Zagari · Renan A. Torres<br>
  <strong>Grupo Sala 14</strong> · FIAP · 2026
</div>

Note:
30s de fechamento. Repo URL, modelo no HF, disclaimer canônico. Voltar pro browser pra screenshot final ou parar gravação.
