import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, UnexpectedAlertPresentException
from pyvirtualdisplay import Display


chrome_options = Options()
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--remote-debugging-port=9222")

display = Display(visible=0, size=(1080, 725)).start()

driver = webdriver.Chrome(options=chrome_options)

headers = {
        'User-Agent': f'{driver.execute_script("return navigator.userAgent;")}'
        }

driver.get("http://subscene.com")

session = requests.session()
session.headers.update(headers)
for cookie in driver.get_cookies():
    c = {cookie['name']: cookie['value']}
    session.update(c)

print(driver.page_source)
#req = session.get("http://subscene.com")
#print(req.text)

