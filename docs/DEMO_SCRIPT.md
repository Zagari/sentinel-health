# Demo Script — Vídeo Sentinel Health (15 min)

Roteiro detalhado da gravação demonstrativa exigida pelo Tech Challenge Fase 4.

> **Entregável PDF:** *"Vídeo com até 15 minutos demonstrando: upload no YouTube ou Vimeo (público ou não listado). Demonstração do processamento multimodal: exemplo prático da análise de áudio e vídeo. Detecção e resposta a anomalias. Integração dos serviços Azure. Fluxo final do alerta à equipe médica."*

## Pré-requisitos antes de gravar

| Item | Onde verificar |
|---|---|
| Plataforma rodando em algum host | `curl http://localhost/health` retorna 200 (ou URL pública equivalente) |
| `best.pt` baixado | Auto-download no 1º boot do surgical (~30s). Se já estava lá, instantâneo. |
| `OPENAI_API_KEY` válida | Em `modules/insight/emotion-recognizer/.env` |
| Áudio com fala em inglês para o Insight | WAV/MP3 de 30-60s. Pode usar gravação livre simulando consulta. |
| Vídeo cirúrgico para o Surgical | Galeria de samples S3 já carregada (categoria `bleeding`). |
| Apresentação reveal.js pronta | `landing/presentation/` aberta em fullscreen no browser (Phase 7) |
| Ferramenta de captura | OBS, QuickTime, Loom, Camtasia, etc. com captura de tela + microfone |
| Conta YouTube/Vimeo | Logado, pronto pra upload |

## Estrutura (15 min)

```
00:00 ─┐
       │ 01. Abertura
01:00 ─┤
       │ 02. Cobertura do desafio
02:30 ─┤
       │ 03. Sentinel Surgical (live demo)
08:00 ─┤
       │ 04. Sentinel Insight (live demo)
13:30 ─┤
       │ 05. Multi-cloud + privacidade
14:30 ─┤
       │ 06. Fechamento
15:00 ─┘
```

---

## Bloco 1 · 00:00 – 01:00 (60s) — Abertura

**Cena:** Slide 1 da apresentação reveal.js (capa) em fullscreen.

**Fala:**
> "Olá, sou Eduardo Zagari, parte do Grupo Sala 14 do curso de Pós-Graduação em IA para Devs da FIAP. Hoje vamos apresentar o Sentinel Health: uma plataforma multimodal de monitoramento contínuo da saúde da mulher, desenvolvida para a Fase 4 do Tech Challenge."
>
> "A equipe é composta por Adriana Martins de Souza, Diego Oliveira da Silva, Renan de Assis Torres e eu, Eduardo Nicola F. Zagari."
>
> "O desafio nos pedia para construir um sistema que processasse dados multimodais — áudio, vídeo e texto — para identificar precocemente riscos específicos da saúde feminina. Nós escolhemos atender três das quatro funcionalidades sugeridas e os cinco objetivos do desafio."

**Transição:** clique para slide 2 (O Problema) → slide 3 (A Proposta) → slide 4 (Cobertura).

---

## Bloco 2 · 01:00 – 02:30 (90s) — Cobertura do desafio

**Cena:** Slide 4 da apresentação mostrando a matriz resumida + janela do browser mostrando `/coverage.html` interativa.

**Fala:**
> "Antes de mostrar a plataforma rodando, queremos deixar claro o que está e o que não está atendido. Cobrimos 20 dos 25 itens da proposta plenamente, mais 3 parciais — totalizando 23 dos 25. Os outros 2 ficaram em roadmap declarado: análise de fisioterapia e detecção de sinais vitais."
>
> "Esta matriz é interativa em `/coverage.html`. Olhem aqui — Funcionalidades: escolhemos 3 das 4 opções, sendo o mínimo 2. Objetivos: cobrimos os 5 dos 5. Requisito 1 de Vídeo: 6 atendidos plenamente. Requisito 2 de Áudio: 4 dos 4. Entregáveis: este vídeo é o último a ser concluído."

**Ações práticas:**
- alt-tab para o browser em `http://<host>/coverage.html`
- demonstra 2 filtros: clique em "Status: ✅ Atendido" → tabela reduz para 20 cards; depois clique em "Tipo: Áudio" → reduz mais.
- volta o filtro pra "Todos"
- alt-tab de volta para a apresentação, próximo slide

---

## Bloco 3 · 02:30 – 08:00 (5min 30s) — Sentinel Surgical

**Cena:** Slides 5-8 (Surgical visão geral) + browser em `/surgical/`.

### 03:00 – 03:30 — Slide 5 (Visão geral)

**Fala:**
> "O primeiro módulo é o Sentinel Surgical. Ele detecta sangramento anômalo em cirurgias ginecológicas em tempo near real-time. O modelo é um YOLOv8m treinado em 3 fases: primeiro com o CholecSeg8k, dataset de colecistectomia laparoscópica com máscaras de segmentação pixel-level; depois adicionamos class weights para compensar o desbalanceamento; e por fim fizemos fine-tuning com 1020 frames anotados manualmente do GynSurg, dataset de cirurgias ginecológicas."
>
> "Os resultados: na versão v3_finetuned, alcançamos 91.72% de taxa de detecção com apenas 13.44% de falsos positivos — exatamente as metas que estabelecemos para o projeto."

### 03:30 – 07:30 — Live demo da UI do Surgical

**Cena:** alt-tab para `http://<host>/surgical/`.

**Roteiro de ações:**

1. **Mostra a galeria de samples** (S3 do AWS)
   - "Aqui temos clips de exemplo carregados diretamente de um bucket S3 público. Cada clip é classificado entre bleeding e non-bleeding pelo dataset GynSurg original — vou usar isso como ground truth."

2. **Clica num clip de `bleeding`** (escolher um curto, idealmente < 30s)
   - "Vou pegar este clip de 3 segundos do paciente case_110, classificado como bleeding. Click em 'Processar'."

3. **Aguarda processamento** (~30-60s; falar enquanto roda)
   - "Enquanto o YOLOv8 processa, deixa eu explicar o que está acontecendo. O FastAPI recebeu o vídeo, começou um background task, está percorrendo cada frame com `cv2.VideoCapture`, fazendo inferência YOLO com threshold 0.30, desenhando bounding boxes, e gerando um JSON com todas as detecções."

4. **Vídeo anotado abre**
   - "Aqui vemos o resultado. Olhem as bounding boxes vermelhas: o modelo detectou regiões de sangramento corretamente, com confiança acima de 30%. As azuis seriam graspers — instrumentos cirúrgicos — mas não tem nenhum visível neste clip."

5. **Mostra o JSON download**
   - "E aqui está o JSON exportado com todas as detecções: frame number, timestamp, classe, confiança, bbox. Isso pode ser facilmente integrado num EHR ou num sistema de alerta clínico."

### 07:30 – 08:00 — Slide 8 (Threshold sweep)

**Fala:**
> "Para deixar transparente como chegamos no threshold 0.30: aqui está o sweep de thresholds que fizemos. Em 0.10 temos 94% de detecção mas com 19% de FP. Em 0.70 temos só 5% de FP mas perdemos detecção — caímos para 86%. Escolhemos 0.30 como balanço entre sensibilidade e precisão, porque em contexto cirúrgico é preferível ter mais falsos positivos do que perder sangramento real."

---

## Bloco 4 · 08:00 – 13:30 (5min 30s) — Sentinel Insight

**Cena:** Slides 9-11 + browser em `/insight/`.

### 08:00 – 08:30 — Slide 9 (Visão geral)

**Fala:**
> "O segundo módulo é o Sentinel Insight. Ele faz análise emocional multimodal de consultas, combinando três sinais: expressão facial via DeepFace, voz via Whisper-1 da OpenAI para transcrição, e LLM GPT-5.4-nano para análise contextual do conteúdo da fala."
>
> "O Insight cobre 100% do Requisito de Áudio do desafio: consultas ginecológicas, acompanhamento pré-natal, depressão pós-parto, e atendimento a vítimas de violência. Cada um desses casos é detectado via prompt LLM dedicado, com fallback keyword baseado em 27 padrões regex caso a API esteja indisponível."

### 08:30 – 12:30 — Live demo da UI do Insight

**Cena:** alt-tab para `http://<host>/insight/`.

**Roteiro de ações:**

1. **Modo "Audio Only"** + upload de um WAV
   - Áudio sugerido: simular paciente relatando ansiedade, ou trecho de violência. **Ético:** não use áudios reais de pacientes; sintetize com ferramenta TTS ou grave a si mesmo simulando.

2. **Click "Analyse Audio"**
   - "Enquanto processa: o Whisper-1 está transcrevendo o áudio. Em paralelo, o GPT-5.4-nano vai receber a transcrição e fazer análise psicológica via prompt dedicado."

3. **UI mostra resultados** (após ~10-30s)
   - "Aqui temos 4 métricas no topo: sentiment, risk level, score 0-10, e source — neste caso `openai_llm` confirmando que a chamada chegou."
   - "Detected signals: a IA identificou padrões emocionais específicos."
   - "Keywords: palavras-chave que dispararam alertas."
   - "E aqui em 'Details': justificativa do modelo, ação recomendada — pronto pra integração com sistema de alerta da equipe médica."

4. **Mostra a transcrição completa** (expander)
   - "E aqui está o que o Whisper transcreveu literalmente, com a timestamp opcional."

5. **Download do JSON**
   - "E claro, exportável como JSON — mesma estrutura pronta pra integração."

### 12:30 – 13:30 — Slide 11 (O que detectamos — exemplo de output)

**Cena:** slide com snippet JSON de output do voice_analyzer.

**Fala:**
> "Aqui está um exemplo do JSON real exportado pelo Insight num caso de detecção de violência doméstica. Os campos `risk_level=high`, `score=8`, `detected_signals` listando 'fear', 'crying', 'physical harm', e `domestic_violence_signals` declarando 'strong indicators' — esse JSON, num cenário de produção, dispararia automaticamente um alerta no EHR e na escala de atendimento da equipe especializada."

---

## Bloco 5 · 13:30 – 14:30 (60s) — Multi-cloud + Privacidade

**Cena:** Slide 12 (multi-cloud diagram).

**Fala:**
> "Antes de fechar, um destaque arquitetural. O Sentinel Health é multi-cloud por design: usamos AWS para infraestrutura — S3 para datasets, EC2 com Terraform para deploy demonstrável, SSM Parameter Store pra secrets, SageMaker como opção. Usamos OpenAI API para o LLM e Whisper. E usamos o Hugging Face Hub para distribuir publicamente nosso modelo YOLOv8m treinado, com model card profissional documentando as 3 fases de treino, datasets e métricas."
>
> "Sobre privacidade — sabemos que estamos lidando com dados sensíveis de saúde feminina. Volumes locais para arquivos temporários, transito criptografado, secrets em SSM Parameter Store nunca commitados, SSH desabilitado nas instâncias, e acesso administrativo só via SSM Session Manager com auditoria em CloudTrail. Buckets S3 com `public_access_block` em todas as dimensões."

---

## Bloco 6 · 14:30 – 15:00 (30s) — Fechamento

**Cena:** Slide 14 (Roadmap) → Slide 15 (Fechamento).

**Fala:**
> "Próximos passos no roadmap: Sentinel Motion para fisioterapia pós-parto via pose estimation, Sentinel VitalSigns para sinais vitais, Sentinel Realtime para streaming síncrono ao vivo, e Sentinel Pose para complementar a análise de linguagem corporal."
>
> "O código-fonte completo, infrastructure-as-code com Terraform, model card no Hugging Face Hub, relatório técnico e esta apresentação estão disponíveis publicamente em `github.com/Zagari/sentinel-health`, sob licença MIT."
>
> "Aviso importante: este é um protótipo acadêmico. **Não é um dispositivo médico. Não deve ser usado para decisões clínicas reais.**"
>
> "Obrigado pela atenção!"

**Tela final:** logo da FIAP + URLs do repositório e do modelo no HF Hub, congelado por 3-5 segundos.

---

## Checklist técnico antes da gravação

- [ ] Resolução de captura: 1920x1080 mínimo (Full HD) ou 2560x1440 para clareza extra
- [ ] Áudio: microfone próximo, ambiente sem eco, sem ar-condicionado ruidoso
- [ ] Browser limpo: aba única por demo (landing/coverage/surgical/insight) — sem aba de "FIAP Bug Tracker" aparecendo no fundo
- [ ] Modo escuro/claro do sistema consistente
- [ ] Notificações desabilitadas (Do Not Disturb)
- [ ] Cursor visível ou destaque (zoom localizado quando clicar)
- [ ] **Teste o áudio antes:** 10s de gravação + playback pra confirmar volume
- [ ] **Teste o fluxo end-to-end antes:** se o `best.pt` ainda não foi baixado, tem 30s de espera no primeiro upload — pode "queimar tempo" no vídeo. Pré-aqueça o detector com 1 upload antes da gravação.
- [ ] Internet estável (chamadas pra OpenAI durante a demo do Insight)

## Pós-produção

- [ ] Cortar inícios/fins mortos
- [ ] Adicionar legendas (acessibilidade — bônus para avaliação)
- [ ] Verificar que o vídeo total NÃO ultrapassa 15:00 (PDF é explícito)
- [ ] Exportar 1080p, 30fps, codec H.264 mp4
- [ ] Upload no YouTube/Vimeo como **público ou não listado** (PDF aceita ambos)
- [ ] Atualizar `landing/index.html` rodapé e `coverage-data.json` com URL final do vídeo
- [ ] Atualizar `del-video` no JSON: status `partial` → `ok`
- [ ] Re-sincronizar `docs/CHALLENGE_COVERAGE.md` (20 → 21 ok)

## Backup plan se algo der errado durante a gravação

- **Plataforma fora do ar:** use screenshots/GIFs em vez de live demo (menos pontos, mas funciona)
- **OpenAI API offline:** o fallback keyword do Insight ainda funciona — anuncie "estamos no fallback porque a API caiu, mas o sistema graciosamente degradou"
- **Vídeo muito longo:** corte o threshold sweep (07:30-08:00) e o exemplo JSON de violência (12:30-13:30); ganha 1 min
- **Vídeo muito curto:** adicione 30s mostrando o Terraform plan output ou o GitHub repo com o histórico de commits "ao vivo"
