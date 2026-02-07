import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

URL = "https://sbi.bank.in/web/interest-rates/deposit-rates/retail-domestic-term-deposits"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def extract_sbi():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")

    best_rate = 0
    best_period = ""

    table = soup.find("table")  # SBI main FD table

    rows = table.find_all("tr")

    for row in rows[1:]:  # skip header
        cols = [c.get_text(strip=True) for c in row.find_all("td")]

        if len(cols) >= 3:
            period = cols[0]

            try:
                # revised general rate column (latest)
                general_rate = float(cols[2])

                if general_rate > best_rate:
                    best_rate = general_rate
                    best_period = period

            except:
                continue

    return best_rate, best_period

rate, period = extract_sbi()

result = {
    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "banks": [
        {
            "bank": "SBI",
            "scheme": "Retail FD (<3 Cr)",
            "period": period,
            "rate_general": f"{rate:.2f}%",
            "rate_senior": f"{rate + 0.5:.2f}%"
        }
    ]
}

with open("fd_rates.json", "w") as f:
    json.dump(result, f, indent=2)

print("SBI FD scraped successfully!")
