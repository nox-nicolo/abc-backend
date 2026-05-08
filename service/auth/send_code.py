
import os

from fastapi.responses import JSONResponse
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

# send code via mail
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", "nicolooseph@gmail.com"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", "vnkd vrcx gflf yhdf"),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "465")),
    MAIL_FROM=os.getenv("MAIL_FROM", "nicolooseph@gmail.com"),
    MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME", "African Beauty Community"),

    # Encryption settings (recommended)
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "true").lower() == "true",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "false").lower() == "true",

    # Other settings (generally recommended)
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)


def enqueue_verification_email(code: str, email: str) -> bool:
    if os.getenv("BACKGROUND_JOBS_ENABLED", "false").lower() != "true":
        return False

    try:
        from worker.tasks import send_verification_email

        send_verification_email.delay(code=code, email=email)
        return True
    except Exception as e:
        print(f"Error queueing verification email: {e}")
        return False


async def mail_send(code: str, email: str):
    """

        Sends a verification code to the user's email (synchronous).
        
        Args:
            code (str): The verification code.
            email (str): The user's email address.
            
    """
    
    html = f"""
       <body style="display: flex; justify-content: center; align-items: center; height: 100vh; padding-right: 20px; text-align: center;">
            <div style="max-width: 600px; padding: 20px; background-color: #f9f9f9; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
                <h1>Welcome to the Africa Beauty Community!</h1>
                <br />
                <p>We're so thrilled to have you join our vibrant and inspiring community! Here, we celebrate the beauty in all its forms, and we can't wait for you to be a part of it.</p>
                <p>To get started, please use the code below to activate your account:</p>
                <p style="background-color: lightblue; padding: 10px; border-radius: 5px; font-weight: bold; text-align: center;">{code}</p>
                <p>We're excited to connect with you!</p>
            </div>
        </body>
    """
    
    message = MessageSchema(
        subject = "Verification Code", 
        recipients = [email],
        body = html, 
        subtype = MessageType.html 
    )
    
    fm = FastMail(conf)
    
    try:
        await fm.send_message(message=message)  # Await the send_message call
        return JSONResponse(
            status_code=200,
            content={"message": "Email has been sent"}
        )
    except Exception as e:  # Catch potential email sending errors
        print(f"Error sending email: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to send email"}
        )

# send code via sms
