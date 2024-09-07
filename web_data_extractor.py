from googlesearch import search
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def initialize_selenium():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def fetch_page_content(url, use_selenium=False):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    try:
        if use_selenium:
            driver = initialize_selenium()
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            html_content = driver.page_source
            driver.quit()
            return html_content
        else:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.text
            else:
                print(f"Failed to retrieve page: {url}. Status code: {response.status_code}")
                return None
    except Exception as e:
        print(f"Error fetching the URL {url}: {e}")
        return None

def is_valid_phone_number(phone):
    digits_only = re.sub(r"[^\d]", "", phone)
    return len(digits_only) >= 10 and len(digits_only) <= 15

def extract_data(soup, data_type):
    if data_type == "links":
        return set(link.get('href') for link in soup.find_all('a') if link.get('href'))
    
    elif data_type == "headings":
        headings = set()
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            headings.update(heading.text.strip() for heading in soup.find_all(tag))
        return headings
    
    elif data_type == "paragraphs":
        return set(p.text.strip() for p in soup.find_all('p'))
    
    elif data_type == "images":
        return set(img.get('src') for img in soup.find_all('img') if img.get('src'))
    
    elif data_type == "phone numbers":
        raw_phone_numbers = set(re.findall(r'\+?\d[\d -]{8,}\d', soup.get_text()))
        valid_phone_numbers = set(phone for phone in raw_phone_numbers if is_valid_phone_number(phone))
        return valid_phone_numbers
    
    elif data_type == "emails":
        emails = set(re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', soup.get_text()))
        return emails
    
    else:
        print("Unsupported data type.")
        return set()

def process_url(url, data_type, use_selenium=False):
    print(f"Processing {url}...")
    html_content = fetch_page_content(url, use_selenium=use_selenium)
    
    if html_content:
        soup = BeautifulSoup(html_content, "html.parser")
        return extract_data(soup, data_type)
    else:
        print(f"Skipping {url} due to failed content retrieval.")
        return set()

def save_to_csv(data, data_type, file_name):
    df = pd.DataFrame(data, columns=[data_type])
    df.to_csv(file_name, index=False)
    print(f"Data saved to {file_name}")

def main():
    query = input("Enter the search query: ").strip()
    
    num_results = int(input("Enter the number of websites to retrieve (e.g., 50): ").strip())
    
    print("Searching for websites...")
    urls = []
    try:
        for url in search(query, num_results=num_results, lang="en"):
            urls.append(url)
            print(f"Found: {url}")
    except Exception as e:
        print(f"An error occurred during the search: {e}")
        return
    
    print("\nWhat type of data would you like to extract? (links, headings, paragraphs, images, phone numbers, emails)")
    data_type = input("Enter the type of data: ").strip().lower()

    use_selenium = input("\nDo you want to use Selenium to bypass CAPTCHAs? (yes/no): ").strip().lower() == "yes"
    
    unique_data = set()
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(process_url, url, data_type, use_selenium): url for url in urls}
        
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
                if data:
                    unique_data.update(data)
                    print(f"Extracted {len(data)} unique {data_type} from {url}.")
                else:
                    print(f"No {data_type} found on {url}.")
            except Exception as exc:
                print(f"{url} generated an exception: {exc}")
    
    if unique_data:
        print(f"\nTotal unique {data_type} extracted: {len(unique_data)}")
        print(f"\nListing all extracted {data_type}:")
        for idx, item in enumerate(unique_data, start=1):
            print(f"{idx}. {item}")
    
        save_option = input("\nDo you want to save the data to a CSV file? (yes/no): ").strip().lower()
        if save_option == 'yes':
            file_name = input("Enter the file name (without .csv extension): ").strip() + ".csv"
            save_to_csv(unique_data, data_type, file_name)
        else:
            print("Data not saved.")
    else:
        print("No data to save.")

if __name__ == "__main__":
    main()
