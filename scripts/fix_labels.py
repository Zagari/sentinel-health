import os
from pathlib import Path

labels_dir = Path("anotacoes-gynsurg/yolo_export/labels/train")

count = 0
for label_file in labels_dir.glob("*.txt"):
    content = label_file.read_text().strip()

    if content:  # Se tem conteúdo (frame com sangramento)
        label_file.write_text("1 0.5 0.5 0.2 0.2\n")
        count += 1

print(f"Labels atualizados: {count} arquivos")
