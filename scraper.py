import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

URL = "https://sbi.co.in/web/interest-rates/deposit-rates/retail-domestic-term-deposits"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def extract_sbi_best():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")

    best_rate = 0
    best_period = ""

    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")

        for row in rows:
            text = row.get_text(" ", strip=True)

            rates = re.findall(r"\d+\.\d+", text)
            if rates:
                rate = max(float(r) for r in rates)

                if rate > best_rate:
                    best_rate = rate
                    best_period = text

    return best_rate, best_period


rate, period = extract_sbi_best()

result = {
    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "banks": [
        {
            "bank": "SBI",
            "scheme": "Best FD Slab",
            "period": period,
            "rate_general": f"{rate:.2f}%",
            "rate_senior": f"{rate + 0.5:.2f}%"
        }
    ]
}

with open("fd_rates.json", "w") as f:
    json.dump(result, f, indent=2)

print("SBI FD scraped successfully!")
