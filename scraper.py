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

    r = requests.get(PDF_URL)
    pdf_file = io.BytesIO(r.content)

    best_rate = 0
    best_period = ""

    with pdfplumber.open(pdf_file) as pdf:
        page = pdf.pages[0]  # first page only
        tables = page.extract_tables()

        for table in tables:
            header = table[0]

            target_col = None
            for i, col in enumerate(header):
                if col and "less than" in col.lower():
                    target_col = i
                    break

            if target_col is None:
                continue

            for row in table[1:]:
                if not row or len(row) <= target_col:
                    continue

                tenure = row[0]
                rate_text = row[target_col]

                if not tenure or not rate_text:
                    continue

                rate = clean_rate(rate_text)

                if rate > best_rate:
                    best_rate = rate
                    best_period = tenure

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
