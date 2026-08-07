#!/usr/bin/env python
# coding: utf-8

# In[255]:
import sys
import pandas as pd
import argparse
from pathlib import Path
import numpy as np
from clean import normalize_paint, merge_variants, classify_exclusives, check_category_for_exclusivity, check_grade, parse_price, parse_year, to_list, clean_franchise, normalize_glue, CSV_TO_DB_RENAME


# In[256]:


INFOBOX_FIELDS = ["kit_name","image","categories","franchise","run","release date", "materials", "scale", "classification", 
                  "image_url", "price", "need glue?", "japanese name", "model of", "jan/isbn", "lineup no.", "variant of", "subtitle", "need to paint", "illustration by",
                  "need paint?","exclusive to", "imgsize"]

PAINT_COLS = ["need paint", "need paint?", "need to paint?"]


# In[257]:

def main():
    parser = argparse.ArgumentParser(description="Clean raw Gunpla JSONL into a flat CSV")
    parser.add_argument("--input", required=True, help="Path to raw JSONL file")
    parser.add_argument("--output", required=True, help="Path to write cleaned CSV")
    args = parser.parse_args()
    json_file = args.input


    # In[258]:


    #Create df
    df = pd.read_json(json_file, lines=True)


    # In[259]:


    # Pull out image URL into separate column and drop original image column
    df['image_url'] = df['image'].map(lambda x: x.get('url', x) if isinstance(x, dict) else None)
    df = df.drop(columns=['image'])


    # In[260]:


    # Pull out all infobox fields into their own columns
    df = pd.concat([df.drop(['infobox'], axis=1), df['infobox'].apply(pd.Series)], axis=1)
    df = df.replace(r'^\s*$', np.nan, regex=True)


    # In[261]:


    df.columns


    # In[262]:


    # Check to see if rows have more than 1 paint column
    conflict = df[PAINT_COLS].notna().sum(axis=1) > 1
    df = df.drop(columns=['need paint']) # 'need paint' only has 1 row with this not equal to NaN, and it's not even visible on the wiki page :D
    df['need_paint_clean'] = df['need paint?'].apply(normalize_paint)
    df['need_to_paint_clean'] = df['need to paint?'].apply(normalize_paint)

    real_conflict = (df['need_paint_clean'].notna() & df['need_to_paint_clean'].notna() & (df['need_paint_clean'] != df['need_to_paint_clean']))
    print(df.loc[real_conflict, ['kit_name', 'need paint?', 'need to paint?']])

    df['need_paint'] = df['need_paint_clean'].combine_first(df['need_to_paint_clean'])
    df = df.drop(columns=['need paint?', 'need to paint?', 'need_paint_clean', 'need_to_paint_clean'])


    # In[263]:


    from difflib import get_close_matches
    cols = list(df.columns)
    for c in cols:
        matches = get_close_matches(c, cols, n=3, cutoff=0.8)
        if len(matches) > 1:
            print(c, "~", matches)


    # In[264]:


    # Compare variant columns and combine into one
    VARIANT_COL = [c for c in df.columns if 'variant' in c.lower()]
    variant_conflict = df[VARIANT_COL].notna().sum(axis=1) > 1
    print(f"{variant_conflict.sum()} rows with both variant columns populated")
    df.loc[variant_conflict, ['kit_name','variant']]

    df['variant_of'] = df.apply(merge_variants, axis=1)
    df = df.drop(columns=VARIANT_COL)


    # In[265]:


    # These really don't relate to the gunpla itself but rather the illustrator of the gundam or for figures + plus the random "1", "2" columns
    df = df.drop(columns=['illustration by', 'image', 'sculptor','1','2','illustration','cg works by', 'finish work by','imgsize','figure sculpt','character design'])


    # In[266]:


    df['exclusivity_type'] = df['exclusive to'].apply(classify_exclusives)  
    print(df['exclusivity_type'].value_counts(dropna=False))
    print(df.loc[df['exclusivity_type'] == 'Other', 'kit_name'].unique())


    # In[267]:


    # Create is_exclusive column
    df['is_exclusive'] = df['categories'].apply(lambda cats: isinstance(cats, list) and any('exclusive' in c.lower() for c in cats))
    print(f'{df['is_exclusive'].sum()} Exclusive kits out of {len(df)} kits')

    needs_backfill = df['exclusive to'].isna() & df['is_exclusive']
    inferred = df.loc[needs_backfill, 'categories'].apply(lambda cats: pd.Series(check_category_for_exclusivity(cats), index=['exclusivity_type', 'matched_category']))

    df.loc[needs_backfill, 'exclusive_channel_type_from_category'] = inferred['exclusivity_type']
    df.loc[needs_backfill, 'exclusive_value_from_category'] = inferred['matched_category']

    print(f"Backfilled {inferred['exclusivity_type'].notna().sum()} of {needs_backfill.sum()} exclusive-but-unlabeled rows")
    print(df.loc[needs_backfill & inferred['exclusivity_type'].notna(), ['kit_name', 'categories', 'exclusive_channel_type_from_category']].head(20))


    # In[268]:


    pd.set_option('display.max_rows', 21)
    still_unmatched = needs_backfill & inferred['exclusivity_type'].isna()
    print(f"{still_unmatched.sum()} exclusive rows still unclassified")

    unmatched_cats = df.loc[still_unmatched, 'categories'].explode()
    unmatched_cats[unmatched_cats.str.contains('exclusive', case=False, na=False)].value_counts().head(30)

    # We can probably leave the remaining exclusive kits that don't have a specification alone, stuff like CD-exclusive/ molds/ aren't specific enough


    # In[269]:


    ADDON_COLS = [c for c in df.columns if c in ['for use with', 'add-on for']]
    conflict = df[ADDON_COLS].notna().sum(axis=1) > 1
    print(f"{conflict.sum()} rows with both columns populated")
    df.loc[conflict, ['kit_name'] + ADDON_COLS]


    # In[270]:


    # Drop add-on for as it's either a duplicate of for use with, or it's not a searchable kit
    df = df.rename(columns={'for use with' : 'used_for'})
    df = df.drop(columns=['add-on for', 'name'])
    df.loc[df['used_for'].notna(), ['kit_name','used_for']]


    # In[271]:


    df.loc[df['exclusive_channel_type_from_category'].notna(), ['exclusive_channel_type_from_category','exclusive_value_from_category']]


    # In[272]:


    df.columns


    # In[273]:


    pd.set_option('display.max_rows', 25)

    df.notna().mean().sort_values(ascending=False)


    # In[274]:


    df = df.rename(columns={'release date': 'release_date', 'need glue?' : 'glue_needed', 'lineup no.':'lineup_num', 'model of':'model_of', 'exclusive to':'exclusive_to', 'japanese name':'japanese_name'})


    # In[275]:


    df.columns


    # In[276]:


    print(df['used_for'].dropna().head(10))


    # In[277]:


    df.columns.tolist()


    # In[278]:


    df = df.drop(columns=['exclusivity_type'])
    df = df.rename(columns={'used_for' : 'requires_kit'})


    # In[279]:


    df['exclusive_channel_type'] = df['exclusive_to'].apply(classify_exclusives).combine_first(df['exclusive_channel_type_from_category'])


    # In[280]:


    df = df.drop(columns=['exclusive_channel_type_from_category'])


    # In[281]:


    df.notna().mean().sort_values(ascending=False)


    # In[282]:


    df['grade'] = df.apply(lambda r: check_grade(r['kit_name'], r['classification']), axis=1)
    df[['price_value', 'price_currency']] = df['price'].apply(lambda x: pd.Series(parse_price(x)))
    df = df.drop(columns=['price'])
    df['release_year'] = df['release_date'].apply(parse_year)


    # In[283]:


    print(df['grade'].value_counts(dropna=False))
    print(f"No grade (gradeless line): {df['grade'].isna().mean():.1%}")
    no_grade = df[df['grade'].isna()]


    # In[284]:


    pd.set_option('display.max_rows', 100)
    print(no_grade['classification'].value_counts())


    # In[285]:


    df = df.rename(columns={'model of': 'model_of'})
    df['model_of'] = df['model_of'].apply(to_list)
    df['kit_count'] = df['model_of'].apply(lambda x: max(len(x), 1) if isinstance(x, list) else pd.NA)


    # In[286]:


    print(f"Missing price: {df['price_value'].isna().mean():.1%}")
    print(f"Missing release_year: {df['release_year'].isna().mean():.1%}")
    print(df['kit_count'].value_counts())


    # In[287]:


    # Some wiki entries have the price under a different section, like isbn or need to paint (bruh)
    MANUAL_PRICE_OVERRIDE = {
        "Figure-rise Standard Kamen Rider Kuuga (Mighty Form)/Decade Ver." : (3200, 'JPY'),
        "Super Mini-pla Shinka Gattai Daizyuzin": (4968, 'JPY')
    }

    for name, (value, currency) in MANUAL_PRICE_OVERRIDE.items():
        mask = df['kit_name'] == name
        df.loc[mask, 'price_value'] = value
        df.loc[mask, 'price_currency'] = currency


    # In[288]:


    franchise_semicolon = df['franchise'].dropna().str.contains(';')
    multi_semicolon = df['franchise'].dropna().str.count(';') > 1
    print(f"{franchise_semicolon.sum()} rows with semicolon in franchise")
    print(f"{multi_semicolon.sum()} rows with multiple semicolons in franchise")


    # In[289]:


    # Clean up franchise name to only keep second part of franchise if it contains a semicolon
    df['franchise'] = df['franchise'].apply(clean_franchise)


    # In[290]:


    new_semicolon = df['franchise'].dropna().str.contains(';')
    print(f"{new_semicolon.sum()} rows with semicolon in franchise")


    # In[291]:


    dupes = df[df.duplicated('kit_name', keep=False)].sort_values('kit_name')
    print(f"{df['kit_name'].duplicated().sum()} duplicated kit_name rows")
    print(dupes[['kit_name', 'jan/isbn', 'price_value', 'release_year']])


    # In[292]:


    before = len(df)
    df = df.drop_duplicates(subset='kit_name', keep='last')
    print(f"Dropped {before - len(df)} duplicate rows, {len(df)} remaining")


    # In[293]:


    df['glue_needed'] = df['glue_needed'].apply(normalize_glue)


    # In[294]:


    df.loc[df['kit_name'] == '1/100 ASW-G-01 Gundam Bael']


    # In[ ]:





    # In[295]:


    df.to_csv(args.output, index=False)


    # In[ ]:

if __name__ == "__main__":
    main()


