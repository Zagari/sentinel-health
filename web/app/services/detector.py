"""
Serviço de detecção usando YOLOv8.
"""
import cv2
import json
from pathlib import Path
from typing import Callable, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class VideoDetector:
    """Detector de sangramento e instrumentos em vídeos cirúrgicos."""

    def __init__(self, model_path: str = "models/best.pt"):
        """
        Inicializa o detector.

        Args:
            model_path: Caminho para o modelo YOLOv8 treinado
        """
        self.model_path = model_path
        self.model = None
        self._load_model()

    def _load_model(self):
        """Carrega o modelo YOLOv8."""
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            logger.info(f"Modelo carregado: {self.model_path}")
            logger.info(f"Classes: {self.model.names}")
        except Exception as e:
            logger.error(f"Erro ao carregar modelo: {e}")
            raise

    def process_video(
        self,
        video_path: str,
        output_dir: str,
        job_id: str,
        progress_callback: Optional[Callable[[float], None]] = None,
        conf_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        Processa vídeo e gera resultados.

        Args:
            video_path: Caminho do vídeo de entrada
            output_dir: Diretório para salvar resultados
            job_id: ID único do job
            progress_callback: Função para reportar progresso (0-100)
            conf_threshold: Threshold de confiança para detecções

        Returns:
            Dict com caminho do vídeo anotado, relatório e sumário
        """
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"Não foi possível abrir o vídeo: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logger.info(f"Processando vídeo: {total_frames} frames, {fps} fps, {width}x{height}")

        # Output video
        output_dir = Path(output_dir)
        output_video = output_dir / f"{job_id}_annotated.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(str(output_video), fourcc, fps, (width, height))

        # Estatísticas
        detections = []
        class_counts = {}
        frames_with_blood = 0
        frames_with_grasper = 0

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Detectar
            results = self.model(frame, conf=conf_threshold, verbose=False)

            # Processar resultados
            frame_has_blood = False
            frame_has_grasper = False

            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        cls_id = int(box.cls[0])
                        cls_name = self.model.names[cls_id]
                        conf = float(box.conf[0])

                        # Contar
                        class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

                        if cls_name == "blood":
                            frame_has_blood = True
                        elif cls_name == "grasper":
                            frame_has_grasper = True

                        # Registrar detecção
                        detections.append({
                            "frame": frame_idx,
                            "timestamp": round(frame_idx / fps, 2),
                            "class": cls_name,
                            "confidence": round(conf, 3),
                            "bbox": [round(x, 1) for x in box.xyxy[0].tolist()]
                        })

            if frame_has_blood:
                frames_with_blood += 1
            if frame_has_grasper:
                frames_with_grasper += 1

            # Desenhar anotações
            annotated = results[0].plot()
            writer.write(annotated)

            # Progresso
            frame_idx += 1
            if progress_callback and frame_idx % 10 == 0:
                progress = (frame_idx / total_frames) * 100
                progress_callback(progress)

        cap.release()
        writer.release()

        # Gerar sumário
        duration_seconds = total_frames / fps
        summary = {
            "video_path": video_path,
            "total_frames": total_frames,
            "duration_seconds": round(duration_seconds, 2),
            "fps": round(fps, 2),
            "resolution": f"{width}x{height}",
            "total_detections": len(detections),
            "detections_by_class": class_counts,
            "frames_with_blood": frames_with_blood,
            "frames_with_grasper": frames_with_grasper,
            "blood_detection_rate": round(frames_with_blood / max(total_frames, 1) * 100, 2),
            "grasper_detection_rate": round(frames_with_grasper / max(total_frames, 1) * 100, 2),
            "processed_at": datetime.now().isoformat(),
            "model": self.model_path,
            "confidence_threshold": conf_threshold
        }

        # Salvar JSON
        json_path = output_dir / f"{job_id}_detections.json"
        with open(json_path, "w") as f:
            json.dump({"summary": summary, "detections": detections}, f, indent=2)

        logger.info(f"Processamento concluído: {len(detections)} detecções")

        return {
            "video": str(output_video),
            "json": str(json_path),
            "summary": summary
        }

    def detect_frame(self, frame, conf_threshold: float = 0.3) -> Dict[str, Any]:
        """
        Detecta objetos em um único frame.

        Args:
            frame: Frame do OpenCV (numpy array)
            conf_threshold: Threshold de confiança

        Returns:
            Dict com detecções e frame anotado
        """
        results = self.model(frame, conf=conf_threshold, verbose=False)

        detections = []
        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = self.model.names[cls_id]
                    conf = float(box.conf[0])

                    detections.append({
                        "class": cls_name,
                        "confidence": round(conf, 3),
                        "bbox": [round(x, 1) for x in box.xyxy[0].tolist()]
                    })

        annotated = results[0].plot()

        return {
            "detections": detections,
            "annotated_frame": annotated
        }
