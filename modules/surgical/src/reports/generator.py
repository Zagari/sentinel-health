"""
Gerador de Relatórios PDF para Análise de Vídeos Cirúrgicos.
Cria relatórios profissionais com detecções, anomalias e recomendações.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

try:
    from fpdf import FPDF
except ImportError:
    print("AVISO: fpdf2 não instalado. Execute: pip install fpdf2")
    FPDF = None


class SurgicalReportGenerator:
    """
    Gerador de relatórios PDF para análises cirúrgicas.

    Inclui:
        - Resumo executivo
        - Estatísticas de detecção
        - Lista de anomalias com severidade
        - Recomendações clínicas
        - Linha do tempo de eventos
    """

    SEVERITY_COLORS = {
        "high": (255, 0, 0),      # Vermelho
        "medium": (255, 165, 0),  # Laranja
        "low": (255, 255, 0),     # Amarelo
    }

    def __init__(self):
        """Inicializa o gerador de relatórios."""
        if not FPDF:
            raise ImportError("fpdf2 não instalado. Execute: pip install fpdf2")

    def generate_report(
        self,
        analysis_json: str,
        output_path: str,
        title: str = "Relatório de Análise Cirúrgica",
        include_timeline: bool = True,
    ) -> str:
        """
        Gera relatório PDF a partir de análise JSON.

        Args:
            analysis_json: Caminho do arquivo JSON com análise
            output_path: Caminho do PDF de saída
            title: Título do relatório
            include_timeline: Incluir linha do tempo de eventos

        Returns:
            Caminho do PDF gerado
        """
        # Carregar análise
        with open(analysis_json, "r") as f:
            analysis = json.load(f)

        # Criar PDF
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Página de capa
        self._add_cover_page(pdf, title, analysis)

        # Resumo executivo
        self._add_executive_summary(pdf, analysis)

        # Estatísticas de detecção
        self._add_detection_stats(pdf, analysis)

        # Anomalias detectadas
        if analysis.get("anomalies"):
            self._add_anomalies_section(pdf, analysis)

        # Linha do tempo
        if include_timeline and analysis.get("detections"):
            self._add_timeline(pdf, analysis)

        # Recomendações
        self._add_recommendations(pdf, analysis)

        # Salvar PDF
        pdf.output(output_path)
        print(f"Relatório gerado: {output_path}")

        return output_path

    def _add_cover_page(self, pdf: FPDF, title: str, analysis: Dict):
        """Adiciona página de capa."""
        pdf.add_page()

        # Título
        pdf.set_font("Helvetica", "B", 24)
        pdf.cell(0, 40, "", ln=True)
        pdf.cell(0, 15, title, ln=True, align="C")

        # Subtítulo
        pdf.set_font("Helvetica", "", 14)
        pdf.cell(0, 10, "Sistema de Detecção de Anomalias em Cirurgias", ln=True, align="C")

        # Linha divisória
        pdf.cell(0, 20, "", ln=True)
        pdf.set_draw_color(0, 0, 128)
        pdf.line(40, pdf.get_y(), 170, pdf.get_y())

        # Informações do vídeo
        pdf.cell(0, 20, "", ln=True)
        pdf.set_font("Helvetica", "", 12)

        video_name = Path(analysis.get("video_path", "N/A")).name
        pdf.cell(0, 8, f"Vídeo analisado: {video_name}", ln=True, align="C")

        duration = analysis.get("duration", 0)
        pdf.cell(0, 8, f"Duração: {duration:.2f} segundos", ln=True, align="C")

        resolution = analysis.get("resolution", [0, 0])
        pdf.cell(0, 8, f"Resolução: {resolution[0]}x{resolution[1]}", ln=True, align="C")

        # Data de processamento
        pdf.cell(0, 30, "", ln=True)
        processed_at = analysis.get("processed_at", datetime.now().isoformat())
        pdf.cell(0, 8, f"Processado em: {processed_at[:19].replace('T', ' ')}", ln=True, align="C")

        # Rodapé
        pdf.set_y(-30)
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 10, "Surgical Video AI - FIAP Tech Challenge Fase 4", align="C")

    def _add_executive_summary(self, pdf: FPDF, analysis: Dict):
        """Adiciona resumo executivo."""
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Resumo Executivo", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.cell(0, 5, "", ln=True)

        summary = analysis.get("summary", {})
        anomalies = analysis.get("anomalies", [])

        # Status geral
        pdf.set_font("Helvetica", "B", 12)
        high_severity = sum(1 for a in anomalies if a.get("severity") == "high")

        if high_severity > 0:
            pdf.set_text_color(255, 0, 0)
            status = "ATENCAO NECESSARIA"
        elif len(anomalies) > 0:
            pdf.set_text_color(255, 165, 0)
            status = "REVISAO RECOMENDADA"
        else:
            pdf.set_text_color(0, 128, 0)
            status = "PROCEDIMENTO NORMAL"

        pdf.cell(0, 10, f"Status: {status}", ln=True)
        pdf.set_text_color(0, 0, 0)

        # Números principais
        pdf.cell(0, 5, "", ln=True)
        pdf.set_font("Helvetica", "", 11)

        total_detections = summary.get("total_detections", 0)
        total_anomalies = summary.get("total_anomalies", 0)
        duration = analysis.get("duration", 0)

        pdf.cell(0, 8, f"Total de deteccoes: {total_detections}", ln=True)
        pdf.cell(0, 8, f"Anomalias identificadas: {total_anomalies}", ln=True)
        pdf.cell(0, 8, f"Anomalias de alta severidade: {high_severity}", ln=True)

        # Taxa de detecção
        if duration > 0:
            rate = total_detections / duration * 60
            pdf.cell(0, 8, f"Taxa de deteccao: {rate:.1f} deteccoes/minuto", ln=True)

        # Descrição textual
        pdf.cell(0, 10, "", ln=True)
        pdf.set_font("Helvetica", "", 11)

        if high_severity > 0:
            text = (
                "O sistema detectou condicoes que requerem atencao imediata. "
                f"Foram identificadas {high_severity} anomalia(s) de alta severidade "
                "relacionadas a sangramento excessivo ou prolongado. "
                "Recomenda-se revisao detalhada das secoes marcadas."
            )
        elif total_anomalies > 0:
            text = (
                f"O procedimento apresentou {total_anomalies} anomalia(s) de severidade "
                "moderada. Embora nao representem risco imediato, recomenda-se "
                "revisao para fins de documentacao e melhoria de processos."
            )
        else:
            text = (
                "O procedimento foi realizado dentro dos parametros normais. "
                "Nao foram detectadas anomalias significativas de sangramento "
                "ou uso inadequado de instrumentos."
            )

        pdf.multi_cell(0, 6, text)

    def _add_detection_stats(self, pdf: FPDF, analysis: Dict):
        """Adiciona estatísticas de detecção."""
        pdf.cell(0, 15, "", ln=True)

        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Estatisticas de Deteccao", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.cell(0, 5, "", ln=True)

        summary = analysis.get("summary", {})
        classes = summary.get("classes", {})

        if not classes:
            pdf.set_font("Helvetica", "I", 11)
            pdf.cell(0, 10, "Nenhuma deteccao registrada.", ln=True)
            return

        # Tabela de classes
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(240, 240, 240)

        col_widths = [60, 40, 50, 40]
        headers = ["Classe", "Quantidade", "Conf. Media", "Area Max"]

        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 8, header, border=1, fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 11)
        for class_name, stats in classes.items():
            pdf.cell(col_widths[0], 8, class_name.capitalize(), border=1)
            pdf.cell(col_widths[1], 8, str(stats.get("count", 0)), border=1, align="C")
            pdf.cell(col_widths[2], 8, f"{stats.get('avg_confidence', 0):.2%}", border=1, align="C")
            pdf.cell(col_widths[3], 8, f"{stats.get('max_area', 0):.2%}", border=1, align="C")
            pdf.ln()

    def _add_anomalies_section(self, pdf: FPDF, analysis: Dict):
        """Adiciona seção de anomalias."""
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Anomalias Detectadas", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.cell(0, 5, "", ln=True)

        anomalies = analysis.get("anomalies", [])
        fps = analysis.get("fps", 30)

        # Agrupar por severidade
        for severity in ["high", "medium", "low"]:
            severity_anomalies = [a for a in anomalies if a.get("severity") == severity]
            if not severity_anomalies:
                continue

            # Título da severidade
            pdf.set_font("Helvetica", "B", 12)
            r, g, b = self.SEVERITY_COLORS.get(severity, (0, 0, 0))
            pdf.set_text_color(r, g, b)
            pdf.cell(0, 10, f"Severidade {severity.upper()} ({len(severity_anomalies)})", ln=True)
            pdf.set_text_color(0, 0, 0)

            pdf.set_font("Helvetica", "", 10)
            for anomaly in severity_anomalies[:10]:  # Limitar a 10 por severidade
                atype = anomaly.get("type", "unknown")

                if atype == "excessive_bleeding":
                    frame = anomaly.get("frame", 0)
                    timestamp = anomaly.get("timestamp", frame / fps)
                    area = anomaly.get("area", 0)
                    text = f"- Sangramento excessivo em {timestamp:.1f}s (area: {area:.1%})"

                elif atype == "prolonged_bleeding":
                    start = anomaly.get("start_frame", 0) / fps
                    end = anomaly.get("end_frame", 0) / fps
                    duration = anomaly.get("duration", end - start)
                    text = f"- Sangramento prolongado: {start:.1f}s - {end:.1f}s (duracao: {duration:.1f}s)"

                else:
                    text = f"- {atype}: frame {anomaly.get('frame', 'N/A')}"

                pdf.cell(0, 6, text, ln=True)

            pdf.cell(0, 5, "", ln=True)

    def _add_timeline(self, pdf: FPDF, analysis: Dict):
        """Adiciona linha do tempo simplificada."""
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Linha do Tempo", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.cell(0, 5, "", ln=True)

        detections = analysis.get("detections", [])
        duration = analysis.get("duration", 0)

        if not detections or duration == 0:
            pdf.set_font("Helvetica", "I", 11)
            pdf.cell(0, 10, "Sem eventos para exibir.", ln=True)
            return

        # Agrupar detecções por intervalos de 30 segundos
        interval = 30
        intervals = {}
        for det in detections:
            bucket = int(det.get("timestamp", 0) / interval) * interval
            if bucket not in intervals:
                intervals[bucket] = {"blood": 0, "grasper": 0, "electrocautery": 0}
            class_name = det.get("class", "unknown")
            if class_name in intervals[bucket]:
                intervals[bucket][class_name] += 1

        # Tabela de timeline
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(240, 240, 240)

        col_widths = [50, 40, 40, 40]
        headers = ["Intervalo", "Sangue", "Grasper", "Cauterizador"]

        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 7, header, border=1, fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 10)
        for bucket in sorted(intervals.keys()):
            data = intervals[bucket]
            start = f"{int(bucket // 60):02d}:{int(bucket % 60):02d}"
            end_sec = min(bucket + interval, int(duration))
            end = f"{int(end_sec // 60):02d}:{int(end_sec % 60):02d}"

            pdf.cell(col_widths[0], 7, f"{start} - {end}", border=1)
            pdf.cell(col_widths[1], 7, str(data["blood"]), border=1, align="C")
            pdf.cell(col_widths[2], 7, str(data["grasper"]), border=1, align="C")
            pdf.cell(col_widths[3], 7, str(data["electrocautery"]), border=1, align="C")
            pdf.ln()

    def _add_recommendations(self, pdf: FPDF, analysis: Dict):
        """Adiciona recomendações clínicas."""
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Recomendacoes", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.cell(0, 5, "", ln=True)

        anomalies = analysis.get("anomalies", [])
        high_severity = [a for a in anomalies if a.get("severity") == "high"]

        pdf.set_font("Helvetica", "", 11)

        recommendations = []

        if high_severity:
            recommendations.extend([
                "1. Revisao imediata dos momentos marcados como alta severidade",
                "2. Documentar incidentes de sangramento excessivo no prontuario",
                "3. Avaliar necessidade de intervencao adicional",
                "4. Comunicar equipe medica sobre achados criticos",
            ])

        bleeding_anomalies = [a for a in anomalies if "bleeding" in a.get("type", "")]
        if bleeding_anomalies:
            recommendations.extend([
                f"5. Total de {len(bleeding_anomalies)} eventos de sangramento registrados",
                "6. Considerar revisao de tecnica hemostasica",
            ])

        if not recommendations:
            recommendations = [
                "1. Procedimento dentro dos parametros normais",
                "2. Nenhuma acao imediata necessaria",
                "3. Manter documentacao padrao",
            ]

        for rec in recommendations:
            pdf.cell(0, 8, rec, ln=True)

        # Disclaimer
        pdf.cell(0, 20, "", ln=True)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(128, 128, 128)
        pdf.multi_cell(
            0, 5,
            "AVISO: Este relatorio foi gerado automaticamente por sistema de IA "
            "e deve ser utilizado apenas como ferramenta auxiliar. Todas as decisoes "
            "clinicas devem ser tomadas por profissionais de saude qualificados."
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gerar relatorio PDF")
    parser.add_argument("--json", "-j", required=True, help="Arquivo JSON com analise")
    parser.add_argument("--output", "-o", required=True, help="Caminho do PDF de saida")
    parser.add_argument("--title", "-t", default="Relatorio de Analise Cirurgica")

    args = parser.parse_args()

    generator = SurgicalReportGenerator()
    generator.generate_report(
        analysis_json=args.json,
        output_path=args.output,
        title=args.title,
    )
