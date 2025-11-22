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

    # Handle potential overlay (country selector or popup)
    try:
        popup = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder13_ctl01_mainWrap"))
        )
        driver.execute_script("document.getElementById('ctl00_ContentPlaceHolder13_ctl01_mainWrap').style.display = 'none';")
        print(f"Popup closed for {part_number} via JavaScript")
    except Exception as e:
        print(f"No popup found or already closed for {part_number}.", e)

    # Wait for the search icon to be clickable and click it
    search_icon = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[@class='search-icon-container']"))
    )
    search_icon.click()

    # Find the search input box and enter the part number
    search_box = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//input[@class='input-search-box']"))
    )
    search_box.clear()  # Clear any existing text
    search_box.send_keys(part_number)
    search_box.send_keys(Keys.RETURN)  # Press Enter

    # Wait for the swiper container to load
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CLASS_NAME, "swiper-container"))
    )

    # Get image URLs from the swiper container
    image_urls = scrape_multiple_product_images(driver)

    # Close the driver after scraping
    driver.quit()

    return image_urls

# Function to download images and save them in a folder with part_number and index
def download_images(image_urls, part_number):
    folder_path = 'Supersprint_images'
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    downloaded_count = 0
    for index, url in enumerate(image_urls, start=1):
        try:
            if url.startswith('/'):
                url = 'https://www.supersprint.com' + url

            response = requests.get(url)
            if response.status_code == 200:
                image_name = f"{part_number}_{index}.jpg"
                image_path = os.path.join(folder_path, image_name)
                with open(image_path, 'wb') as file:
                    file.write(response.content)
                print(f"Downloaded {image_name}")
                downloaded_count += 1
            else:
                print(f"Failed to download {url}")
        except Exception as e:
            print(f"Error downloading {url}: {e}")

    return downloaded_count

# Function to read processed part numbers from a CSV file
def read_processed_part_numbers():
    if os.path.exists('processed_part_numbers.csv'):
        with open('processed_part_numbers.csv', 'r', newline='') as f:
            reader = csv.DictReader(f)
            return {row['part_number']: int(row['number_of_images']) for row in reader}
    return {}

# Function to write processed part numbers and the number of images to CSV
def write_processed_part_number(part_number, num_images):
    # Check if file exists, if not create it
    file_exists = os.path.exists('processed_part_numbers.csv')

    with open('processed_part_numbers.csv', 'a', newline='') as f:
        fieldnames = ['part_number', 'number_of_images']
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        # Write header only if the file is empty (on first run)
        if not file_exists:
            writer.writeheader()

        writer.writerow({'part_number': part_number, 'number_of_images': num_images})

# Function to process part numbers from CSV
def process_part_numbers_from_csv(csv_file):
    processed_part_numbers = read_processed_part_numbers()  # Read already processed part numbers
    with open(csv_file, mode='r') as file:
        reader = csv.DictReader(file)
        part_numbers_to_process = []
        for row in reader:
            part_number = row['part_number']
            if part_number not in processed_part_numbers:
                part_numbers_to_process.append(part_number)

    return part_numbers_to_process

# Function to process a single part number
def process_single_part_number(part_number):
    print(f"Processing part number: {part_number}")
    image_urls = scrape_product_images(part_number)
    if image_urls:
        num_images = download_images(image_urls, part_number)
        write_processed_part_number(part_number, num_images)  # Mark as processed with image count
    else:
        print(f"No images found for {part_number}")

# Main function to process part numbers in parallel
def main():
    part_numbers = process_part_numbers_from_csv('part_numbers.csv')
    if part_numbers:
        # Use ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:  # You can adjust max_workers as needed
            executor.map(process_single_part_number, part_numbers)
    else:
        print("No unprocessed part numbers found.")
    print("Download process completed.")

# Run the main function
if __name__ == "__main__":
    main()