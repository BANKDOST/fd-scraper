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
def extract_pnb():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://www.pnb.bank.in/Interest-Rates-Deposit.html")

    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    wait = WebDriverWait(driver, 20)

    # click Domestic Term Deposit
    domestic = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//*[contains(text(),'Domestic Term Deposit')]"))
    )
    driver.execute_script("arguments[0].click();", domestic)

    # click ≤ 3 Cr option
    below3 = wait.until(
    EC.element_to_be_clickable((By.XPATH, "//*[contains(text(),'3 Crore')]"))
)
driver.execute_script("arguments[0].click();", below3)  # ✅ aligned with above


    # wait for FD table rows
    rows = wait.until(
        EC.presence_of_all_elements_located((By.XPATH, "//table//tr"))
    )

    best_rate = 0
    best_period = ""

    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) < 3:
            continue

        tenure = cols[0].text.strip()
        rate_text = cols[2].text.strip()
        rate = clean_rate(rate_text)

        if rate > best_rate:
            best_rate = rate
            best_period = tenure

    driver.quit()
    return best_rate, best_period

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
