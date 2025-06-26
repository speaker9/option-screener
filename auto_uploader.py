import os
import time
import shutil
from datetime import datetime
import pandas as pd
import subprocess

# === Your NIFTY Option Chain Excel Path ===
SOURCE_FILE = "H:/CE PE/nifty_option_chain.xlsx"
DESTINATION_FOLDER = "H:/CE PE/option-screener"

# === Step 1: Copy latest Excel to repo folder ===
def copy_excel_to_repo():
    if os.path.exists(SOURCE_FILE):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        target = os.path.join(DESTINATION_FOLDER, "nifty_option_chain.xlsx")
        shutil.copy(SOURCE_FILE, target)
        print(f"✅ Copied Excel at {timestamp}")
    else:
        print("❌ Source Excel file not found!")

# === Step 2: Push changes to GitHub ===
def push_to_github():
    os.chdir(DESTINATION_FOLDER)
    subprocess.call(["git", "add", "."])
    subprocess.call(["git", "commit", "-m", f"Auto update {datetime.now().strftime('%H:%M:%S')}"])
    subprocess.call(["git", "push"])
    print("🚀 GitHub push done.")

# === Run full job ===
def auto_sync():
    copy_excel_to_repo()
    push_to_github()

# Run every 5 mins (optional)
if __name__ == "__main__":
    auto_sync()
