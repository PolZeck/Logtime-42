from dotenv import load_dotenv
load_dotenv()
import requests
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

import os

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
USER_LOGIN = "pledieu"  # Ton login 42
CAMPUS_ID = 9  # ID de ton campus (42 Lyon par exemple)

# ⚙️ Paramètres d'envoi de mail (utiliser Gmail ou autre)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "paul.ledieu@gmail.com"
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = "paul.ledieu@gmail.com"


print("CLIENT_ID:", CLIENT_ID)
print("CLIENT_SECRET:", CLIENT_SECRET)
print("EMAIL_PASSWORD:", EMAIL_PASSWORD)


# 🔑 Obtenir le token d'accès OAuth 2.0
def get_access_token():
    url = "https://api.intra.42.fr/oauth/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    response = requests.post(url, data=data)
    return response.json().get("access_token")


# 📡 Récupérer toutes les sessions de connexion de l'utilisateur
def get_logtime_data():
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    all_sessions = []
    page = 1

    while True:
        url = f"https://api.intra.42.fr/v2/users/{USER_LOGIN}/locations?page={page}&per_page=100"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print("Erreur API:", response.text)
            break

        page_data = response.json()
        if not page_data:
            break

        all_sessions.extend(page_data)
        page += 1

    return all_sessions


# 🕒 Calculer le temps total d'une période donnée en gérant les chevauchements et les sessions ouvertes
from datetime import datetime, timezone

def calculate_logtime(sessions, start_date, end_date, subtract_minutes=False):
    total_seconds = 0

    for session in sessions:
        begin_at = datetime.strptime(session["begin_at"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        end_at_raw = session["end_at"]
        
        if not end_at_raw:
            end_at = datetime.now(timezone.utc)
            if subtract_minutes:
                end_at -= timedelta(minutes=10)
        else:
            end_at = datetime.strptime(end_at_raw, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)

        if begin_at < end_date and end_at > start_date:
            session_start = max(begin_at, start_date)
            session_end = min(end_at, end_date)
            duration = (session_end - session_start).total_seconds()
            total_seconds += duration

    return total_seconds



# 🔢 Convertir les secondes en heures et minutes
def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}min"

# 📊 Récupérer les statistiques de logtime
from datetime import datetime, timedelta, timezone

def get_logtime_report():
    sessions = get_logtime_data()
    now = datetime.now(timezone.utc)

    # Début et fin de périodes en UTC
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = end_of_today

    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_of_month = end_of_today

    logtime_today = calculate_logtime(sessions, start_of_today, end_of_today)
    logtime_week = calculate_logtime(sessions, start_of_week, end_of_week)
    logtime_month = calculate_logtime(sessions, start_of_month, end_of_month, subtract_minutes=True)

    return {
        "today": format_time(logtime_today),
        "week": format_time(logtime_week),
        "month": format_time(logtime_month)
    }


# ✉️ Envoyer un email avec le récapitulatif
def send_email_report():
    report = get_logtime_report()
    subject = "🕒 Récapitulatif Logtime 42"
    body = f"""
    Bonjour !

    Voici ton récapitulatif de logtime 42 :

    📅 Aujourd'hui : {report["today"]}
    📆 Cette semaine : {report["week"]}
    🗓️ Ce mois : {report["month"]}

    Bon travail ! 🚀
    """
    
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print("📩 Email envoyé avec succès !")
    except Exception as e:
        print("❌ Erreur lors de l'envoi de l'email :", e)

# 📌 Lancer l'envoi du mail automatiquement chaque jour
if __name__ == "__main__":
    send_email_report()
