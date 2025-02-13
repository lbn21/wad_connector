# WBD Connector & XML-to-CSV Converter

## Requirements:

 - Python 3.6+
 - Packages: requests, colorama (These are listed in the provided requirements.txt file.)

## Installation:

1. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage:

1. **Download XML Data**:
   
   Run `wbd_connector.py` to download batches of XML data.
   
   Example:
   ```bash
   python3 wbd_connector.py --client-id YOUR_CLIENT_ID --password YOUR_PASSWORD
   ```

   Optional parameters:
   - `--base-url`: Base URL of the service (default: http://services.azymut.pl/oferta/servlet/)
   - `--total-records`: Total expected records (default: 164000)
   - `--batch-size`: Number of records per batch (default: 500)
   
   The XML files will be saved in the "batches" directory.

2. **Convert XML to CSV**:

   Run `xml_to_csv.py` to convert the XML files to CSV.

   Example:
   ```bash
   python3 python xml_to_csv.py
   ```

   Optional parameters:
    - `--batches-dir`: Directory containing XML files (default: batches)
    - `--output-dir`: Directory to store CSV files (default: csv)

   The CSV files will be saved in the "csv" directory.

## Notes:
 - `wbd_connector.py` waits 60 seconds between batches and checks for duplicate downloads.
 - `xml_to_csv.py` removes the "atrybuty" property from book records.
 - Run the scripts in the order above.
