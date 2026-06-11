"""Checks the current VIX value against subscriber thresholds and sends
HTML email alerts, respecting a per-subscriber cooldown interval."""

import logging
import os
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv()

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("alert_monitor")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WEBSITE_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(WEBSITE_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from website.crucialPys.webScrape import get_vix_value as get_vix_value_yfinance
except ImportError:
    logger.error("Could not import VIX helper from webScrape; alerts disabled.")

    def get_vix_value_yfinance():
        return None

MIN_ALERT_INTERVAL = timedelta(hours=int(os.environ.get("ALERT_COOLDOWN_HOURS", "6")))
DB_CONNECT_TIMEOUT = int(os.environ.get("DB_CONNECT_TIMEOUT", "5"))
IMAGE_FOOTER_PATH = os.path.join(PROJECT_ROOT, "website", "static", "images", "mail-footer-logo-removed.png")
IMAGE_FOOTER_CID = 'mailfooterlogo'


def get_db_conn_for_alerts():
    db_name = os.environ.get("DB_NAME")
    db_user = os.environ.get("DB_USER")
    db_pass = os.environ.get("DB_PASS")
    db_host = os.environ.get("DB_HOST", "localhost")

    if not all([db_name, db_user, db_pass]):
        logger.warning("Database credentials not configured; cannot check alerts.")
        return None

    try:
        return psycopg2.connect(
            host=db_host, database=db_name, user=db_user, password=db_pass,
            connect_timeout=DB_CONNECT_TIMEOUT,
        )
    except psycopg2.Error as error:
        logger.error("Database connection failed: %s", error)
        return None


def send_actual_vix_alert(receiver_email, current_vix, user_specific_threshold):
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port_str = os.environ.get("SMTP_PORT")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")

    if not all([receiver_email, smtp_server, smtp_port_str, smtp_user, smtp_pass]):
        logger.warning("SMTP settings incomplete; cannot send alert to %s.", receiver_email)
        return False

    try:
        smtp_port = int(smtp_port_str)
    except ValueError:
        logger.error("Invalid SMTP_PORT value: %r", smtp_port_str)
        return False

    msg = MIMEMultipart('related')
    msg['From'] = smtp_user
    msg['To'] = receiver_email

    current_year = datetime.now(timezone.utc).year
    alert_trigger_time_formatted = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    msg['Subject'] = f"Market Sentiment Dashboard: VIX Alert: VIX is at {current_vix:.2f} (Your Threshold: >{user_specific_threshold:.2f})"

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
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width:600px; margin:0 auto; background-color:#ffffff; border-radius:8px; box-shadow: 0px 0px 15px rgba(0,0,0,0.05);">
                        <tr>
                            <td align="center" style="padding:30px 20px; background-color:#1a1a1a; color:#ffffff; border-top-left-radius:8px; border-top-right-radius:8px;">
                                <h1 style="margin:0; font-size:28px; font-weight:bold;">Market Sentiment Dashboard</h1>
                            </td>
                        </tr>
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
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    part_html = MIMEText(html_body, 'html', 'utf-8')
    msg.attach(part_html)

    try:
        if os.path.exists(IMAGE_FOOTER_PATH):
            with open(IMAGE_FOOTER_PATH, 'rb') as fp:
                img = MIMEImage(fp.read())
            img.add_header('Content-ID', f'<{IMAGE_FOOTER_CID}>')
            img.add_header('Content-Disposition', 'inline', filename=os.path.basename(IMAGE_FOOTER_PATH))
            msg.attach(img)
    except OSError as error:
        logger.warning("Could not attach footer image: %s", error)

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, receiver_email, msg.as_string())
        logger.info("VIX alert sent to %s (VIX %.2f > threshold %.2f).", receiver_email, current_vix, user_specific_threshold)
        return True
    except (smtplib.SMTPException, OSError) as error:
        logger.error("Failed to send VIX alert to %s: %s", receiver_email, error)
        return False


def check_vix_and_send_alerts():
    current_vix = get_vix_value_yfinance()
    if current_vix is None:
        logger.warning("Could not retrieve current VIX value; skipping alert check.")
        return

    conn = get_db_conn_for_alerts()
    if not conn:
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
                logger.info("VIX %.2f: no subscribers to alert.", current_vix)
                return

            for sub in subscriptions_to_alert:
                if send_actual_vix_alert(sub['email'], current_vix, sub['vix_threshold']):
                    try:
                        cur.execute("""
                            UPDATE vix_alerts_subscriptions
                            SET last_alert_sent_at = %s
                            WHERE id = %s
                        """, (datetime.now(timezone.utc), sub['id']))
                        conn.commit()
                    except psycopg2.Error as error:
                        logger.error("Failed to record alert timestamp for %s: %s", sub['email'], error)
                        conn.rollback()
    except psycopg2.Error as error:
        logger.error("Alert check query failed: %s", error)
    finally:
        conn.close()


if __name__ == "__main__":
    check_vix_and_send_alerts()
