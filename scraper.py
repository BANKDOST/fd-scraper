import requests
from bs4 import BeautifulSoup
import json
import re
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


# ---------- ICICI ----------

def extract_icici():
    URL = "https://www.icicibank.com/personal-banking/deposits/fixed-deposit/fd-interest-rates"
    
    try:
        r = requests.get(URL, headers=HEADERS, timeout=30)
        r.raise_for_status()  # raise exception for bad status codes
    except requests.RequestException as e:
        print(f"ICICI request failed: {e}")
        return 0, ""

    soup = BeautifulSoup(r.text, "lxml")
    
    best_rate = 0
    best_period = ""
    
    # Find the relevant FD rates table
    for table in soup.find_all("table"):
        text_lower = table.get_text(" ", strip=True).lower()
        if "premature" in text_lower or "cr" in text_lower or "tax saver" in text_lower:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue
                
                period = cells[0].get_text(strip=True)
                if not period or "tenure" in period.lower() or "general" in period.lower() or "senior" in period.lower():
                    continue  # skip header/sub-header rows
                
                # General citizen rate is in the second column (index 1)
                rate_text = cells[1].get_text(strip=True)
                
                # Clean up: remove %, HIGHEST, extra text → keep only the number
                rate_clean = re.sub(r"[^0-9.]", "", rate_text)
                
                try:
                    rate = float(rate_clean)
                    if rate > best_rate and rate >= 2:  # realistic filter
                        best_rate = rate
                        best_period = period
                except ValueError:
                    continue
            
            # Stop after processing the first matching table with valid rates
            if best_rate > 0:
                break
    
    if best_rate == 0:
        print("ICICI: No valid general citizen rate found in the tables")
    
    return best_rate, best_period



# ---------- RUN ----------
sbi_rate, sbi_period = extract_sbi()
hdfc_rate, hdfc_period = extract_hdfc()
icici_rate, icici_period = extract_icici()

banks = [
    {"bank": "SBI", "period": sbi_period, "rate": sbi_rate},
    {"bank": "HDFC", "period": hdfc_period, "rate": hdfc_rate},
    {"bank": "ICICI", "period": icici_period, "rate": icici_rate},

    # Manual Bank of Baroda
    {"bank": "Bank of Baroda", "period": "444 days", "rate": 6.45},
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

print("SBI + HDFC + ICICI + BoB updated successfully!")
