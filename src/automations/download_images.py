
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.image_downloader import download_images_from_csv

def main():
    data_dir = os.path.join(os.path.dirname(__file__), '../../data/image_downloader')
    csv_file = os.path.join(data_dir, 'images.csv')
    output_dir = os.path.join(data_dir, 'output')
    download_images_from_csv(csv_file, output_dir)

if __name__ == '__main__':
    main()
