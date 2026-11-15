import os

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI(title="Contact Form API")

# 1. Definiera datamodellen för formuläret
class ContactSchema(BaseModel):
    name: str
    email: EmailStr
    message: str

# 2. Inställningar för E-post (SMTP)
SMTP_SERVER = os.environ["SMTP_SERVER"]  # Ändra till din leverantör
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))                  # Standardport för TLS
SENDER_EMAIL = os.environ["SENDER_EMAIL"]
SENDER_PASSWORD = os.environ["SENDER_PASSWORD"]  # Använd ett app-lösenord, inte ditt vanliga lösenord
RECEIVER_EMAIL = os.environ["RECEIVER_EMAIL"]

# Hjälpfunktion för att skicka mejl
def send_email(contact: ContactSchema):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"New message on johnsilvell.com from {contact.name}"

    body = f"""
    You have received a new message via the contact form!

    Name: {contact.name}
    Email: {contact.email}

    Message:
    {contact.message}
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Aktivera kryptering
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"E-postfel: {e}")
        return False

# 3. API-endpoint
@app.post("/contact", status_code=status.HTTP_200_OK)
def handle_contact(contact: ContactSchema):
    success = send_email(contact)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kunde inte skicka meddelandet, försök igen senare."
        )
    return {"message": "Ditt meddelande har skickats!"}
