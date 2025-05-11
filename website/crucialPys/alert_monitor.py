import os  # pentru a lucra cu sistemul de operare (cai, variabile de mediu)
import sys  # pentru a modifica sys.path (lista de locuri unde python cauta module)
import time  # pentru functii legate de timp (desi nu e folosit direct in acest script, e bun de avut)
from datetime import datetime, timezone, timedelta  # pentru a lucra cu date, ore, fusuri orare si diferente de timp
import psycopg2  # biblioteca pentru a ne conecta la baza de date postgresql
from psycopg2.extras import RealDictCursor  # pentru a primi rezultatele din db ca dictionare
import smtplib  # biblioteca pentru a trimite email-uri folosind protocolul smtp

from email.mime.text import MIMEText  # pentru a crea corpul mesajului email in format text/html
from email.mime.multipart import MIMEMultipart # pentru a combina diferite parti ale emailului (text, imagine)
from email.mime.image import MIMEImage # pentru a atasa imagini

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # .../ProjectMarketSentimentMDS/website/crucialPys
WEBSITE_DIR = os.path.dirname(SCRIPT_DIR) # .../ProjectMarketSentimentMDS/website
PROJECT_ROOT = os.path.dirname(WEBSITE_DIR) # .../ProjectMarketSentimentMDS

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)  # adaugam la inceputul listei de cautare

try:
    # incercam sa importam functia get_vix_value_yfinance si flag-ul yfinance_available
    # din modulul webscrape, care se afla in pachetul website.crucialpys
    from website.crucialPys.webScrape import get_vix_value_yfinance, YFINANCE_AVAILABLE

    print("Successfully imported VIX fetching function from webScrape.")
except ImportError as e:  # daca importul esueaza (ex: modulul nu e gasit, eroare in webscrape.py)
    print(f"Could not import get_vix_value_yfinance from website.crucialPys.webScrape: {e}")


    # definim o functie fallback (de rezerva) care nu face nimic, doar afiseaza un mesaj
    def get_vix_value_yfinance():
        print("Fallback: yfinance VIX fetching not available due to import error.");
        return None


    YFINANCE_AVAILABLE = False  # setam flag-ul ca yfinance nu e disponibil
except Exception as e_general:  # prindem orice alta eroare generala la import
    print(f"An unexpected error occurred during import: {e_general}")


    def get_vix_value_yfinance():
        print("Fallback: yfinance VIX fetching not available due to general import error.");
        return None


    YFINANCE_AVAILABLE = False

# intervalul minim (in ore) intre trimiterea a doua alerte consecutive catre acelasi utilizator
MIN_ALERT_INTERVAL = timedelta(hours=6)

# Calea catre imaginea pentru footer-ul emailului
# Din .../ProjectMarketSentimentMDS/website/crucialPys mergem in sus la PROJECT_ROOT
# apoi website/static/images/mail-footer-logo.png
IMAGE_FOOTER_PATH = os.path.join(PROJECT_ROOT, "website", "static", "images", "mail-footer-logo-removed.png")
IMAGE_FOOTER_CID = 'mailfooterlogo' # Content-ID pentru imagine

def get_db_conn_for_alerts():
    """functie care stabileste si returneaza o conexiune la baza de date pentru scriptul de alerte."""
    # citim credentialele db din variabilele de mediu direct in functie
    db_name_local = os.environ.get("DB_NAME")
    db_user_local = os.environ.get("DB_USER")
    db_pass_local = os.environ.get("DB_PASS")
    db_host_local = os.environ.get("DB_HOST", "localhost")  # default la localhost daca nu e setat
    if not all([db_name_local, db_user_local, db_pass_local]):  # verificam daca avem toate credentialele
        print("AlertDB Error: DB credentials missing.")
        return None
    try:
        # incercam sa ne conectam la postgresql
        conn = psycopg2.connect(host=db_host_local, database=db_name_local, user=db_user_local, password=db_pass_local)
        return conn  # returnam obiectul de conexiune
    except Exception as e:  # prindem orice eroare la conectare
        print(f"AlertDB Connection Error: {e}");
        return None


def send_actual_vix_alert(receiver_email, current_vix, user_specific_threshold):
    """functie care trimite efectiv emailul de alerta vix (acum in format HTML cu imagine)."""
    smtp_server_local = os.environ.get("SMTP_SERVER")
    smtp_port_str_local = os.environ.get("SMTP_PORT")
    smtp_user_local = os.environ.get("SMTP_USER")
    smtp_pass_local = os.environ.get("SMTP_PASS")

    if not all([receiver_email, smtp_server_local, smtp_port_str_local, smtp_user_local, smtp_pass_local]):
        print(f"Skipping email to {receiver_email}: SMTP configuration missing from environment variables.")
        return False
    try:
        smtp_port_int = int(smtp_port_str_local)
    except ValueError:
        print(f"Skipping email to {receiver_email}: Invalid SMTP_PORT '{smtp_port_str_local}'.")
        return False

    # cream mesajul ca MIMEMultipart pentru a putea include HTML si imagini
    msg = MIMEMultipart('related')
    msg['From'] = smtp_user_local
    msg['To'] = receiver_email

    current_year = datetime.now(timezone.utc).year
    alert_trigger_time_formatted = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


    msg['Subject'] = f"VIX Alert: VIX is at {current_vix:.2f} (Your Threshold: >{user_specific_threshold:.2f})"

    html_body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VIX Alert - Market Sentiment Dashboard</title>
        <style type="text/css">
            body, table, td, p, a, li, blockquote {{ -webkit-text-size-adjust:none!important; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }}
            table {{ border-collapse:collapse; }}
            img {{ -ms-interpolation-mode:bicubic; display:block; border:0; outline:none; text-decoration:none; }}
        </style>
    </head>
    <body style="margin:0; padding:0; background-color:#f0f0f0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;">
        <table role="presentation" align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color:#f0f0f0;">
            <tr>
                <td align="center" style="padding:20px 0;">
                    <!--[if (gte mso 9)|(IE)]>
                    <table align="center" border="0" cellspacing="0" cellpadding="0" width="600">
                    <tr>
                    <td align="center" valign="top" width="600">
                    <![endif]-->
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width:600px; margin:0 auto; background-color:#ffffff; border-radius:8px; box-shadow: 0px 0px 15px rgba(0,0,0,0.05);">
                        <!-- Header -->
                        <tr>
                            <td align="center" style="padding:30px 20px; background-color:#1a1a1a; color:#ffffff; border-top-left-radius:8px; border-top-right-radius:8px;">
                                <h1 style="margin:0; font-size:28px; font-weight:bold;">Market Sentiment Dashboard</h1>
                            </td>
                        </tr>
                        <!-- Content -->
                        <tr>
                            <td style="padding:30px 25px; color:#333333; font-size:16px; line-height:1.6;">
                                <p style="margin:0 0 20px;">Dear User,</p>
                                <p style="margin:0 0 15px;">This is an automated notification from the Market Sentiment Dashboard (MSD).</p>
                                <p style="margin:0 0 20px;">We wish to inform you that the CBOE Volatility Index (VIX) has registered a significant movement.</p>

                                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="margin:25px 0; background-color:#f5f5f5; border-left:4px solid #555555; padding:15px 20px;">
                                    <tr>
                                        <td>
                                            <p style="margin:0 0 8px; color:#333333; font-size:17px;"><strong>Current VIX Level: <span style="color:#000000; font-size:1.2em;">{current_vix:.2f}</span></strong></p>
                                            <p style="margin:0; color:#333333; font-size:17px;"><strong>Your Alert Threshold: > {user_specific_threshold:.2f}</strong></p>
                                        </td>
                                    </tr>
                                </table>

                                <p style="margin:0 0 15px;">This reading indicates that the VIX is currently above the threshold you have specified,
                                suggesting a potential increase in market volatility.</p>
                                <p style="margin:0 0 25px;">We advise you to monitor market conditions and consult your financial advisor
                                for any investment decisions.</p>

                                <h3 style="font-size:18px; color:#000000; margin:30px 0 10px; padding-bottom:5px; border-bottom:1px solid #dddddd;">Alert Details:</h3>
                                <ul style="margin:0 0 20px; padding-left:20px; list-style-type:disc;">
                                    <li style="margin-bottom:8px;">Alert Trigger Time (UTC): {alert_trigger_time_formatted}</li>
                                    <li style="margin-bottom:8px;">Data Source: Market Sentiment Dashboard</li>
                                </ul>

                                <p style="margin:0 0 15px;">Thank you for using our alert service.</p>
                                <p style="margin:0 0 5px;">Sincerely,</p>
                                <p style="margin:0 0 5px;"><strong>The Market Sentiment Dashboard Team</strong></p>
                                <p style="margin:0;"><em>Dinu Bogdan-Marius, CEO</em></p>
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td align="center" style="padding:25px 20px; background-color:#e0e0e0; color:#444444; font-size:13px; border-bottom-left-radius:8px; border-bottom-right-radius:8px; border-top:1px solid #cccccc;">
                                <p style="margin:0 0 10px;">
                                    <img src="cid:{IMAGE_FOOTER_CID}" alt="MSD Logo Transparent" style="max-width:160px; height:auto; margin-bottom:15px;">
                                </p>
                                <p style="margin:0 0 10px;">Note: This is an automated message. Please do not reply directly to this email.<br>To manage your alert settings, please visit the dashboard.</p>
                                <p style="margin:0;">© {current_year} Market Sentiment Dashboard™ All Rights Reserved.</p>
                            </td>
                        </tr>
                    </table>
                    <!--[if (gte mso 9)|(IE)]>
                    </td>
                    </tr>
                    </table>
                    <![endif]-->
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    # cream partea HTML a mesajului
    part_html = MIMEText(html_body, 'html', 'utf-8')
    msg.attach(part_html)

    try:
        if not os.path.exists(IMAGE_FOOTER_PATH):  # verificare extra daca exista fisieru
            print(f"ERROR: Image file NOT FOUND at {IMAGE_FOOTER_PATH}. Email will be sent without footer image.")
        else:
            with open(IMAGE_FOOTER_PATH, 'rb') as fp:
                img = MIMEImage(fp.read())
            # adaugam header-ul Content-ID pentru a o putea referentia din HTML
            img.add_header('Content-ID', f'<{IMAGE_FOOTER_CID}>')
            # adaugam content-disposition pentru a sugera clientilor de email sa o afiseze inline
            img.add_header('Content-Disposition', 'inline', filename=os.path.basename(IMAGE_FOOTER_PATH))
            msg.attach(img)
            print(f"Successfully attached image: {IMAGE_FOOTER_PATH} with CID: {IMAGE_FOOTER_CID}")
    except FileNotFoundError:
        print(
            f"ERROR: Image file not found at {IMAGE_FOOTER_PATH} (FileNotFoundError). Email will be sent without footer image.")
    except Exception as e_img:
        print(f"Error attaching image {IMAGE_FOOTER_PATH}: {e_img}. Email will be sent without footer image.")


    try:
        print(
            f"Attempting to send VIX alert to {receiver_email} for VIX={current_vix:.2f} (user threshold >{user_specific_threshold:.2f})...")
        with smtplib.SMTP(smtp_server_local, smtp_port_int) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user_local, smtp_pass_local)
            server.sendmail(smtp_user_local, receiver_email, msg.as_string())
        print(f"VIX alert successfully sent to {receiver_email}.")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication Error for {smtp_user_local}: {e}. Check SMTP_USER and SMTP_PASS.")
        print("For Gmail with 2FA, an 'App Password' is required.")
    except Exception as e:
        print(f"Error sending VIX alert email to {receiver_email}: {e}")
    return False


def check_vix_and_send_alerts():
    """
    functia principala a acestui script: verifica valoarea vix curenta
    si trimite alerte utilizatorilor abonati daca pragul lor este depasit.
    """
    print(f"[{datetime.now(timezone.utc)}] Starting VIX alert check...")
    if not YFINANCE_AVAILABLE:
        print("yfinance library not available. Cannot fetch VIX for alerts.")
        return

    current_vix = get_vix_value_yfinance()
    if current_vix is None:
        print("Could not retrieve current VIX value. Skipping alert check.")
        return

    print(f"Current VIX value fetched: {current_vix}")

    conn = get_db_conn_for_alerts()
    if not conn:
        print("Could not connect to database to check subscriptions.")
        return

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, email, vix_threshold, last_alert_sent_at 
                FROM vix_alerts_subscriptions 
                WHERE is_active = TRUE AND %s > vix_threshold 
                AND (last_alert_sent_at IS NULL OR last_alert_sent_at < %s)
            """, (current_vix, datetime.now(timezone.utc) - MIN_ALERT_INTERVAL))

            subscriptions_to_alert = cur.fetchall()

            if not subscriptions_to_alert:
                print("No users to alert for the current VIX level or alerts sent recently.")
                return

            print(f"Found {len(subscriptions_to_alert)} subscriptions to alert for VIX={current_vix}.")
            for sub in subscriptions_to_alert:
                if send_actual_vix_alert(sub['email'], current_vix, sub['vix_threshold']):
                    try:
                        cur.execute("""
                            UPDATE vix_alerts_subscriptions 
                            SET last_alert_sent_at = %s 
                            WHERE id = %s
                        """, (datetime.now(timezone.utc), sub['id']))
                        conn.commit()
                        print(f"Updated last_alert_sent_at for {sub['email']}.")
                    except Exception as db_update_err:
                        print(f"Error updating last_alert_sent_at for {sub['email']}: {db_update_err}")
                        conn.rollback()
    except Exception as e:
        print(f"Error during VIX alert check process: {e}")
    finally:
        if conn:
            conn.close()
    print(f"[{datetime.now(timezone.utc)}] VIX alert check finished.")


if __name__ == "__main__":
    print("Running VIX alert monitor directly...")
    check_vix_and_send_alerts()
    print("VIX alert monitor direct run finished.")

