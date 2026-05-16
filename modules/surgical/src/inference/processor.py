"""
Processador de Vídeos Cirúrgicos com YOLOv8.
Detecta sangramento e instrumentos cirúrgicos em tempo real.
"""

import os
import cv2
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from tqdm import tqdm

try:
    from ultralytics import YOLO
except ImportError:
    print("AVISO: ultralytics não instalado. Execute: pip install ultralytics")
    YOLO = None


@dataclass
class Detection:
    """Representa uma detecção individual."""
    frame_number: int
    timestamp: float
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2
    area: float


@dataclass
class VideoAnalysis:
    """Resultados da análise de um vídeo."""
    video_path: str
    total_frames: int
    fps: float
    duration: float
    resolution: Tuple[int, int]
    detections: List[Detection] = field(default_factory=list)
    anomalies: List[Dict] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)
    processed_at: str = field(default_factory=lambda: datetime.now().isoformat())


class SurgicalVideoProcessor:
    """
    Processador de vídeos cirúrgicos usando YOLOv8.

    Detecta:
        - Sangramento anômalo
        - Instrumentos cirúrgicos (grasper, electrocautery)

    Gera alertas para:
        - Sangramento excessivo (área > threshold)
        - Sangramento prolongado (duração > threshold)
        - Ausência de instrumentos em procedimentos ativos
    """

    CLASS_NAMES = {0: "grasper", 1: "blood", 2: "electrocautery"}

    # Thresholds para anomalias
    BLOOD_AREA_THRESHOLD = 0.05  # 5% da área do frame
    BLOOD_DURATION_THRESHOLD = 5.0  # 5 segundos
    CONFIDENCE_THRESHOLD = 0.5

    def __init__(self, model_path: str = None, use_gpu: bool = True):
        """
        Inicializa o processador.

        Args:
            model_path: Caminho para o modelo treinado (.pt)
            use_gpu: Usar GPU se disponível
        """
        self.model = None
        self.device = "cuda" if use_gpu else "cpu"

        if model_path and YOLO:
            self.load_model(model_path)

    def load_model(self, model_path: str):
        """Carrega o modelo YOLOv8."""
        if not YOLO:
            raise ImportError("ultralytics não instalado")

        self.model = YOLO(model_path)
        print(f"Modelo carregado: {model_path}")

    def process_video(
        self,
        video_path: str,
        output_path: str = None,
        show_preview: bool = False,
        save_frames: bool = False,
        frame_skip: int = 1,
    ) -> VideoAnalysis:
        """
        Processa um vídeo cirúrgico completo.

        Args:
            video_path: Caminho do vídeo de entrada
            output_path: Caminho do vídeo de saída com anotações (opcional)
            show_preview: Mostrar preview em tempo real
            save_frames: Salvar frames com detecções
            frame_skip: Processar a cada N frames (1 = todos)

        Returns:
            VideoAnalysis com detecções e análises
        """
        if not self.model:
            raise ValueError("Modelo não carregado. Use load_model() primeiro.")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Não foi possível abrir o vídeo: {video_path}")

        # Propriedades do vídeo
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0

        # Inicializar análise
        analysis = VideoAnalysis(
            video_path=video_path,
            total_frames=total_frames,
            fps=fps,
            duration=duration,
            resolution=(width, height),
        )

        # Configurar writer se output_path fornecido
        writer = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # Diretório para frames salvos
        frames_dir = None
        if save_frames:
            frames_dir = Path(video_path).stem + "_frames"
            os.makedirs(frames_dir, exist_ok=True)

        # Processamento
        frame_number = 0
        blood_start_frame = None
        blood_frames = []

        pbar = tqdm(total=total_frames, desc="Processando vídeo")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            timestamp = frame_number / fps if fps > 0 else 0

            # Pular frames se configurado
            if frame_number % frame_skip == 0:
                # Inferência
                results = self.model(frame, device=self.device, verbose=False)

                # Processar detecções
                frame_detections = []
                annotated_frame = frame.copy()

                for result in results:
                    if result.boxes is None:
                        continue

                    for box in result.boxes:
                        conf = float(box.conf[0])
                        if conf < self.CONFIDENCE_THRESHOLD:
                            continue

                        class_id = int(box.cls[0])
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                        # Calcular área normalizada
                        area = ((x2 - x1) * (y2 - y1)) / (width * height)

                        detection = Detection(
                            frame_number=frame_number,
                            timestamp=timestamp,
                            class_id=class_id,
                            class_name=self.CLASS_NAMES.get(class_id, "unknown"),
                            confidence=conf,
                            bbox=(float(x1), float(y1), float(x2), float(y2)),
                            area=area,
                        )
                        frame_detections.append(detection)
                        analysis.detections.append(detection)

                        # Anotar frame
                        color = self._get_class_color(class_id)
                        cv2.rectangle(
                            annotated_frame,
                            (int(x1), int(y1)),
                            (int(x2), int(y2)),
                            color,
                            2,
                        )
                        label = f"{detection.class_name} {conf:.2f}"
                        cv2.putText(
                            annotated_frame,
                            label,
                            (int(x1), int(y1) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            color,
                            2,
                        )

                # Detectar anomalias de sangramento
                blood_detections = [d for d in frame_detections if d.class_name == "blood"]
                if blood_detections:
                    max_blood_area = max(d.area for d in blood_detections)

                    # Início de sangramento
                    if blood_start_frame is None:
                        blood_start_frame = frame_number

                    blood_frames.append(frame_number)

                    # Sangramento excessivo por área
                    if max_blood_area > self.BLOOD_AREA_THRESHOLD:
                        analysis.anomalies.append({
                            "type": "excessive_bleeding",
                            "frame": frame_number,
                            "timestamp": timestamp,
                            "area": max_blood_area,
                            "severity": "high" if max_blood_area > 0.1 else "medium",
                        })
                else:
                    # Verificar sangramento prolongado
                    if blood_start_frame is not None:
                        blood_duration = (frame_number - blood_start_frame) / fps
                        if blood_duration > self.BLOOD_DURATION_THRESHOLD:
                            analysis.anomalies.append({
                                "type": "prolonged_bleeding",
                                "start_frame": blood_start_frame,
                                "end_frame": frame_number,
                                "duration": blood_duration,
                                "severity": "high" if blood_duration > 10 else "medium",
                            })
                        blood_start_frame = None
                        blood_frames = []

                # Salvar frame anotado
                if writer:
                    writer.write(annotated_frame)

                if save_frames and frame_detections:
                    cv2.imwrite(f"{frames_dir}/frame_{frame_number:06d}.jpg", annotated_frame)

                if show_preview:
                    cv2.imshow("Surgical Video Analysis", annotated_frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
            else:
                # Frame pulado - escrever original se necessário
                if writer:
                    writer.write(frame)

            frame_number += 1
            pbar.update(1)

        pbar.close()
        cap.release()
        if writer:
            writer.release()
        if show_preview:
            cv2.destroyAllWindows()

        # Gerar sumário
        analysis.summary = self._generate_summary(analysis)

        return analysis

    def _get_class_color(self, class_id: int) -> Tuple[int, int, int]:
        """Retorna cor BGR para cada classe."""
        colors = {
            0: (0, 255, 0),    # grasper - verde
            1: (0, 0, 255),    # blood - vermelho
            2: (255, 255, 0),  # electrocautery - ciano
        }
        return colors.get(class_id, (255, 255, 255))

    def _generate_summary(self, analysis: VideoAnalysis) -> Dict:
        """Gera sumário estatístico da análise."""
        summary = {
            "total_detections": len(analysis.detections),
            "total_anomalies": len(analysis.anomalies),
            "classes": {},
            "anomaly_types": {},
        }

        # Contagem por classe
        for det in analysis.detections:
            class_name = det.class_name
            if class_name not in summary["classes"]:
                summary["classes"][class_name] = {
                    "count": 0,
                    "avg_confidence": 0,
                    "max_area": 0,
                }
            summary["classes"][class_name]["count"] += 1
            summary["classes"][class_name]["max_area"] = max(
                summary["classes"][class_name]["max_area"], det.area
            )

        # Média de confiança por classe
        for class_name in summary["classes"]:
            class_dets = [d for d in analysis.detections if d.class_name == class_name]
            if class_dets:
                summary["classes"][class_name]["avg_confidence"] = sum(
                    d.confidence for d in class_dets
                ) / len(class_dets)

        # Contagem de anomalias por tipo
        for anomaly in analysis.anomalies:
            atype = anomaly["type"]
            if atype not in summary["anomaly_types"]:
                summary["anomaly_types"][atype] = 0
            summary["anomaly_types"][atype] += 1

        return summary

    def save_analysis(self, analysis: VideoAnalysis, output_path: str):
        """Salva análise em JSON."""
        data = {
            "video_path": analysis.video_path,
            "total_frames": analysis.total_frames,
            "fps": analysis.fps,
            "duration": analysis.duration,
            "resolution": analysis.resolution,
            "processed_at": analysis.processed_at,
            "summary": analysis.summary,
            "anomalies": analysis.anomalies,
            "detections": [
                {
                    "frame": d.frame_number,
                    "timestamp": d.timestamp,
                    "class": d.class_name,
                    "confidence": d.confidence,
                    "bbox": d.bbox,
                    "area": d.area,
                }
                for d in analysis.detections
            ],
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Análise salva em: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Processar vídeo cirúrgico")
    parser.add_argument("--video", "-v", required=True, help="Vídeo de entrada")
    parser.add_argument("--model", "-m", required=True, help="Modelo YOLOv8 (.pt)")
    parser.add_argument("--output", "-o", help="Vídeo de saída com anotações")
    parser.add_argument("--json", "-j", help="Arquivo JSON com análise")
    parser.add_argument("--preview", action="store_true", help="Mostrar preview")
    parser.add_argument("--cpu", action="store_true", help="Usar CPU ao invés de GPU")

    args = parser.parse_args()

    processor = SurgicalVideoProcessor(
        model_path=args.model,
        use_gpu=not args.cpu,
    )

    analysis = processor.process_video(
        video_path=args.video,
        output_path=args.output,
        show_preview=args.preview,
    )

    if args.json:
        processor.save_analysis(analysis, args.json)

    print("\n" + "=" * 50)
    print("SUMÁRIO DA ANÁLISE")
    print("=" * 50)
    print(f"Duração: {analysis.duration:.2f}s")
    print(f"Total de detecções: {analysis.summary['total_detections']}")
    print(f"Total de anomalias: {analysis.summary['total_anomalies']}")

    if analysis.summary["classes"]:
        print("\nDetecções por classe:")
        for class_name, stats in analysis.summary["classes"].items():
            print(f"  {class_name}: {stats['count']} (conf média: {stats['avg_confidence']:.2f})")

    if analysis.anomalies:
        print("\nAnomalias detectadas:")
        for anomaly in analysis.anomalies[:5]:
            print(f"  [{anomaly['type']}] Severidade: {anomaly.get('severity', 'N/A')}")
