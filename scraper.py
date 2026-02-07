import requests
import re
import json
from datetime import datetime

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

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def extract_best_rate(html):
    rates = re.findall(r"\d+\.\d+%", html)
    if not rates:
        return None
    rates = [float(r.replace("%", "")) for r in rates]
    return max(rates)

results = []

for bank in BANKS:
    try:
        print(f"Fetching {bank['name']}...")
        response = requests.get(bank["url"], headers=HEADERS, timeout=20)
        html = response.text

        best = extract_best_rate(html)

        if best:
            row = {
                "bank": bank["name"],
                "scheme": "Highest FD Slab",
                "period": "Best Available",
                "rate_general": f"{best:.2f}%",
                "rate_senior": f"{best + 0.5:.2f}%"
            }
            results.append(row)
        else:
            print(f"No rate found for {bank['name']}")

    except Exception as e:
        print(f"Error scraping {bank['name']}:", e)

final = {
    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "total_banks": len(results),
    "banks": results
}

with open("fd_rates.json", "w") as f:
    json.dump(final, f, indent=2)

print("FD JSON updated successfully!")
