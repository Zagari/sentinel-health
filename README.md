# Sentinel Health

> Plataforma multimodal de monitoramento contínuo da saúde da mulher.
> **FIAP Tech Challenge — Fase 4** | Pós-Graduação em Inteligência Artificial para Devs

🚧 **Em construção.** Esta é a versão inicial; o README completo virá após a Phase 6 do plano de implementação.

## Módulos

- [Sentinel Surgical](./modules/surgical/) — detecção de sangramento anômalo em cirurgias ginecológicas (YOLOv8m fine-tuned, 91.72% det / 13.44% FP).
- [Sentinel Insight](./modules/insight/) — análise emocional multimodal de consultas (face via DeepFace + voz via Whisper + LLM via GPT-5).

## Documentação

Em construção. Estará em:

- `docs/CHALLENGE_COVERAGE.md` — matriz item-a-item da cobertura do desafio.
- `docs/ARCHITECTURE.md` — diagrama e descrição da hospedagem unificada.
- `docs/DEMO_SCRIPT.md` — roteiro do vídeo demo de 15 min.
- `landing/coverage.html` — versão interativa da matriz de cobertura.
- `landing/presentation/` — slides para a apresentação demo.
- `relatorio/` — relatório técnico LaTeX.

## Deploy

Ver [`deploy/README.md`](./deploy/README.md) quando disponível.

## Equipe

- Adriana Martins de Souza — RM 368050
- Diego Oliveira da Silva — RM 367964
- Eduardo Nicola F. Zagari — RM 368021
- Renan de Assis Torres — RM 368513

## Plano de implementação

O plano detalhado de construção desta plataforma está em [`../thoughts/shared/plans/2026-05-16-sentinel-health-platform.md`](../thoughts/shared/plans/2026-05-16-sentinel-health-platform.md).
