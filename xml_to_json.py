#!/usr/bin/env python3
import os
import glob
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
    If an element has no children, its text content is returned (or merged as 'text' if other keys exist).
    """
    d = {}
    # Merge element attributes
    d.update(elem.attrib)
    # Process child elements recursively
    for child in elem:
        child_dict = element_to_dict(child)
        tag = child.tag
        # If multiple children with the same tag, group them in a list
        if tag in d:
            if isinstance(d[tag], list):
                d[tag].append(child_dict)
            else:
                d[tag] = [d[tag], child_dict]
        else:
            d[tag] = child_dict
    # If no child elements, use the text content (if any)
    if not list(elem):
        text = elem.text.strip() if elem.text else ""
        if text:
            if d:
                d["text"] = text
            else:
                return text
    return d

def extract_batch_num(filename):
    """Extracts the batch number from a filename assuming the format 'batch_XXXX_...xml'."""
    base = os.path.basename(filename)
    parts = base.split('_')
    try:
        return int(parts[1])
    except Exception:
        return 0

def convert_batches_to_json(batches_dir, output_file):
    """
    Reads all XML files from batches_dir (sorted by batch number), extracts <book> elements,
    converts them to dictionaries, and writes a single JSON file.
    """
    books = []
    # Sort XML files based on batch number to preserve order
    xml_files = sorted(glob.glob(os.path.join(batches_dir, "*.xml")), key=extract_batch_num)
    logging.info(f"Found {len(xml_files)} XML file(s) in '{batches_dir}'")

    for xml_file in xml_files:
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            # Find all <book> elements in document order
            file_books = root.findall(".//book")
            logging.info(f"{xml_file}: found {len(file_books)} book(s)")
            for book_elem in file_books:
                book_dict = element_to_dict(book_elem)
                books.append(book_dict)
        except Exception as e:
            logging.error(f"Error processing {xml_file}: {e}")

    # Create the final JSON structure
    data = {"books": books}
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logging.info(f"Converted {len(books)} book(s) into JSON file '{output_file}'")

def main():
    parser = argparse.ArgumentParser(
        description="Convert XML batch files from the 'batches' folder into a single JSON file."
    )
    parser.add_argument("--batches-dir", default="batches", help="Directory containing XML batch files (default: batches)")
    parser.add_argument("--output-file", default="batches/__books.json", help="Output JSON file (default: books.json)")
    args = parser.parse_args()
    convert_batches_to_json(args.batches_dir, args.output_file)

if __name__ == "__main__":
    main()
