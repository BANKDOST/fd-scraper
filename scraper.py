import requests
from bs4 import BeautifulSoup
import json
import re
import pdfplumber
import io
from datetime import datetime

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


# ---------- Axis (PDF parsing) ----------
def extract_axis():
    url = "https://www.axis.bank.in/docs/default-source/default-document-library/interest-rates/domestic-fixed-deposits-12-february-26.pdf"

    r = requests.get(url)
    pdf_bytes = io.BytesIO(r.content)

    best_rate = 0
    best_period = ""

    with pdfplumber.open(pdf_bytes) as pdf:
        page = pdf.pages[0]   # first page only
        tables = page.extract_tables()

        for table in tables:
            for row in table:
                if not row or len(row) < 2:
                    continue

                tenure = (row[0] or "").strip()
                rate_text = (row[1] or "").strip()

                # skip headers
                if not tenure or "tenure" in tenure.lower():
                    continue

                # extract numeric rate
                match = re.search(r"\d+(\.\d+)?", rate_text)
                if not match:
                    continue

                rate = float(match.group())

                if rate > best_rate:
                    best_rate = rate
                    best_period = tenure

    return {
        "bank": "Axis Bank",
        "scheme": "Callable FD ≤ 3Cr",
        "period": best_period,
        "rate_general": f"{best_rate:.2f}%",
    }# ---------- PNB ----------
def extract_pnb():
    URL = "https://www.pnb.bank.in/Interest-Rates-Deposit.html"
    r = requests.get(URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")

    best_rate = 0
    best_period = ""

    section = soup.find("div", id="fa-tab132")
    if not section:
        return 0, ""

    table = section.find("table", class_="inner-page-table")
    rows = table.find_all("tr")

    for row in rows[2:]:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        period = cols[1].get_text(strip=True)
        rate = clean_rate(cols[2].get_text(strip=True))

        if rate > best_rate:
            best_rate = rate
            best_period = period

    return best_rate, best_period


# ---------- Canara ----------

def extract_canara():
    URL = "https://www.canarabank.bank.in/pages/deposit-interest-rates"
    r = requests.get(URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")

    best_rate = 0
    best_period = ""

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cols = [c.get_text(strip=True) for c in row.find_all("td")]

            if len(cols) < 2:
                continue

            period = cols[0].lower()

            # only accept real FD rows
            if not any(x in period for x in ["day", "year"]):
                continue

            if "na" in cols[1].lower():
                continue

            rate = clean_rate(cols[1])

            # sanity check
            if rate <= 0 or rate > 20:
                continue

            if rate > best_rate:
                best_rate = rate
                best_period = cols[0]

    return best_rate, best_period

# ---------- Union Bank ----------
def extract_union():
    URL = "https://www.unionbankofindia.bank.in/en/details/rate-of-interest"
    r = requests.get(URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")

    best_rate = 0
    best_period = ""

    table = soup.find("div", class_="inner-table")
    if not table:
        return 0, ""

    rows = table.find_all("tr")

    for row in rows:
        cols = [c.get_text(strip=True) for c in row.find_all("td")]

        if len(cols) < 2:
            continue

        period = cols[0]
        rate = clean_rate(cols[1])

        # ignore junk rows
        if rate <= 0 or rate > 20:
            continue

        if rate > best_rate:
            best_rate = rate
            best_period = period

    return best_rate, best_period

# ---------- Indian Bank ----------
def extract_indianbank():
    URL = "https://indianbank.bank.in/departments/deposit-rates/"
    r = requests.get(URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "lxml")

    best_rate = 0
    best_period = ""

    table = soup.find("table")
    if not table:
        return 0, ""

    for row in table.find_all("tr"):
        cols = [c.get_text(strip=True) for c in row.find_all("td")]

        # skip header or bad rows
        if len(cols) < 2:
            continue

        period = cols[0]
        rate_text = cols[1]

        if not re.search(r"\d+(?:\.\d+)?", rate_text):
            continue

        rate = clean_rate(rate_text)

        if rate > best_rate:
            best_rate = rate
            best_period = period

    return best_rate, best_period

# ---------- IDFC FIRST Bank (PDF multi-table parsing) ----------
def extract_idfcfirst():
    pdf_url = "https://www.idfcfirst.bank.in/content/dam/idfcfirstbank/interest-rate/Interest-Rates-on-Retail-Deposits-4th-November-2025.pdf"

    try:
        r = requests.get(pdf_url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return 0, ""

        pdf_file = io.BytesIO(r.content)

        best_rate = 0
        best_period = ""

        with pdfplumber.open(pdf_file) as pdf:
            page = pdf.pages[0]
            tables = page.extract_tables()

        if not tables:
            return 0, ""

        # loop through ALL tables on page 1
        for table in tables:
            for row in table:
                if not row or len(row) < 2:
                    continue

                period = str(row[0]).strip()
                rate_text = str(row[1]).strip()

                rate = clean_rate(rate_text)

                if rate > best_rate:
                    best_rate = rate
                    best_period = period

        return best_rate, best_period

    except Exception as e:
        print("IDFC scraping failed:", e)
        return 0, ""





# ---------- RUN ----------
sbi_rate, sbi_period = extract_sbi()
hdfc_rate, hdfc_period = extract_hdfc()
axis_rate, axis_period = extract_axis()
pnb_rate, pnb_period = extract_pnb()
canara_rate, canara_period = extract_canara()
union_rate, union_period = extract_union()
indianbank_rate, indianbank_period = extract_indianbank()
idfc_rate, idfc_period = extract_idfcfirst()




banks = [
    {"bank": "SBI", "period": sbi_period, "rate": sbi_rate},
    {"bank": "HDFC", "period": hdfc_period, "rate": hdfc_rate},
    {"bank": "Axis Bank", "period": axis_period, "rate": axis_rate},
    {"bank": "PNB", "period": pnb_period, "rate": pnb_rate},
    {"bank": "Canara Bank", "period": canara_period, "rate": canara_rate},
    {"bank": "ICICI", "period": "3 Years 1 Day to 5 Years", "rate": 6.5},
    {"bank": "Bank of Baroda", "period": "444 days", "rate": 6.45},
    {"bank": "Union Bank", "period": union_period, "rate": union_rate},
    {"bank": "Indian Bank", "period": indianbank_period, "rate": indianbank_rate},
    {"bank": "IDFC FIRST Bank", "period": idfc_period, "rate": idfc_rate},
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
