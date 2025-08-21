import instaloader
import csv
import time
import random
import os
from datetime import datetime
import sys
import json
from dotenv import load_dotenv
from multiprocessing import Pool, cpu_count

# =========================
# CONFIGURATION
# =========================

load_dotenv()

SCRAPER_ACCOUNTS = os.environ.get("scraper accounts")

ACCOUNT_CHECKPOINT_FILE = "account_checkpoint.json"
TARGET_CHECKPOINT_FILE = "target_checkpoint.json"
MAX_ATTEMPTS_PER_ACCOUNT = 2  # Tries before marking blocked
POST_DELAY_RANGE = (1, 3)     # Delay between posts in seconds
BIG_PAUSE_RANGE = (20, 40)    # Pause every 20 posts
CHUNK_SIZE = None             # Will be auto-calculated


# =========================
# CHECKPOINT HELPERS
# =========================
def load_account_checkpoint():
    if os.path.exists(ACCOUNT_CHECKPOINT_FILE):
        try:
            with open(ACCOUNT_CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"blocked": []}
    return {"blocked": []}

def save_account_checkpoint(data):
    with open(ACCOUNT_CHECKPOINT_FILE, 'w') as f:
        json.dump(data, f)

def load_target_checkpoint():
    if os.path.exists(TARGET_CHECKPOINT_FILE):
        try:
            with open(TARGET_CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_target_checkpoint(data):
    with open(TARGET_CHECKPOINT_FILE, 'w') as f:
        json.dump(data, f)


# =========================
# SCRAPER FUNCTION
# =========================
def scrape_instagram_posts(username, scraper_account):
    """Scrape posts for a target account using a specific scraper account"""
    L = instaloader.Instaloader(
        sleep=True,
        quiet=True,
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
        max_connection_attempts=1
    )
    
    print(f"🔑 Using scraper account: @{scraper_account['username']}")
    
    try:
        L.login(scraper_account['username'], scraper_account['password'])
        print("✅ Login successful")
    except Exception as e:
        print(f"⚠️ Login failed: {str(e)}")
        return None, "login_failed"

    try:
        profile = instaloader.Profile.from_username(L.context, username)
        total_posts = profile.mediacount
        print(f"📊 @{username} has {total_posts} total posts")
        summary_file = "accounts_summary.csv"
        summary_exists = os.path.exists(summary_file)

        existing_accounts = set()
        if summary_exists:
            with open(summary_file, 'r', encoding='utf-8') as sf:
                reader = csv.reader(sf)
                next(reader, None)  # Skip header
                for row in reader:
                    if row:
                        existing_accounts.add(row[0])

        if username not in existing_accounts:
            with open(summary_file, 'a', newline='', encoding='utf-8') as sf:
                writer = csv.writer(sf)
                if not summary_exists:
                    writer.writerow(['Username', 'Total_Posts'])
                writer.writerow([username, total_posts])
    except Exception as e:
        print(f"❌ Profile error: {str(e)}")
        return None, "profile_error"

    filename = f"{username}_posts.csv"
    save_path = os.path.abspath(filename)
    existing_shortcodes = set()
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    if len(row) > 3:
                        existing_shortcodes.add(row[3])
            print(f"⏩ Resuming from {len(existing_shortcodes)} posts")
        except Exception as e:
            print(f"⚠️ Error reading file: {str(e)}")

    mode = 'a' if os.path.exists(filename) else 'w'
    with open(filename, mode, newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if mode == 'w':
            writer.writerow(['Type', 'URL', 'Timestamp', 'Shortcode', 'Likes', 'Comments'])
            csvfile.flush()
        
        post_count = len(existing_shortcodes)
        new_posts = 0
        status = "completed"
        
        try:
            for post in profile.get_posts():
                if post.shortcode in existing_shortcodes:
                    continue
                try:
                    row = [
                        "Reel" if post.is_video else "Post",
                        f"https://www.instagram.com/p/{post.shortcode}/",
                        post.date_utc.strftime('%Y-%m-%d %H:%M:%S'),
                        post.shortcode,
                        post.likes if post.likes else 0,
                        post.comments if post.comments else 0
                    ]
                    writer.writerow(row)
                    csvfile.flush()
                    post_count += 1
                    new_posts += 1
                    existing_shortcodes.add(post.shortcode)

                    progress = min(100, int(post_count / total_posts * 100)) if total_posts > 0 else 0
                    bar_length = 30
                    filled_length = int(bar_length * progress / 100)
                    bar = '█' * filled_length + '-' * (bar_length - filled_length)
                    sys.stdout.write(f"\r⏳ {username}: [{bar}] {progress}% | 📦 {post_count}/{total_posts} | ✨ New: {new_posts}")
                    sys.stdout.flush()
                    
                    time.sleep(random.uniform(*POST_DELAY_RANGE))

                    if new_posts > 0 and new_posts % 20 == 0:
                        nap = random.uniform(*BIG_PAUSE_RANGE)
                        print(f"\n💤 Short pause for {nap:.0f} sec to avoid detection")
                        time.sleep(nap)

                except Exception as e:
                    print(f"\n❌ Error on post: {str(e)}")
                    if "blocked" in str(e).lower() or "429" in str(e):
                        status = "blocked"
                        break
                    time.sleep(5)
        except KeyboardInterrupt:
            print("\n⏹️ Interrupted by user")
            status = "interrupted"
        except Exception as e:
            print(f"\n🔥 Critical error: {str(e)}")
            status = "error"
    
    print(f"\n✅ Finished {post_count}/{total_posts} posts for @{username}")
    return filename, status


# =========================
# PROCESS FUNCTION (FOR MULTIPROCESSING)
# =========================
def process_chunk(args):
    usernames, scraper_account = args
    account_checkpoint = load_account_checkpoint()
    target_checkpoint = load_target_checkpoint()
    processed_files = []

    for username in usernames:
        if username in target_checkpoint.get("completed", []):
            continue

        print(f"\n🚀 Processing @{username} on @{scraper_account['username']}")
        result_file, status = scrape_instagram_posts(username, scraper_account)

        if status == "completed":
            processed_files.append(result_file)
            target_checkpoint.setdefault("completed", []).append(username)
            save_target_checkpoint(target_checkpoint)
        elif status == "blocked":
            account_checkpoint.setdefault("blocked", []).append(scraper_account['username'])
            save_account_checkpoint(account_checkpoint)
            break  # Stop using this account if blocked

    return processed_files


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    print("🚀 Parallel Instagram Scraper")
    print("==============================")

    csv_file = input("Enter path to CSV with usernames: ").strip()
    if not os.path.exists(csv_file):
        print(f"❌ File not found: {csv_file}")
        sys.exit(1)

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if 'username' not in reader.fieldnames:
            print("❌ CSV must have 'username' column")
            sys.exit(1)
        all_usernames = [row['username'].strip().lower() for row in reader if row['username'].strip()]

    # Split usernames into chunks for each account
    CHUNK_SIZE = len(all_usernames) // len(SCRAPER_ACCOUNTS) + 1
    chunks = [all_usernames[i:i + CHUNK_SIZE] for i in range(0, len(all_usernames), CHUNK_SIZE)]
    chunked_args = [(chunks[i], SCRAPER_ACCOUNTS[i]) for i in range(len(chunks))]

    with Pool(processes=len(chunked_args)) as pool:
        results = pool.map(process_chunk, chunked_args)

    print("\n✅ All scraping done.")
    for files in results:
        for f in files:
            print(f"- {os.path.abspath(f)}")
