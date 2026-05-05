from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

from app.booking.models import Booking
from app.rating.models import GuideRating
from app.college.models import CollegeFeedback


def generate_summary_pdf(booking_id, db):

    # booking fetch
    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise Exception("Booking not found")

    rating = db.query(GuideRating).filter(
        GuideRating.booking_id == booking_id
    ).first()

    feedback = db.query(CollegeFeedback).filter(
        CollegeFeedback.booking_id == booking_id
    ).first()

    # folder create
    os.makedirs("summaries", exist_ok=True)

    file_path = f"summaries/summary_{booking_id}.pdf"

    c = canvas.Canvas(file_path, pagesize=letter)

    y = 750

    c.drawString(100, y, "College Consultation Summary Report")
    y -= 40

    c.drawString(100, y, f"Booking ID: {booking_id}")
    y -= 20

    # seeker rating section
    if rating:
        c.drawString(100, y, "Guide Rating:")
        y -= 20

        c.drawString(120, y, f"Rating: {rating.rating}")
        y -= 20

        c.drawString(120, y, f"Honesty: {rating.honesty}")
        y -= 20

        c.drawString(120, y, f"Recommend: {rating.recommend}")
        y -= 20

        if rating.comments:
            c.drawString(120, y, f"Comments: {rating.comments}")
            y -= 20

    # college feedback section
    if feedback:
        y -= 20
        c.drawString(100, y, "College Feedback:")
        y -= 20

        c.drawString(120, y, f"Faculty: {feedback.faculty_rating}")
        y -= 20

        c.drawString(120, y, f"Placements: {feedback.placement_rating}")
        y -= 20

        c.drawString(120, y, f"Infrastructure: {feedback.infrastructure_rating}")
        y -= 20

        c.drawString(120, y, f"Hidden Fees: {feedback.hidden_fees}")
        y -= 20

        c.drawString(120, y, f"Strict Attendance: {feedback.strict_attendance}")
        y -= 20

        c.drawString(120, y, f"Ragging: {feedback.ragging_situation}")
        y -= 20

        if feedback.comments:
            c.drawString(120, y, f"Comments: {feedback.comments}")
            y -= 20

    c.save()

    return file_path