# WBDConnector

This is a sample Python application to download book data from the Azymut API (WBDConnector) in batches.
Each batch is assumed to contain 500 records. The script implements the following improvements:

- **60‑second delay:** The script waits at least 60 seconds between requests.
- **Duplicate batch detection:** Instead of using the transaction ID, the script now compares the "indeks" (index) of the first book in each batch. If the first record’s index matches the last saved batch, it is considered a duplicate and is not saved again.
- **Batch file saving:** Each batch is saved as its own XML file in the `batches` folder.
- **Resume capability:** If the script is interrupted, it can be restarted and will check the existing batch files to avoid re‑processing a batch.

## Requirements

- Python 3.6 or newer
- The `requests` library

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/your_username/wbd_connector.git
