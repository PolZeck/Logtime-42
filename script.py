import requests
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

# ⚙️ Paramètres de l'API 42
CLIENT_ID = "u-s4t2ud-4b31e0fd02482feb6bfd0507f44a967c6b9bd7932341f388b76c0e24f91103a2"
CLIENT_SECRET = "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"
USER_LOGIN = "pledieu"  # Ton login 42
CAMPUS_ID = 9  # ID de ton campus (42 Lyon par exemple)

# ⚙️ Paramètres d'envoi de mail (utiliser Gmail ou autre)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "paul.ledieu@gmail.com"
EMAIL_PASSWORD = "zgfk ozcl niik lqzp"
EMAIL_RECEIVER = "paul.ledieu@gmail.com"

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
    url = f"https://api.intra.42.fr/v2/users/{USER_LOGIN}/locations"

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("Erreur API:", response.text)
        return []
    
    return response.json()

# 🕒 Calculer le temps total d'une période donnée en gérant les chevauchements et les sessions ouvertes
def calculate_logtime(sessions, start_date, end_date):
    total_seconds = 0

    for session in sessions:
        begin_at = datetime.strptime(session["begin_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
        end_at = session["end_at"]
        
        # 🟢 Si la session est encore ouverte, prendre UTC now comme fin
        if not end_at:
            end_at = datetime.utcnow()
        else:
            end_at = datetime.strptime(end_at, "%Y-%m-%dT%H:%M:%S.%fZ")

        # 🟡 Vérifier si la session chevauche la période demandée
        if begin_at < end_date and end_at > start_date:
            # Déterminer la vraie période de la session à inclure dans la plage
            session_start = max(begin_at, start_date)  # On prend la plus grande date
            session_end = min(end_at, end_date)  # On prend la plus petite date
            duration = (session_end - session_start).total_seconds()

            total_seconds += duration  # Ajouter la durée de la session

    return total_seconds

# 🔢 Convertir les secondes en heures et minutes
def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}min"

# 📊 Récupérer les statistiques de logtime
def get_logtime_report():
    sessions = get_logtime_data()
    today = datetime.utcnow()

    # Début et fin des périodes
    start_of_week = today - timedelta(days=today.weekday())  # Lundi de cette semaine
    start_of_month = today.replace(day=1)  # 1er du mois
    end_of_day = today.replace(hour=23, minute=59, second=59)

    # Calculs avec prise en compte des chevauchements
    logtime_today = calculate_logtime(sessions, today.replace(hour=0, minute=0, second=0), end_of_day)
    logtime_week = calculate_logtime(sessions, start_of_week, end_of_day)
    logtime_month = calculate_logtime(sessions, start_of_month, end_of_day)

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
