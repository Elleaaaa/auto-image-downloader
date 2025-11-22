import pandas as pd
import requests
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# Correct file path using raw string
file_path = r'C:\Users\Sherwin\Desktop\Ongoing Dave\DiodeDynamics_Images.csv'
df = pd.read_csv(file_path)

# Folder where you want to save the images
save_folder = r'C:\Users\Sherwin\Desktop\DiodeDynamics_Images'

# Create the folder if it doesn't exist
if not os.path.exists(save_folder):
    os.makedirs(save_folder)

# File to log failed downloads
failed_downloads_file = os.path.join(save_folder, "failed_downloads.csv")

# Create the failed_downloads file if it doesn't exist
if not os.path.exists(failed_downloads_file):
    pd.DataFrame(columns=['part_number', 'image_url', 'reason']).to_csv(failed_downloads_file, index=False)

# Function to sanitize file names
def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

# Function to log a failed download entry immediately
def log_failed_download(part_number, image_url, reason):
    part_number = str(part_number)
    failed_entry = pd.DataFrame(
        [{'part_number': part_number, 'image_url': image_url, 'reason': reason}]
    )
    failed_entry.to_csv(failed_downloads_file, mode='a', header=False, index=False)

# Function to download a single image
def download_image(part_number, image_url, index):
    part_number = str(part_number)
    if pd.isna(image_url) or not isinstance(image_url, str) or not image_url.strip():
        return f"Skipping empty URL for {part_number}"
    
    image_url = image_url.strip()
    sanitized_part_number = sanitize_filename(part_number)
    image_suffix = f"_{index}" if index > 0 else ""
    image_path = os.path.join(save_folder, f"{sanitized_part_number}{image_suffix}.jpg")
    
    # Skip if the image already exists
    if os.path.exists(image_path):
        return f"Image {image_path} already exists. Skipping."
    
    # Ensure the URL has a valid scheme
    if not image_url.startswith('http'):
        log_failed_download(part_number, image_url, "Invalid URL")
        return f"Invalid URL for {part_number}: {image_url}"
    
    # Download the image
    try:
        response = requests.get(image_url, stream=True, timeout=10)
        response.raise_for_status()
        
        with open(image_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        return f"Downloaded: {image_path}"
    except requests.exceptions.Timeout:
        log_failed_download(part_number, image_url, "Timeout Error")
        return f"Failed to download {image_url}: Timeout Error"
    except requests.exceptions.HTTPError as http_err:
        log_failed_download(part_number, image_url, f"HTTP Error: {http_err}")
        return f"Failed to download {image_url}: HTTP Error"
    except requests.exceptions.RequestException as e:
        log_failed_download(part_number, image_url, f"Request Error: {e}")
        return f"Failed to download {image_url}: Request Error"

# Use ThreadPoolExecutor for parallel downloads
with ThreadPoolExecutor(max_workers=50) as executor:  # Adjust `max_workers` based on your system
    futures = []
    
    for _, row in df.iterrows():
        part_number = row['part_number']
        for index, col in enumerate(df.columns[1:]):  # Skip 'part_number' column
            futures.append(executor.submit(download_image, part_number, row[col], index))
    
    for future in as_completed(futures):
        print(future.result())

print("Download process completed.")