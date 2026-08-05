import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# -----------------------------
# CONFIG — EDIT THESE
# -----------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = "harryoverton07@gmail.com"
EMAIL_PASS = "Anfield2007"
SEND_TO = "harryoverton07@gmail.com"
# -----------------------------

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)

def build_email_body():
    summary = load_json("dashboards/dashboard.json")
    vault = load_json("vault.json")
    history = load_json("history/portfolio_history.json")
    coin_pnl = load_json("history/coin_pnl.json")

    if not summary:
        return "No trading summary available yet."

    body = []
    body.append(f"Daily Summary — {datetime.utcnow().strftime('%Y-%m-%d')}\n")
    body.append("=====================================\n")

    # Latest cycle
    body.append("LATEST CYCLE\n")
    body.append(f"Timestamp: {summary['timestamp']}\n")
    body.append(f"Trading Pot Start: {summary['trading_pot_start']:.2f}\n")
    body.append(f"Trading Pot End: {summary['trading_pot_end']:.2f}\n")
    body.append(f"P&L: {summary['profit_loss']:.2f}\n")
    body.append(f"Skimmed: {summary['skimmed']:.2f}\n")
    body.append(f"BTC Regime: {summary['btc_regime']}\n\n")

    # Positions
    body.append("POSITIONS\n")
    for coin, pos in summary["positions"].items():
        body.append(f"{coin}: {pos['signal']}\n")
    body.append("\n")

    # Vault
    if vault:
        body.append("VAULT\n")
        body.append(f"Trading Pot Balance: {vault['balance']:.2f}\n")
        body.append(f"Vault Skim Total: {vault['vault_value']:.2f}\n\n")

    # Equity curve
    if history:
        body.append("EQUITY CURVE\n")
        body.append(f"Total Cycles: {len(history)}\n")
        body.append(f"First Value: {history[0]['trading_pot']:.2f}\n")
        body.append(f"Latest Value: {history[-1]['trading_pot']:.2f}\n\n")

    # Per-coin P&L
    if coin_pnl:
        body.append("PER-COIN P&L\n")
        for coin, pnl in coin_pnl.items():
            body.append(f"{coin}: {pnl:.2f}\n")

    return "\n".join(body)

def send_email(body):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = SEND_TO
    msg["Subject"] = "Daily Crypto Trading Summary"

    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

def main():
    body = build_email_body()
    send_email(body)
    print("Daily summary email sent.")

if __name__ == "__main__":
    main()
