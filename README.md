# App Analyzer API

This API provides functionality to analyze Android apps and find similar apps for business analysis.

## Requirements

- Python 3.11 (required for compatibility with all dependencies)
- pip3

## Setup

1. Create a virtual environment with Python 3.11:
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

3. Run the API:
```bash
python3 main.py
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### POST /analyze-app

Analyzes an Android app and finds similar apps.

**Request Body:**
```json
{
    "android_app_name": "string",
    "url": "string"
}
```

Example:
```json
{
    "android_app_name": "WhatsApp",
    "url": "https://play.google.com/store/apps/details?id=com.whatsapp"
}
```

**Response:**
The response includes detailed information about the target app and similar apps, including:
- App name
- Package name
- Developer information
- Ratings and reviews
- Download statistics
- Price
- Description
- Screenshots
- And more

**Example curl command for testing:**
```bash
curl -X POST "http://localhost:8000/analyze-app" -H "Content-Type: application/json" -d '{"android_app_name": "WhatsApp", "url": "https://play.google.com/store/apps/details?id=com.whatsapp"}'
```

## Error Handling

The API returns appropriate HTTP status codes:
- 200: Success
- 400: Invalid request (e.g., invalid URL format)
- 500: Server error

## Future Enhancement Plan

### Reading from Google Sheets and Using the API

1. **Google Sheets API Setup**:
   - Create a Google Cloud project and enable the Google Sheets API.
   - Download a service account JSON key and share your Google Sheet with the service account email.

2. **Install Required Packages**:
   Add the following to your `requirements.txt`:
   ```
   gspread==5.12.4
   oauth2client==4.1.3
   ```
   Then install:
   ```sh
   pip install gspread oauth2client
   ```

3. **Example Script**:
   Create a Python script to read from Google Sheets and call the API:
   ```python
   import gspread
   from oauth2client.service_account import ServiceAccountCredentials
   import requests

   # Google Sheets setup
   SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
   CREDS_FILE = 'path/to/your/service_account.json'  # <-- update this path
   SHEET_NAME = 'Sheet1'  # or whatever your sheet is called
   SPREADSHEET_ID = '1rdYtxxR04wXYFnDwI8ErVeI5Xp1HB-ScTldUYkuPZik'

   # API setup
   API_URL = 'http://localhost:8000/analyze-app'

   # Authenticate and open sheet
   creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
   client = gspread.authorize(creds)
   sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

   # Read all rows (skip header)
   rows = sheet.get_all_records()

   for row in rows:
       app_name = row['AppName']
       url = row['Url']
       payload = {
           "android_app_name": app_name,
           "url": url
       }
       response = requests.post(API_URL, json=payload)
       print(f"App: {app_name}, Status: {response.status_code}")
       print(response.json())
   ```

4. **Run the Script**:
   - Ensure your FastAPI server is running.
   - Run the script to process each row from the Google Sheet. 