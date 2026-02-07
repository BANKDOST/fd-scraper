import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}

BANKS = [
    {"name": "SBI", "url": "https://sbi.co.in/web/interest-rates/deposit-rates/retail-domestic-term-deposits"},
    {"name": "HDFC", "url": "https://www.hdfcbank.com/personal/save/deposits/fixed-deposit/fd-interest-rates"},
    {"name": "PNB", "url": "https://www.pnbindia.in/interest-rates-deposits.html"},
    {"name": "Bank of Baroda", "url": "https://www.bankofbaroda.in/interest-rate-and-service-charges/deposits-interest-rates"},
    {"name": "Canara Bank", "url": "https://canarabank.com/pages/Interest-Rates"},
    {"name": "Bank of India", "url": "https://bankofindia.co.in/interest-rates"},
    {"name": "ICICI", "url": "https://www.icicibank.com/personal-banking/deposits/fixed-deposit/fd-interest-rates"},
    {"name": "Axis", "url": "https://www.axisbank.com/interest-rate-on-deposits"},
    {"name": "IDFC First", "url": "https://www.idfcfirstbank.com/personal-banking/deposits/fixed-deposit/interest-rates"},
    {"name": "HDFC Small Finance", "url": "https://www.hdfcbank.com/sme/deposits/fixed-deposit-interest-rates"}
]

def extract_best_rate(html):
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text()

    rates = re.findall(r"\d+\.\d+%", text)
    if not rates:
        return None

    rates = [float(r.replace("%", "")) for r in rates]
    return max(rates)

results = []

for bank in BANKS:
    try:
        print(f"Fetching {bank['name']}...")

        r = requests.get(bank["url"], headers=HEADERS, timeout=30)
        html = r.text

        best = extract_best_rate(html)

        if best:
            results.append({
                "bank": bank["name"],
                "scheme": "Best FD Slab",
                "period": "Highest Available",
                "rate_general": f"{best:.2f}%",
                "rate_senior": f"{best + 0.5:.2f}%"
            })
        else:
            print("No rate found for", bank["name"])

    except Exception as e:
        print("Error scraping", bank["name"], e)

final = {
    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "total_banks": len(results),
    "banks": results
}

with open("fd_rates.json", "w") as f:
    json.dump(final, f, indent=2)

print("FD JSON updated successfully!")
