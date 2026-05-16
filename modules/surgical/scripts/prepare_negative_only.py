from pathlib import Path
import shutil

source_dir = Path("anotacoes-gynsurg/yolo_export")
output_dir = Path("anotacoes-gynsurg/negative_only")

# Criar estrutura
(output_dir / "images/train").mkdir(parents=True, exist_ok=True)
(output_dir / "labels/train").mkdir(parents=True, exist_ok=True)

copied = 0
for label_file in (source_dir / "labels/train").glob("*.txt"):
    content = label_file.read_text().strip()

    # Só copiar frames SEM sangramento (labels vazios)
    if not content:
        img_name = label_file.stem + ".jpg"
        img_src = source_dir / "images/train" / img_name
        if img_src.exists():
            shutil.copy(img_src, output_dir / "images/train" / img_name)
            shutil.copy(label_file, output_dir / "labels/train" / label_file.name)
            copied += 1

print(f"Copiados {copied} frames negativos (sem sangramento)")

# Criar data.yaml
data_yaml = output_dir / "data.yaml"
data_yaml.write_text(f"""path: {output_dir.absolute()}
train: images/train
val: images/train
nc: 2
names:
  0: grasper
  1: blood
""")
print(f"Criado: {data_yaml}")
