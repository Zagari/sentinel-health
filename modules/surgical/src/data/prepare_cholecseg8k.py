"""
Preparação do dataset CholecSeg8k para formato YOLO.
Converte máscaras de segmentação para bounding boxes.

Classes do CholecSeg8k:
    0: Background
    1: Abdominal Wall
    2: Liver
    3: Gastrointestinal Tract
    4: Fat
    5: Grasper
    6: Connective Tissue
    7: Blood
    8: Cystic Duct
    9: L-hook Electrocautery
    10: Gallbladder
    11: Hepatic Vein
    12: Liver Ligament

Para este projeto, focamos em:
    - Blood (7): Detecção de sangramento
    - Grasper (5): Instrumento cirúrgico
    - L-hook Electrocautery (9): Instrumento cirúrgico
"""

import os
import cv2
import numpy as np
from pathlib import Path
from tqdm import tqdm
import yaml
import shutil
from sklearn.model_selection import train_test_split


# Configuração das classes de interesse
# Valores reais encontrados nas máscaras watershed do CholecSeg8k:
#   23 = Blood (RGB 255, 85, 0 - laranja/vermelho)
#   50 = Grasper (RGB 127, 127, 127 - cinza)
CLASSES_OF_INTEREST = {
    50: "grasper",
    23: "blood",
}

# Mapeamento para YOLO (índices começam em 0)
YOLO_CLASS_MAP = {
    50: 0,  # grasper -> 0
    23: 1,  # blood -> 1
}


def mask_to_bbox(mask: np.ndarray, class_id: int) -> list:
    """
    Converte máscara de segmentação para bounding boxes no formato YOLO.

    Args:
        mask: Máscara de segmentação (H, W) com IDs de classe
        class_id: ID da classe para extrair

    Returns:
        Lista de bounding boxes no formato YOLO [class, x_center, y_center, width, height]
    """
    bboxes = []
    height, width = mask.shape

    # Criar máscara binária para a classe
    binary_mask = (mask == class_id).astype(np.uint8)

    if binary_mask.sum() == 0:
        return bboxes

    # Encontrar contornos
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        # Ignorar contornos muito pequenos (ruído)
        if cv2.contourArea(contour) < 100:
            continue

        x, y, w, h = cv2.boundingRect(contour)

        # Converter para formato YOLO (normalizado)
        x_center = (x + w / 2) / width
        y_center = (y + h / 2) / height
        w_norm = w / width
        h_norm = h / height

        yolo_class = YOLO_CLASS_MAP[class_id]
        bboxes.append([yolo_class, x_center, y_center, w_norm, h_norm])

    return bboxes


def process_cholecseg8k(input_dir: str, output_dir: str, train_ratio: float = 0.8):
    """
    Processa o dataset CholecSeg8k e converte para formato YOLO.

    Args:
        input_dir: Diretório raiz do CholecSeg8k extraído
        output_dir: Diretório de saída para o dataset YOLO
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # Criar estrutura de diretórios YOLO
    for split in ["train", "val"]:
        (output_path / split / "images").mkdir(parents=True, exist_ok=True)
        (output_path / split / "labels").mkdir(parents=True, exist_ok=True)

    # Coletar todos os pares imagem/máscara
    all_samples = []

    # Percorrer estrutura do CholecSeg8k: video01/video01_00080/frame_*.png
    for video_dir in sorted(input_path.glob("video*")):
        for frame_dir in sorted(video_dir.glob("video*")):
            for frame_file in sorted(frame_dir.glob("*_endo.png")):
                # Pular arquivos de máscara
                if "_mask" in frame_file.name:
                    continue

                # Encontrar máscara correspondente
                mask_file = frame_file.with_name(frame_file.stem + "_watershed_mask.png")
                if not mask_file.exists():
                    mask_file = frame_file.with_name(frame_file.stem + "_mask.png")

                if mask_file.exists():
                    all_samples.append((frame_file, mask_file))

    print(f"Encontradas {len(all_samples)} amostras válidas")

    if len(all_samples) == 0:
        print("ERRO: Nenhuma amostra encontrada. Verifique a estrutura do diretório.")
        print(f"Esperado: {input_dir}/video*/frame*.png")
        return

    # Dividir em treino e validação
    train_samples, val_samples = train_test_split(
        all_samples, train_size=train_ratio, random_state=42
    )

    print(f"Treino: {len(train_samples)} amostras")
    print(f"Validação: {len(val_samples)} amostras")

    # Processar cada split
    stats = {"train": {}, "val": {}}

    for split, samples in [("train", train_samples), ("val", val_samples)]:
        class_counts = {name: 0 for name in CLASSES_OF_INTEREST.values()}

        for img_file, mask_file in tqdm(samples, desc=f"Processando {split}"):
            # Ler imagem e máscara
            img = cv2.imread(str(img_file))
            mask = cv2.imread(str(mask_file), cv2.IMREAD_GRAYSCALE)

            if img is None or mask is None:
                continue

            # Extrair bounding boxes para cada classe
            all_bboxes = []
            for class_id, class_name in CLASSES_OF_INTEREST.items():
                bboxes = mask_to_bbox(mask, class_id)
                all_bboxes.extend(bboxes)
                class_counts[class_name] += len(bboxes)

            # Gerar nome único (video01_00080_frame_100_endo)
            frame_dir_name = img_file.parent.name
            frame_name = img_file.stem
            unique_name = f"{frame_dir_name}_{frame_name}"

            # Salvar imagem
            output_img = output_path / split / "images" / f"{unique_name}.jpg"
            cv2.imwrite(str(output_img), img)

            # Salvar labels (mesmo sem detecções)
            output_label = output_path / split / "labels" / f"{unique_name}.txt"
            with open(output_label, "w") as f:
                for bbox in all_bboxes:
                    line = " ".join([str(bbox[0])] + [f"{v:.6f}" for v in bbox[1:]])
                    f.write(line + "\n")

        stats[split] = class_counts

    # Criar arquivo data.yaml
    yaml_content = {
        "path": str(output_path.absolute()),
        "train": "train/images",
        "val": "val/images",
        "names": {v: k for k, v in YOLO_CLASS_MAP.items()},
        "nc": len(CLASSES_OF_INTEREST),
    }

    # Corrigir names para usar os nomes das classes
    yaml_content["names"] = {i: name for i, (_, name) in enumerate(
        sorted([(YOLO_CLASS_MAP[k], v) for k, v in CLASSES_OF_INTEREST.items()])
    )}

    with open(output_path / "data.yaml", "w") as f:
        yaml.dump(yaml_content, f, default_flow_style=False)

    # Imprimir estatísticas
    print("\n" + "=" * 50)
    print("ESTATÍSTICAS DO DATASET")
    print("=" * 50)

    for split in ["train", "val"]:
        print(f"\n{split.upper()}:")
        for class_name, count in stats[split].items():
            print(f"  {class_name}: {count} instâncias")

    print(f"\nDataset salvo em: {output_path}")
    print(f"Arquivo de configuração: {output_path / 'data.yaml'}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Preparar CholecSeg8k para YOLO")
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Diretório raiz do CholecSeg8k extraído"
    )
    parser.add_argument(
        "--output", "-o",
        default="data/yolo_format",
        help="Diretório de saída (default: data/yolo_format)"
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.8,
        help="Proporção de dados para treino (default: 0.8)"
    )

    args = parser.parse_args()
    process_cholecseg8k(args.input, args.output, args.train_ratio)
