from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI(title="Kontaktformulär API")

# 1. Definiera datamodellen för formuläret
class ContactSchema(BaseModel):
    name: str
    email: EmailStr
    message: str

# 2. Inställningar för E-post (SMTP)
SMTP_SERVER = "smtp.gmail.com"  # Ändra till din leverantör
SMTP_PORT = 587                  # Standardport för TLS
SENDER_EMAIL = "din_epost@gmail.com"
SENDER_PASSWORD = "ditt_app_lösenord"  # Använd ett app-lösenord, inte ditt vanliga lösenord
RECEIVER_EMAIL = "mottagare@exempel.se"

# Hjälpfunktion för att skicka mejl
def send_email(contact: ContactSchema):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"Nytt kontaktmeddelande från {contact.name}"

    body = f"""
    Du har fått ett nytt meddelande via kontaktformuläret!

    Namn: {contact.name}
    E-post: {contact.email}
    
    Meddelande:
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
