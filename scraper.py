import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ---------- SBI ----------
def extract_sbi():
    URL = "https://sbi.bank.in/web/interest-rates/deposit-rates/retail-domestic-term-deposits"
    r = requests.get(URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")

    tables = soup.find_all("table")
    target_table = tables[0]  # callable <= 3Cr

    best_rate = 0
    best_period = ""

    for row in target_table.find_all("tr")[1:]:
        cols = [c.get_text(strip=True).replace("*", "") for c in row.find_all("td")]

        if len(cols) >= 3:
            period = cols[0]

            try:
                rate = float(cols[2])

                if rate > best_rate:
                    best_rate = rate
                    best_period = period

            except:
                continue

    return best_rate, best_period


# ---------- HDFC ----------
def extract_hdfc():
    URL = "https://www.hdfcbank.com/personal/resources/rates"
    r = requests.get(URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")

    best_rate = 0
    best_period = ""

    tables = soup.find_all("table")

    for table in tables:
        if "3 crore" in table.get_text().lower():
            for row in table.find_all("tr")[1:]:
                cols = [c.get_text(strip=True).replace("%", "") for c in row.find_all("td")]

                if len(cols) >= 2:
                    period = cols[0]

                    try:
                        rate = float(cols[1])

                        if rate > best_rate:
                            best_rate = rate
                            best_period = period

                    except:
                        continue
            break

    return best_rate, best_period


# ---------- RUN ----------
sbi_rate, sbi_period = extract_sbi()
hdfc_rate, hdfc_period = extract_hdfc()

result = {
    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "banks": [
        {
            "bank": "SBI",
            "scheme": "Callable FD ≤ 3Cr",
            "period": sbi_period,
            "rate_general": f"{sbi_rate:.2f}%",
            "rate_senior": f"{sbi_rate + 0.5:.2f}%"
        },
        {
            "bank": "HDFC",
            "scheme": "Callable FD ≤ 3Cr",
            "period": hdfc_period,
            "rate_general": f"{hdfc_rate:.2f}%",
            "rate_senior": f"{hdfc_rate + 0.5:.2f}%"
        }
    ]
}

with open("fd_rates.json", "w") as f:
    json.dump(result, f, indent=2)

print("SBI + HDFC FD scraped successfully!")
