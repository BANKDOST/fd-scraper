import requests
from bs4 import BeautifulSoup
import pdfplumber
import json
import re
import io
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0"}


# ---------- Helper ----------
def clean_rate(text):
    match = re.search(r"\d+(\.\d+)?", text)
    return float(match.group()) if match else 0


# ---------- SBI ----------
def extract_sbi():
    URL = "https://sbi.bank.in/web/interest-rates/deposit-rates/retail-domestic-term-deposits"
    r = requests.get(URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")

    best_rate = 0
    best_period = ""

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cols = [c.get_text(strip=True) for c in row.find_all("td")]

            if len(cols) >= 3:
                rate = clean_rate(cols[2])
                if rate > best_rate:
                    best_rate = rate
                    best_period = cols[0]

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
            for row in table.find_all("tr"):
                cols = [c.get_text(strip=True) for c in row.find_all("td")]

                if len(cols) >= 2:
                    rate = clean_rate(cols[1])
                    if rate > best_rate:
                        best_rate = rate
                        best_period = cols[0]
            break

    return best_rate, best_period


# ---------- AXIS (PDF scrape) ----------

def extract_axis():
    PDF_URL = "https://www.axisbank.com/docs/default-source/deposits/domestic-term-deposit-rates.pdf"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/pdf"
    }

    r = requests.get(PDF_URL, headers=headers, timeout=30)

    if "application/pdf" not in r.headers.get("Content-Type", ""):
        print("Axis PDF download failed")
        return 0, ""

    pdf_file = io.BytesIO(r.content)

    best_rate = 0
    best_period = ""

    with pdfplumber.open(pdf_file) as pdf:
        text = pdf.pages[0].extract_text()

    lines = text.split("\n")

    reading = False

    for line in lines:

        # start after correct section header
        if "less than ₹ 3" in line.lower() or "less than 3" in line.lower():
            reading = True
            continue

        # stop when next section begins
        if reading and ("above ₹" in line.lower() or "more than" in line.lower()):
            break

        if not reading:
            continue

        # find ALL % in line
        matches = re.findall(r"\d+(\.\d+)?", line)
        percents = re.findall(r"\d+\.\d+|\d+", line)

        if len(percents) < 1:
            continue

        # FIRST % is general column
        rate = float(percents[0])

        # tenure = text before first %
        period = line.split(percents[0])[0].strip()

        if rate > best_rate:
            best_rate = rate
            best_period = period

    return best_rate, best_period

            


# ---------- RUN ----------
sbi_rate, sbi_period = extract_sbi()
hdfc_rate, hdfc_period = extract_hdfc()
axis_rate, axis_period = extract_axis()

banks = [
    {"bank": "SBI", "period": sbi_period, "rate": sbi_rate},
    {"bank": "HDFC", "period": hdfc_period, "rate": hdfc_rate},
    {"bank": "Axis Bank", "period": axis_period, "rate": axis_rate},

    # Manual ICICI
    {"bank": "ICICI", "period": "3 Years 1 Day to 5 Years", "rate": 6.5},

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

print("FD rates updated successfully!")
