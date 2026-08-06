from engine.engine import Engine
from shared_vault import Vault
from live_data import get_live_ohlc
import shutil
def main():
    vault = Vault()
    vault.load()

    for coin in ["BTC", "ETH", "SOL", "XRP", "ADA"]:
        vault.data[coin] = get_live_ohlc(coin)

    engine = Engine(vault)
    summary = engine.run_cycle()

    print(summary)   # ← ADD THIS

    vault.save()

if __name__ == "__main__":
    main()
shutil.copy("dashboards/dashboard.json", "docs/dashboard.json")
shutil.copy("vaults/vault.json", "docs/vault.json")
import os
import shutil
import subprocess
from datetime import datetime

# ---------------------------------------------------------
# COPY FILES INTO /docs FOR GITHUB PAGES
# ---------------------------------------------------------
shutil.copy("dashboards/dashboard.json", "docs/dashboard.json")
shutil.copy("vaults/vault.json", "docs/vault.json")

# ---------------------------------------------------------
# AUTO GIT PUSH (CRON SAFE)
# ---------------------------------------------------------

# Ensure script runs inside repo
os.chdir("/home/harryoverton07/crypto_predictor")

# Use SSH key for GitHub
os.environ["GIT_SSH_COMMAND"] = "ssh -i /home/harryoverton07/.ssh/id_rsa"

# Timestamp commit message
commit_message = f"Auto update at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

try:
    subprocess.run(["/usr/bin/git", "add", "."], check=True)
    subprocess.run(["/usr/bin/git", "commit", "-m", commit_message], check=False)
    subprocess.run(["/usr/bin/git", "push", "origin", "main"], check=True)
    print("✅ Auto Git push successful.")
except Exception as e:
    print("❌ Auto Git push failed:", e)
