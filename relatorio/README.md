# Relatório Técnico — Sentinel Health (Fase 4)

Este diretório contém apenas o **PDF final** do relatório técnico do Tech
Challenge da Fase 4.

## Arquivo

- **[`sentinel-health-relatorio-tecnico-fase4.pdf`](./sentinel-health-relatorio-tecnico-fase4.pdf)** — 47 páginas, ~557 KB

## Estrutura do relatório

| Capítulo | Conteúdo |
|---|---|
| 1 | Introdução — contexto, desafio, escopo |
| 2 | Fundamentação teórica — YOLOv8, DeepFace, Whisper, LLMs |
| 3 | Arquitetura multimodal — componentes, fluxos, deployment |
| 4 | Sentinel Surgical — datasets, pipeline 3-fases, métricas |
| 5 | Sentinel Insight — pipeline multimodal, 4 cenários, fallback |
| 6 | Infraestrutura, Cloud e LGPD |
| 7 | Resultados e discussão |
| 8 | Conclusões e roadmap |

## Fontes LaTeX

As fontes LaTeX (`.tex`, `.bib`, scripts de build, anotações originais
da Fase 1 preservadas) ficam no diretório `relatorio/` na **raiz do
trabalho de pós-graduação** (fora deste monorepo), para manter o
versionamento do Sentinel Health focado apenas no produto final.

## Geração

O PDF é gerado com `pdflatex` + `biber` + `makeglossaries` (TeX Live 2026
ou superior) a partir dos `.tex` no diretório de fontes. Build limpo,
sem warnings de quebra de coluna ou overfull/underfull box.
