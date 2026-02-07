import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

URL = "https://sbi.bank.in/web/interest-rates/deposit-rates/retail-domestic-term-deposits"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def extract_sbi():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")

    # Find callable <= 3 Cr table
    tables = soup.find_all("table")
    target_table = tables[0]  # SBI page: first table is callable <= 3Cr

    best_rate = 0
    best_period = ""

    for row in target_table.find_all("tr")[1:]:
        cols = [c.get_text(strip=True).replace("*", "") for c in row.find_all("td")]

        if len(cols) >= 3:
            period = cols[0]

            try:
                general_rate = float(cols[2])  # general column only

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
            "scheme": "Callable FD ≤ 3Cr",
            "period": period,
            "rate_general": f"{rate:.2f}%",
            "rate_senior": f"{rate + 0.5:.2f}%"
        }
    ]
}

with open("fd_rates.json", "w") as f:
    json.dump(result, f, indent=2)

print("SBI callable FD scraped successfully!")
