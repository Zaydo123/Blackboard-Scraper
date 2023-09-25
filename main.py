# Imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from time import sleep
from selenium.common.exceptions import NoSuchElementException
import traceback
from colorama import Fore, Back, Style, init
import os
from PyPDF2 import PdfReader
import requests

init(autoreset=True)


def copy_cookies_to_requests(driver):
    session = requests.Session()
    cookies = driver.get_cookies()
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])
    return session


def download_files(session, links, folder_name='downloaded_files'):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    for idx, link in enumerate(links):
        try:
            response = session.get(link)
            response.raise_for_status()

            # Check if the file is a PDF
            if '.pdf' in link:
                # Initialize PdfReader object from BytesIO
                pdf_reader = PdfReader(BytesIO(response.content))

                # Try to get a title from the PDF metadata
                metadata = pdf_reader.metadata
                title = metadata.get('Title', f"file_{idx}") if metadata else f"file_{idx}"

                # Save PDF as a file
                filename = f"{title}.pdf"

            else:
                # For non-PDF files, save with a generic name
                filename = f"file_{idx}"

            with open(os.path.join(folder_name, filename), 'wb') as f:
                f.write(response.content)

            print(f"Saved {filename}")

        except Exception as e:
            print(f"Could not download {link}. Reason: {e}")

# Helper Functions
def find_content_list_container(driver):
    try:
        content_list_container = driver.find_element("id", "content_listContainer")
        content_list_container_children = content_list_container.find_elements("xpath", "./*")
        return content_list_container_children
    except NoSuchElementException:
        return []


def get_pdf_links(driver):
    pdf_links = driver.find_elements("xpath", "//*[contains(text(), '.pdf') and @href]")
    collected_links = [pdf.get_attribute("href") for pdf in pdf_links]
    for link in collected_links:
        print(Fore.RED + link)
    return collected_links
def explore_and_download_pdfs(driver, collected_links):
    stack = [driver.current_url]
    visited_urls = set()

    while stack:
        url = stack.pop()

        if url in visited_urls:
            continue

        if "blackboard" not in url:
            print(f"Skipping URL: {url}")
            continue

        if any(ext in url for ext in ['.pptx', '.ppt', '.key', '.odp']):
            print(f"Collecting but not navigating or clicking: {url}")
            collected_links.append(url)
            visited_urls.add(url)
            continue  

        visited_urls.add(url)

        # Navigate to the URL
        if not any(ext in url for ext in ['.pptx', '.ppt', '.key', '.odp']):
          driver.get(url)
          sleep(2)

        pdf_links = get_pdf_links(driver)
        collected_links.extend(pdf_links)

        content_list_container_children = find_content_list_container(driver)
        for child in content_list_container_children:
            try:
                link = child.find_element("tag name", "a").get_attribute("href")
                stack.append(link)
            except Exception as e:
                print("Failed to click on child")
                traceback.print_exc()
                continue


# Blackboard Course class
class Course:
    def __init__(self, course_name, course_link):
        self.course_name = course_name
        self.course_link = course_link
        self.course_tabs = []

    def add_tab(self, tab):
        self.course_tabs.append(tab)

    def get_tabs(self):
        return self.course_tabs


# Initialize WebDriver and Log In
print(Back.WHITE + Fore.BLACK + "Follow the instructions to login to your blackboard account")

login_url = input("Enter the login url for blackboard: ")
bb_email = input("Enter your email: ")
bb_pass = input("Enter your password: ")

wd_options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=wd_options)
driver.get(login_url)

WebDriverWait(driver, 10).until(lambda driver: driver.find_element("xpath", "//*[contains(text(), 'Sign In')]"))
sign_in_button = driver.find_element("xpath", "//*[contains(text(), 'Sign In')]")
sign_in_button.click()

WebDriverWait(driver, 10).until(lambda driver: driver.find_element("xpath", "//*[@type='email']"))
email_field = driver.find_element("xpath", "//*[@type='email']")
email_field.send_keys(bb_email)

WebDriverWait(driver, 10).until(lambda driver: driver.find_element("xpath", "//*[@type='submit']"))
submit_email_button = driver.find_element("xpath", "//*[@type='submit']")
submit_email_button.click()

sleep(2)
WebDriverWait(driver, 10).until(lambda driver: driver.find_element("xpath", "//*[@type='password']"))
password_field = driver.find_element("xpath", "//*[@type='password']")
password_field.send_keys(bb_pass)

sign_in_button = driver.find_element("xpath", "//*[contains(text(), 'Sign in')]")
sign_in_button.click()

# Navigate to course list
WebDriverWait(driver, 10).until(lambda driver: driver.find_element("xpath", "/html/body/div[1]/div[2]/bb-base-layout/div/aside/div[1]/nav/ul/bb-base-navigation-button[4]/div/li/a"))
driver.find_element("xpath", "/html/body/div[1]/div[2]/bb-base-layout/div/aside/div[1]/nav/ul/bb-base-navigation-button[4]/div/li/a").click()

# Wait for course list to load
WebDriverWait(driver, 10).until(lambda driver: driver.find_element("class name", "course-org-list"))
sleep(2)

# Choose a course
course_elements = driver.find_elements("class name", "js-course-title-element")
class_options = ""
for count, className in enumerate(course_elements):
    class_options += str(count) + "." + className.text + "\n"

print(class_options)
chosen_class = int(input("Enter the number of the class you want to download from: "))
course_elements[chosen_class].click()

# Initialize current course
current_course = Course(course_elements[chosen_class].text, driver.current_url)
sleep(3)
driver.switch_to.frame(driver.find_element("class name", "classic-learn-iframe"))

# Get tabs
WebDriverWait(driver, 10).until(lambda driver: driver.find_element("id", "courseMenuPalette_contents"))
tab_elements = driver.find_elements("xpath", "//*[@id='courseMenuPalette_contents']/li")

tab_links = []
tab_names = []

for tab in tab_elements:
    try:
        tab_links.append(tab.find_element("tag name", "a").get_attribute("href"))
        tab_names.append(tab.find_element("tag name", "span").text)
    except NoSuchElementException:
        traceback.print_exc()
        continue

for count, tab in enumerate(tab_names):
    current_course.add_tab({"name": tab, "link": tab_links[count]})

print(current_course.get_tabs())

# Start collecting PDFs
collected_links = []

for tab in current_course.get_tabs():
    try:
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[-1])
        driver.get(tab["link"])
        sleep(2)

        explore_and_download_pdfs(driver, collected_links)

        driver.close()
        driver.switch_to.window(driver.window_handles[0])
    except Exception as e:
        print("Failed to open tab")
        continue

print("Collected Links:", collected_links)

#write to file just in case something goes wrong
with open("links.txt", "w") as f:
    for link in collected_links:
        f.write(link + "\n")



# read links from file
with open("links.txt", "r") as f:
    collected_links = f.readlines()
    # format into array
    collected_links = [x.strip() for x in collected_links]



session = copy_cookies_to_requests(driver)
driver.quit()
download_files(session, collected_links)

