from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def generate_report(file_path, booking, rating, feedback):

    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("College Consultation Report", styles['Heading1']))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"Booking ID: {booking.id}", styles['Normal']))
    content.append(Paragraph(f"Guide ID: {booking.guide_id}", styles['Normal']))
    content.append(Spacer(1, 10))

    content.append(Paragraph("Guide Rating:", styles['Heading2']))
    content.append(Paragraph(f"Stars: {rating.rating}", styles['Normal']))
    content.append(Paragraph(f"Honesty: {rating.honesty}", styles['Normal']))
    content.append(Paragraph(f"Recommend: {rating.recommend}", styles['Normal']))
    content.append(Spacer(1, 10))

    content.append(Paragraph("College Insights:", styles['Heading2']))
    content.append(Paragraph(f"Faculty: {feedback.faculty_rating}", styles['Normal']))
    content.append(Paragraph(f"Placements: {feedback.placement_rating}", styles['Normal']))
    content.append(Paragraph(f"Infrastructure: {feedback.infrastructure_rating}", styles['Normal']))
    content.append(Paragraph(f"Hidden Fees: {feedback.hidden_fees}", styles['Normal']))
    content.append(Paragraph(f"Attendance: {feedback.strict_attendance}", styles['Normal']))
    content.append(Paragraph(f"Ragging: {feedback.ragging_situation}", styles['Normal']))
    content.append(Paragraph(f"Comments: {feedback.comments}", styles['Normal']))

    doc.build(content)