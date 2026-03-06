# Phone Search Application

Streamlit application for searching phone numbers by contract number from Oracle database.

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create secrets file:
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

3. Edit `.streamlit/secrets.toml` with your database credentials

4. Run the app:
```bash
streamlit run app.py
```

## Deploy to Streamlit Cloud

1. Push code to GitHub repository

2. Go to [share.streamlit.io](https://share.streamlit.io)

3. Connect your GitHub account

4. Select your repository and branch

5. Set the main file path to: `app.py`

6. Add secrets in Streamlit Cloud dashboard:
   - Go to app settings
   - Click "Secrets" in the left menu
   - Add your database credentials in TOML format:
   ```toml
   [database]
   login = "your_login"
   host = "your_host"
   port = 1521
   password = "your_password"
   service = "your_service"
   ```

7. Deploy!

## Features

- Search phone contacts by contract number
- Display contact information with relationships
- Remove duplicate entries
- Export results to Excel
- Clean and responsive interface
