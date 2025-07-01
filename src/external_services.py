import requests
import smtplib
from email.mime.text import MIMEText
from config import OLLAMA_API_URL, EMAIL_SERVER, EMAIL_PORT, EMAIL_FROM, EMAIL_TO

class OllamaClient:
    # Made generate_blog accept a prompt for flexibility
    def generate_blog(self, prompt="Write a 200-word blog post on a productivity topic."):
        try:
            payload = {
                "model": "codellama:7b",
                "prompt": prompt,
                "stream": False
            }
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=30)
            response.raise_for_status()
            return response.json().get("response", "Failed to generate blog.")
        except requests.RequestException as e:
            return f"Error generating blog: {e}"

class EmailClient:
    def send_email(self, subject, body):
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = EMAIL_FROM
            msg["To"] = ", ".join(EMAIL_TO)
            with smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT) as server:
                server.send_message(msg)
            print(f"Email sent to {', '.join(EMAIL_TO)} with subject: {subject}")
        except smtplib.SMTPException as e:
            print(f"Failed to send email: {e}")