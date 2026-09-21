# InvoiceIQ

> Turn invoice PDFs into structured, validated financial data and actionable invoice insights.

**InvoiceIQ** is a PDF invoice-processing and analytics app for teams that handle supplier and customer invoices. It reduces manual data entry by extracting invoice details, checking financial consistency, storing records, and surfacing totals, outstanding balances, and payment activity in a dashboard.


## What it does

- Extracts invoice text from PDFs with PyMuPDF.
- Parses parties, invoice metadata, line items, taxes, totals, and round-off.
- Validates extracted values and financial consistency.
- Processes batches of invoice PDFs.
- Persists invoice records in Google Cloud Firestore.
- Displays financial, invoice, tax, party, and dashboard analytics.
- Supports invoice search, detail views, upload, and deletion.
- Tracks received and outstanding amounts, with a payment-history interface.
- Exports extracted data to Excel.

## Architecture

Invoice PDFs flow through extraction and parsing, validation, and Firestore persistence; the analytics/query layer then supplies data to the FastAPI service and NiceGUI interface.

```text
Invoice PDF
    → Extraction and parsing
    → Validation
    → Firestore
    → Analytics and query layer
    → FastAPI
    → NiceGUI dashboard and invoice UI
```

## Tech stack

- **Language:** Python
- **API:** FastAPI
- **UI:** NiceGUI
- **PDF processing:** PyMuPDF
- **Database:** Google Cloud Firestore / Firebase Admin SDK
- **Data and export:** Pandas, Excel tooling
- **Testing:** Pytest

## Quick Start

Run these from the repository root after installing dependencies and configuring Firebase:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --reload
```

In a **second terminal**:

```powershell
python -m frontend.app
```

Open the local frontend URL printed in the terminal. Make sure the frontend API base URL points to the API you started.

## Local Setup

### Requirements

- Python 3.x, with the exact minimum version determined by the project's dependencies and deployment runtime.
- A Firebase project with Cloud Firestore enabled.
- Firebase credentials available to the local runtime.

### 1. Clone the repository

```bash
git clone https://github.com/Aksshaanshsingh01/InvoiceIQ.git
cd InvoiceIQ
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

For development and tests:

```bash
python -m pip install -r requirements-dev.txt
```

### 4. Configure Firebase

Create a `.env` file based on `.env.example` and configure the Firebase settings required by the project. Enable Firestore and provide credentials securely to the local runtime.

Use the exact environment-variable names and credential setup documented in `.env.example` and the database initialization code.

**Never commit `.env`, Firebase service-account JSON files, private keys, or real customer invoices.** For hosted deployments, configure secrets through the hosting provider.

### 5. Start the application

See **Quick Start** above for the API and frontend commands.

## Run Tests

```bash
pytest
```

## Project Structure

```text
InvoiceIQ/
├── analytics/       # Financial, invoice, tax, party, and dashboard analytics
├── api/             # FastAPI application
├── database/        # Firestore connection and query layer
├── extraction/      # PDF extraction, parsing, validation, and batch processing
├── export/          # Excel export functionality
├── frontend/        # NiceGUI app and API client
├── tests/           # Automated tests
├── samples/         # Sample PDFs; do not add confidential documents
├── uploads/         # Runtime uploads; keep out of version control
├── output/          # Generated files; keep out of version control
├── requirements.txt
└── requirements-dev.txt
```

## Deployment

The app needs a reachable frontend and API, plus valid Firestore credentials.

Before sharing a deployed instance:

1. Set the frontend API base URL to the deployed API.
2. Configure required environment variables and Firestore credentials in the host.
3. Confirm the deployed service can access Firestore.
4. Test upload, retrieval, deletion, and payment recording.
5. Confirm payment history survives a page reload and a fresh deployment.
6. Avoid uploading confidential invoices to a public demo.

## Known verification item

Payment history is represented in the interface, but the complete save-and-reload flow should be verified against the deployed API and Firestore configuration before relying on it for business records.

## Results and evaluation

No extraction-accuracy or benchmark figure is published here because a documented evaluation result has not yet been added. Add a measured result only after testing against a labeled set of invoices, and state the dataset size and what counts as a correct extraction.

## License

No license has been specified yet. Until a license is added to the repository, others should not assume they have permission to reuse, modify, or redistribute this code. Add a `LICENSE` file if you intend to publish it under an open-source license.

## Project status

InvoiceIQ is under active development. Features and deployment configuration may evolve.
