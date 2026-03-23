from io import BytesIO

from django.http import HttpResponse
from django.utils.text import slugify
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _build_styles():
    styles = getSampleStyleSheet()
    return {
        "header": ParagraphStyle(
            "ResultHeader",
            parent=styles["Heading1"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=24,
            textColor=colors.HexColor("#0ea4ba"),
            spaceAfter=6,
        ),
        "subheader": ParagraphStyle(
            "ResultSubheader",
            parent=styles["BodyText"],
            alignment=TA_CENTER,
            fontName="Helvetica",
            fontSize=12,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=16,
        ),
        "title": ParagraphStyle(
            "ResultTitle",
            parent=styles["Heading2"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=18,
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#1e293b"),
        ),
        "table_label": ParagraphStyle(
            "TableLabel",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#475569"),
        ),
        "status": ParagraphStyle(
            "ResultStatus",
            parent=styles["Heading2"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=colors.HexColor("#166534"),
        ),
    }


def _build_footer(canvas, doc, generated_at):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#e2e8f0"))
    canvas.line(doc.leftMargin, 1.7 * cm, doc.leftMargin + doc.width, 1.7 * cm)
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    page_center = doc.leftMargin + (doc.width / 2)
    canvas.drawCentredString(
        page_center,
        1.2 * cm,
        "This is a computer-generated document and requires no physical signature.",
    )
    canvas.drawCentredString(
        page_center,
        0.85 * cm,
        f"Generated on {generated_at:%Y-%m-%d %H:%M:%S}",
    )
    canvas.restoreState()


def render_result_pdf(result, generated_at):
    buffer = BytesIO()
    styles = _build_styles()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2.5 * cm,
        title="Statement of Results",
        author="Online Examination System",
    )

    student_name = result.student.user.get_full_name().strip() or result.student.user.username
    matric_number = result.student.matric_number or "N/A"
    status_text = "PASSED" if result.passed else "FAILED"
    status_background = "#f0fdf4" if result.passed else "#fef2f2"
    status_border = "#bbf7d0" if result.passed else "#fecaca"
    status_color = "#166534" if result.passed else "#991b1b"
    styles["status"].textColor = colors.HexColor(status_color)

    story = [
        Paragraph("Online Examination System", styles["header"]),
        Paragraph("Official Examination Result Slip", styles["subheader"]),
        Paragraph("Statement of Results", styles["title"]),
    ]

    student_table_data = [
        [
            Paragraph("Student Name:", styles["table_label"]),
            Paragraph(student_name, styles["table_cell"]),
        ],
        [
            Paragraph("Matric Number:", styles["table_label"]),
            Paragraph(matric_number, styles["table_cell"]),
        ],
        [
            Paragraph("Course/Exam:", styles["table_label"]),
            Paragraph(result.exam.course_name, styles["table_cell"]),
        ],
        [
            Paragraph("Date of Exam:", styles["table_label"]),
            Paragraph(result.date.strftime("%B %d, %Y at %H:%M"), styles["table_cell"]),
        ],
        [
            Paragraph("Attempt Number:", styles["table_label"]),
            Paragraph(str(result.attempt_number), styles["table_cell"]),
        ],
    ]
    student_table = Table(student_table_data, colWidths=[5.2 * cm, 10.3 * cm], hAlign="LEFT")
    student_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend([student_table, Spacer(1, 0.7 * cm)])

    result_table_data = [
        [
            Paragraph("Category", styles["table_label"]),
            Paragraph("Score / Details", styles["table_label"]),
        ],
        [
            Paragraph("Total Questions", styles["table_cell"]),
            Paragraph(str(result.total_questions), styles["table_cell"]),
        ],
        [
            Paragraph("Correct Answers", styles["table_cell"]),
            Paragraph(str(result.correct_answers), styles["table_cell"]),
        ],
        [
            Paragraph("Total Marks Obtained", styles["table_cell"]),
            Paragraph(f"{result.marks} / {result.total_possible_marks}", styles["table_cell"]),
        ],
        [
            Paragraph("Percentage Score", styles["table_cell"]),
            Paragraph(f"{result.percentage}%", styles["table_cell"]),
        ],
        [
            Paragraph("Minimum Pass Mark", styles["table_cell"]),
            Paragraph(f"{result.exam.pass_mark}%", styles["table_cell"]),
        ],
    ]
    result_table = Table(result_table_data, colWidths=[7.4 * cm, 8.1 * cm], hAlign="LEFT")
    result_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#475569")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.75, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.extend([result_table, Spacer(1, 0.7 * cm)])

    status_table = Table(
        [[Paragraph(f"RESULT: {status_text}", styles["status"])]],
        colWidths=[15.5 * cm],
        hAlign="LEFT",
    )
    status_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(status_background)),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor(status_border)),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    story.append(status_table)

    document.build(
        story,
        onFirstPage=lambda canvas, doc: _build_footer(canvas, doc, generated_at),
        onLaterPages=lambda canvas, doc: _build_footer(canvas, doc, generated_at),
    )

    file_stub = slugify(f"{student_name}-{result.exam.course_name}") or f"result-{result.pk}"
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{file_stub}-result-slip.pdf"'
    return response
