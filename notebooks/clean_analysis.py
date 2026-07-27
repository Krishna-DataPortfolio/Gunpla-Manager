#!/usr/bin/env python
# coding: utf-8

# In[50]:


get_ipython().run_line_magic('load_ext', 'autoreload')
get_ipython().run_line_magic('autoreload', '2')
import sys
import pandas as pd
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path().resolve().parents[0]))
from transform.clean import normalize_paint, merge_variants, classify_exclusives, check_category_for_exclusivity, check_grade, parse_price, parse_year, to_list


# In[51]:


INFOBOX_FIELDS = ["kit_name","image","categories","franchise","run","release date", "materials", "scale", "classification", 
                  "image_url", "price", "need glue?", "japanese name", "model of", "jan/isbn", "lineup no.", "variant of", "subtitle", "need to paint", "illustration by",
                  "need paint?","exclusive to", "imgsize"]

PAINT_COLS = ["need paint", "need paint?", "need to paint?"]


# In[52]:


# Acquire path for dataset (it's in a folder on an upper level)
parent_path = Path().resolve().parents[0]
json_file = parent_path / "data/final/bandai_dataset_2026-07-01.jsonl"


# In[53]:


#Create df
df = pd.read_json(json_file, lines=True)


# In[54]:


# Pull out image URL into separate column and drop original image column
df['image_url'] = df['image'].map(lambda x: x.get('url', x) if isinstance(x, dict) else None)
df = df.drop(columns=['image'])


# In[55]:


# Pull out all infobox fields into their own columns
df = pd.concat([df.drop(['infobox'], axis=1), df['infobox'].apply(pd.Series)], axis=1)
df = df.replace(r'^\s*$', np.nan, regex=True)


# In[56]:


df.columns


# In[57]:


# Check to see if rows have more than 1 paint column
conflict = df[PAINT_COLS].notna().sum(axis=1) > 1
df = df.drop(columns=['need paint']) # 'need paint' only has 1 row with this not equal to NaN, and it's not even visible on the wiki page :D
df['need_paint_clean'] = df['need paint?'].apply(normalize_paint)
df['need_to_paint_clean'] = df['need to paint?'].apply(normalize_paint)

real_conflict = (df['need_paint_clean'].notna() & df['need_to_paint_clean'].notna() & (df['need_paint_clean'] != df['need_to_paint_clean']))
print(df.loc[real_conflict, ['kit_name', 'need paint?', 'need to paint?']])

df['need_paint'] = df['need_paint_clean'].combine_first(df['need_to_paint_clean'])
df = df.drop(columns=['need paint?', 'need to paint?', 'need_paint_clean', 'need_to_paint_clean'])


# In[58]:


from difflib import get_close_matches
cols = list(df.columns)
for c in cols:
    matches = get_close_matches(c, cols, n=3, cutoff=0.8)
    if len(matches) > 1:
        print(c, "~", matches)


# In[59]:


# Compare variant columns and combine into one
VARIANT_COL = [c for c in df.columns if 'variant' in c.lower()]
variant_conflict = df[VARIANT_COL].notna().sum(axis=1) > 1
print(f"{variant_conflict.sum()} rows with both variant columns populated")
df.loc[variant_conflict, ['kit_name','variant']]

df['variant_of'] = df.apply(merge_variants, axis=1)
df = df.drop(columns=VARIANT_COL)


# In[ ]:


# These really don't relate to the gunpla itself but rather the illustrator of the gundam or for figures + plus the random "1", "2" columns
df = df.drop(columns=['illustration by', 'image', 'sculptor','1','2','illustration','cg works by', 'finish work by','imgsize','figure sculpt','character design'])


# In[ ]:


df['exclusivity_type'] = df['exclusive to'].apply(classify_exclusives)  
print(df['exclusivity_type'].value_counts(dropna=False))
print(df.loc[df['exclusivity_type'] == 'Other', 'kit_name'].unique())


# In[ ]:


# Create is_exclusive column
df['is_exclusive'] = df['categories'].apply(lambda cats: isinstance(cats, list) and any('exclusive' in c.lower() for c in cats))
print(f'{df['is_exclusive'].sum()} Exclusive kits out of {len(df)} kits')

needs_backfill = df['exclusive to'].isna() & df['is_exclusive']
inferred = df.loc[needs_backfill, 'categories'].apply(lambda cats: pd.Series(check_category_for_exclusivity(cats), index=['exclusivity_type', 'matched_category']))

df.loc[needs_backfill, 'exclusive_channel_type_from_category'] = inferred['exclusivity_type']
df.loc[needs_backfill, 'exclusive_value_from_category'] = inferred['matched_category']

print(f"Backfilled {inferred['exclusivity_type'].notna().sum()} of {needs_backfill.sum()} exclusive-but-unlabeled rows")
print(df.loc[needs_backfill & inferred['exclusivity_type'].notna(), ['kit_name', 'categories', 'exclusive_channel_type_from_category']].head(20))


# In[ ]:


pd.set_option('display.max_rows', 21)
still_unmatched = needs_backfill & inferred['exclusivity_type'].isna()
print(f"{still_unmatched.sum()} exclusive rows still unclassified")

unmatched_cats = df.loc[still_unmatched, 'categories'].explode()
unmatched_cats[unmatched_cats.str.contains('exclusive', case=False, na=False)].value_counts().head(30)

# We can probably leave the remaining exclusive kits that don't have a specification alone, stuff like CD-exclusive/ molds/ aren't specific enough


# In[ ]:


ADDON_COLS = [c for c in df.columns if c in ['for use with', 'add-on for']]
conflict = df[ADDON_COLS].notna().sum(axis=1) > 1
print(f"{conflict.sum()} rows with both columns populated")
df.loc[conflict, ['kit_name'] + ADDON_COLS]


# In[ ]:


# Drop add-on for as it's either a duplicate of for use with, or it's not a searchable kit
df = df.rename(columns={'for use with' : 'used_for'})
df = df.drop(columns=['add-on for', 'name'])
df.loc[df['used_for'].notna(), ['kit_name','used_for']]


# In[ ]:


df.loc[df['exclusive_channel_type_from_category'].notna(), ['exclusive_channel_type_from_category','exclusive_value_from_category']]


# In[ ]:


df.columns


# In[ ]:


pd.set_option('display.max_rows', 25)

df.notna().mean().sort_values(ascending=False)


# In[ ]:


df = df.rename(columns={'release date': 'release_date', 'need glue?' : 'glue_needed', 'lineup no.':'lineup_num', 'model of':'model_of', 'exclusive to':'exclusive_to', 'japanese name':'japanese_name'})


# In[ ]:


df.columns


# In[ ]:


print(df['used_for'].dropna().head(10))


# In[ ]:


df.columns.tolist()


# In[ ]:


df = df.drop(columns=['exclusivity_type'])
df = df.rename(columns={'used_for' : 'requires_kit'})


# In[ ]:


df['exclusive_channel_type'] = df['exclusive_to'].apply(classify_exclusives).combine_first(df['exclusive_channel_type_from_category'])


# In[ ]:


df = df.drop(columns=['exclusive_channel_type_from_category'])


# In[ ]:


df.notna().mean().sort_values(ascending=False)


# In[61]:


df['grade'] = df.apply(lambda r: check_grade(r['kit_name'], r['classification']), axis=1)
df['price_yen'] = df['price'].apply(parse_price)
df['release_year'] = df['release_date'].apply(parse_year)


# In[ ]:


print(df['grade'].value_counts(dropna=False))
print(f"No grade (gradeless line): {df['grade'].isna().mean():.1%}")
no_grade = df[df['grade'].isna()]


# In[ ]:


pd.set_option('display.max_rows', 100)
print(no_grade['classification'].value_counts())


# In[ ]:


df = df.rename(columns={'model of': 'model_of'})
df['model_of'] = df['model_of'].apply(to_list)
df['kit_count'] = df['model_of'].apply(lambda x: max(len(x), 1) if isinstance(x, list) else pd.NA)


# In[60]:


print(f"Missing price_yen: {df['price_yen'].isna().mean():.1%}")
print(f"Missing release_year: {df['release_year'].isna().mean():.1%}")
print(df['kit_count'].value_counts())


# In[ ]:


print(df['kit_count'].dtype)
print(df['kit_count'].apply(type).value_counts())


# In[ ]:


row = df[df['kit_count'].apply(type) == tuple].iloc[0]
print(repr(row['model_of']))
print(type(row['model_of']))
print(repr(row['kit_count']))




