#!/bin/bash
# =============================================================================
# Atualiza o modelo na aplicação web
# Baixa modelo do S3 e reinicia o container
# =============================================================================

set -e

S3_MODELS_BUCKET="surgical-detection-models-dev"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
WEB_MODELS_DIR="$PROJECT_DIR/web/models"

show_help() {
    echo "Uso: $0 [versão] [opções]"
    echo ""
    echo "Versões disponíveis:"
    echo "  baseline          Modelo v1 baseline (best.pt)"
    echo "  v2_classweight    Modelo v2 com class weights"
    echo "  <custom>          Qualquer nome de arquivo no S3 (sem .pt)"
    echo ""
    echo "Opções:"
    echo "  --no-restart      Não reinicia o container após atualizar"
    echo "  --list            Lista modelos disponíveis no S3"
    echo ""
    echo "Exemplos:"
    echo "  $0                      # Baixa o modelo baseline (best.pt)"
    echo "  $0 v2_classweight       # Baixa best_v2_classweight.pt"
    echo "  $0 --list               # Lista modelos no S3"
    echo "  $0 v2_classweight --no-restart"
}

list_models() {
    echo "Modelos disponíveis no S3:"
    echo ""
    aws s3 ls "s3://$S3_MODELS_BUCKET/trained/" | grep "\.pt$" | awk '{print "  " $4}'
    echo ""
}

# Processar argumentos
VERSION=""
RESTART=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --list)
            list_models
            exit 0
            ;;
        --no-restart)
            RESTART=false
            shift
            ;;
        *)
            VERSION="$1"
            shift
            ;;
    esac
done

# Determinar arquivo no S3
if [ -z "$VERSION" ] || [ "$VERSION" == "baseline" ]; then
    S3_FILE="best.pt"
    VERSION_LABEL="baseline"
else
    S3_FILE="best_${VERSION}.pt"
    VERSION_LABEL="$VERSION"
fi

echo "========================================"
echo "  ATUALIZAÇÃO DO MODELO WEB"
echo "========================================"
echo ""
echo "Versão: $VERSION_LABEL"
echo "Arquivo S3: s3://$S3_MODELS_BUCKET/trained/$S3_FILE"
echo "Destino: $WEB_MODELS_DIR/best.pt"
echo ""

# Verificar AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI não encontrado."
    exit 1
fi

# Criar diretório se não existir
mkdir -p "$WEB_MODELS_DIR"

# Verificar se arquivo existe no S3
echo "[1/3] Verificando modelo no S3..."
if ! aws s3 ls "s3://$S3_MODELS_BUCKET/trained/$S3_FILE" &> /dev/null; then
    echo "❌ Modelo não encontrado: s3://$S3_MODELS_BUCKET/trained/$S3_FILE"
    echo ""
    echo "Modelos disponíveis:"
    list_models
    exit 1
fi
echo "✅ Modelo encontrado"

# Backup do modelo atual (se existir)
if [ -f "$WEB_MODELS_DIR/best.pt" ]; then
    BACKUP_NAME="best.pt.backup.$(date +%Y%m%d_%H%M%S)"
    echo ""
    echo "[2/3] Fazendo backup do modelo atual..."
    cp "$WEB_MODELS_DIR/best.pt" "$WEB_MODELS_DIR/$BACKUP_NAME"
    echo "✅ Backup: $BACKUP_NAME"
else
    echo ""
    echo "[2/3] Nenhum modelo anterior para backup"
fi

# Baixar novo modelo
echo ""
echo "[3/3] Baixando modelo do S3..."
aws s3 cp "s3://$S3_MODELS_BUCKET/trained/$S3_FILE" "$WEB_MODELS_DIR/best.pt"
echo "✅ Modelo baixado: best.pt"

# Criar cópia versionada localmente
if [ "$VERSION_LABEL" != "baseline" ]; then
    VERSIONED_FILE="best_${VERSION_LABEL}.pt"
else
    VERSIONED_FILE="best_v1_baseline.pt"
fi
cp "$WEB_MODELS_DIR/best.pt" "$WEB_MODELS_DIR/$VERSIONED_FILE"
echo "✅ Cópia versionada: $VERSIONED_FILE"

# Criar arquivo de versão para rastreabilidade
cat > "$WEB_MODELS_DIR/model_version.txt" << EOF
version: $VERSION_LABEL
s3_file: $S3_FILE
local_file: best.pt
versioned_file: $VERSIONED_FILE
updated_at: $(date -Iseconds)
EOF

# Reiniciar container
if [ "$RESTART" = true ]; then
    echo ""
    echo "Reiniciando container..."

    cd "$PROJECT_DIR/web"

    if docker-compose ps | grep -q "Up"; then
        docker-compose restart
        echo "✅ Container reiniciado"
    else
        echo "⚠️  Container não está rodando. Inicie com:"
        echo "   cd web && docker-compose up -d"
    fi
else
    echo ""
    echo "⚠️  Container não reiniciado (--no-restart)"
    echo "   Para aplicar, execute: cd web && docker-compose restart"
fi

echo ""
echo "========================================"
echo "  MODELO ATUALIZADO!"
echo "========================================"
echo ""
echo "Versão ativa: $VERSION_LABEL"
echo "Arquivos:"
echo "  Canônico:   $WEB_MODELS_DIR/best.pt"
echo "  Versionado: $WEB_MODELS_DIR/$VERSIONED_FILE"
echo ""
