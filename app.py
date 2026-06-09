import re
import time
from pathlib import Path
from urllib.parse import urlparse, quote_plus
from difflib import SequenceMatcher
import pandas as pd
import streamlit as st
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title='Competitor Promo Agent', layout='wide')

OFFICIAL_SOURCES = {
    'Whites': 'https://www.whites.sa/ar-sa',
    'Nahdi': 'https://www.nahdionline.com/en-sa',
    'Al-Dawaa': 'https://www.al-dawaa.com/en/',
    'Nice One': 'https://niceonesa.com/en',
    'Ninja': 'https://ananinja.com/sa/ar',
}

SEARCH_PATTERNS = {
    'Nahdi': 'https://www.nahdionline.com/en-sa/search?q={q}',
    'Al-Dawaa': 'https://www.al-dawaa.com/en/search?text={q}',
    'Nice One': 'https://niceonesa.com/en/search?q={q}',
    'Ninja': 'https://ananinja.com/sa/ar/product/search?q={q}',
}

USER_AGENT = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
}

SCREEN_DIR = Path('assets/screenshots')
SCREEN_DIR.mkdir(parents=True, exist_ok=True)


def fetch_html(url, timeout=25):
    try:
        r = requests.get(url, headers=USER_AGENT, timeout=timeout)
        r.raise_for_status()
        return r.text, None
    except Exception as e:
        return None, str(e)


def clean_text(x):
    if not x:
        return ''
    return re.sub(r'\s+', ' ', x).strip()


def get_meta(soup, *keys):
    for key in keys:
        tag = soup.find('meta', attrs={'property': key}) or soup.find('meta', attrs={'name': key})
        if tag and tag.get('content'):
            return clean_text(tag['content'])
    return ''


def detect_retailer(url):
    host = urlparse(url).netloc.lower()
    if 'whites' in host:
        return 'Whites'
    if 'nahdi' in host:
        return 'Nahdi'
    if 'al-dawaa' in host or 'aldawaa' in host:
        return 'Al-Dawaa'
    if 'niceone' in host:
        return 'Nice One'
    if 'ninja' in host or 'ananinja' in host:
        return 'Ninja'
    return host


def normalize_text(s):
    s = (s or '').lower()
    s = re.sub(r'[^\w\s]', ' ', s)
    return clean_text(s)


def similarity(a, b):
    return round(SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio(), 2)


def extract_prices(text):
    prices = []
    for m in re.finditer(r'(?<!\d)(\d{1,4}(?:[\.,]\d{1,2})?)(?!\d)', text or ''):
        try:
            prices.append(float(m.group(1).replace(',', '')))
        except:
            pass
    uniq = []
    for p in prices:
        if p not in uniq:
            uniq.append(p)
    return uniq[:12]


def extract_discount(text):
    m = re.search(r'(\d{1,2})\s*%\s*(?:off|خصم)', text or '', re.I)
    return int(m.group(1)) if m else None


def extract_candidate_links(html, base_domain):
    soup = BeautifulSoup(html, 'html.parser')
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        txt = clean_text(a.get_text(' ', strip=True))
        if href.startswith('/'):
            href = base_domain.rstrip('/') + href
        if href.startswith('http'):
            links.append((href, txt))
    out, seen = [], set()
    for href, txt in links:
        if href not in seen:
            seen.add(href)
            out.append((href, txt))
    return out


def parse_product_page(url):
    html, err = fetch_html(url)
    retailer = detect_retailer(url)
    if err:
        return {'retailer': retailer, 'url': url, 'status': 'Fetch failed', 'error': err, 'title': '', 'image': '', 'price_current': None, 'price_old': None, 'discount_pct': None, 'availability': 'Unknown', 'mechanic': '', 'description': '', 'screenshot_path': ''}

    soup = BeautifulSoup(html, 'html.parser')
    title = get_meta(soup, 'og:title', 'twitter:title') or clean_text(soup.title.text if soup.title else '')
    description = get_meta(soup, 'og:description', 'description', 'twitter:description')
    image = get_meta(soup, 'og:image', 'twitter:image')
    body_text = clean_text(soup.get_text(' ', strip=True))
    prices = extract_prices(body_text)
    discount = extract_discount(body_text)

    price_current, price_old = None, None
    if len(prices) >= 2:
        vals = sorted(prices[:8])
        price_current, price_old = vals[0], vals[1]
    elif len(prices) == 1:
        price_current = prices[0]

    availability = 'Unknown'
    low = body_text.lower()
    if any(x in low for x in ['out of stock', 'not available', 'غير متوفر', 'نفذت الكمية']):
        availability = 'Out of stock'
    elif any(x in low for x in ['add to cart', 'add to bag', 'أضف إلى السلة', 'buy now', 'اشتري الآن']):
        availability = 'Available'

    mechanic = ''
    if discount:
        mechanic = f'{discount}% off'
    elif 'second' in low or 'piece' in low or 'قطعة' in low:
        mechanic = 'Multi-buy / second-piece offer'

    return {'retailer': retailer, 'url': url, 'status': 'Parsed', 'error': '', 'title': title, 'image': image, 'price_current': price_current, 'price_old': price_old, 'discount_pct': discount, 'availability': availability, 'mechanic': mechanic, 'description': description, 'screenshot_path': ''}


def derive_search_query(title, url=''):
    t = normalize_text(title)
    tokens = [x for x in t.split() if x not in {'shop', 'online', 'saudi', 'arabia', 'whites'}]
    return ' '.join(tokens[:8]) or normalize_text(url)


def auto_search_official(retailer, query):
    search_url = SEARCH_PATTERNS[retailer].format(q=quote_plus(query))
    html, err = fetch_html(search_url)
    if err or not html:
        return {'retailer': retailer, 'search_url': search_url, 'matched_url': '', 'matched_text': '', 'score': 0, 'status': f'Search failed: {err}'}

    base_domain = OFFICIAL_SOURCES[retailer]
    candidates = extract_candidate_links(html, base_domain)
    best = {'href': '', 'txt': '', 'score': 0}
    for href, txt in candidates:
        s = similarity(query, txt + ' ' + href)
        if s > best['score']:
            best = {'href': href, 'txt': txt, 'score': s}
    return {'retailer': retailer, 'search_url': search_url, 'matched_url': best['href'], 'matched_text': best['txt'], 'score': best['score'], 'status': 'Candidate found' if best['href'] else 'No strong candidate'}


def slugify(text):
    text = normalize_text(text)
    text = re.sub(r'\s+', '-', text)
    return text[:60] or 'capture'


def capture_screenshot(url, retailer):
    outfile = SCREEN_DIR / f"{retailer.lower().replace(' ', '_')}_{slugify(url)}.png"
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 2200}, locale='en-US')
            page.goto(url, wait_until='networkidle', timeout=45000)
            page.screenshot(path=str(outfile), full_page=True)
            browser.close()
        return str(outfile), ''
    except Exception as e:
        return '', str(e)


def recommendation(base_row, comp_rows):
    base_price = base_row.get('price_current')
    if not base_price:
        return 'Whites price parsing is uncertain. Use screenshots and OCR verification before taking pricing action.'
    cheaper = [r for r in comp_rows if r.get('price_current') and r['price_current'] < base_price]
    if cheaper:
        best = min(cheaper, key=lambda x: x['price_current'])
        gap = round(base_price - best['price_current'], 2)
        return f"{best['retailer']} appears cheaper by {gap} SAR. Action: evaluate targeted response, not broad markdown."
    return 'Whites appears competitive on parsed unit price. Action: keep monitoring competitor mechanics and verify screenshots.'


def render_card(row, base_title=''):
    with st.container(border=True):
        st.subheader(row['retailer'])
        if row.get('screenshot_path'):
            st.image(row['screenshot_path'], use_container_width=True)
        elif row.get('image'):
            st.image(row['image'], use_container_width=True)
        else:
            st.caption('No image/screenshot available yet')
        st.write(row.get('title') or 'No parsed title')
        c1, c2 = st.columns(2)
        c1.metric('Current', f"{row['price_current']:.2f} SAR" if row.get('price_current') else '—')
        c2.metric('Old', f"{row['price_old']:.2f} SAR" if row.get('price_old') else '—')
        st.caption(f"Availability: {row.get('availability', 'Unknown')}")
        st.caption(f"Mechanic: {row.get('mechanic') or '-'}")
        if base_title:
            st.caption(f"Match confidence: {similarity(base_title, row.get('title', ''))}")
        st.link_button('Open source', row['url'])
        if row.get('error'):
            st.warning(row['error'])


st.title('Competitive Promo Agent — Streamlit v3')
st.write('This version adds official-site auto-search plus real screenshot capture hooks using Playwright when enabled.')

with st.sidebar:
    st.header('Controls')
    auto_mode = st.checkbox('Auto-search competitors from official sites', value=True)
    enable_screens = st.checkbox('Capture screenshots with Playwright', value=False)
    manual_urls = st.checkbox('Override with manual competitor URLs', value=False)
    st.divider()
    st.caption('If Playwright is not installed in your environment, screenshot capture will fail gracefully and still keep the parsed comparison.')

base_product = st.text_input('Whites product URL', value='https://www.whites.sa/ar-sa/sensibio-make-up-removing-micellar-solution-500ml/')
manual = {}
if manual_urls:
    col1, col2 = st.columns(2)
    with col1:
        manual['Nahdi'] = st.text_input('Nahdi URL', '')
        manual['Al-Dawaa'] = st.text_input('Al-Dawaa URL', '')
    with col2:
        manual['Nice One'] = st.text_input('Nice One URL', '')
        manual['Ninja'] = st.text_input('Ninja URL', '')

run = st.button('Run comparison', type='primary', use_container_width=True)

if run:
    t0 = time.time()
    base = parse_product_page(base_product)
    base_title = base.get('title') or ''
    query = derive_search_query(base_title, base_product)

    if enable_screens:
        p, err = capture_screenshot(base_product, 'Whites')
        base['screenshot_path'] = p
        if err:
            base['error'] = (base.get('error','') + ' | Screenshot: ' + err).strip(' |')

    rows = [base]
    search_rows = []

    for retailer in ['Nahdi', 'Al-Dawaa', 'Nice One', 'Ninja']:
        if manual_urls and manual.get(retailer):
            row = parse_product_page(manual[retailer])
            row['retailer'] = retailer
            row['status'] = 'Manual URL parsed'
            if enable_screens:
                p, err = capture_screenshot(manual[retailer], retailer)
                row['screenshot_path'] = p
                if err:
                    row['error'] = (row.get('error','') + ' | Screenshot: ' + err).strip(' |')
            rows.append(row)
            search_rows.append({'retailer': retailer, 'search_url': manual[retailer], 'matched_url': manual[retailer], 'matched_text': row.get('title',''), 'score': similarity(base_title, row.get('title','')), 'status': 'Manual override'})
        elif auto_mode:
            s = auto_search_official(retailer, query)
            search_rows.append(s)
            if s['matched_url']:
                row = parse_product_page(s['matched_url'])
                row['retailer'] = retailer
                row['status'] = f"Auto-searched ({s['score']})"
                if enable_screens:
                    p, err = capture_screenshot(s['matched_url'], retailer)
                    row['screenshot_path'] = p
                    if err:
                        row['error'] = (row.get('error','') + ' | Screenshot: ' + err).strip(' |')
                rows.append(row)
            else:
                rows.append({'retailer': retailer, 'url': OFFICIAL_SOURCES[retailer], 'status': s['status'], 'error': '', 'title': '', 'image': '', 'price_current': None, 'price_old': None, 'discount_pct': None, 'availability': 'Pending manual review', 'mechanic': '', 'description': '', 'screenshot_path': ''})
        else:
            rows.append({'retailer': retailer, 'url': OFFICIAL_SOURCES[retailer], 'status': 'Skipped', 'error': '', 'title': '', 'image': '', 'price_current': None, 'price_old': None, 'discount_pct': None, 'availability': 'Not searched', 'mechanic': '', 'description': '', 'screenshot_path': ''})

    st.markdown('## Search status')
    search_df = pd.DataFrame(search_rows)
    if not search_df.empty:
        st.dataframe(search_df, use_container_width=True)

    st.markdown('## Comparison table')
    df = pd.DataFrame(rows)
    st.dataframe(df[['retailer','status','title','price_current','price_old','discount_pct','availability','mechanic','url','screenshot_path']], use_container_width=True)

    st.markdown('## Visual comparison')
    cols = st.columns(len(rows))
    for i, row in enumerate(rows):
        with cols[i]:
            render_card(row, base_title)

    st.markdown('## Recommendation')
    st.info(recommendation(base, [r for r in rows if r['retailer'] != 'Whites']))

    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button('Download comparison CSV', csv, 'comparison_output_v3.csv', 'text/csv', use_container_width=True)
    st.caption(f"Run time: {round(time.time()-t0,2)} sec")
