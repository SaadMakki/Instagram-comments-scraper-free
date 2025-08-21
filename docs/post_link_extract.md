# 📄 post_link_extract.py - Documentation

## 🎯 Purpose
Extracts Instagram post links and metadata from target accounts using multiple scraper accounts with parallel processing capabilities.

---

## 🔧 How It Works

### Core Functionality
1. **Multi-Account Processing**: Uses multiple Instagram accounts to distribute the workload
2. **Parallel Execution**: Processes multiple target accounts simultaneously  
3. **Checkpoint System**: Saves progress and resumes from interruptions
4. **Rate Limit Management**: Implements delays and pauses to avoid detection

### Data Extracted
- Post URLs (Instagram links)
- Post timestamps
- Shortcodes (unique identifiers)
- Like counts
- Comment counts  
- Post types (Regular post vs Reel)

---

## 📊 Output Format

The script generates `{username}_posts.csv` files with the following structure:

| Column | Description | Example |
|--------|-------------|---------|
| Type | Post or Reel | "Post" |
| URL | Instagram post link | "https://www.instagram.com/p/ABC123/" |
| Timestamp | When post was created | "2024-01-15 14:30:00" |
| Shortcode | Unique post identifier | "ABC123def" |
| Likes | Number of likes | 1250 |
| Comments | Number of comments | 89 |

---

## ⚙️ Configuration

### Required Files

#### 1. accounts.csv
```csv
username
target_user1
target_user2
target_user3
```

#### 2. .env file
```env
scraper accounts=[
    {"username": "scraper1", "password": "pass123"},
    {"username": "scraper2", "password": "pass456"}
]
```

### Configuration Variables
```python
MAX_ATTEMPTS_PER_ACCOUNT = 2    # Retry attempts before marking blocked
POST_DELAY_RANGE = (1, 3)       # Delay between posts (seconds)
BIG_PAUSE_RANGE = (20, 40)      # Long pause every 20 posts
```

---

## 🚀 Usage Instructions

### Windows
```cmd
python post_link_extract.py
```

### macOS/Linux  
```bash
python3 post_link_extract.py
```

### Interactive Prompts
1. **CSV File Path**: Enter path to your accounts.csv file
2. **Progress Display**: Real-time progress bars show extraction status

---

## 📈 Progress Tracking

### Visual Indicators
```
⏳ username: [██████████████████────] 75% | 📦 150/200 | ✨ New: 25
```

- **Progress Bar**: Visual completion status
- **Post Count**: Current/Total posts processed
- **New Posts**: Recently added posts in this session

### Status Messages
- ✅ **Login successful**: Account authentication worked
- ⚠️ **Login failed**: Check credentials
- 💤 **Short pause**: Rate limiting delay
- ❌ **Error**: Post processing issue

---

## 🔄 Checkpoint System

### Files Created
- `account_checkpoint.json`: Tracks blocked accounts
- `target_checkpoint.json`: Tracks completed users  
- `accounts_summary.csv`: Overall statistics

### Resume Capability
- Automatically resumes from last processed post
- Skips already completed accounts
- Handles interruptions gracefully

---

## ⚠️ Error Handling

### Common Scenarios

**Account Blocked**
```
⚠️ Login failed: Challenge required
```
- **Solution**: Switch to different scraper account
- **Prevention**: Use delays and limit requests

**Profile Not Found**  
```
❌ Profile error: User not found
```
- **Solution**: Verify username spelling
- **Check**: Account might be private/deleted

**Network Issues**
```
🔥 Critical error: Connection timeout
```
- **Solution**: Check internet connection
- **Retry**: Script will resume from checkpoint

---

## 🎛️ Advanced Features

### Parallel Processing
- Automatically distributes usernames across available accounts
- Processes multiple targets simultaneously  
- Optimizes resource utilization

### Smart Resuming
```python
# Checks existing files and skips processed posts
if post.shortcode in existing_shortcodes:
    continue
```

### Rate Limit Protection
```python
# Regular delays
time.sleep(random.uniform(*POST_DELAY_RANGE))

# Longer pauses every 20 posts
if new_posts > 0 and new_posts % 20 == 0:
    time.sleep(random.uniform(*BIG_PAUSE_RANGE))
```

---

## 📋 Troubleshooting

### Performance Issues
- **Slow Processing**: Normal due to rate limits (30-60 min per account)
- **Memory Usage**: Large accounts may use more RAM
- **Disk Space**: Ensure sufficient storage for CSV files

### Authentication Problems  
- Verify .env file format is correct
- Check account credentials are valid
- Ensure accounts aren't already blocked

### Data Quality
- Missing posts may indicate private content
- Zero likes/comments could be new posts
- Timestamp format is UTC

---

## 💡 Best Practices

1. **Account Safety**: Use dedicated accounts, not personal ones
2. **Timing**: Run during off-peak hours for better success rates  
3. **Monitoring**: Watch for blocking signs and rotate accounts
4. **Backup**: Keep checkpoint files safe to resume interrupted runs
5. **Patience**: Instagram rate limits are strict - expect delays

---

## 🔗 Next Steps

After successful completion:
1. Verify CSV files were created for each target user
2. Check `accounts_summary.csv` for overview statistics  
3. Proceed to **comments_extract.py** for comment extraction
4. Use **organize.py** to structure files into folders

---

**[⬅️ Back to Main README](../README.md)**