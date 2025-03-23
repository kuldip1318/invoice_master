### Project Description for Invoice Master

**Invoice Master** is an accounting application designed to streamline the process of handling hospital invoices. Users can upload an invoice, which is then processed using Azure OCR (Optical Character Recognition) to extract the relevant data. Once the OCR data is produced, OpenAI prompts are used to convert it into structured JSON data. The extracted data is then displayed in a table format on the frontend for easy review and modification. Users can either save the data as a CSV or Excel file, or push it directly to the database.

---

### README for Invoice Master

```markdown
# Invoice Master

## Description

**Invoice Master** is an accounting application that simplifies processing hospital invoices. It leverages **Azure OCR** to extract data from uploaded invoices, then utilizes **OpenAI prompts** to convert the OCR results into structured JSON. The extracted data is displayed in a table format, where users can modify it before saving it as CSV/Excel or pushing it to a database.

## Features

- Upload hospital invoices for processing.
- Azure OCR extracts the relevant invoice data.
- OpenAI processes the OCR results and converts them into structured JSON.
- Display extracted data in a table format on the frontend.
- Modify the table data as needed.
- Save the modified data as CSV or Excel.
- Push the data to the database for further processing.

## How to Start

### 1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/invoice-master.git
   ```

### 2. Install Dependencies
   - Navigate to the project directory and install dependencies:
     ```bash
     npm install
     ```

### 3. Set Up Azure OCR
   - Make sure you have a valid **Azure OCR** API key and endpoint. Configure it in your project settings or environment variables.

### 4. Start the Application
   - Run the application:
     ```bash
     npm start
     ```

### 5. Access the Web Interface
   - Open your browser and go to:
     ```bash
     http://localhost:9000
     ```

### 6. Upload Invoice
   - Use the interface to upload hospital invoices (PDF, image,.zip formats).
   
### 7. Modify Data
   - The extracted data will appear in a table format. You can review, modify, or adjust the data as needed.

### 8. Save or Push Data
   - After modification, you can:
     - Save the data as a CSV or Excel file.
     - Push the data directly to the connected database.

## Technologies Used

- **Frontend**: (e.g., React, Nextjs)
- **Backend**: (e.g., Node.js, PythonScripts)
- **OCR**: Azure OCR API
- **AI Processing**: OpenAI API
- **Database**: (e.g., PostgresDB)
- **File Formats**: CSV, Excel

## Contribution

Feel free to fork this repository, report issues, or contribute improvements by creating pull requests. All contributions are welcome!

```

---

### Key Features and Steps Breakdown:

- **Azure OCR**: Extracts invoice details from images or PDFs.
- **OpenAI Integration**: Converts the extracted OCR data into a structured JSON format for easy parsing and display.
- **Frontend Display**: Displays the data in a user-friendly table format, where users can modify the information.
- **Export Options**: Users can save the modified data as CSV or Excel or push it directly to a database for further use.
