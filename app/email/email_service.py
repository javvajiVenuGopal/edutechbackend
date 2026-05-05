from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail,
    Attachment,
    FileContent,
    FileName,
    FileType,
    Disposition,
    Email,
    To
)
from app.core.config import SENDGRID_API_KEY, EMAIL_USER
import base64


# =========================
# COMMON SEND FUNCTION
# =========================
def send_mail(message):
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        print("Status:", response.status_code)
        print("Response:", response.body)

        return response.status_code == 202

    except Exception as e:
        print("❌ SendGrid Error:", str(e))
        return False


# =========================
# OTP EMAIL (IMPROVED)
# =========================
def send_email(to_email: str, otp: str):
    try:
        message = Mail(
            from_email=Email(EMAIL_USER, "SeniorGuide"),  # ✅ FIXED FORMAT
            to_emails=To(to_email),
            subject="Your verification code",
            plain_text_content=f"Your verification code is {otp}",
            html_content=f"""
            <div style="font-family: Arial; padding:20px;">
                <h2 style="color:#ff6b35;">SeniorGuide</h2>

                <p>Hello,</p>

                <p>Your verification code is:</p>

                <div style="font-size:28px; font-weight:bold; letter-spacing:3px;">
                    {otp}
                </div>

                <p>This code will expire in 5 minutes.</p>

                <p style="font-size:12px; color:gray;">
                    If you did not request this, please ignore this email.
                </p>
            </div>
            """
        )

        return send_mail(message)

    except Exception as e:
        print("❌ OTP Error:", e)
        return False


# =========================
# REPORT EMAIL (PDF)
# =========================
def send_report_email(to_email: str, file_path: str):
    try:
        with open(file_path, "rb") as f:
            encoded_file = base64.b64encode(f.read()).decode()

        message = Mail(
            from_email=Email(EMAIL_USER, "SeniorGuide"),
            to_emails=To(to_email),
            subject="Your consultation report",
            plain_text_content="Your consultation report is attached.",
            html_content="<p>Your consultation report is attached.</p>"
        )

        attachment = Attachment(
            FileContent(encoded_file),
            FileName("report.pdf"),
            FileType("application/pdf"),
            Disposition("attachment")
        )

        message.attachment = [attachment]

        return send_mail(message)

    except Exception as e:
        print("❌ Report Error:", e)
        return False


# =========================
# CALENDAR INVITE (ICS)
# =========================
def send_calendar_invite(to_email: str, ics_file: str):
    try:
        with open(ics_file, "rb") as f:
            encoded_file = base64.b64encode(f.read()).decode()

        message = Mail(
            from_email=Email(EMAIL_USER, "SeniorGuide"),
            to_emails=To(to_email),
            subject="Your consultation call schedule",
            plain_text_content="Your consultation call is scheduled.",
            html_content="<p>Your consultation call is scheduled. Calendar invite attached.</p>"
        )

        attachment = Attachment(
            FileContent(encoded_file),
            FileName("invite.ics"),
            FileType("text/calendar"),
            Disposition("attachment")
        )

        message.attachment = [attachment]

        return send_mail(message)

    except Exception as e:
        print("❌ Calendar Error:", e)
        return False