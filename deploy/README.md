# Deploy unificado — Sentinel Health

Sobe a plataforma inteira (landing + Surgical + Insight) num único `docker-compose` atrás de um nginx reverse proxy.

## Topologia

```
                  ┌───────────────────────────────────────────────────┐
                  │  Host (qualquer VPS / EC2 / Docker Desktop local) │
                  │                                                   │
                  │  :80  →  nginx  ──┬──→  /         → landing :80   │
   browser ───────┤                   ├──→  /surgical/* → surgical :8000 │
                  │                   └──→  /insight/*  → insight  :8501 │
                  │                                                   │
                  │  network: sentinel-net (bridge)                   │
                  └───────────────────────────────────────────────────┘
```

## Pré-requisitos

| Requisito | Notas |
|---|---|
| Docker + Docker Compose v2 | Testado com Docker 29.x e Compose v2 |
| Porta `80` livre no host | nginx publica nessa porta |
| `~/.aws/credentials` | Necessário para a galeria S3 do Surgical. Se ausente, a galeria não funciona mas o resto da app fica de pé. |
| `OPENAI_API_KEY` em `../modules/insight/emotion-recognizer/.env` | Necessário para Whisper + LLM do Insight. Se ausente, o caminho LLM falha graciosamente e o Insight usa fallback keyword-based. |
| `best.pt` em `../modules/surgical/web/models/` | Necessário para detecção de fato. Baixe do S3 via `modules/surgical/scripts/update-web-model.sh`. **Sem o modelo, o `/surgical/health` responde 200 mas qualquer upload de vídeo falha ao chamar o detector.** |

## Subir

```bash
cd sentinel-health/deploy
docker-compose up -d
```

Aguarde ~15-30s para os containers ficarem `healthy` (Streamlit do Insight leva alguns segundos para iniciar).

## Endpoints

| URL | Aponta para | Observações |
|---|---|---|
| `http://localhost/` | landing institucional | placeholder em construção; Phase 4 do plano traz a versão completa |
| `http://localhost/surgical/` | UI do Sentinel Surgical | requer `best.pt` em `modules/surgical/web/models/` |
| `http://localhost/surgical/health` | health check do Surgical | sempre 200 (não depende do modelo) |
| `http://localhost/surgical/api/info/model` | metadados do modelo | dicionário estático, sem dependência de runtime |
| `http://localhost/insight/` | UI do Sentinel Insight (Streamlit) | requer `OPENAI_API_KEY` para LLM/Whisper |
| `http://localhost/insight/_stcore/health` | health check do Streamlit | responde `ok` |

## Logs

```bash
docker-compose logs -f nginx
docker-compose logs -f surgical
docker-compose logs -f insight
docker-compose logs -f landing

# todos juntos
docker-compose logs -f
```

## Derrubar

```bash
docker-compose down
```

Para limpar também os volumes nomeados (uploads/resultados do Surgical):

```bash
docker-compose down -v
```

## Imagens criadas

| Imagem | Tamanho aprox. | Conteúdo |
|---|---:|---|
| `sentinel-landing:latest` | ~50 MB | nginx:alpine + HTML estático |
| `sentinel-surgical:latest` | ~5 GB | Python 3.10 + PyTorch + Ultralytics + OpenCV + FastAPI |
| `sentinel-insight:latest` | ~4 GB | Python 3.12 + TensorFlow + DeepFace + Streamlit + OpenAI SDK |
| `nginx:alpine` (pull) | ~50 MB | reverse proxy |

**Total:** ~9 GB. Recomendado: 16 GB RAM no host para conforto.

## Variante: atrás de reverse proxy do host

Cenário: o host já tem um nginx (ou outro web server) na porta 80, e você
quer que **ele** faça o proxy reverso pro sentinel.

### Como subir o sentinel em loopback:8100

```bash
cd sentinel-health/deploy
docker compose \
  -f docker-compose.yml \
  -f docker-compose.behind-proxy.yml \
  up -d
```

O que muda: a única diferença é o binding do `nginx` do container — em vez de
`80:80` (público), fica em `127.0.0.1:8100:80` (loopback-only). O nginx
**interno** do sentinel não muda; o roteamento por path (`/`, `/surgical/`,
`/insight/`) continua acontecendo lá dentro.

### Configurar o nginx do host

Copie o snippet pronto:

```bash
sudo cp nginx/host-snippet.conf /etc/nginx/conf.d/sentinel.conf
sudo $EDITOR /etc/nginx/conf.d/sentinel.conf   # ajustar server_name
sudo nginx -t && sudo systemctl reload nginx
```

O snippet em [`nginx/host-snippet.conf`](./nginx/host-snippet.conf) inclui:
- `map $http_upgrade $connection_upgrade { ... }` (necessário para o WebSocket do Streamlit)
- `proxy_pass http://127.0.0.1:8100`
- Headers `X-Forwarded-*` repassados
- `proxy_http_version 1.1` + `Upgrade`/`Connection` para WebSocket
- Timeouts longos (uploads do Surgical, sessão do Insight)
- Bloco `ssl_*` comentado pronto pra ativar quando tiver certificado

### Confirmar que funcionou

```bash
# A 8100 só responde via loopback do host:
curl -I http://127.0.0.1:8100/                # 200, vindo do host
curl -I http://<ip-externo-do-host>:8100/     # connection refused (desejado)

# Já o host nginx atende externamente:
curl -I http://sentinel.example.com/          # 200 (proxy → 127.0.0.1:8100 → containers)
curl -I http://sentinel.example.com/insight/_stcore/health  # 200
```

### Gotcha mais comum

Se a UI do Insight (Streamlit) **carrega mas fica preso em "Please wait"**, o
host nginx não está repassando o upgrade de WebSocket. Confira no snippet
do host:

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}
# e dentro do location:
proxy_http_version 1.1;
proxy_set_header   Upgrade    $http_upgrade;
proxy_set_header   Connection $connection_upgrade;
```

> **Requisito:** Docker Compose v2.24+ para a diretiva `!override` usada no
> override. Em versões mais antigas, copie `docker-compose.yml` inteiro para
> `docker-compose.behind-proxy.yml` e troque a linha `"80:80"` manualmente.

## Problemas comuns

### `bind: address already in use` na porta 80
Algo já escuta na porta 80. Pare o serviço concorrente ou ajuste a porta do nginx no `docker-compose.yml` (`"8080:80"` em vez de `"80:80"`).

### Surgical retorna 500 em `/api/video/upload`
`best.pt` não está em `modules/surgical/web/models/`. Baixe do S3:
```bash
aws s3 cp s3://surgical-detection-models-dev/trained/best.pt \
          ../modules/surgical/web/models/best.pt
```

### Insight retorna "⚠️ LLM unavailable" no summary
`OPENAI_API_KEY` ausente ou inválido em `../modules/insight/emotion-recognizer/.env`. O fallback keyword-based ainda funciona — só o caminho LLM falha.

### Streamlit não carrega CSS/JS via `/insight/`
Verifique que a env `STREAMLIT_SERVER_BASE_URL_PATH=/insight` está setada no Dockerfile do Insight (já está; é a peça que faz o proxy reverso funcionar sem rewrite).

## GPU (NVIDIA)

Este compose é CPU-only por portabilidade. Para usar GPU NVIDIA com o Surgical, use o compose original em `../modules/surgical/web/docker-compose.yml` (que tem a reservation `nvidia`).
