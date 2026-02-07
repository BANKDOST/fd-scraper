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

    table = soup.find_all("table")[0]

    best_rate = 0
    best_period = ""

    for row in table.find_all("tr")[1:]:
        cols = [c.get_text(strip=True).replace("*", "") for c in row.find_all("td")]

        if len(cols) >= 3:
            try:
                rate = float(cols[2])
                if rate > best_rate:
                    best_rate = rate
                    best_period = cols[0]
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

    for table in soup.find_all("table"):
        if "3 crore" in table.get_text().lower():
            for row in table.find_all("tr")[1:]:
                cols = [c.get_text(strip=True).replace("%", "") for c in row.find_all("td")]
                if len(cols) >= 2:
                    try:
                        rate = float(cols[1])
                        if rate > best_rate:
                            best_rate = rate
                            best_period = cols[0]
                    except:
                        continue
            break

    return best_rate, best_period


# ---------- Bank of Baroda ----------
def extract_bob():
    URL = "https://bankofbaroda.bank.in/interest-rate-and-service-charges/deposits-interest-rates/fixed-deposits-callable-and-non-callable-upto-ten-crores"
    r = requests.get(URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")

    best_rate = 0
    best_period = ""

    # Find the FD callable section by heading text
    # Then find the first table that has 'Domestic Term Deposits'
    tables = soup.find_all("table")

    for table in tables:
        text = table.get_text().lower()
        if "domestic term deposits including nro deposits below" in text:
            for row in table.find_all("tr")[1:]:
                cols = [c.get_text(strip=True).replace("%", "") for c in row.find_all("td")]

                if len(cols) >= 2:
                    try:
                        rate = float(cols[1])
                        if rate > best_rate:
                            best_rate = rate
                            best_period = cols[0]
                    except:
                        continue
            break

    return best_rate, best_period



# ---------- RUN ----------
sbi_rate, sbi_period = extract_sbi()
hdfc_rate, hdfc_period = extract_hdfc()
bob_rate, bob_period = extract_bob()

banks = [
    {"bank": "SBI", "period": sbi_period, "rate": sbi_rate},
    {"bank": "HDFC", "period": hdfc_period, "rate": hdfc_rate},
    {"bank": "Bank of Baroda", "period": bob_period, "rate": bob_rate},
]

banks.sort(key=lambda x: x["rate"], reverse=True)

output = []
for b in banks:
    output.append({
        "bank": b["bank"],
        "scheme": "Callable FD ≤ 3Cr",
        "period": b["period"],
        "rate_general": f'{b["rate"]:.2f}%',
        "rate_senior": f'{b["rate"] + 0.5:.2f}%'
    })

result = {
    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "banks": output
}

with open("fd_rates.json", "w") as f:
    json.dump(result, f, indent=2)

print("SBI + HDFC + BoB scraped successfully!")
