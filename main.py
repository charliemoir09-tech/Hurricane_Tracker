import pandas as pd
print("READING CSV FILE...")
df= pd.read_csv("2_ibtracs_all_list_v04r01.csv")
print("CSV FILE READ SUCCESSFULLY.")
print(df.head())