import instaloader
import csv
import time
import random
import os
from datetime import datetime
import sys
import json
from multiprocessing import Pool, cpu_count

# =========================
# CONFIGURATION
# =========================
SCRAPER_ACCOUNTS = os.environ.get("scraper accounts")

ACCOUNT_CHECKPOINT_FILE = "account_comments_checkpoint.json"
TARGET_CHECKPOINT_FILE = "target_comments_checkpoint.json"
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
    """Scrape all comments + replies for posts, reusing username_posts.csv if available"""
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
        followers_count = profile.followers
        print(f"📊 @{username} has {total_posts} posts, {followers_count} followers")
    except Exception as e:
        print(f"❌ Profile error: {str(e)}")
        return None, "profile_error"

    # ---- check if username_posts.csv already exists ----
    posts_file = f"{username}_posts.csv"
    posts_list = []

    if os.path.exists(posts_file):
        print(f"📂 Found {posts_file}, reusing post links...")
        with open(posts_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "URL" in row and row["URL"]:
                    posts_list.append((row["Shortcode"], row["URL"], row["Timestamp"], row["Likes"], row["Comments"]))
    else:
        print(f"⚠️ {posts_file} not found, scraping posts directly...")
        posts_list = [(p.shortcode,
                       f"https://www.instagram.com/p/{p.shortcode}/",
                       p.date_utc.strftime('%Y-%m-%d %H:%M:%S'),
                       p.likes,
                       p.comments)
                      for p in profile.get_posts()]

    filename = f"{username}_posts_comments.csv"
    mode = 'a' if os.path.exists(filename) else 'w'

    with open(filename, mode, newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if mode == 'w':
            writer.writerow([
                'Username', 'Followers Count', 'Total Posts',
                'Post ID', 'Post Link', 'Number of Post',
                'Comment Count', 'Like Count', 'Date of Post',
                'Commentor Username', 'Comment Text', 'Comment Date',
                'Comment Likes Count', 'Parent Comment ID'
            ])
            csvfile.flush()

        status = "completed"
        new_posts = 0

        for i, (shortcode, url, post_date, like_count, comment_count) in enumerate(posts_list, 1):
            try:
                post = instaloader.Post.from_shortcode(L.context, shortcode)

                # --- Extract all comments + replies ---
                for comment in post.get_comments():
                    writer.writerow([
                        username, followers_count, total_posts,
                        post.mediaid, url, i,
                        comment_count, like_count, post_date,
                        comment.owner.username,
                        comment.text,
                        comment.created_at_utc.strftime('%Y-%m-%d %H:%M:%S'),
                        getattr(comment, "likes_count", 0),
                        ""  # Top-level comment → no parent
                    ])
                    csvfile.flush()

                    # Handle replies
                    for reply in comment.answers:
                        writer.writerow([
                            username, followers_count, total_posts,
                            post.mediaid, url, i,
                            comment_count, like_count, post_date,
                            reply.owner.username,
                            reply.text,
                            reply.created_at_utc.strftime('%Y-%m-%d %H:%M:%S'),
                            getattr(reply, "likes_count", 0),
                            comment.id  # parent comment ID
                        ])
                        csvfile.flush()

                new_posts += 1

                # progress bar
                progress = min(100, int(i / len(posts_list) * 100))
                bar_length = 30
                filled_length = int(bar_length * progress / 100)
                bar = '█' * filled_length + '-' * (bar_length - filled_length)
                sys.stdout.write(f"\r⏳ {username}: [{bar}] {progress}% | 📦 {i}/{len(posts_list)}")
                sys.stdout.flush()

                time.sleep(random.uniform(*POST_DELAY_RANGE))

            except Exception as e:
                print(f"\n❌ Error on post {url}: {str(e)}")
                status = "error"
                continue

    print(f"\n✅ Finished {len(posts_list)} posts for @{username}")
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
