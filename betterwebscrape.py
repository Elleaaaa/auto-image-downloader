import os
import time
import requests
import csv
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Function to initialize Edge WebDriver
def init_driver():
    options = Options()
    options.headless = True  # Run browser in the background (optional)
    edge_driver_path = r'C:\Users\Sherwin\Downloads\edgedriver_win64\msedgedriver.exe'
    driver = webdriver.Edge(service=Service(edge_driver_path), options=options)
    return driver

# Function to scrape multiple product images from the swiper-container (carousel)
def scrape_multiple_product_images(driver):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    swiper_slide_tags = soup.find_all('div', {'class': 'swiper-slide'})
    image_urls = []
    for swiper_slide in swiper_slide_tags:
        img_tag = swiper_slide.find('img', {'class': 'system-components-pack-item-image'})
        if img_tag and img_tag.get('src'):
            image_urls.append(img_tag['src'])
    return image_urls

# Function to scrape product images for a given part number
def scrape_product_images(part_number):
    driver = init_driver()
    driver.get("https://www.supersprint.com/en-us/default.aspx")

    try:
        popup = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder13_ctl01_mainWrap"))
        )
        driver.execute_script("document.getElementById('ctl00_ContentPlaceHolder13_ctl01_mainWrap').style.display = 'none';")
        print(f"Popup closed for {part_number} via JavaScript")
    except Exception as e:
        print(f"No popup found or already closed for {part_number}.", e)

    search_icon = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[@class='search-icon-container']"))
    )
    search_icon.click()

    search_box = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//input[@class='input-search-box']"))
    )
    search_box.clear()
    search_box.send_keys(part_number)
    search_box.send_keys(Keys.RETURN)

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CLASS_NAME, "swiper-container"))
    )

    image_urls = scrape_multiple_product_images(driver)
    driver.quit()
    return image_urls

# ✅ Modified: Download with retry logic
def download_images(image_urls, part_number):
    folder_path = 'Supersprint_images'
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    def safe_download(url, retries=3, delay=2):
        for attempt in range(retries):
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
                    return response
                else:
                    print(f"Invalid response on attempt {attempt + 1} for {url}")
            except Exception as e:
                print(f"Error on attempt {attempt + 1} for {url}: {e}")
            time.sleep(delay)
        print(f"Failed to download after {retries} attempts: {url}")
        return None

    downloaded_count = 0
    for index, url in enumerate(image_urls, start=1):
        if url.startswith('/'):
            url = 'https://www.supersprint.com' + url

        response = safe_download(url)
        if response:
            image_name = f"{part_number}_{index}.jpg"
            image_path = os.path.join(folder_path, image_name)
            with open(image_path, 'wb') as file:
                file.write(response.content)
            print(f"Downloaded {image_name}")
            downloaded_count += 1

    return downloaded_count

# Read processed part numbers
def read_processed_part_numbers():
    if os.path.exists('processed_part_numbers.csv'):
        with open('processed_part_numbers.csv', 'r', newline='') as f:
            reader = csv.DictReader(f)
            return {row['part_number']: int(row['number_of_images']) for row in reader}
    return {}

# Write processed part numbers
def write_processed_part_number(part_number, num_images):
    file_exists = os.path.exists('processed_part_numbers.csv')
    with open('processed_part_numbers.csv', 'a', newline='') as f:
        fieldnames = ['part_number', 'number_of_images']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({'part_number': part_number, 'number_of_images': num_images})

# ✅ Modified: Added logging for skipped part numbers
def process_part_numbers_from_csv(csv_file):
    processed_part_numbers = read_processed_part_numbers()
    with open(csv_file, mode='r') as file:
        reader = csv.DictReader(file)
        part_numbers_to_process = []
        for row in reader:
            part_number = row['part_number'].strip()
            if part_number not in processed_part_numbers:
                part_numbers_to_process.append(part_number)
            else:
                print(f"Skipping already processed: {part_number}")
    return part_numbers_to_process

# Process single part number
def process_single_part_number(part_number):
    print(f"Processing part number: {part_number}")
    image_urls = scrape_product_images(part_number)
    if image_urls:
        num_images = download_images(image_urls, part_number)
        write_processed_part_number(part_number, num_images)
    else:
        print(f"No images found for {part_number}")

# Main function
def main():
    part_numbers = process_part_numbers_from_csv('part_numbers.csv')
    if part_numbers:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(process_single_part_number, part_numbers)
    else:
        print("No unprocessed part numbers found.")
    print("Download process completed.")

# Run the main function
if __name__ == "__main__":
    main()
