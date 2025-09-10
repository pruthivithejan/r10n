import csv
import os

import requests


def download_images_from_csv(csv_file, output_dir="downloaded_images"):
    """
    Downloads images from URLs in a CSV file and saves them with names from the first column.
    Each row in the CSV should be: name,url
    """
    os.makedirs(output_dir, exist_ok=True)
    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) != 2:
                continue  # skip malformed rows
            name, url = row
            filename = f"{name.strip()}.jpg"
            filepath = os.path.join(output_dir, filename)
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                with open(filepath, "wb") as img_file:
                    img_file.write(response.content)
                print(f"Downloaded {filename}")
            except Exception as e:
                print(f"Failed to download {url}: {e}")
