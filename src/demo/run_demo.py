"""
Script de demonstração do Surgical Video AI.
Executa pipeline completo: detecção, análise e geração de relatório.
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from inference.processor import SurgicalVideoProcessor
from reports.generator import SurgicalReportGenerator


def run_demo(
    video_path: str,
    model_path: str,
    output_dir: str = "demo_output",
    use_gpu: bool = True,
    show_preview: bool = False,
):
    """
    Executa demonstração completa do sistema.

    Args:
        video_path: Caminho do vídeo de entrada
        model_path: Caminho do modelo YOLOv8 treinado
        output_dir: Diretório para saídas
        use_gpu: Usar GPU se disponível
        show_preview: Mostrar preview em tempo real
    """
    print("=" * 60)
    print("  SURGICAL VIDEO AI - DEMONSTRAÇÃO")
    print("=" * 60)
    print()

    # Criar diretório de saída
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_name = Path(video_path).stem

    # Caminhos de saída
    output_video = output_path / f"{video_name}_analyzed_{timestamp}.mp4"
    output_json = output_path / f"{video_name}_analysis_{timestamp}.json"
    output_pdf = output_path / f"{video_name}_report_{timestamp}.pdf"

    # -------------------------------------------------------------------------
    # Etapa 1: Processamento do Vídeo
    # -------------------------------------------------------------------------
    print("[1/3] Processando vídeo...")
    print(f"      Entrada: {video_path}")
    print(f"      Modelo: {model_path}")
    print()

    processor = SurgicalVideoProcessor(
        model_path=model_path,
        use_gpu=use_gpu,
    )

    analysis = processor.process_video(
        video_path=video_path,
        output_path=str(output_video),
        show_preview=show_preview,
    )

    # Salvar análise JSON
    processor.save_analysis(analysis, str(output_json))

    print()
    print(f"      Vídeo anotado: {output_video}")
    print(f"      Análise JSON: {output_json}")
    print()

    # -------------------------------------------------------------------------
    # Etapa 2: Gerar Relatório PDF
    # -------------------------------------------------------------------------
    print("[2/3] Gerando relatório PDF...")

    generator = SurgicalReportGenerator()
    generator.generate_report(
        analysis_json=str(output_json),
        output_path=str(output_pdf),
        title="Análise de Procedimento Cirúrgico",
    )

    print(f"      Relatório: {output_pdf}")
    print()

    # -------------------------------------------------------------------------
    # Etapa 3: Exibir Resumo
    # -------------------------------------------------------------------------
    print("[3/3] Resumo da análise:")
    print()

    summary = analysis.summary
    print(f"      Duração do vídeo: {analysis.duration:.2f}s")
    print(f"      Total de frames: {analysis.total_frames}")
    print(f"      Total de detecções: {summary.get('total_detections', 0)}")
    print(f"      Total de anomalias: {summary.get('total_anomalies', 0)}")
    print()

    if summary.get("classes"):
        print("      Detecções por classe:")
        for class_name, stats in summary["classes"].items():
            print(f"        - {class_name}: {stats['count']} detecções")
    print()

    if analysis.anomalies:
        high_count = sum(1 for a in analysis.anomalies if a.get("severity") == "high")
        medium_count = sum(1 for a in analysis.anomalies if a.get("severity") == "medium")

        print("      Anomalias por severidade:")
        print(f"        - Alta: {high_count}")
        print(f"        - Média: {medium_count}")
        print()

        if high_count > 0:
            print("      ⚠️  ATENÇÃO: Anomalias de alta severidade detectadas!")
            print()

    # -------------------------------------------------------------------------
    # Conclusão
    # -------------------------------------------------------------------------
    print("=" * 60)
    print("  DEMONSTRAÇÃO CONCLUÍDA")
    print("=" * 60)
    print()
    print("Arquivos gerados:")
    print(f"  1. Vídeo anotado: {output_video}")
    print(f"  2. Análise JSON:  {output_json}")
    print(f"  3. Relatório PDF: {output_pdf}")
    print()

    return {
        "video": str(output_video),
        "json": str(output_json),
        "pdf": str(output_pdf),
        "analysis": analysis,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Demonstração do Surgical Video AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Processar vídeo local
  python run_demo.py --video videos/input/cirurgia.mp4 --model models/best.pt

  # Com preview em tempo real
  python run_demo.py --video videos/input/cirurgia.mp4 --model models/best.pt --preview

  # Usando CPU
  python run_demo.py --video videos/input/cirurgia.mp4 --model models/best.pt --cpu
        """,
    )

    parser.add_argument(
        "--video", "-v",
        required=True,
        help="Caminho do vídeo de entrada",
    )
    parser.add_argument(
        "--model", "-m",
        required=True,
        help="Caminho do modelo YOLOv8 treinado (.pt)",
    )
    parser.add_argument(
        "--output", "-o",
        default="demo_output",
        help="Diretório de saída (default: demo_output)",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Mostrar preview em tempo real",
    )
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Usar CPU ao invés de GPU",
    )

    args = parser.parse_args()

    # Verificar se arquivos existem
    if not os.path.exists(args.video):
        print(f"ERRO: Vídeo não encontrado: {args.video}")
        sys.exit(1)

    if not os.path.exists(args.model):
        print(f"ERRO: Modelo não encontrado: {args.model}")
        sys.exit(1)

    # Executar demonstração
    run_demo(
        video_path=args.video,
        model_path=args.model,
        output_dir=args.output,
        use_gpu=not args.cpu,
        show_preview=args.preview,
    )


if __name__ == "__main__":
    main()
