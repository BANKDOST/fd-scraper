import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

URL = "https://sbi.bank.in/web/interest-rates/deposit-rates/retail-domestic-term-deposits"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def is_valid_fd_row(text):
    t = text.lower()

    if "non callable" in t:
        return False
    if "above card rate" in t:
        return False
    if "bonus" in t:
        return False

    # must contain tenure words
    if not any(word in t for word in ["day", "month", "year"]):
        return False

    return True

def extract_sbi():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")

    best_rate = 0
    best_row = ""

    rows = soup.find_all("tr")

    for row in rows:
        text = row.get_text(" ", strip=True)

        if not is_valid_fd_row(text):
            continue

        rates = re.findall(r"\d+\.\d+", text)

        for r in rates:
            rate = float(r)

            if rate > best_rate and rate < 15:
                best_rate = rate
                best_row = text

    return best_rate, best_row

rate, period = extract_sbi()

result = {
    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "banks": [
        {
            "bank": "SBI",
            "scheme": "Highest Callable FD",
            "period": period,
            "rate_general": f"{rate:.2f}%",
            "rate_senior": f"{rate + 0.5:.2f}%"
        }
    ]
}

with open("fd_rates.json", "w") as f:
    json.dump(result, f, indent=2)

print("SBI cleaned FD scraped successfully!")
