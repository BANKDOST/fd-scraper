import requests
from bs4 import BeautifulSoup
import json
import re
import pdfplumber
import io
from datetime import datetime
import time

# selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

HEADERS = {"User-Agent": "Mozilla/5.0"}


# ---------- Helper ----------
def clean_rate(text):
    match = re.search(r"\d+(?:\.\d+)?", text)
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


# ---------- AXIS (PDF parsing) ----------
def extract_axis():
    PDF_URL = "https://www.axis.bank.in/docs/default-source/default-document-library/interest-rates/domestic-fixed-deposits-11-february-26.pdf"

    r = requests.get(PDF_URL, headers=HEADERS, timeout=30)
    pdf_file = io.BytesIO(r.content)

    best_rate = 0
    best_period = ""

    with pdfplumber.open(pdf_file) as pdf:
        text = pdf.pages[0].extract_text()

    lines = text.split("\n")
    in_section = False

    for line in lines:
        lower = line.lower()

        if "less than" in lower and "3 cr" in lower:
            in_section = True
            continue

        if not in_section:
            continue

        if "3 cr to less than" in lower:
            break

        decimals = re.findall(r"\d+\.\d+", line)

        if not decimals:
            continue

        try:
            general_rate = float(decimals[0])
        except:
            continue

        if general_rate > best_rate:
            best_rate = general_rate
            best_period = line.split(decimals[0])[0].strip()

    return best_rate, best_period


# ---------- PNB (Selenium JS scraping) ----------
import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0"}

def clean_rate(text):
    """Extract float rate from string"""
    match = re.search(r"\d+(?:\.\d+)?", text)
    return float(match.group()) if match else 0.0

def extract_pnb_domestic_fd():
    url = "https://www.pnb.bank.in/Interest-Rates-Deposit.html"
    r = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")

    # Find the table for Domestic/NRO $ Fixed Deposit Scheme
    table = None
    for t in soup.find_all("table"):
        heading = t.find_previous("h3")
        if heading and "Domestic/NRO" in heading.get_text(strip=True):
            table = t
            break

    if not table:
        return 0, ""  # fallback if table not found

    best_rate = 0
    best_tenure = ""

    for row in table.find_all("tr")[1:]:  # skip header
        cols = row.find_all("td")
        if len(cols) < 3:
            continue
        tenure = cols[0].get_text(strip=True)
        rate_text = cols[2].get_text(strip=True)
        rate = clean_rate(rate_text)
        if rate > best_rate:
            best_rate = rate
            best_tenure = tenure

    return best_rate, best_tenure

# ---------- RUN ----------
pnb_rate, pnb_period = extract_pnb_domestic_fd()

banks = [
    {"bank": "PNB", "period": pnb_period, "rate": pnb_rate},
]

# Format JSON output
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

with open("pnb_fd_rates.json", "w") as f:
    json.dump(result, f, indent=2)

print("PNB Domestic Term Deposit FD rates updated successfully!")
print(json.dumps(result, indent=2))

# ---------- RUN ----------
sbi_rate, sbi_period = extract_sbi()
hdfc_rate, hdfc_period = extract_hdfc()
axis_rate, axis_period = extract_axis()
pnb_rate, pnb_period = extract_pnb()

banks = [
    {"bank": "SBI", "period": sbi_period, "rate": sbi_rate},
    {"bank": "HDFC", "period": hdfc_period, "rate": hdfc_rate},
    {"bank": "Axis Bank", "period": axis_period, "rate": axis_rate},
    {"bank": "PNB", "period": pnb_period, "rate": pnb_rate},
    {"bank": "ICICI", "period": "3 Years 1 Day to 5 Years", "rate": 6.5},
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
