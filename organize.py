import os 
import pandas as pd
import shutil

search_folder = input("Enter the folder path where all the .csv files are :")
folder_name = f"{search_folder}/organized folder"
os.mkdir(folder_name)
destination_folder = folder_name
account_name = "accounts.csv"
df = pd.read_csv(account_name)

files = os.listdir(search_folder)


for user in df["username"]:
    # Refresh file list each time
    for f in os.listdir(search_folder):
        if user in f:
            filepath = os.path.join(search_folder, f)

            if os.path.exists(filepath):  # ✅ Check file still exists
                user_folder = os.path.join(destination_folder, user)
                os.makedirs(user_folder, exist_ok=True)

                dest_path = os.path.join(user_folder, f)

                shutil.move(filepath, dest_path)
                print(f"Moved {filepath} -> {dest_path}")


