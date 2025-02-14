#!/usr/bin/env python3
import os
import glob
import csv
import json
import xml.etree.ElementTree as ET
import argparse
import logging
from colorama import Fore, Style, init

# Initialize colorama (with auto-reset)
init(autoreset=True)

# Configure logging for output messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def element_to_dict(elem):
    """
    Recursively converts an XML element and its children into a dictionary.
    Attributes are merged into the dictionary.
    If an element has no children, its text content is used.
    """
    d = {}
    d.update(elem.attrib)
    for child in elem:
        child_dict = element_to_dict(child)
        tag = child.tag
        if tag in d:
            if isinstance(d[tag], list):
                d[tag].append(child_dict)
            else:
                d[tag] = [d[tag], child_dict]
        else:
            d[tag] = child_dict
    if not list(elem):
        text = elem.text.strip() if elem.text else ""
        if text:
            if d:
                d["text"] = text
            else:
                return text
    return d

def flatten_value(val):
    """
    Converts the value to a string. If the value is a dictionary or list,
    returns a JSON-formatted string.
    """
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    return str(val)

def validate_csv(csv_file, expected_columns=None, expected_rows=None):
    """
    Validates the CSV file by checking headers and row count.
    Returns True if validation succeeds, False otherwise.
    """
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            if expected_columns and set(headers) != set(expected_columns):
                return False
            row_count = sum(1 for _ in reader)
            if expected_rows is not None and row_count != expected_rows:
                return False
            return True
    except Exception:
        return False

def process_xml_file(xml_file, output_dir):
    """
    Processes a single XML file:
      - Parses the XML to extract <book> elements and determine expected CSV structure.
      - Determines the expected CSV filename.
      - If that CSV exists, it is validated:
          * If valid, the file is skipped.
          * If invalid, a message is logged and the file is reprocessed (overwritten).
      - If no CSV exists (or the existing one failed validation), converts the XML to CSV.
      - Runs CSV validation on the newly created CSV.
    Returns a tuple:
      (num_books, validation_success, filename, already_processed)
      where 'already_processed' is True if the CSV already existed and was valid.
    """
    base_name = os.path.basename(xml_file)
    name_without_ext = os.path.splitext(base_name)[0]
    csv_file = os.path.join(output_dir, f"{name_without_ext}.csv")
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        books = root.findall(".//book")
        if not books:
            logging.info(f"{Fore.YELLOW}[{base_name}] No <book> elements found, skipping.")
            return 0, True, base_name, False  # Nothing to convert, but considered valid.
        book_dicts = []
        for book_elem in books:
            book_dict = element_to_dict(book_elem)
            if isinstance(book_dict, dict) and "atrybuty" in book_dict:
                del book_dict["atrybuty"]
            book_dicts.append(book_dict)

        # Determine the union of keys (expected CSV headers)
        keys = set()
        for book in book_dicts:
            if isinstance(book, dict):
                keys.update(book.keys())
        keys = sorted(keys)
        num_books = len(book_dicts)

        # Check if CSV already exists.
        if os.path.exists(csv_file):
            valid = validate_csv(csv_file, expected_columns=keys, expected_rows=num_books)
            if valid:
                # CSV is already processed and valid.
                return num_books, True, base_name, True
            else:
                logging.error(f"{Fore.RED}[{base_name}] Existing CSV failed validation; reprocessing file...{Style.RESET_ALL}")

        # (Re)generate the CSV file (overwrites if exists)
        with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=keys, extrasaction='ignore')
            writer.writeheader()
            for book in book_dicts:
                row = {key: flatten_value(book.get(key, "")) for key in keys}
                writer.writerow(row)

        valid = validate_csv(csv_file, expected_columns=keys, expected_rows=num_books)
        return num_books, valid, base_name, False

    except Exception as e:
        logging.error(f"{Fore.RED}[{base_name}] Error processing file: {e}{Style.RESET_ALL}")
        return None, False, base_name, False

def main():
    parser = argparse.ArgumentParser(
        description="Convert XML files in the batches directory into CSV files (with validation)."
    )
    parser.add_argument("--batches-dir", default="batches", help="Directory containing XML batch files (default: batches)")
    parser.add_argument("--output-dir", default="csv", help="Directory to store CSV files (default: csv)")
    args = parser.parse_args()

    # Ensure output directory exists.
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # Get sorted list of XML files from batches directory.
    xml_files = sorted(glob.glob(os.path.join(args.batches_dir, "*.xml")))
    total_files = len(xml_files)
    logging.info(f"{Fore.CYAN}=== Starting CSV Conversion for {total_files} XML file(s) ==={Style.RESET_ALL}\n")

    for i, xml_file in enumerate(xml_files, 1):
        num_books, valid, fname, already = process_xml_file(xml_file, args.output_dir)
        if num_books is not None:
            if already:
                logging.info(f"{Fore.GREEN}Already Processed {i}/{total_files}: {fname} -> {num_books} book(s) (CSV validated).{Style.RESET_ALL}")
            else:
                logging.info(f"{Fore.GREEN}Converted {i}/{total_files}: {fname} -> {num_books} book(s) converted.{Style.RESET_ALL}")
            if valid:
                logging.info(f"{Fore.BLUE}    ↳ CSV Validation succeeded: {num_books} row(s) in CSV.{Style.RESET_ALL}\n")
            else:
                logging.error(f"{Fore.RED}    ↳ ⚠ CSV Validation FAILED: expected {num_books} row(s).{Style.RESET_ALL}\n")
        else:
            logging.error(f"{Fore.RED}Converted {i}/{total_files}: {fname} conversion/validation FAILED.{Style.RESET_ALL}\n")

    logging.info(f"{Fore.CYAN}=== CSV Conversion complete: Processed {total_files} file(s). ==={Style.RESET_ALL}")

if __name__ == "__main__":
    main()
