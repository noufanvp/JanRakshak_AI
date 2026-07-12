"""
JanRakshak AI
PDF Report Export
"""

import os
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet


class PDFExporter:

    def __init__(self):

        self.output_folder = "reports"

        os.makedirs(self.output_folder, exist_ok=True)

    def export(self, report):

        report_id = report[0]

        filename = os.path.join(
            self.output_folder,
            f"Report_{report_id}.pdf"
        )

        styles = getSampleStyleSheet()

        pdf = SimpleDocTemplate(filename)

        story = []

        story.append(
            Paragraph("<b>JanRakshak AI Report</b>", styles["Title"])
        )

        story.append(
            Paragraph(f"<b>Report ID:</b> {report[0]}", styles["Normal"])
        )

        story.append(
            Paragraph(f"<b>Description:</b> {report[1]}", styles["Normal"])
        )

        story.append(
            Paragraph(f"<b>Issue:</b> {report[2]}", styles["Normal"])
        )

        story.append(
            Paragraph(f"<b>Priority:</b> {report[3]}", styles["Normal"])
        )

        story.append(
            Paragraph(f"<b>Department:</b> {report[4]}", styles["Normal"])
        )

        story.append(
            Paragraph(f"<b>Confidence:</b> {report[5]}", styles["Normal"])
        )

        story.append(
            Paragraph(f"<b>Advice:</b> {report[6]}", styles["Normal"])
        )

        story.append(
            Paragraph(f"<b>Risk Score:</b> {report[7]}", styles["Normal"])
        )

        story.append(
            Paragraph(f"<b>Reason:</b> {report[8]}", styles["Normal"])
        )

        story.append(
            Paragraph(f"<b>Suggested Action:</b> {report[9]}", styles["Normal"])
        )

        pdf.build(story)

        return filename