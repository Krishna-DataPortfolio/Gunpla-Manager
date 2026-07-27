import re
import pandas as pd

DATE_REGEX = re.compile(r'\b(19|20)\d{2}\b|January|February|March|April|May|June|July|August|September|October|November|December', re.IGNORECASE)
EXCLUSIVE_KEYWORDS = {
    'Event': ['hobby show', 'expo', 'fes', 'fes(', "fes'", 'c3 x hobby', 'next future', 'side-f', 'runner\u2019s gate', "runner's gate", 'plamo fes'
              , 'chara hobby', 'gundam docks','plamodel radicon show', 'bandai museum', 'gundam world'],
    'Magazine': ['gundam ace', 'issue'],
    'Campaign': ['campaign', 'anniversary','theater'],
    'Lottery': ['ichiban kuji'],
    'Storefront': ['bandai hobby', 'gundam base', 'tmall', 'gundam front tokyo', 'gundam factory yokohama', 'amazon japan', '7-11'],
    'Placeholder': ['see below', 'n/a', 'tbd', 'unknown', '']
}

GRADE_PATTERN = [
    ("Perfect Grade", r"\bPG\b|Perfect Grade"),
    ("Master Grade", r"\bMG\b|Master Grade"),
    ("High Grade", r"\bHG\b|High Grade"),
    ("Real Grade", r"\bRG\b|Real Grade"),
    ("Entry Grade", r"\bEG\b|Entry Grade"),
    ("Super Deformed", r"\bSD\b|SD Gundam"),
    ("Master Grade SD", r"\bMGSD\b|Master Grade SD"),
    ("First Grade", r"\bFG\b|First Grade"),
    ("30 Minutes Missions", r"\b30MM\b|\b30FM\b|30 Minutes? (?:Fantasy )?Missions|30 Minutes? Fantasy(?: Model Series)?"),
    ("30 Minutes Sisters", r"\b30MS\b|30 Minutes? (?:Sisters )?Missions|30 Minutes? Sisters(?: Model Series)?"),
    ("30 Minutes Preference", r"\b30MP\b|30 Minutes Preference"),
    ("Full Mechanics", r"\bFM\b|Full Mechanics"),
    ("Mega Size", r"\bMega Size\b|Mega Size Model"),
    ("Advanced Grade", r"\bAG\b|Advanced Grade")
]


def normalize_paint(val):
    if pd.isna(val):
        return None
    val = str(val).strip()

    if re.fullmatch(r'\d{8,}', val): # There's a random JAN/ISBN Code in one of the results
        return None
    low = val.lower()
    if low.startswith('yes'):
        return 'Yes'
    if low.startswith('no'):
        return 'No'
    if 'optional' in low:
        return 'Optional'
    return val # keep the values not matching the above options the same (we'll need to validate these manually)


def to_list(val):
    if pd.isna(val):
        return None  # preserve missingness — don't collapse to []
    parts = re.split(r'[;,]', str(val))
    return [p.strip() for p in parts if p.strip()]


def merge_variants(row):
    combined = (to_list(row['variant of']) or []) + (to_list(row['variant']) or [])
    seen = set()
    dedup = []
    for item in combined:
        if item not in seen:
            dedup.append(item)
            seen.add(item)
    return dedup

def date_range_check(val):
    if pd.isna(val):
        return False
    return bool()

def is_placeholder(val):
    return pd.notna(val) and str(val).strip().lower() in EXCLUSIVE_KEYWORDS['Placeholder']

def classify_exclusives(val):
    if pd.isna(val) or is_placeholder(val):
        return None
    low = val.lower()
    for label, keywords in EXCLUSIVE_KEYWORDS.items():
        if label == 'Placeholder':
            continue
        if any(k in low for k in keywords):
            return label
    return 'Other'

def check_category_for_exclusivity(categories):
    # There are a lot of rows where 'exclusive to' is NaN, and a lot of those columns are in fact exclusive from what we can tell in the categories tab
    if not isinstance(categories, list):
        return None, None
    for cat in categories:
        if cat.strip().lower() == 'exclusives':
            continue
        label = classify_exclusives(cat)
        if label and label != 'Other':
            return label, cat
    return None, None


def check_grade(kit_name : str, classification : str):
    for text in (classification, kit_name):
        if pd.isna(text):
            continue
        for label, pattern in GRADE_PATTERN:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return label
    return None

def parse_price(price_raw : str):
    if not price_raw or not isinstance(price_raw, str):
        return None
    low = price_raw.strip().lower()
    if low in EXCLUSIVE_KEYWORDS['Placeholder']:
        return None

    match = re.search(r'([￥¥$])\s*([\d,]+(?:\.\d+)?)', price_raw)
    if not match:
        yen_match = re.search(r'([\d,]+)\s*yen', low)
        if yen_match:
            value = int(yen_match.group(1).replace(',',''))
            return (value, 'JPY')
        return None, None
    symbol, digits = match.group(1), match.group(2)
    currency = 'JPY' if symbol == '¥' or symbol =='￥' else 'USD'
    value = float(digits.replace(',',''))

    bounds = (50, 500_000) if currency == 'JPY' else (1, 3000)
    if value <= bounds[0] or bounds[1] <= value:
        return None, None

    return (int(value) if currency == 'JPY' else value), currency

def parse_year(date : str):
    if not date or not isinstance(date, str):
        return None
    if date.strip().lower() == 'see below': # See below is present as the release date in a lot of kits
        return None
    match = re.search(r"(19|20)\d{2}", date)
    return int(match.group()) if match else None
