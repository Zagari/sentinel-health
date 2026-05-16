# Surgical Video AI

Sistema de análise de vídeos cirúrgicos utilizando YOLOv8 customizado para detecção de **sangramento anômalo** e **instrumentos cirúrgicos** em procedimentos ginecológicos.

## FIAP - Pós-Graduação em Inteligência Artificial para Devs
**Tech Challenge - Fase 4: Análise de Dados**

---

## Objetivo

Desenvolver um sistema de visão computacional para monitoramento de saúde da mulher:
- Detectar sangramento anômalo durante cirurgias ginecológicas
- Identificar instrumentos cirúrgicos em tempo real
- Gerar alertas automáticos para a equipe médica
- Produzir relatórios de análise de procedimentos

## Estratégia de Datasets

Este projeto utiliza uma abordagem de **validação cross-dataset** para garantir a generalização do modelo:

| Dataset | Uso | Descrição |
|---------|-----|-----------|
| **CholecSeg8k** | Treinamento | 8.080 frames de colecistectomia com máscaras de segmentação pixel-level para sangramento e instrumentos |
| **GynSurg** | Validação/Demo | Clips de 3 segundos de cirurgias ginecológicas laparoscópicas com labels de bleeding/non-bleeding |

### Por que dois datasets?

1. **CholecSeg8k** fornece anotações precisas (máscaras de segmentação) ideais para treinar o modelo de detecção
2. **GynSurg** permite validar a capacidade de generalização do modelo em cirurgias ginecológicas reais
3. Esta abordagem demonstra que o modelo aprende padrões universais de sangramento e instrumentos cirúrgicos

### Estatísticas dos Datasets

**CholecSeg8k (Treinamento)**
- Total: 8.080 imagens
- Train: 6.464 imagens | Val: 1.616 imagens
- Classes: grasper (13.680 instâncias), blood (2.545 instâncias)

**GynSurg Action Recognition (Validação)**
- Bleeding: 977 clips (3s cada, 4K)
- Non-bleeding: 1.064 clips
- Resolução: 3840x2160 @ 30fps

## Tecnologias

| Componente | Tecnologia |
|------------|------------|
| Detecção de Objetos | YOLOv8m (Ultralytics) |
| Backend API | FastAPI |
| Frontend | HTML/CSS/JavaScript |
| Container | Docker |
| Cloud Storage | AWS S3 |
| IaC | Terraform |
| Linguagem | Python 3.10+ |

## Estrutura do Projeto

```
surgical-video-ai/
│
├── web/                           # APLICAÇÃO WEB (FastAPI + Frontend)
│   ├── app/
│   │   ├── main.py                # Entry point FastAPI
│   │   ├── routers/
│   │   │   ├── video.py           # Upload e processamento de vídeo
│   │   │   ├── samples.py         # Galeria de clips de exemplo (S3)
│   │   │   ├── info.py            # Info do modelo e métricas
│   │   │   └── annotation.py      # Interface de anotação (fine-tuning)
│   │   ├── services/
│   │   │   └── detector.py        # Serviço YOLOv8 (threshold: 0.30)
│   │   └── static/
│   │       ├── index.html         # Interface principal
│   │       ├── annotation.html    # Interface de anotação
│   │       └── js/app.js          # JavaScript do frontend
│   ├── models/                    # Modelos .pt (montado no container)
│   ├── docker-compose.yml         # Deploy com GPU
│   └── docker-compose.cpu.yml     # Deploy sem GPU
│
├── scripts/                       # SCRIPTS DE AUTOMAÇÃO
│   │
│   │ # Treinamento
│   ├── server-setup.sh            # Configura servidor GPU
│   ├── server-train.sh            # Treino v1 (baseline)
│   ├── server-train-v2-classweight.sh  # Treino v2 (cls=3.0)
│   ├── finetune-gynsurg.sh        # Fine-tuning v3 com anotações
│   │
│   │ # Validação
│   ├── generate-validation-set.sh # Gera set fixo reproduzível
│   ├── validate-gynsurg.sh        # Valida uma versão do modelo
│   ├── validate-all-versions.sh   # Valida todas as versões
│   ├── analyze-threshold.sh       # Testa diferentes thresholds
│   ├── compare-validations.sh     # Compara resultados
│   └── update-web-model.sh        # Atualiza modelo na aplicação web
│
├── src/                           # CÓDIGO PYTHON
│   ├── data/
│   │   └── prepare_cholecseg8k.py # Converte CholecSeg8k → formato YOLO
│   ├── inference/
│   │   └── processor.py           # Processador de vídeo
│   └── reports/
│       └── generator.py           # Gerador de relatórios
│
├── anotacoes-gynsurg/             # DADOS DE ANOTAÇÃO (fine-tuning v3)
│   └── yolo_export/
│       ├── images/train/          # 1020 frames anotados
│       ├── labels/train/          # 1020 labels YOLO
│       └── data.yaml              # Config do dataset
│
├── terraform/                     # INFRAESTRUTURA AWS (IaC)
│   ├── modules/                   # S3, EC2, SageMaker
│   └── environments/              # training, inference
│
├── data/                          # Datasets (não versionado)
├── models/                        # Modelos (não versionado)
├── docs/                          # Documentação e relatórios
└── README.md                      # Este arquivo
```

## Fluxo de Trabalho

O modelo de produção (v3_finetuned) foi desenvolvido em 3 fases:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FASE 1: BASELINE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  CholecSeg8k (8080 imgs) ──▶ server-train.sh ──▶ v1_baseline               │
│                                                   5.41% det | 76.11% FP     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FASE 2: CLASS WEIGHTS                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Ajuste cls=3.0 ──▶ server-train-v2-classweight.sh ──▶ v2_classweight      │
│  (compensa desbalanceamento 5.4:1)                    12.14% det | 46.89% FP│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FASE 3: FINE-TUNING                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  Interface /annotation ──▶ 1020 frames anotados ──▶ finetune-gynsurg.sh    │
│  (475 bleeding + 545 non-bleeding)                                          │
│                                                    ▼                        │
│                                             v3_finetuned ✅                 │
│                                             91.72% det | 13.44% FP          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Validação:** Todos os modelos são validados no dataset GynSurg (cirurgias ginecológicas) usando um validation set fixo de 20 clips (10 bleeding + 10 non-bleeding) para garantir comparações reproduzíveis.

## Quick Start

### 1. Pré-requisitos

- Python 3.10+
- AWS CLI configurado
- Docker (para interface web)
- **Para treinamento**: Servidor com GPU NVIDIA **OU** conta AWS com acesso a instâncias GPU

### 2. Preparar Dataset CholecSeg8k

```bash
# Preparar para formato YOLO
python src/data/prepare_cholecseg8k.py \
    --input ./CholecSeg8k \
    --output data/yolo_format
```

### 3. Treinamento

#### Opção A: Servidor Local com GPU (Recomendado)

```bash
# Copiar scripts para o servidor
scp -r scripts/ usuario@servidor:~/

# No servidor
./scripts/server-setup.sh      # Configurar ambiente
./scripts/server-train.sh      # Treinar modelo (~3-4 horas)
```

#### Opção B: AWS com Terraform

```bash
# Provisionar infraestrutura AWS (requer conta com acesso a instâncias GPU)
cd terraform/environments/training
terraform init
terraform apply

# Conectar à instância EC2 criada
ssh -i ~/.ssh/sua-chave.pem ubuntu@<IP_DA_INSTANCIA>

# Na instância EC2
./scripts/server-setup.sh
./scripts/server-train.sh

# IMPORTANTE: Destruir recursos após o treino para evitar custos
terraform destroy
```

### 4. Validação com GynSurg

O sistema de validação permite testar o modelo treinado em clips de cirurgias ginecológicas e comparar diferentes versões do modelo de forma reproduzível.

#### 4.1. Gerar Validation Set Fixo (uma única vez)

```bash
# Cria arquivos com lista fixa de clips para validação reproduzível
./scripts/generate-validation-set.sh /path/to/GynSurg_Action_3sec

# Opcionalmente, especifique o número de clips (default: 10)
./scripts/generate-validation-set.sh /path/to/GynSurg_Action_3sec 20
```

Arquivos gerados em `GynSurg_Action_3sec/validation_sets/`:
- `validation_set_bleeding.txt` - Lista de clips com sangramento
- `validation_set_non_bleeding.txt` - Lista de clips sem sangramento

#### 4.2. Executar Validação

```bash
# Validação reproduzível com tag de versão do modelo
./scripts/validate-gynsurg.sh /path/to/GynSurg_Action_3sec --fixed --version v1_baseline

# Com upload para S3
./scripts/validate-gynsurg.sh /path/to/GynSurg_Action_3sec --fixed --version v1_baseline --upload
```

**Opções disponíveis:**

| Opção | Descrição |
|-------|-----------|
| `--fixed` | Usa o validation set fixo gerado anteriormente |
| `--seed` | Usa shuf com seed 42 (reproduzível, mas não usa arquivo) |
| `--version TAG` | Tag de versão do modelo (ex: v1_baseline, v2_classweight) |
| `--upload` | Faz upload dos resultados para S3 |

Os resultados são salvos em `~/surgical-training/validation_gynsurg_TIMESTAMP/` com:
- `validation_report.json` - Métricas e versão do modelo
- `bleeding_results/` - Detecções em clips com sangramento
- `non_bleeding_results/` - Detecções em clips sem sangramento

#### 4.3. Comparar Validações

```bash
# Comparar TODAS as validações existentes
./scripts/compare-validations.sh

# Comparar duas validações específicas
./scripts/compare-validations.sh validation_gynsurg_20260510_120000 validation_gynsurg_20260510_140000
```

#### 4.4. Fluxo Recomendado para Iteração do Modelo

1. **Baseline:** `--fixed --version v1_baseline`
2. **Após ajuste de class weights:** `--fixed --version v2_classweight`
3. **Após fine-tuning:** `--fixed --version v3_finetuned`
4. **Comparar progresso:** `./scripts/compare-validations.sh`

#### 4.5. Análise de Threshold

O script `analyze-threshold.sh` permite testar diferentes thresholds de confiança:

```bash
# Testar thresholds padrão (0.1 a 0.7)
./scripts/analyze-threshold.sh /path/to/GynSurg --version v3_finetuned

# Testar thresholds customizados
./scripts/analyze-threshold.sh /path/to/GynSurg --version v3_finetuned --thresholds 0.2,0.25,0.3,0.35,0.4
```

#### 4.6. Validar Todas as Versões

Para comparar todas as versões do modelo de uma só vez:

```bash
./scripts/validate-all-versions.sh /path/to/GynSurg_Action_3sec
```

Este script valida automaticamente todas as versões disponíveis e gera um relatório comparativo.

---

## Resultados

### Comparativo de Versões do Modelo

Validação cross-dataset: treino em CholecSeg8k, validação em GynSurg (10 clips bleeding + 10 clips non-bleeding).

| Versão | Descrição | Detecção | Falso Positivo | Status |
|--------|-----------|----------|----------------|--------|
| v1_baseline | Treino padrão | 5.41% | 76.11% | ❌ |
| v2_classweight | cls=3.0 | 12.14% | 46.89% | ⚠️ |
| **v3_finetuned** | **Fine-tuning com anotações GynSurg** | **91.72%** | **13.44%** | **✅** |
| v5_negative_only | Fine-tuning só com negativos | 0.00% | 0.00% | ❌ |

### Modelo de Produção: v3_finetuned

O modelo v3 foi selecionado como modelo de produção por atingir ambas as metas do projeto:

| Métrica | Meta | Resultado | Status |
|---------|------|-----------|--------|
| Taxa de Detecção | > 60% | **91.72%** | ✅ |
| Taxa de Falso Positivo | < 20% | **13.44%** | ✅ |

### Análise de Threshold (v3_finetuned)

| Threshold | Detecção | Falso Positivo | Recomendação |
|-----------|----------|----------------|--------------|
| 0.10 | 94.48% | 19.33% | Máxima sensibilidade |
| 0.20 | 93.05% | 14.78% | Alta sensibilidade |
| **0.30** | **91.72%** | **13.44%** | **Balanço (default)** |
| 0.40 | 90.07% | 10.67% | Balanço conservador |
| 0.50 | 88.96% | 9.33% | Menor FP |
| 0.60 | 87.86% | 6.78% | Melhor score (det-FP) |
| 0.70 | 85.76% | 4.89% | Mínimo FP |

**Threshold recomendado: 0.30** - Para contexto cirúrgico, é preferível ter mais falsos positivos do que perder detecções de sangramento real.

### Evolução do Modelo

```
v1 (baseline)     ████░░░░░░░░░░░░░░░░  5.41% det | 76.11% FP
v2 (classweight)  ██████░░░░░░░░░░░░░░ 12.14% det | 46.89% FP
v3 (finetuned)    ██████████████████░░ 91.72% det | 13.44% FP ✅
```

### Estratégia de Fine-tuning

O modelo v3 foi criado através de fine-tuning do v2 com 475 frames anotados manualmente do dataset GynSurg:
- **Base**: Modelo v2 (treinado com class weights)
- **Dados**: 475 frames com sangramento + 545 frames sem sangramento
- **Técnica**: Pseudo-bounding boxes centralizados
- **Parâmetros**: 30 epochs, lr=0.001, freeze=10 camadas

### 5. Baixar Modelo Treinado

O modelo de produção é o **v3_finetuned** (91.72% detecção, 13.44% FP).

```bash
cd web
mkdir -p models

# Baixar modelo v3 do S3 (recomendado)
aws s3 cp s3://surgical-detection-models-dev/trained/best_v3_finetuned.pt models/best.pt

# Ou baixar o modelo padrão de produção
aws s3 cp s3://surgical-detection-models-dev/trained/best.pt models/best.pt
```

**Modelos disponíveis no S3:**
| Arquivo | Versão | Descrição |
|---------|--------|-----------|
| `best.pt` | v3 | Modelo de produção (recomendado) |
| `best_v3_finetuned.pt` | v3 | Fine-tuned com anotações GynSurg |
| `best_v2_classweight.pt` | v2 | Treinado com class weights |
| `best_v1_baseline.pt` | v1 | Baseline original |

### 6. Interface Web

```bash
cd web

# Com GPU NVIDIA (requer nvidia-docker)
docker-compose up -d

# Sem GPU (apenas CPU - mais lento, mas funcional)
docker-compose -f docker-compose.cpu.yml up -d

# Acessar: http://localhost:8100
```

**Quando usar cada opção:**
- **GPU**: Processamento em tempo real, demonstrações ao vivo
- **CPU**: Testes, desenvolvimento local, ambientes sem GPU dedicada

## Interface Web

A interface web permite demonstrar o sistema de detecção de forma interativa.

### Funcionalidades

| Recurso | Descrição |
|---------|-----------|
| **Upload de Vídeo** | Envie vídeos do seu computador para análise |
| **URL de Vídeo** | Cole uma URL (YouTube, etc.) para processar |
| **Galeria de Exemplos** | Selecione clips do dataset GynSurg pré-carregados no S3 |
| **Visualização** | Veja detecções em tempo real com bounding boxes |
| **Download** | Baixe o vídeo anotado e relatório JSON |
| **Informações** | Dados sobre o modelo, datasets e estratégia |

### Endpoints da API

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Interface web |
| `/health` | GET | Health check |
| `/api/video/upload` | POST | Upload de vídeo |
| `/api/video/url` | POST | Processar URL |
| `/api/video/status/{job_id}` | GET | Status do processamento |
| `/api/video/result/{job_id}/video` | GET | Baixar vídeo anotado |
| `/api/samples/list` | GET | Listar clips de exemplo |
| `/api/samples/process/{category}/{filename}` | POST | Processar clip |
| `/api/info/model` | GET | Informações do modelo |

### Estrutura Web

```
web/
├── app/
│   ├── main.py              # FastAPI app
│   ├── routers/
│   │   ├── video.py         # Processamento de vídeo
│   │   ├── samples.py       # Galeria de exemplos
│   │   ├── info.py          # Informações
│   │   └── annotation.py    # Interface de anotação
│   ├── services/
│   │   └── detector.py      # Serviço YOLOv8 (threshold: 0.30)
│   └── static/
│       ├── index.html       # Interface principal
│       └── annotation.html  # Interface de anotação
├── models/                  # Modelo best.pt (v3_finetuned)
├── Dockerfile
├── docker-compose.yml       # Deploy com GPU
├── docker-compose.cpu.yml   # Deploy sem GPU
└── requirements.txt
```

### Interface de Anotação

A interface `/annotation` permite anotar frames do dataset GynSurg para fine-tuning:

- **URL**: `http://localhost:8100/annotation`
- **Atalhos**: `S` = Sangramento, `N` = Não, `Espaço` = Pular
- **Exportação**: Gera dataset YOLO para fine-tuning

## Infraestrutura Terraform

O projeto inclui módulos Terraform para provisionar a infraestrutura na AWS:

```
terraform/
├── modules/
│   ├── storage/      # S3 buckets para datasets, modelos e resultados
│   ├── training/     # EC2 com GPU para treinamento (g4dn.xlarge)
│   └── inference/    # SageMaker endpoint para inferência
└── environments/
    ├── training/     # Ambiente de treinamento
    └── inference/    # Ambiente de produção
```

### Custos Estimados AWS

| Recurso | Tipo | Custo/hora | Uso típico |
|---------|------|------------|------------|
| EC2 Training | g4dn.xlarge | ~$0.52 | 3-4 horas |
| S3 Storage | - | ~$0.023/GB/mês | Contínuo |
| SageMaker | ml.g4dn.xlarge | ~$0.74 | Por demanda |

**⚠️ IMPORTANTE**: Sempre execute `terraform destroy` após o uso para evitar custos!

## Recursos AWS (S3)

| Bucket | Descrição |
|--------|-----------|
| `surgical-detection-datasets-dev` | Dataset YOLO (726 MB) |
| `surgical-detection-models-dev` | Modelos treinados (.pt) |
| `surgical-detection-results-dev` | Resultados de inferência |

## Classes Detectadas

| ID | Classe | Descrição |
|----|--------|-----------|
| 0 | grasper | Pinça de apreensão |
| 1 | blood | Sangramento detectado |

**Configuração de produção:**
- Modelo: v3_finetuned
- Threshold de confiança: 0.30
- Taxa de detecção: 91.72%
- Taxa de falso positivo: 13.44%

## Documentação

Para detalhes sobre a implementação do Sistema de Análise de Vídeo, consulte o relatório técnico:

📄 [docs/relatorio_.pdf](docs/relatorio_.pdf)

▶️ [Vídeo demonstrativo]()

## Equipe

- Adriana Martins de Souza - RM 368050
- Diego Oliveira da Silva - RM 367964
- Eduardo Nicola F. Zagari - RM 368021
- Renan de Assis Torres - RM 368513

## Licença

Este projeto é desenvolvido para fins acadêmicos como parte do Tech Challenge da FIAP.

---

**Aviso**: Este sistema é um protótipo acadêmico e não deve ser usado para decisões médicas reais.
