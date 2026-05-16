# Cobertura do Desafio — FIAP Tech Challenge Fase 4

Mapeamento item-a-item da proposta do desafio (PDF `POSTECH - IADT - Tech Challenge - Fase 4.pdf`) pela plataforma Sentinel Health.

> **Versão interativa com filtros:** [`landing/coverage.html`](../landing/coverage.html) (renderiza esta matriz em runtime a partir do JSON canônico `landing/assets/coverage-data.json`).

## Resumo

| Métrica | Valor | % |
|---|---:|---:|
| ✅ Itens atendidos | **20** | 80% |
| ⚠️ Itens parciais | 3 | 12% |
| 🚀 Itens em roadmap | 2 | 8% |
| **Total da proposta** | **25** | 100% |

**Cobertura efetiva:** 23 dos 25 itens (20 plenos + 3 parciais).

## Legenda de status

| Símbolo | Significado |
|:---:|---|
| ✅ | **Atendido.** Requisito implementado e funcional. |
| ⚠️ | **Parcial.** Requisito parcialmente cumprido com lacunas declaradas. |
| 🚀 | **Roadmap.** Fora do escopo da Fase 4; documentado como evolução futura. |

## Legenda de módulos

| Badge | Módulo | Diretório |
|---|---|---|
| **Surgical** | Sentinel Surgical (YOLOv8m + FastAPI) | [`modules/surgical/`](../modules/surgical/) |
| **Insight** | Sentinel Insight (DeepFace + Whisper + GPT) | [`modules/insight/`](../modules/insight/) |

---

## 1. Funcionalidades

> PDF: *"escolha pelo menos duas opções"* — escolhemos **3 de 4**.
>
> **Atendidas:** 3 · **Mínimo PDF:** 2 · **Em roadmap:** 1.

| ID | Status | Requisito | Módulo(s) | Evidência |
|---|:---:|---|---|---|
| `func-video` | ✅ | Analisar vídeos de cirurgias / consultas / partos / fisioterapia | Surgical · Insight | Funcionalidade escolhida (PDF: "pelo menos 2 de 4"). Surgical cobre cirurgias ginecológicas; Insight cobre consultas via DeepFace. Partos e fisioterapia listados como sub-exemplos no PDF — tratados como evolução em Sentinel Motion (roadmap). |
| `func-audio` | ✅ | Processar gravações de voz (depressão, ansiedade, violência doméstica, fadiga hormonal) | Insight | Insight transcreve via Whisper-1 + análise emocional via GPT-5.4-nano + fallback keyword com 27 padrões ponderados. |
| `func-vitals` | 🚀 | Detectar anomalias em sinais vitais (pressão em gestantes, batimentos fetais) | — | Fora do escopo declarado. Documentado como **Sentinel VitalSigns** na roadmap pública. |
| `func-cloud` | ✅ | Integrar com serviços gerenciados em nuvem | Surgical · Insight | Multi-cloud: AWS (S3 + EC2 via Terraform + SageMaker opcional + SSM) para o Surgical; OpenAI API para o Insight; Hugging Face Hub hospeda o modelo YOLOv8m (entrypoint do container faz pull automático). |

## 2. Objetivos

> PDF: *"escolha pelo menos três das opções abaixo"* — escolhemos **5 de 5** (cobertura total).
>
> **Atendidos:** 5 · **Mínimo PDF:** 3 · **Em roadmap:** 0.

| ID | Status | Requisito | Módulo(s) | Evidência |
|---|:---:|---|---|---|
| `obj-materno` | ✅ | Detectar precocemente riscos em saúde materna e ginecológica | Surgical | YOLOv8m v3_finetuned: 91.72% de detecção de sangramento em cirurgias ginecológicas, 13.44% FP @ threshold 0.30. |
| `obj-violencia` | ✅ | Identificar sinais de violência doméstica ou abuso | Insight | Insight: prompt LLM dedicado retornando 'domestic violence signals' + 27 keywords (kill, threat, abuse, hurt me, hit me, ...). |
| `obj-psico` | ✅ | Monitorar bem-estar psicológico feminino | Insight | Insight: sentiment (positivo/neutro/negativo), risk_level (low/moderate/high), distress score 0-10, signals (anxiety, depression, sadness, etc). |
| `obj-cloud` | ✅ | Utilizar serviços em nuvem para ampliar capacidade | Surgical · Insight | Multi-cloud: AWS (S3 + EC2 + SageMaker + SSM Parameter Store) para deploy do Surgical; OpenAI API para Insight (LLM + Whisper); Hugging Face Hub para distribuição pública do modelo YOLOv8m com model card profissional. |
| `obj-realtime` | ✅ | Aplicar técnicas de detecção de anomalias em tempo real | Surgical · Insight | Objetivo escolhido (PDF: "pelo menos 3 de 5"). Aplicamos detecção de anomalias com latência fim-a-fim ≤ 1 min (near real-time) — caminho LLM + fallback keyword para áudio, YOLOv8m frame-a-frame para vídeo. Streaming síncrono sub-segundo está em Sentinel Realtime (roadmap), mas o objetivo "aplicar a técnica" está cumprido. |

## 3. Requisito Obrigatório 1 — Análise de Vídeo

> 6 atendidos · 2 parciais · 1 em roadmap.

| ID | Status | Requisito | Módulo(s) | Evidência |
|---|:---:|---|---|---|
| `vid-cirurgias` | ✅ | Cirurgias: detecção de complicações ou sangramento anômalo | Surgical | YOLOv8m fine-tuned com CholecSeg8k + GynSurg. Threshold 0.30, 91.72% detecção. |
| `vid-consultas` | ✅ | Consultas: sinais não-verbais de desconforto ou medo | Insight | DeepFace classifica fear / sad / disgust frame-a-frame; gráfico de emoção sobre o tempo. |
| `vid-fisio` | 🚀 | Fisioterapia: análise de movimentos e recuperação | — | Roadmap: **Sentinel Motion** via pose estimation (MediaPipe / MoveNet). |
| `vid-violencia` | ⚠️ | Triagem de violência: linguagem corporal indicativa de abuso | Insight | Insight cobre face + voz; pose corporal estimation ainda em roadmap (Sentinel Pose). |
| `vid-yolo` | ✅ | YOLOv8 customizado (1 dos itens da lista do PDF) | Surgical | Item escolhido: 'Sangramento anômalo durante procedimentos'. YOLOv8m v3_finetuned, 91.72% det. |
| `vid-rel-obstetricos` | ⚠️ | Relatórios — desvios em procedimentos obstétricos | Surgical | Surgical registra anomalias temporais (excessive/prolonged bleeding) no pipeline CLI; o domínio é ginecológico geral, sem distinguir 'obstétrico'. |
| `vid-rel-complicacoes` | ✅ | Relatórios — complicações em cirurgias ginecológicas | Surgical | Relatório JSON via API + geração PDF (`SurgicalReportGenerator`) com severidade alta / média / baixa. |
| `vid-rel-desconforto` | ✅ | Relatórios — indicadores visuais de desconforto psicológico | Insight | Gráfico de emoção sobre o tempo + tabela detalhada + summary GPT-5.4-nano multimodal. |
| `vid-rel-violencia` | ✅ | Relatórios — alertas para violência doméstica | Insight | JSON exportado contém `risk_level`, `domestic violence signals` e `recommended_action`. Pronto para integração com EHR. |

## 4. Requisito Obrigatório 2 — Análise de Áudio

> 4 atendidos (cobertura total).

| ID | Status | Requisito | Módulo(s) | Evidência |
|---|:---:|---|---|---|
| `aud-ginecol` | ✅ | Consultas ginecológicas: tom de voz, hesitação | Insight | Whisper-1 transcreve com timestamps; GPT-5.4-nano extrai sentiment + summary + detected signals. |
| `aud-prenatal` | ✅ | Acompanhamento pré-natal: sinais de ansiedade gestacional | Insight | Keywords 'anxiety' / 'panic' / 'worry' (peso 2 cada) + LLM contextualiza no domínio gestacional via prompt. |
| `aud-posparto` | ✅ | Consultas pós-parto: detecção precoce de depressão pós-parto | Insight | Keyword 'depress' (peso 2) no fallback + LLM contextualiza para depressão pós-parto via prompt dedicado. |
| `aud-violencia` | ✅ | Atendimento a vítimas de violência: padrões vocais de trauma | Insight | Prompt LLM dedicado retornando `risk_level`, `score` 0-10, `domestic violence signals` e `recommended_action`. |

## 5. Entregáveis

> 2 atendidos · 1 parcial (vídeo demo pendente de gravação).

| ID | Status | Requisito | Módulo(s) | Evidência |
|---|:---:|---|---|---|
| `del-repo` | ✅ | Repositório Git com código-fonte completo | Surgical · Insight | Monorepo [`github.com/Zagari/sentinel-health`](https://github.com/Zagari/sentinel-health) (público, MIT). Subtrees preservam histórico do `surgical-video-ai` e `emotion-detector`. |
| `del-relatorio` | ✅ | Relatório técnico (fluxo multimodal, modelos, resultados) | — | `relatorio/relatorio_tech_challenge.pdf` — LaTeX adaptado do template Fase 1 com cap01 incluindo esta matriz de cobertura. (Em conclusão na Phase 8 do plano de implementação.) |
| `del-video` | ⚠️ | Vídeo demo até 15 min (YouTube/Vimeo) | — | Roteiro completo em [`docs/DEMO_SCRIPT.md`](./DEMO_SCRIPT.md) + apresentação HTML em `landing/presentation/`. Gravação pendente. |

---

## Itens em roadmap (transparência)

Os 2 itens não atendidos estão documentados publicamente como evoluções futuras na landing institucional ([`landing/index.html` § "Roadmap"](../landing/index.html#roadmap)):

| Item | Módulo proposto | Tecnologia indicativa |
|---|---|---|
| `func-vitals` — sinais vitais (pressão gestacional, batimentos fetais) | **Sentinel VitalSigns** | Sensores IoT + séries temporais + threshold-based anomaly detection |
| `vid-fisio` — fisioterapia pós-parto (movimentos, recuperação) | **Sentinel Motion** | MediaPipe / MoveNet pose estimation + análise temporal de cinemática |

## Sincronização

Este documento é **derivado** de [`landing/assets/coverage-data.json`](../landing/assets/coverage-data.json), a **fonte canônica** da matriz. Qualquer mudança na cobertura começa por editar o JSON; este markdown é re-sincronizado manualmente.

Pontos de presença da mesma matriz na plataforma:

| Artefato | Como consome o JSON |
|---|---|
| `landing/coverage.html` | `fetch()` em runtime + filtros JS |
| `docs/CHALLENGE_COVERAGE.md` (este arquivo) | sincronização markdown manual |
| `landing/presentation/` (Phase 7) | slide dedicado importa snapshot do JSON |
| `relatorio/chapters/cap01_introducao.tex` (Phase 8) | tabela LaTeX manualmente sincronizada |
