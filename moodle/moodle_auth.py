import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

LOGIN_URL = "https://www.moodle.tum.de/login/index.php"


def _build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)


def get_moodle_session(username: str, password: str) -> requests.Session:
    driver = _build_driver()
    try:
        wait = WebDriverWait(driver, 30)

        # Step 1: Load Moodle login page and click "TUM LOGIN" SSO button
        driver.get(LOGIN_URL)
        wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "TUM LOGIN"))).click()

        # Step 2: On login.tum.de IDP page, fill in TUM credentials
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(username)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # Step 3: Wait for redirect back to Moodle dashboard
        wait.until(EC.url_contains("moodle.tum.de/my/"))

        # Step 4: Transfer all Moodle cookies to a requests.Session
        session = requests.Session()
        for cookie in driver.get_cookies():
            session.cookies.set(cookie["name"], cookie["value"], domain=cookie.get("domain"))
        return session

    finally:
        driver.quit()
