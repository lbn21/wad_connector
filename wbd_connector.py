#!/usr/bin/env python3
import os
import time
import glob
import math
import requests
import xml.etree.ElementTree as ET
import argparse
import logging
from colorama import Fore, Style, init

# Initialize colorama (with auto-reset)
init(autoreset=True)

# Configure logging for output messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

BATCH_DIR = "batches"

def ensure_batch_dir():
    """Ensure that the batches directory exists."""
    if not os.path.exists(BATCH_DIR):
        os.makedirs(BATCH_DIR)

def get_last_batch_info():
    """
    Returns a tuple (last_filename, last_first_index).
    The last_first_index is the 'indeks' attribute of the first <book> element
    in the last saved batch file.
    If no batch file exists, returns (None, None).
    """
    ensure_batch_dir()
    batch_files = glob.glob(os.path.join(BATCH_DIR, "batch_*.xml"))
    if not batch_files:
        return None, None
    batch_files.sort()
    last_file = batch_files[-1]
    try:
        tree = ET.parse(last_file)
        root = tree.getroot()
        first_book = root.find(".//book")
        last_first_index = first_book.get("indeks") if first_book is not None else None
    except Exception as e:
        logging.error(f"Error reading last batch file: {e}")
        last_first_index = None
    return last_file, last_first_index

def get_next_batch_number():
    """
    Determines the next batch number based on existing files.
    """
    ensure_batch_dir()
    batch_files = glob.glob(os.path.join(BATCH_DIR, "batch_*.xml"))
    if not batch_files:
        return 1
    batch_files.sort()
    last_file = os.path.basename(batch_files[-1])
    parts = last_file.split('_')
    try:
        last_num = int(parts[1])
    except Exception:
        last_num = 0
    return last_num + 1

def save_batch(content, batch_num, first_index, confirmed=False):
    """
    Saves the batch content to a file.
    The filename format is:
      batch_{batch_num:04d}_{first_index}{_confirmed}.xml
    """
    suffix = "_confirmed" if confirmed else ""
    filename = os.path.join(BATCH_DIR, f"batch_{batch_num:04d}_{first_index}{suffix}.xml")
    with open(filename, "wb") as f:
        f.write(content)
    return filename

def update_confirmation(filename):
    """
    Renames the file to mark it as confirmed by appending _confirmed before the .xml extension.
    """
    if "_confirmed" in filename:
        return filename
    new_filename = filename.replace(".xml", "_confirmed.xml")
    os.rename(filename, new_filename)
    return new_filename

def print_header(records_downloaded, total_records, batch_size):
    """Prints a colored header message with download stats and estimated time remaining."""
    remaining = total_records - records_downloaded
    batches_left = math.ceil(remaining / batch_size) if batch_size > 0 else 0
    total_remaining_seconds = batches_left * 60  # 60 seconds per batch
    hours = total_remaining_seconds // 3600
    minutes = (total_remaining_seconds % 3600) // 60
    seconds = total_remaining_seconds % 60
    header_message = (
        f"{Fore.GREEN}Starting Download:\n"
        f"  Total records      : {total_records:,} (guide)\n"
        f"  Already downloaded : {records_downloaded:,}\n"
        f"  Remaining          : {remaining:,} records ({batches_left:,} batches estimated)\n"
        f"  Estimated time     : {hours} hours, {minutes} minutes, {seconds} seconds\n"
        f"{Style.RESET_ALL}"
    )
    print(header_message)

def get_with_retries(url, params, retries=3, delay=5):
    """Attempt a GET request with retries on failure."""
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response
            else:
                logging.error(f"Attempt {attempt}: Received status code {response.status_code}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Attempt {attempt}: Request failed: {e}")
        if attempt < retries:
            logging.info(f"Retrying in {delay} seconds...")
            time.sleep(delay)
    return None

def get_books(client_id, password, base_url, total_records, batch_size):
    """
    Downloads books data from the API.

    Example GET URL for getdb:
      http://services.azymut.pl/oferta/servlet/?mode=getdb&id=FAKE_ID&p=FAKE_PASSWORD

    And for confirmation:
      http://services.azymut.pl/oferta/servlet/?mode=confirm&id=FAKE_ID&p=FAKE_PASSWORD&transactionId=...
    """
    # Build parameter dictionaries for getdb and confirm calls.
    getdb_params = {
        "mode": "getdb",
        "id": client_id,
        "p": password
    }
    confirm_params = {
        "mode": "confirm",
        "id": client_id,
        "p": password
    }

    while True:
        batch_num = get_next_batch_number()
        _, last_first_index = get_last_batch_info()
        records_downloaded = (batch_num - 1) * batch_size

        print_header(records_downloaded, total_records, batch_size)

        # Wait 60 seconds if we've already downloaded at least one batch.
        if records_downloaded > 0:
            logging.info(f"{Fore.CYAN}Waiting 60 seconds before next request...{Style.RESET_ALL}")
            time.sleep(60)

        logging.info(f"{Fore.YELLOW}Requesting a new batch from getdb...{Style.RESET_ALL}")
        response = get_with_retries(base_url, params=getdb_params)
        if response is None:
            logging.error("Failed to fetch data after retries; exiting.")
            break

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as e:
            logging.error(f"Error parsing XML: {e}")
            break

        books = root.findall(".//book")
        if not books:
            logging.info("No records returned by getdb; ending download.")
            break

        current_first_index = books[0].get("indeks")
        if last_first_index is not None and current_first_index == last_first_index:
            logging.info(f"{Fore.MAGENTA}Duplicate batch detected (first record index matches last saved batch).{Style.RESET_ALL}")
            confirm_params["transactionId"] = root.get("transactionId")
            confirm_response = get_with_retries(base_url, params=confirm_params)
            if confirm_response is not None and confirm_response.status_code == 200:
                logging.info(f"{Fore.GREEN}Confirmation succeeded on duplicate batch. Updating last batch file.{Style.RESET_ALL}")
                last_file, _ = get_last_batch_info()
                if last_file and "_confirmed" not in last_file:
                    update_confirmation(last_file)
                last_first_index = None
            else:
                logging.error("Confirmation failed on duplicate batch.")
            continue

        logging.info(f"{Fore.YELLOW}Saving new batch {batch_num} with first record index {current_first_index}.{Style.RESET_ALL}")
        filename = save_batch(response.content, batch_num, current_first_index, confirmed=False)

        confirm_params["transactionId"] = root.get("transactionId")
        confirm_response = get_with_retries(base_url, params=confirm_params)
        if confirm_response is not None and confirm_response.status_code == 200:
            logging.info(f"{Fore.GREEN}Batch confirmed successfully.{Style.RESET_ALL}")
            update_confirmation(filename)
            last_first_index = None
        else:
            logging.error("Batch confirmation failed; will retry this batch next time.")
            last_first_index = current_first_index
            continue

    logging.info("Download complete.")

def main():
    parser = argparse.ArgumentParser(
        description="Download books data from the Azymut API (WBDConnector) with delay, duplicate check, and resume capability."
    )
    parser.add_argument("--client-id", required=True, help="Client ID for authentication (e.g., FAKE_ID)")
    parser.add_argument("--password", required=True, help="Password for authentication (e.g., FAKE_PASSWORD)")
    parser.add_argument("--base-url", default="http://services.azymut.pl/oferta/servlet/", help="Base URL for the service")
    parser.add_argument("--total-records", type=int, default=164000, help="Total expected records to download (guide only)")
    parser.add_argument("--batch-size", type=int, default=500, help="Number of records per batch (default: 500)")

    args = parser.parse_args()
    get_books(client_id=args.client_id,
              password=args.password,
              base_url=args.base_url,
              total_records=args.total_records,
              batch_size=args.batch_size)

if __name__ == "__main__":
    main()
