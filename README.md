# Competitive Promo Agent - Streamlit v3

This version adds:
- Official-site auto-search
- Product image extraction
- Optional Playwright full-page screenshots
- CSV export
- Recommendation block

## Install
```bash
pip install -r requirements.txt
playwright install chromium
streamlit run app.py
```

## Notes
- Screenshot capture is optional from the sidebar.
- If Playwright is not installed, the app still runs and parsing still works.
- OCR is the next planned enhancement after screenshot capture.
