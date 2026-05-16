# Surgical Video AI - Web Interface

Interface web para demonstração do sistema de detecção de sangramento e instrumentos em cirurgias ginecológicas.

## Funcionalidades

- **Upload de vídeo**: Envie um vídeo do seu computador
- **URL de vídeo**: Cole uma URL (YouTube, etc.)
- **Galeria de exemplos**: Selecione clips do dataset GynSurg pré-carregados
- **Visualização de resultados**: Veja detecções e baixe vídeo anotado
- **Informações do modelo**: Dados sobre treinamento e datasets

## Pré-requisitos

- Docker e Docker Compose
- Modelo treinado (`best.pt`) na pasta `models/`
- AWS CLI configurado (para acesso aos clips de exemplo no S3)
- GPU NVIDIA (recomendado) ou CPU

## Quick Start

### 1. Copiar modelo treinado

```bash
# Baixar do S3
aws s3 cp s3://surgical-detection-models-dev/trained/best.pt models/

# Ou copiar do servidor de treinamento
scp usuario@servidor:~/surgical-training/results/surgical_detection/weights/best.pt models/
```

### 2. Iniciar com GPU

```bash
docker-compose up -d
```

### 3. Iniciar sem GPU (apenas CPU)

```bash
docker-compose -f docker-compose.cpu.yml up -d
```

### 4. Acessar

Abra no navegador: http://localhost:8100

## Desenvolvimento Local (sem Docker)

```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Executar
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Interface web |
| `/health` | GET | Health check |
| `/api/video/upload` | POST | Upload de vídeo |
| `/api/video/url` | POST | Processar URL |
| `/api/video/status/{job_id}` | GET | Status do processamento |
| `/api/video/result/{job_id}/video` | GET | Baixar vídeo anotado |
| `/api/video/result/{job_id}/report` | GET | Baixar relatório JSON |
| `/api/samples/list` | GET | Listar clips de exemplo |
| `/api/samples/process/{category}/{filename}` | POST | Processar clip de exemplo |
| `/api/info/model` | GET | Informações do modelo |
| `/api/info/dataset` | GET | Informações dos datasets |
| `/api/info/strategy` | GET | Estratégia cross-dataset |

## Estrutura

```
web/
├── app/
│   ├── main.py              # FastAPI app
│   ├── routers/
│   │   ├── video.py         # Processamento de vídeo
│   │   ├── samples.py       # Galeria de exemplos
│   │   └── info.py          # Informações
│   ├── services/
│   │   └── detector.py      # Serviço YOLOv8
│   └── static/
│       ├── index.html       # Frontend
│       ├── css/style.css    # Estilos
│       └── js/app.js        # JavaScript
├── models/                  # Modelos .pt
├── Dockerfile
├── docker-compose.yml       # Com GPU
├── docker-compose.cpu.yml   # Sem GPU
└── requirements.txt
```

## Variáveis de Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `MODEL_PATH` | Caminho do modelo | `models/best.pt` |
| `S3_BUCKET` | Bucket com clips de exemplo | `surgical-detection-datasets-dev` |
| `AWS_DEFAULT_REGION` | Região AWS | `us-east-1` |
