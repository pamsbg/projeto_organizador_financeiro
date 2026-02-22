import pandas as pd
import utils

df = utils.load_data()
income_df = utils.load_income_data()

print("--- EXAMINING EXPENSES (df) ---")
print("Unique Categories:", df['category'].unique() if not df.empty else "Empty")
if not df.empty:
    aplic_df = df[df['category'].str.contains('aplic', case=False, na=False) | df['title'].str.contains('aplic', case=False, na=False)]
    resg_df = df[df['category'].str.contains('resgate', case=False, na=False) | df['title'].str.contains('resgate', case=False, na=False)]
    print(f"Found {len(aplic_df)} rows for aplic in df.")
    print(f"Found {len(resg_df)} rows for resgate in df.")
    if len(aplic_df) > 0: print("Sample aplic:", aplic_df[['date', 'title', 'amount', 'category']].head(3))
    if len(resg_df) > 0: print("Sample resgate:", resg_df[['date', 'title', 'amount', 'category']].head(3))

print("\n--- EXAMINING INCOME (income_df) ---")
if not income_df.empty:
    aplic_inc = income_df[income_df['source'].str.contains('aplic', case=False, na=False)]
    resg_inc = income_df[income_df['source'].str.contains('resgate', case=False, na=False)]
    print(f"Found {len(aplic_inc)} rows for aplic in income.")
    print(f"Found {len(resg_inc)} rows for resgate in income.")
    if len(aplic_inc) > 0: print("Sample aplic:", aplic_inc[['date', 'source', 'amount']].head(3))
    if len(resg_inc) > 0: print("Sample resgate:", resg_inc[['date', 'source', 'amount']].head(3))
