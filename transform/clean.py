import re
import pandas as pd

DATE_REGEX = re.compile(r'\b(19|20)\d{2}\b|January|February|March|April|May|June|July|August|September|October|November|December', re.IGNORECASE)

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


def variant_to_list(val):
    if pd.isna(val):
        return []
    return [p.strip() for p in re.split(r'[;,]', str(val)) if p.strip()]


def merge_variants(row):
    combined = variant_to_list(row['variant of']) + variant_to_list(row['variant'])
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