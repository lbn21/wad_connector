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

def process_xml_file(xml_file, output_dir):
    """
    Processes a single XML file:
    - Extracts all <book> elements.
    - Drops the 'atrybuty' property if present.
    - Writes the books to a CSV file in output_dir using the same base filename.
    - Returns the number of books converted (or None on error).
    """
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        books = root.findall(".//book")
        if not books:
            logging.info(f"{Fore.YELLOW}No <book> elements found in {xml_file}, skipping.{Style.RESET_ALL}")
            return 0
        book_dicts = []
        for book_elem in books:
            book_dict = element_to_dict(book_elem)
            if isinstance(book_dict, dict) and "atrybuty" in book_dict:
                del book_dict["atrybuty"]
            book_dicts.append(book_dict)

        # Determine the union of keys across all book dictionaries for CSV columns
        keys = set()
        for book in book_dicts:
            if isinstance(book, dict):
                keys.update(book.keys())
        keys = sorted(keys)

        # Prepare the output CSV file path using the same base filename as the XML file
        base_name = os.path.basename(xml_file)
        name_without_ext = os.path.splitext(base_name)[0]
        csv_file = os.path.join(output_dir, f"{name_without_ext}.csv")

        with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=keys, extrasaction='ignore')
            writer.writeheader()
            for book in book_dicts:
                row = {key: flatten_value(book.get(key, "")) for key in keys}
                writer.writerow(row)
        return len(book_dicts)
    except Exception as e:
        logging.error(f"{Fore.RED}Error processing {xml_file}: {e}{Style.RESET_ALL}")
        return None

def main():
    parser = argparse.ArgumentParser(
        description="Convert each XML file in the batches directory into its own CSV file."
    )
    parser.add_argument("--batches-dir", default="batches", help="Directory containing XML batch files (default: batches)")
    parser.add_argument("--output-dir", default="csv", help="Directory to store CSV files (default: csv)")
    args = parser.parse_args()

    # Ensure output directory exists
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # Get a sorted list of XML files from the batches directory
    xml_files = sorted(glob.glob(os.path.join(args.batches_dir, "*.xml")))
    total_files = len(xml_files)
    logging.info(f"{Fore.CYAN}=== Starting CSV Conversion for {total_files} XML file(s) ==={Style.RESET_ALL}")

    converted_count = 0
    for i, xml_file in enumerate(xml_files, 1):
        num_books = process_xml_file(xml_file, args.output_dir)
        if num_books is not None:
            converted_count += 1
            logging.info(f"{Fore.GREEN}Converted {i}/{total_files}: {os.path.basename(xml_file)} -> {num_books} book(s) converted.{Style.RESET_ALL}")
        else:
            logging.error(f"{Fore.RED}Conversion failed for {os.path.basename(xml_file)}.{Style.RESET_ALL}")

    logging.info(f"{Fore.CYAN}=== CSV Conversion complete: {converted_count} out of {total_files} file(s) processed. ==={Style.RESET_ALL}")

if __name__ == "__main__":
    main()
