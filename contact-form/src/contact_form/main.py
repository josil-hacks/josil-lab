import logging
import os
import smtplib
import ssl
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, field_validator
from email_validator import EmailNotValidError, validate_email

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    smtp_server: str
    smtp_port: int
    sender_email: str
    receiver_email: str
    password: str = field(repr=False)


def load_settings() -> Settings:
    def required(name: str) -> str:
        value = os.environ.get(name, '').strip()
        if not value:
            raise ValueError(f'{name} is required')
        return value

    server = required('SMTP_SERVER')
    try:
        port = int(os.environ.get('SMTP_PORT', '587'))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise ValueError('SMTP_PORT must be an integer between 1 and 65535') from None
    addresses = []
    for name in ('SENDER_EMAIL', 'RECEIVER_EMAIL'):
        try:
            addresses.append(validate_email(required(name), check_deliverability=False).normalized)
        except EmailNotValidError:
            raise ValueError(f'{name} must be a valid email address') from None
    password_file = required('SMTP_PASSWORD_FILE')
    try:
        password = Path(password_file).read_text(encoding='utf-8').rstrip('\r\n')
    except (OSError, UnicodeError):
        raise ValueError('SMTP_PASSWORD_FILE must point to a readable UTF-8 password file') from None
    if not password or not password.strip() or '\n' in password or '\r' in password:
        raise ValueError('SMTP_PASSWORD_FILE must contain a non-empty single-line password')
    return Settings(server, port, *addresses, password)


def allowed_origins() -> list[str]:
    origins = [origin.strip() for origin in os.environ.get('CORS_ORIGINS', '').split(',') if origin.strip()]
    for origin in origins:
        try:
            parsed = urlsplit(origin)
            valid = (parsed.scheme in ('http', 'https') and parsed.hostname and
                     parsed.username is None and parsed.password is None and
                     parsed.path == '' and not parsed.query and not parsed.fragment and
                     parsed.port != 0)
        except ValueError:
            valid = False
        if not valid or '*' in origin:
            raise ValueError('CORS_ORIGINS must be a comma-separated list of explicit HTTP(S) origins')
    return origins


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = load_settings()
    yield


app = FastAPI(title='Contact Form API', lifespan=lifespan)
origins = allowed_origins()
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['POST'], allow_headers=['Content-Type'])


class ContactSchema(BaseModel):
    name: str = Field(max_length=100)
    email: EmailStr = Field(max_length=254)
    message: str = Field(max_length=5000)

    @field_validator('name', mode='before')
    @classmethod
    def clean_name(cls, value):
        if isinstance(value, str):
            value = value.replace('\r', ' ').replace('\n', ' ').strip()
            if not value:
                raise ValueError('Name must not be empty')
        return value

    @field_validator('message')
    @classmethod
    def clean_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Message must not be empty')
        return value


def send_email(contact: ContactSchema, settings: Settings) -> bool:
    msg = EmailMessage()
    msg['From'] = settings.sender_email
    msg['To'] = settings.receiver_email
    msg['Reply-To'] = str(contact.email)
    msg['Subject'] = f'New contact form message from {contact.name}'
    msg.set_content(f'Name: {contact.name}\nEmail: {contact.email}\n\nMessage:\n{contact.message}')
    try:
        with smtplib.SMTP(settings.smtp_server, settings.smtp_port, timeout=10) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(settings.sender_email, settings.password)
            server.send_message(msg)
    except (smtplib.SMTPException, OSError, ssl.SSLError):
        # SMTP server responses and exception text can contain credentials or message data.
        logger.error('SMTP delivery failed; check server connectivity, TLS and credentials')
        return False
    return True


@app.post('/contact', status_code=status.HTTP_200_OK)
def handle_contact(contact: ContactSchema, request: Request):
    if not send_email(contact, request.app.state.settings):
        raise HTTPException(status_code=500, detail='Kunde inte skicka meddelandet, försök igen senare.')
    return {'message': 'Ditt meddelande har skickats!'}
