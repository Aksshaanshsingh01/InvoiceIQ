# InvoiceIQ

InvoiceIQ is an invoice-processing and analytics application. It extracts information from invoice PDFs, validates the extracted data, stores invoice records in Firestore, and presents invoice and financial insights through a NiceGUI web interface.

## Features

- PDF text extraction with PyMuPDF
- Invoice parsing for parties, line items, taxes, totals, and round-off
- Validation of extracted data and financial consistency
- Batch processing of invoice PDFs
- Firestore persistence
- Financial, invoice, tax, party, and dashboard analytics
- Invoice search and detail views
- Invoice upload through the web interface
- Payment tracking and payment-history interface
- Excel export

## Tech Stack

Python · FastAPI · NiceGUI · PyMuPDF · Firebase Admin SDK · Google Cloud Firestore · Pandas · Pytest

## Project Structure

```text
InvoiceIQ/
├── analytics/       # Financial and invoice analytics
├── api/             # FastAPI application
├── database/        # Firestore connection and query layer
├── extraction/      # PDF extraction, parsing, validation, batch processing
├── export/          # Excel export
├── frontend/        # NiceGUI app and API client
├── tests/           # Automated tests
├── samples/         # Sample PDFs; avoid confidential documents
├── uploads/         # Runtime uploads; keep out of version control
├── output/          # Generated files; keep out of version control
├── requirements.txt
└── requirements-dev.txt
```

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/Aksshaanshsingh01/InvoiceIQ.git
cd InvoiceIQ
```

### 2. Create and activate a virtual environment

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

Create a `.env` file based on `.env.example` and configure the Firebase settings required by the project. Set up Firestore and provide credentials securely to the local runtime.

**Never commit `.env`, Firebase service-account JSON files, private keys, or real customer invoices.** For hosted deployments, configure secrets through the hosting provider.

Use the exact environment-variable names and credential setup documented in `.env.example` and the database initialization code.

### 5. Start the API

From the repository root:

```bash
python -m uvicorn api.main:app --reload
```

### 6. Start the frontend

Open a second terminal from the repository root:

```bash
python -m frontend.app
```

Open the local URL printed by the frontend. Ensure the frontend API base URL is configured to reach the running API.

## Run Tests

```bash
pytest
```

## Deployment Checklist

Before sharing a public demo:

1. Configure the deployed frontend to use the correct API URL.
2. Configure required environment variables and Firestore credentials.
3. Verify Firestore connectivity from the hosted service.
4. Test upload, invoice retrieval, deletion, and payment recording.
5. Verify payment history persists after reload and redeployment.
6. Avoid using confidential invoices in a public demo unless appropriate access controls are in place.

## Security and Data

- Keep credentials and private keys out of Git.
- Do not commit real invoices or customer data.
- Treat invoice and payment information as sensitive business data.
- Review access controls before exposing the application publicly.

## Project Status

InvoiceIQ is under active development. Features and deployment configuration may evolve.
