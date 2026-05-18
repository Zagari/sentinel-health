# Terraform — Sentinel Health AWS Deploy

Infraestrutura como código para subir a plataforma Sentinel Health (landing + Surgical + Insight) em AWS. Pensado para o padrão **provisiona → demonstra → destrói**, minimizando custo.

## Topologia

```
                  ┌──────────────────────────────────────────────┐
                  │  AWS us-east-1                               │
                  │                                              │
                  │  ┌─────────────────────────────────────────┐ │
                  │  │  EC2 t3.medium (Amazon Linux 2023)      │ │
   browser ──:80──┼──┤    sentinel-health-runtime-demo         │ │
                  │  │    nginx + landing + surgical + insight │ │
                  │  │    via docker-compose (3 containers)    │ │
                  │  └──────────┬────────────────┬─────────────┘ │
                  │     IAM Role│                │                │
                  │             ▼                ▼                │
                  │      ┌────────────┐ ┌─────────────────────┐  │
                  │      │ SSM Param  │ │ S3 (cross-bucket):  │  │
                  │      │ OPENAI_KEY │ │  surgical-detection │  │
                  │      │            │ │  -datasets-dev      │  │
                  │      │            │ │  (gynsurg_sample/)  │  │
                  │      └────────────┘ └─────────────────────┘  │
                  └──────────────────────────────────────────────┘
   admin ────────► SSM Session Manager (sem SSH público)

   best.pt ──────► Hugging Face Hub (puxado no boot do container)
```

## Estrutura

```
terraform/
├── modules/
│   └── runtime/main.tf      # EC2 + SG + IAM/SSM + EIP + user_data
│                            # bootstrap: docker + compose + clone repo
│                            #            + fetch OPENAI key do SSM
│                            # (best.pt vem do Hugging Face Hub via container)
│
└── environments/
    └── demo/main.tf         # instancia o módulo runtime
                             # outputs: URLs, instance_id, SSM command
```

## Pré-requisitos

| Requisito | Notas |
|---|---|
| `terraform` CLI ≥ 1.0 | `brew install terraform` |
| `aws` CLI configurado | `aws configure` ou `~/.aws/credentials` válidos |
| Conta AWS com permissões | EC2, IAM, SSM, EBS, EIP (S3 só leitura no bucket de clips externo) |
| Chave OpenAI | Para o SSM Parameter Store (Insight não funciona sem ela) |
| Bucket `surgical-detection-datasets-dev` | Pré-existente (do projeto surgical-video-ai) — fonte dos clips GynSurg do Surgical |

## Workflow completo

### 1. Provisionar a infra

```bash
cd sentinel-health/terraform/environments/demo
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

Tempo de provisionamento: ~3-5 min (cria IAM, EC2, EIP).

### 2. Obter outputs

```bash
terraform output

# Exemplo:
# public_url           = "http://54.123.45.67/"
# surgical_url         = "http://54.123.45.67/surgical/"
# insight_url          = "http://54.123.45.67/insight/"
# instance_id          = "i-0abc123..."
# ssm_session_command  = "aws ssm start-session --target i-0abc123... --region us-east-1"
```

### 3. `best.pt` — não precisa fazer nada

O container Surgical baixa automaticamente do [Hugging Face Hub](https://huggingface.co/zagari/sentinel-surgical-yolov8m-bleeding)
no primeiro boot, via seu `entrypoint.sh`.

### 4. Setar `OPENAI_API_KEY` no SSM Parameter Store

```bash
aws ssm put-parameter \
  --name /sentinel-health/demo/openai-api-key \
  --type SecureString \
  --value sk-proj-... \
  --region us-east-1
```

> **Importante:** se você fez o `apply` **antes** do passo 4, o user_data do EC2 já rodou sem encontrar a key. Após colocá-la no SSM, reinicie o stack remotamente:
>
> ```bash
> INSTANCE_ID=$(terraform output -raw instance_id)
> aws ssm start-session --target "$INSTANCE_ID" --region us-east-1
> # dentro da sessão:
> sudo su -c "
>   cd /home/ec2-user/sentinel-health
>   git pull
>   OPENAI_KEY=\$(aws ssm get-parameter --name /sentinel-health/demo/openai-api-key --with-decryption --query Parameter.Value --output text --region us-east-1)
>   echo OPENAI_API_KEY=\$OPENAI_KEY > modules/insight/emotion-recognizer/.env
>   chmod 600 modules/insight/emotion-recognizer/.env
>   cd deploy && docker compose restart
> " ec2-user
> ```

### 5. Validar

```bash
# Aguardar bootstrap completar (~3-5 min após apply)
URL=$(terraform output -raw public_url)
curl -fsS "${URL}"
curl -fsS "${URL}surgical/health"
curl -fsS "${URL}insight/_stcore/health"
```

Abra no browser:
- `http://<EIP>/` → landing
- `http://<EIP>/surgical/` → UI do Surgical
- `http://<EIP>/insight/` → UI do Insight

### 6. Acessar shell para troubleshooting (sem SSH)

```bash
aws ssm start-session --target $(terraform output -raw instance_id) --region us-east-1
# dentro da sessão:
sudo su - ec2-user
cd ~/sentinel-health/deploy
docker compose ps
docker compose logs -f
```

Ou inspecionar o log de bootstrap:

```bash
tail -200 /var/log/sentinel-bootstrap.log
```

### 7. Destruir tudo

```bash
cd sentinel-health/terraform/environments/demo
terraform destroy
```

> Remove EC2, EIP, SG, IAM role e instance profile. Não toca no SSM parameter (`/sentinel-health/demo/openai-api-key`) nem no bucket externo `surgical-detection-datasets-dev`.

## Custo estimado

| Recurso | Custo | Notas |
|---|---:|---|
| EC2 t3.medium (us-east-1) | $0.0416/h | $30/mês se sempre ligado |
| EBS gp3 30 GB | $0.08/GB/mês × 30 | ~$2.40/mês; FREE pelos primeiros 12 meses (até 30 GB) |
| Elastic IP | $0 quando associado, $0.005/h se não associado | mantemos associado |
| Data transfer out | $0.09/GB após 1 GB free | ~$0 para demo de poucos minutos |
| SSM Parameter Store (Standard) | grátis | até 10K parâmetros |
| SSM Session Manager | grátis | sem custo de minuto |
| **Demo de 1 hora** | **~$0.04** | |
| **Sempre ligado 24/7** | **~$30/mês** | t3.medium é o item dominante |

## Variáveis customizáveis

Para mudar defaults sem editar os módulos:

```bash
terraform apply \
  -var="aws_region=sa-east-1" \
  -var="instance_type=t3.large" \
  -var="environment=staging"
```

Variáveis disponíveis no env `demo`:
- `aws_region` (default: `us-east-1`)
- `environment` (default: `demo`)
- `project_name` (default: `sentinel-health`)
- `instance_type` (default: `t3.medium`)

## Diferenças vs Terraform do `modules/surgical/`

| Aspecto | surgical/training | sentinel-health/demo |
|---|---|---|
| Propósito | Treinar YOLO com GPU | Servir 3 containers atrás de nginx |
| Instance | t3.xlarge → g4dn.xlarge | t3.medium |
| AMI | Deep Learning Ubuntu (GPU) | Amazon Linux 2023 (CPU, light) |
| Acesso admin | SSH com porta 22 aberta ao mundo | SSM Session Manager (sem porta SSH) |
| Repo URL | hardcoded no user_data | variável `repo_url` |
| Secrets | env var em `~/.aws/` | SSM Parameter Store (SecureString) |
| Bucket de results | sim, com lifecycle 90d | não (uploads ficam em volume EBS) |
| Inference module | SageMaker endpoint separado | inferência roda no mesmo EC2 |
| Custo/hora | $0.166 (t3.xl) ou $0.526 (g4dn) | $0.0416 (t3.medium) |

## Segurança

- **Sem SSH público.** Único acesso shell é via SSM Session Manager (IAM-controlled, auditado em CloudTrail).
- **IAM least-privilege.** Role do EC2 tem apenas: SSM Session Manager + leitura do parâmetro `OPENAI_API_KEY` + read-only no bucket externo `surgical-detection-datasets-dev`.
- **Secrets fora do código.** OPENAI_API_KEY no SSM Parameter Store (SecureString); não vai para o `.env` versionado.
- **TLS.** Esta versão serve HTTP plano. Para HTTPS, adicionar ACM cert + ALB + Route 53 (não incluído no escopo demo).

## Limitações conhecidas

- Single-AZ, single-instance (sem HA). Para demo é suficiente.
- Sem auto-scaling. Carga alta derrubaria o EC2.
- Logs locais no EC2 (não vão para CloudWatch). Para auditoria seria preciso adicionar agente CW.
- HTTP-only. Sem TLS.
- Sem domain (acessa via IP). Adicionar Route 53 record é trivial mas requer hosted zone.
