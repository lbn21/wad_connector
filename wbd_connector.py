#!/usr/bin/env python3
import os
import time
import glob
import requests
import xml.etree.ElementTree as ET
import argparse
import logging

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

def get_books(client_id, password, base_url, total_records, batch_size):
    getdb_url = f"{base_url}/getdb"
    confirm_url = f"{base_url}/confirm"

    # Retrieve info from any previous run
    _, last_first_index = get_last_batch_info()
    batch_num = get_next_batch_number()
    records_downloaded = (batch_num - 1) * batch_size
    logging.info(f"Resuming download. Approximately {records_downloaded} records already saved.")

    while records_downloaded < total_records:
        logging.info("Waiting 60 seconds before next request...")
        time.sleep(60)

        logging.info("Requesting a new batch from getdb...")
        response = requests.get(getdb_url, params={'id': client_id, 'p': password})
        if response.status_code != 200:
            logging.error(f"Error fetching data: {response.status_code}")
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

        # Use the first book's index to detect duplicates
        current_first_index = books[0].get("indeks")
        if last_first_index is not None and current_first_index == last_first_index:
            logging.info("Duplicate batch detected (first record index matches last saved batch).")
            # Reattempt confirmation in case it failed previously
            confirm_response = requests.get(confirm_url, params={'id': client_id, 'p': password, 'transactionId': root.get("transactionId")})
            if confirm_response.status_code == 200:
                logging.info("Confirmation succeeded on duplicate batch. Updating last batch file.")
                last_file, _ = get_last_batch_info()
                if last_file and "_confirmed" not in last_file:
                    update_confirmation(last_file)
                last_first_index = None  # Reset duplicate check marker
            else:
                logging.error(f"Confirmation failed on duplicate batch: {confirm_response.status_code}")
            continue  # Do not save duplicate batch

        # Save the new batch
        logging.info(f"Saving new batch {batch_num} with first record index {current_first_index}.")
        filename = save_batch(response.content, batch_num, current_first_index, confirmed=False)

        # Attempt to confirm the batch
        confirm_response = requests.get(confirm_url, params={'id': client_id, 'p': password, 'transactionId': root.get("transactionId")})
        if confirm_response.status_code == 200:
            logging.info("Batch confirmed successfully.")
            update_confirmation(filename)
            last_first_index = None  # Reset duplicate check marker
            records_downloaded += len(books)
            batch_num += 1
            logging.info(f"Total records processed (approx.): {records_downloaded}")
        else:
            logging.error(f"Batch confirmation failed (status: {confirm_response.status_code}). Will retry this batch next time.")
            last_first_index = current_first_index  # Mark this batch as unconfirmed to detect duplicate in next call

    logging.info("Download complete.")

def main():
    parser = argparse.ArgumentParser(
        description="Download books data from the Azymut API (WBDConnector) with delay, duplicate check, and resume capability."
    )
    parser.add_argument("--client-id", required=True, help="Client ID for authentication")
    parser.add_argument("--password", required=True, help="Password for authentication")
    parser.add_argument("--base-url", default="https://services.azymut.pl/oferta", help="Base URL for the service")
    parser.add_argument("--total-records", type=int, default=8000, help="Total expected records to download")
    parser.add_argument("--batch-size", type=int, default=500, help="Number of records per batch (default: 500)")

    args = parser.parse_args()
    get_books(client_id=args.client_id,
              password=args.password,
              base_url=args.base_url,
              total_records=args.total_records,
              batch_size=args.batch_size)

if __name__ == "__main__":
    main()
