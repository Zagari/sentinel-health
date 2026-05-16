# Apresentação — Sentinel Health

Slides reveal.js (zero build, CDN) para apoiar a gravação do vídeo demo de
15 minutos exigido pelo FIAP Tech Challenge Fase 4. 15 slides alinhados
**1:1 com o roteiro em [`../../docs/DEMO_SCRIPT.md`](../../docs/DEMO_SCRIPT.md)**.

## Estrutura

| Arquivo | O que é |
|---|---|
| `index.html` | Entry point com reveal.js v5 via CDN + estilos FIAP |
| `slides.md` | Conteúdo dos 15 slides em markdown (parsing pelo plugin `RevealMarkdown`) |
| `README.md` | Este arquivo |

## Como apresentar

### Via deploy unificado (recomendado)

A pasta `landing/` toda vira `/` no nginx do compose. Ou seja, basta:

```bash
cd ../../deploy
docker compose up -d
# abrir:
open http://localhost/presentation/
```

### Local, sem Docker

```bash
cd sentinel-health/landing
python3 -m http.server 8765
# abrir:
open http://localhost:8765/presentation/
```

> ⚠️ **Não funciona via `file://` direto** — reveal.js precisa de HTTP pra fazer `fetch()` no `slides.md`. Sempre via um servidor (Docker, python http.server, etc.).

## Controles de teclado

| Tecla | Ação |
|---|---|
| `→` / `Espaço` | Próximo slide |
| `←` | Slide anterior |
| `↑` / `↓` | Slides verticais (não usado nesta apresentação) |
| `Esc` ou `o` | Visão geral (overview) |
| `F` | Fullscreen |
| `S` | Speaker view (janela separada com notas) |
| `B` ou `.` | Tela preta (transições) |
| `?` | Lista completa de atalhos |

## Speaker notes

Cada slide em `slides.md` tem um bloco `Note:` no final com a fala/tempo
sugeridos. Acessa via tecla `S` durante a apresentação — abre uma janela
separada com:
- Slide atual
- Slide próximo (preview)
- Cronômetro
- Speaker notes

## Exportar como PDF

Adiciona `?print-pdf` ao URL e usa Chrome (não funciona bem no Safari):

```
http://localhost/presentation/?print-pdf
```

Depois `Cmd+P` → "Salvar como PDF". Resultado: 15 páginas A4 horizontal.

## Cronometragem (alinhada com `DEMO_SCRIPT.md`)

| # | Slide | Tempo | Bloco do roteiro |
|---|---|:---:|---|
| 1 | Capa | 00:00 – 00:30 | Abertura |
| 2 | O Problema | 00:30 – 01:00 | " |
| 3 | A Proposta | 01:00 – 01:30 | " |
| 4 | Cobertura | 01:30 – 02:30 | Cobertura |
| 5 | Arquitetura | 02:30 – 03:00 | Surgical |
| 6 | Surgical visão geral | 03:00 – 03:30 | " |
| 7 | **Live demo Surgical** | 03:30 – 07:30 | " |
| 8 | Surgical resultados | 07:30 – 08:00 | " |
| 9 | Insight visão geral | 08:00 – 08:30 | Insight |
| 10 | **Live demo Insight** | 08:30 – 12:30 | " |
| 11 | Insight JSON output | 12:30 – 13:00 | " |
| 12 | Multi-cloud | 13:00 – 13:30 | Multi-cloud + privacidade |
| 13 | Privacidade & LGPD | 13:30 – 14:00 | " |
| 14 | Roadmap | 14:00 – 14:30 | Fechamento |
| 15 | Fechamento + disclaimer | 14:30 – 15:00 | " |

**Total:** 15:00 mínimo de demonstração (cabe nos 15 min do PDF do desafio).

## Customizar

- **Conteúdo dos slides:** edita `slides.md`. Reveal recarrega no refresh.
- **Estilos visuais:** edita `<style>` no topo do `index.html` (paleta FIAP, layout das tabelas, métricas, etc).
- **Tema base reveal.js:** troca `theme/white.css` por `black`, `league`, `beige`, `night`, `serif`, `simple`, `sky`, `solarized` em `index.html` (linha do `<link rel="stylesheet">` com `id="theme"`).

## Pré-requisito de rede

Os 4 arquivos CSS/JS do reveal.js vêm de `cdn.jsdelivr.net`. Pra rodar
**offline** (sem internet durante a gravação):

```bash
cd presentation
mkdir -p vendor
curl -L https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reset.css -o vendor/reset.css
curl -L https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.css -o vendor/reveal.css
curl -L https://cdn.jsdelivr.net/npm/reveal.js@5/dist/theme/white.css -o vendor/white.css
curl -L https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.js -o vendor/reveal.js
curl -L https://cdn.jsdelivr.net/npm/reveal.js@5/plugin/markdown/markdown.js -o vendor/markdown.js
curl -L https://cdn.jsdelivr.net/npm/reveal.js@5/plugin/notes/notes.js -o vendor/notes.js
curl -L https://cdn.jsdelivr.net/npm/reveal.js@5/plugin/highlight/highlight.js -o vendor/highlight.js
curl -L https://cdn.jsdelivr.net/npm/reveal.js@5/plugin/highlight/monokai.css -o vendor/monokai.css
# depois substitui URLs no index.html por ./vendor/...
```

Pro demo da Fase 4, CDN está ok — assume-se internet ativa durante gravação.

## Pra gravar

1. Resolução de captura: **1920×1080** (Full HD)
2. Abrir em fullscreen (`F`)
3. Ferramenta: OBS, QuickTime, Loom, Camtasia
4. Microfone próximo, ambiente sem eco
5. Browser limpo (uma aba só desta apresentação, e mais 2 abas pros live demos: `/surgical/` e `/insight/`)
6. **Notificações desabilitadas** (Do Not Disturb)
7. **Pré-aquecer o detector** com 1 upload antes da gravação (best.pt já carregado em memória — evita os 5-10s de cold start no live demo)
8. Cronometrar uma vez antes — usar `S` (speaker view) tem cronômetro embutido
