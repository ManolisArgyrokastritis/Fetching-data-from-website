import warnings
import re
import subprocess
import sys
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import logging
import pandas as pd
import concurrent.futures
import time

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    import pandas as pd
except ImportError:
    install('pandas')
    import pandas as pd

try:
    import openpyxl
except ImportError:
    install('openpyxl')
    import openpyxl

def configure_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.cookies": 2,
        "profile.managed_default_content_settings.javascript": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)
    service = Service(r'D:\\Chrome Downloads\\chromedriver-win64\\chromedriver-win64\\chromedriver.exe')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def scrape_contact_info(url, driver):
    retry_attempts = 3
    for attempt in range(retry_attempts):
        try:
            logging.getLogger('selenium').setLevel(logging.CRITICAL)
            warnings.filterwarnings("ignore", category=DeprecationWarning)

            driver.get(url)
            time.sleep(2)  # Allow some time for the page to load
            html = driver.page_source

            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, html)

            phone_pattern = r'\b(\d{5}\s\d{2}\s\d{3}|\d{5}\s\d{5}|\d{3}\s\d{4}\s\d{3}|\d{10})\b'
            phones = re.findall(phone_pattern, html)

            return set(emails), set(phones)
        except Exception as e:
            if attempt < retry_attempts - 1:
                print(f"Retrying {url} (attempt {attempt + 1}/{retry_attempts})")
                time.sleep(2)
            else:
                print(f"Error scraping {url}: {e}", file=sys.stderr)
                return set(), set()

def scrape_site(site, driver):
    emails, phones = scrape_contact_info(site, driver)
    domain = urlparse(site).netloc
    company_name = domain.split('.')[-2].capitalize()
    return {
        "Company Name": company_name,
        "Emails": ', '.join(emails) if emails else 'None',
        "Contact Phone": ', '.join(phones) if phones else 'None'
    }

def run_scraper():
    websites = [
        "https://simoscamping.gr/epikinonia/",
        "https://www.armenistis.gr/en/contact-form-en",
        "https://www.ouzounibeach.gr/el/epikoinonia.html",
        "https://www.rellasamortiser.gr/el/contact",
        "https://www.infoquest.gr/en/contact"
    ]

    drivers = [configure_driver() for _ in range(min(len(websites), 5))]
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(scrape_site, site, drivers[i % len(drivers)]): site for i, site in enumerate(websites)}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    for driver in drivers:
        driver.quit()

    df = pd.DataFrame(results)
    df.to_excel("contact_info.xlsx", index=False)
    print("Data has been written to contact_info.xlsx")

if __name__ == "__main__":
    run_scraper()
