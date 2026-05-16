#!/bin/bash
# =============================================================================
# Setup do servidor para treinamento YOLOv8
# Executar uma única vez no servidor
# =============================================================================

set -e

echo "========================================"
echo "  SETUP DO SERVIDOR - SURGICAL VIDEO AI"
echo "========================================"

# Verificar GPU NVIDIA
echo ""
echo "[1/5] Verificando GPU..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total --format=csv
    echo "✅ GPU NVIDIA detectada"
else
    echo "❌ nvidia-smi não encontrado. Instale os drivers NVIDIA primeiro."
    echo "   sudo apt install nvidia-driver-535"
    exit 1
fi

# Verificar/instalar Python
echo ""
echo "[2/5] Verificando Python..."
if command -v python3 &> /dev/null; then
    python3 --version
    echo "✅ Python instalado"
else
    echo "Instalando Python..."
    sudo apt update && sudo apt install -y python3 python3-pip python3-venv
fi

# Criar ambiente virtual
echo ""
echo "[3/5] Criando ambiente virtual..."
VENV_DIR="$HOME/surgical-venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "✅ Ambiente virtual criado em $VENV_DIR"
else
    echo "✅ Ambiente virtual já existe"
fi

# Ativar e instalar dependências
echo ""
echo "[4/5] Instalando dependências..."
source "$VENV_DIR/bin/activate"

pip install --upgrade pip

# Instalar PyTorch com CUDA (do índice oficial)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Instalar ultralytics e outras dependências (do PyPI)
pip install ultralytics boto3 opencv-python-headless pyyaml tqdm fpdf2

# Verificar instalação
echo ""
echo "[5/5] Verificando instalação..."
python3 -c "import torch; print(f'PyTorch: {torch.__version__}')"
python3 -c "import torch; print(f'CUDA disponível: {torch.cuda.is_available()}')"
python3 -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
python3 -c "from ultralytics import YOLO; print('Ultralytics: OK')"

echo ""
echo "========================================"
echo "  SETUP CONCLUÍDO!"
echo "========================================"
echo ""
echo "Para ativar o ambiente:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "Próximo passo:"
echo "  ./scripts/server-train.sh"
