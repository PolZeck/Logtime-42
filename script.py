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
    sessions = sorted(sessions, key=lambda s: s["begin_at"])
    now = datetime.now(timezone.utc)
    merged_intervals = []

    for session in sessions:
        begin_at = datetime.strptime(session["begin_at"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        end_raw = session["end_at"]
        end_at = (
            datetime.strptime(end_raw, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
            if end_raw else now - timedelta(minutes=10) if subtract_minutes else now
        )

        # Ignorer si totalement hors période
        if begin_at >= end_date or end_at <= start_date:
            continue

        # Tronquer aux limites de la période
        begin_at = max(begin_at, start_date)
        end_at = min(end_at, end_date)

        # Fusion intelligente
        if not merged_intervals:
            merged_intervals.append((begin_at, end_at))
        else:
            last_begin, last_end = merged_intervals[-1]
            if begin_at <= last_end:  # chevauchement
                # Fusionner
                new_begin = min(last_begin, begin_at)
                new_end = max(last_end, end_at)
                merged_intervals[-1] = (new_begin, new_end)
            else:
                merged_intervals.append((begin_at, end_at))

    # Calcul final du logtime
    total_seconds = sum((end - start).total_seconds() for start, end in merged_intervals)
    return total_seconds


import calendar

def calculate_remaining_times(now, logtime_week_sec, logtime_month_sec):
    WEEKLY_GOAL_SEC = 35 * 3600  # Objectif hebdo : 35h

    # Total des jours ouvrés du mois
    total_days = calendar.monthrange(now.year, now.month)[1]
    total_working_days = sum(
        1 for day in range(1, total_days + 1)
        if datetime(now.year, now.month, day).weekday() < 5
    )
    MONTHLY_GOAL_SEC = total_working_days * 7 * 3600  # Objectif mensuel total

    # ✅ Compensation des -10 min retirées pour affichage
    corrected_logtime_month = logtime_month_sec - 10 * 60

    remaining_week_sec = max(0, WEEKLY_GOAL_SEC - logtime_week_sec)
    remaining_month_sec = max(0, MONTHLY_GOAL_SEC - corrected_logtime_month)

    def fmt(sec):
        h, m = divmod(int(sec) // 60, 60)
        return f"{h}h {m}min"

    return fmt(remaining_week_sec), fmt(remaining_month_sec)



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

    # Début et fin des périodes en UTC
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = end_of_today

    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_of_month = end_of_today

    logtime_today = calculate_logtime(sessions, start_of_today, end_of_today)
    logtime_week = calculate_logtime(sessions, start_of_week, end_of_week)
    
    # → On calcule d'abord le logtime mensuel réel
    logtime_month_raw = calculate_logtime(sessions, start_of_month, end_of_month)
    
    # → Puis on applique -10min juste pour affichage
    logtime_month_display = max(0, logtime_month_raw - 10 * 60)

    return {
        "today": format_time(logtime_today),
        "week": format_time(logtime_week),
        "month": format_time(logtime_month_display),
        "week_raw": logtime_week,
        "month_raw": logtime_month_raw,
        "now": now
    }

import os
import requests

def send_telegram_message(message):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    response = requests.post(url, data=data)
    if response.status_code != 200:
        print("❌ Erreur Telegram:", response.text)
    else:
        print("✅ Message Telegram envoyé.")

# ✉️ Envoyer un email avec le récapitulatif
# def send_email_report(user_login, email_receiver):
#     global USER_LOGIN
#     USER_LOGIN = user_login  # On met à jour le login utilisé dans l'API

#     report = get_logtime_report()
#     remaining_week, remaining_month = calculate_remaining_times(
#         report["now"], report["week_raw"], report["month_raw"]
#     )

#     subject = f"🕒 Récapitulatif Logtime 42 — {user_login}"
#     body = f"""
#     Bonjour {user_login} !

#     Voici ton récapitulatif de logtime 42 :

#     📅 Aujourd'hui : {report["today"]}
#     📆 Cette semaine : {report["week"]}  (⏳ Reste : {remaining_week})
#     🗓️ Ce mois : {report["month"]}  (⏳ Reste : {remaining_month})

#     Bon travail ! 🚀
#     """
    
#     msg = MIMEText(body)
#     msg["Subject"] = subject
#     msg["From"] = EMAIL_SENDER
#     msg["To"] = email_receiver

#     try:
#         server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
#         server.starttls()
#         server.login(EMAIL_SENDER, EMAIL_PASSWORD)
#         server.sendmail(EMAIL_SENDER, email_receiver, msg.as_string())
#         server.quit()
#         print(f"📩 Email envoyé à {email_receiver} (user {user_login})")
#     except Exception as e:
#         print(f"❌ Erreur lors de l'envoi de l'email à {email_receiver} :", e)

if __name__ == "__main__":
    report = get_logtime_report()

    remaining_week, remaining_month = calculate_remaining_times(
        report["now"], report["week_raw"], report["month_raw"]
    )

    msg = f"""
🕒 *Récapitulatif Logtime 42*

📅 *Aujourd'hui* : {report["today"]}
📆 *Cette semaine* : {report["week"]}  (⏳ Reste : {remaining_week})
🗓️ *Ce mois* : {report["month"]}  (⏳ Reste : {remaining_month})

🧠 *Objectifs :*
• Semaine : 35h
• Mois : 7h x chaque jour ouvré

🚀 Continue comme ça champion !
    """.strip()

    send_telegram_message(msg)

    # send_email_report("lcosson", "paul.ledieu@gmail.com")






# # 📌 Lancer l'envoi du mail automatiquement chaque jour
# if __name__ == "__main__":
#     send_email_report("pledieu", "paul.ledieu@gmail.com")
#     # send_email_report("lcosson", "L.cosson@outlook.fr")
