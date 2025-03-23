
from flask import Flask, request, jsonify, session  # <-- Added session
from flask_cors import CORS
import base64
import os
import io
import zipfile
import logging
from dotenv import load_dotenv

# Existing imports...
from google.cloud import vision
from google.oauth2 import service_account
import openai
import json
import fitz  # PyMuPDF
from PIL import Image

# ----- NEW: Azure Document Intelligence Imports -----
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import ContentFormat
# ------------------------------------------------------

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure a secret key for sessions (use a secure key in production)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "FLASK_SECRET_KEY")

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize API clients using environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')

if not OPENAI_API_KEY or not GOOGLE_SERVICE_ACCOUNT_FILE:
    logger.error("Missing environment variables for API keys.")

# Set up OpenAI
openai.api_key = OPENAI_API_KEY

# Set up Google Vision
credentials = service_account.Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_FILE)
vision_client = vision.ImageAnnotatorClient(credentials=credentials)

# ----- NEW: Azure Client Initialization -----
AZURE_ENDPOINT = os.getenv('AZURE_ENDPOINT', 'https://parsing-invoice-dev.cognitiveservices.azure.com/')
AZURE_KEY = os.getenv('AZURE_KEY', 'CJHG53E3QsLxYIBw45xVNyX7NtCUKWkeYiZaKhSUN0RZIvScoCO9JQQJ99BBACYeBjFXJ3w3AAALACOGxoyQ')
document_intelligence_client = DocumentIntelligenceClient(
    endpoint=AZURE_ENDPOINT,
    credential=AzureKeyCredential(AZURE_KEY)
)
# ------------------------------------------------------

# ----- Define Two Invoice Prompts -----
INVENTORY_INVOICE_PROMPT = """
You are a specialized invoice parsing assistant for invoices with inventory. Your task is to extract all data from OCR text of invoices into a precise JSON format.
[You are a specialized medical invoice parsing assistant. Your task is to extract data from OCR text of medical supply invoices into a precise JSON format. Follow these exact rules:
Extract from the header:

1. Basic Document Information
2. Supplier Details (FROM Section)
3. Recipient Details (TO Section)
4. Product Table Extraction
5. Tax Breakdown Section
6. Total Values
7. Authentication Details


Validate with the these above json and line by line cheack with these Mathematical Validations and then give the all correct vlues if you are the stuck or low confidence then take "null"
Mathematical Validations:
1. Product Value = Quantity × Sale Rate
2. GST Value = Product Value × (GST% ÷ 100)
3. Net Value = Product Value + GST Value
4. Sum of all Net Values = Gross Total
5. Final Amount = Gross Total - Total Discount + Total Tax
6. SGST Amount + CGST Amount = GST Value
7.Grand Total or To Pay
]

"""

NON_INVENTORY_INVOICE_PROMPT = """
You are a specialized invoice parsing assistant for invoices without inventory. Your task is to extract all data from OCR text of invoices into a precise JSON format.
[You are a specialized medical invoice parsing assistant. Your task is to extract data from OCR text of medical supply invoices into a precise JSON format. Follow these exact rules:
Extract from the header:

1. Basic Document Information
    
2. Supplier Details (FROM Section)
        
3. Recipient Details (TO Section)
      
4. Tax Breakdown Section
        
5. Total Values
       
6. Authentication Details
          
Validate with the these above json and line by line cheack with these Mathematical Validations and then give the all correct vlues if you are the stuck or low confidence then take "null"
Mathematical Validations:
1. GST Value = Product Value × (GST% ÷ 100)
2. Net Value = Product Value + GST Value
3. Sum of all Net Values = Gross Total
4. Final Amount = Gross Total - Total Discount + Total Tax
5. SGST Amount + CGST Amount = GST Value
6.Grand Total or To Pay]
"""

# ----- Call OpenAI to Get JSON -----
def call_openai_for_json(azure_html, prompt):
    try:
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Extract the invoice data from this OCR text:\n\n{azure_html}\n\nReturn ONLY valid JSON."}
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.0
        )
        json_str = response.choices[0].message.content.strip()
        logger.info("Parsed JSON from OpenAI: %s", json_str)
        return json_str
    except Exception as e:
        logger.exception("Error calling OpenAI for JSON parsing.")
        return None

# ----- Process a Single File Using Azure Document Intelligence -----
def process_single_file_azure(file_content, filename, invoice_type):
    try:
        if filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
            base64_file = base64.b64encode(file_content).decode("utf-8")
            poller = document_intelligence_client.begin_analyze_document(
                "prebuilt-layout",
                {"base64Source": base64_file},
                output_content_format=ContentFormat.MARKDOWN,
            )
            result = poller.result()
            azure_html = result.content  # Azure's markdown/HTML output
            logger.debug("Azure HTML: " + azure_html)

            # Select the prompt based on invoice_type
            if invoice_type == "inventory":
                prompt = INVENTORY_INVOICE_PROMPT
            else:
                prompt = NON_INVENTORY_INVOICE_PROMPT

            # Call OpenAI with the chosen prompt to get structured JSON
            parsed_json = call_openai_for_json(azure_html, prompt)
            return azure_html, parsed_json
        else:
            logger.warning("Unsupported file type for Azure processing: " + filename)
            return None, None
    except Exception as e:
        logger.exception("Error processing file with Azure Document Intelligence")
        return None, None

# ----- Modified /process Endpoint -----
@app.route('/process', methods=['POST'])
def process_file():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['file']
        if not file.filename:
            return jsonify({"error": "No file selected"}), 400

        # Get invoice type from form data: "inventory" or "non_inventory"
        invoice_type = request.form.get('invoice_type', 'non_inventory')
        logger.info("Selected invoice type: %s", invoice_type)
        # Store the selected invoice type in the session for later use if needed
        session['invoice_type'] = invoice_type
        logger.info("Invoice type stored in session: %s", session.get('invoice_type'))

        file_content = file.read()
        
        # If a ZIP file is uploaded, process each supported file within it
        if file.filename.lower().endswith('.zip'):
            logger.info("Processing ZIP file")
            results = []
            zip_buffer = io.BytesIO(file_content)
            with zipfile.ZipFile(zip_buffer) as z:
                file_list = z.namelist()
                logger.info(f"Files in ZIP: {file_list}")
                for filename in file_list:
                    if (filename.endswith('/') or 
                        not any(filename.lower().endswith(ext) for ext in ['.pdf', '.jpg', '.jpeg', '.png'])):
                        continue
                    logger.info(f"Processing file from ZIP: {filename}")
                    try:
                        with z.open(filename) as f:
                            file_bytes = f.read()
                            azure_html, parsed_json = process_single_file_azure(file_bytes, filename, invoice_type)
                            if azure_html:
                                results.append({
                                    'filename': filename,
                                    'azure_html': azure_html,
                                    'parsed_json': parsed_json if parsed_json else ""
                                })
                            else:
                                logger.warning(f"Failed to process {filename} with Azure")
                    except Exception as e:
                        logger.error(f"Error processing {filename} from ZIP: {str(e)}")
                        continue
            if not results:
                return jsonify({"error": "No valid files processed in ZIP"}), 400
            return jsonify({
                "type": "zip",
                "results": results
            })
        
        # Process a single file (PDF or image)
        azure_html, parsed_json = process_single_file_azure(file_content, file.filename, invoice_type)
        if not azure_html:
            return jsonify({"error": "Failed to process file with Azure"}), 500

        return jsonify({
            "type": "single",
            "azure_html": azure_html,
            "parsed_json": parsed_json if parsed_json else ""
        })
    except zipfile.BadZipFile:
        logger.error("Invalid ZIP file")
        return jsonify({"error": "Invalid ZIP file"}), 400
    except Exception as e:
        logger.exception("Error processing request")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
