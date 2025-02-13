#!/usr/bin/env python3
import os
import glob
import csv
import json
import xml.etree.ElementTree as ET
import argparse
import logging

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
    """
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        books = root.findall(".//book")
        if not books:
            logging.info(f"No <book> elements found in {xml_file}, skipping.")
            return
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

        logging.info(f"Writing {len(book_dicts)} books from {xml_file} to {csv_file} with columns: {keys}")
        with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=keys, extrasaction='ignore')
            writer.writeheader()
            for book in book_dicts:
                row = {key: flatten_value(book.get(key, "")) for key in keys}
                writer.writerow(row)
    except Exception as e:
        logging.error(f"Error processing {xml_file}: {e}")

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
    logging.info(f"Found {len(xml_files)} XML file(s) in '{args.batches_dir}'")

    for xml_file in xml_files:
        process_xml_file(xml_file, args.output_dir)

    logging.info("CSV conversion complete.")

if __name__ == "__main__":
    main()
