import os  # pentru a lucra cu sistemul de operare (cai, variabile de mediu)
import sys  # pentru a modifica sys.path (lista de locuri unde python cauta module)
import time  # pentru functii legate de timp (desi nu e folosit direct in acest script, e bun de avut)
from datetime import datetime, timezone, timedelta  # pentru a lucra cu date, ore, fusuri orare si diferente de timp
import psycopg2  # biblioteca pentru a ne conecta la baza de date postgresql
from psycopg2.extras import RealDictCursor  # pentru a primi rezultatele din db ca dictionare
import smtplib  # biblioteca pentru a trimite email-uri folosind protocolul smtp
from email.mime.text import MIMEText  # pentru a crea corpul mesajului email in format text

# --- adaugam directorul radacina al proiectului la sys.path ---
# aflam calea catre directorul unde se gaseste acest script (alert_monitor.py)
PROJECT_ROOT_FOR_ALERT_MONITOR = os.path.dirname(os.path.abspath(__file__))
# daca acest script este in website/crucialpys, trebuie sa urcam doua niveluri pentru a ajunge la radacina proiectului
# daca este deja in radacina proiectului, aceasta linie nu mai este necesara sau trebuie ajustata
# presupunand ca este in radacina proiectului, aceasta linie este corecta pentru importurile de mai jos
if PROJECT_ROOT_FOR_ALERT_MONITOR not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_FOR_ALERT_MONITOR)  # adaugam la inceputul listei de cautare

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
    """functie care trimite efectiv emailul de alerta vix."""
    # citim configuratiile smtp din variabilele de mediu direct in functie
    smtp_server_local = os.environ.get("SMTP_SERVER")
    smtp_port_str_local = os.environ.get("SMTP_PORT")
    smtp_user_local = os.environ.get("SMTP_USER")  # emailul de la care se trimite
    smtp_pass_local = os.environ.get("SMTP_PASS")  # parola (sau parola de aplicatie pentru gmail cu 2fa)

    # verificam daca avem toate configuratiile smtp necesare
    if not all([receiver_email, smtp_server_local, smtp_port_str_local, smtp_user_local, smtp_pass_local]):
        print(f"Skipping email to {receiver_email}: SMTP configuration missing from environment variables.")
        return False
    try:
        smtp_port_int = int(smtp_port_str_local)  # convertim portul la numar intreg
    except ValueError:  # daca portul nu e un numar valid
        print(f"Skipping email to {receiver_email}: Invalid SMTP_PORT '{smtp_port_str_local}'.")
        return False

    # construim subiectul si corpul emailului
    # folosim f-stringuri pentru a insera valorile dinamice
    # :.2f formateaza numarul float cu exact doua zecimale
    subject = f"VIX Alert: VIX is at {current_vix:.2f} (Your Threshold: >{user_specific_threshold:.2f})"
    body = f"""Dear User,

    This is an automated notification from the Market Sentiment Dashboard.

    We wish to inform you that the CBOE Volatility Index (VIX) has registered a significant movement.

    Current VIX Level: {current_vix:.2f}
    Your Alert Threshold: > {user_specific_threshold:.2f}

    This reading indicates that the VIX is currently above the threshold you have specified,
    suggesting a potential increase in market volatility.

    We advise you to monitor market conditions and consult your financial advisor
    for any investment decisions.

    Details:
    - Alert Trigger Time (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}
    - Data Source: Market Sentiment Dashboard

    Thank you for using our alert service.

    Sincerely,
    The Market Sentiment Dashboard Team
    Dinu Bogdan-Marius CEO 
    --------------------------------------
    Note: This is an automated message. Please do not reply directly to this email.
    To manage your alert settings, please visit the dashboard. 
    
    2025 Market Sentiment Dashboard™ 
    
    All Rights Reserved.
    """
    # cream obiectul mesajului email, specificand ca e text simplu si codificare utf-8
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject  # setam subiectul
    msg['From'] = smtp_user_local  # setam expeditorul
    msg['To'] = receiver_email  # setam destinatarul

    try:
        print(
            f"Attempting to send VIX alert to {receiver_email} for VIX={current_vix:.2f} (user threshold >{user_specific_threshold:.2f})...")
        # ne conectam la serverul smtp
        # 'with' se asigura ca server.quit() este apelat automat la final
        with smtplib.SMTP(smtp_server_local, smtp_port_int) as server:
            server.ehlo()  # trimitem un salut initial serverului smtp
            server.starttls()  # pornim criptarea tls (transport layer security)
            server.ehlo()  # salutam din nou serverul dupa ce am pornit tls
            server.login(smtp_user_local, smtp_pass_local)  # ne autentificam la server
            server.sendmail(smtp_user_local, receiver_email, msg.as_string())  # trimitem emailul
        print(f"VIX alert successfully sent to {receiver_email}.")
        return True  # returnam true daca emailul a fost trimis
    except smtplib.SMTPAuthenticationError as e:  # eroare specifica de autentificare smtp
        print(f"SMTP Authentication Error for {smtp_user_local}: {e}. Check SMTP_USER and SMTP_PASS.")
        print("For Gmail with 2FA, an 'App Password' is required.")
    except Exception as e:  # orice alta eroare la trimiterea emailului
        print(f"Error sending VIX alert email to {receiver_email}: {e}")
    return False  # returnam false daca a aparut o eroare


def check_vix_and_send_alerts():
    """
    functia principala a acestui script: verifica valoarea vix curenta
    si trimite alerte utilizatorilor abonati daca pragul lor este depasit.
    """
    print(f"[{datetime.now(timezone.utc)}] Starting VIX alert check...")
    if not YFINANCE_AVAILABLE:  # daca biblioteca yfinance nu e disponibila (din cauza erorii de import)
        print("yfinance library not available. Cannot fetch VIX for alerts.")
        return

    current_vix = get_vix_value_yfinance()  # preluam valoarea vix curenta
    if current_vix is None:  # daca nu am putut prelua vix-ul
        print("Could not retrieve current VIX value. Skipping alert check.")
        return

    print(f"Current VIX value fetched: {current_vix}")

    # nu mai citim vix_alert_threshold din variabilele de mediu aici,
    # deoarece fiecare utilizator are propriul prag in baza de date.

    conn = get_db_conn_for_alerts()  # ne conectam la baza de date
    if not conn:  # daca nu am reusit sa ne conectam
        print("Could not connect to database to check subscriptions.")
        return

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:  # deschidem un cursor
            # selectam toti utilizatorii activi ('is_active = true')
            # pentru care vix-ul curent este mai mare decat pragul lor ('%s > vix_threshold')
            # si carora fie nu li s-a mai trimis alerta ('last_alert_sent_at is null')
            # fie ultima alerta a fost trimisa cu mai mult de min_alert_interval in urma.
            cur.execute("""
                SELECT id, email, vix_threshold, last_alert_sent_at 
                FROM vix_alerts_subscriptions 
                WHERE is_active = TRUE AND %s > vix_threshold 
                AND (last_alert_sent_at IS NULL OR last_alert_sent_at < %s)
            """, (current_vix, datetime.now(timezone.utc) - MIN_ALERT_INTERVAL))

            subscriptions_to_alert = cur.fetchall()  # luam toate subscrierile care indeplinesc conditiile

            if not subscriptions_to_alert:  # daca nu avem pe nimeni de alertat
                print("No users to alert for the current VIX level or alerts sent recently.")
                return

            print(f"Found {len(subscriptions_to_alert)} subscriptions to alert for VIX={current_vix}.")
            for sub in subscriptions_to_alert:  # pentru fiecare subscriere de alertat
                # trimitem emailul, folosind pragul specific al utilizatorului (sub['vix_threshold'])
                if send_actual_vix_alert(sub['email'], current_vix, sub['vix_threshold']):
                    # daca emailul a fost trimis cu succes, actualizam 'last_alert_sent_at' in baza de date
                    try:
                        cur.execute("""
                            UPDATE vix_alerts_subscriptions 
                            SET last_alert_sent_at = %s 
                            WHERE id = %s
                        """, (datetime.now(timezone.utc), sub['id']))
                        conn.commit()  # salvam modificarea
                        print(f"Updated last_alert_sent_at for {sub['email']}.")
                    except Exception as db_update_err:  # daca apare eroare la update
                        print(f"Error updating last_alert_sent_at for {sub['email']}: {db_update_err}")
                        conn.rollback()  # anulam modificarea
    except Exception as e:  # prindem orice eroare in procesul de verificare
        print(f"Error during VIX alert check process: {e}")
    finally:  # indiferent de ce se intampla
        if conn:  # daca conexiunea la db a fost deschisa
            conn.close()  # o inchidem
    print(f"[{datetime.now(timezone.utc)}] VIX alert check finished.")


# acest bloc se executa doar daca scriptul este rulat direct (ex: 'python alert_monitor.py')
if __name__ == "__main__":
    # acest script ar putea fi rulat de scheduler_main.py sau de un cron job separat
    print("Running VIX alert monitor directly...")
    check_vix_and_send_alerts()  # apelam functia principala de verificare si trimitere alerte
    print("VIX alert monitor direct run finished.")