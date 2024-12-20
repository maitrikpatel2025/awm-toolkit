from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from typing import List
import os
from config import MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_PORT, MAIL_SERVER

conf = ConnectionConfig(
    MAIL_USERNAME = str(MAIL_USERNAME),  
    MAIL_PASSWORD = str(MAIL_PASSWORD),
    MAIL_FROM = str(MAIL_FROM),
    MAIL_PORT = MAIL_PORT,
    MAIL_SERVER = str(MAIL_SERVER),
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True
)

class EmailService:
    def __init__(self):
        self.fastmail = FastMail(conf)

    async def send_welcome_email(self, email: EmailStr, username: str):
        message = MessageSchema(
            subject="Welcome to Our Platform!",
            recipients=[email],
            body=f"""
            Hi {username},
            
            Welcome to our platform! We're excited to have you on board.
            
            Best regards,
            Your Platform Team
            """,
            subtype="plain"
        )
        await self.fastmail.send_message(message)

    async def send_password_reset_email(self, email: EmailStr, reset_token: str):
        reset_link = f"{os.getenv('FRONTEND_URL')}/reset-password?token={reset_token}"
        message = MessageSchema(
            subject="Password Reset Request",
            recipients=[email],
            body=f"""
            Hi,
            
            You requested to reset your password. Click the link below to proceed:
            {reset_link}
            
            If you didn't request this, please ignore this email.
            
            Best regards,
            Your Platform Team
            """,
            subtype="plain"
        )
        await self.fastmail.send_message(message) 