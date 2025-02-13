# WBDConnector
This is a sample Python application to download book data from the Azymut API (WBDConnector) in batches. Each batch is assumed to contain 500 records.
## Features
The script implements the following improvements:
* **60-second delay:** The script waits at least 60 seconds between requests to respect API rate limits and prevent overloading the server
* **Duplicate batch detection:** Instead of using the transaction ID, the script compares the "indeks" (index) of the first book in each batch. If the first record's index matches that of the last saved batch, it is considered a duplicate and is not saved again
* **Batch file saving:** Each batch is saved as its own XML file in the `batches` folder for better organization and error recovery
* **Resume capability:** If the script is interrupted, it can be restarted and will check the existing batch files to avoid re-processing a batch

## Requirements
* Python 3.6 or newer
* The `requests` library

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your_username/wbd_connector.git
   ```
2. Change to the repository directory:
   ```bash
   cd wbd_connector
   ```
3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```
## Usage
Run the script from the command line with the required arguments:
   ```bash
   python3 wbd_connector.py --client-id YOUR_CLIENT_ID --password YOUR_PASSWORD
   ```
Optional arguments include:
- `--base-url`
- `--total-records`
- `--batch-size`
## Notes
* The script enforces a 60-second wait between requests
* Duplicate batch detection is based on comparing the first book's index from the current batch with that of the last saved batch
* The resume mechanism is based on the batch files saved in the `batches` folder

## Python Compatibility
This script is written for Python 3.6 and newer.
