import os
import praw
import time
import json
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')
# from dotenv import load_dotenv

# load_dotenv()

# --- Reddit API Configuration ---
# It's recommended to store these in environment variables
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")

# --- Cache Configuration ---
CACHE_DIR = 'temp'
CACHE_FILE = os.path.join(CACHE_DIR, 'reddit_posts.json')


# --- Helper Functions ---
def get_current_timestamp():
    """Returns the current timestamp in ISO format."""
    return datetime.now().isoformat()

def get_reddit_instance():
    """Initializes and returns a PRAW Reddit instance."""
    if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD]):
        print("Warning: Reddit credentials not fully configured. Using read-only mode.")
        return None  # Return None if not configured
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
        username=REDDIT_USERNAME,
        password=REDDIT_PASSWORD,
        check_for_async=False
    )

def save_posts_to_cache(posts):
    """Saves the fetched posts to a local JSON file."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(posts, f, indent=4, ensure_ascii=False)
    print(f"Saved {len(posts)} posts to cache at {CACHE_FILE}")

def load_posts_from_cache():
    """Loads posts from the local JSON cache if it exists."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                posts = json.load(f)
                print(f"Loaded {len(posts)} posts from cache.")
                return posts
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading from cache file: {e}")
            return []
    print("Cache file not found.")
    return []
    
def get_mock_posts():
    """Returns a list of mock posts for demonstration purposes."""
    print("Generating mock data as Reddit API and cache are unavailable.")
    return [
        {
            "id": "mock_post_1",
            "title": "[PAID] Can someone remove the person in the background?",
            "description": "I love this photo of my dog, but the person walking behind ruins it. Can anyone help? Will tip!",
            "imageUrl": "https://placehold.co/600x400/000000/FFFFFF?text=Sample+Image+1",
            "postUrl": "#",
            "created_utc": time.time(),
            "created_date": datetime.now().isoformat(),
            "author": "mock_user_1",
            "score": 152,
            "num_comments": 25,
            "subreddit": "PhotoshopRequest"
        },
        {
            "id": "mock_post_2",
            "title": "Please restore this old photo of my grandparents",
            "description": "This is the only photo I have of them together. It's very faded and has some scratches. Thank you in advance!",
            "imageUrl": "https://placehold.co/600x400/333333/FFFFFF?text=Sample+Image+2",
            "postUrl": "#",
            "created_utc": time.time(),
            "created_date": datetime.now().isoformat(),
            "author": "mock_user_2",
            "score": 89,
            "num_comments": 12,
            "subreddit": "PhotoshopRequest"
        },
        {
            "id": "mock_post_3",
            "title": "Can you change the color of my car to blue?",
            "description": "Thinking about getting my car repainted. Can someone show me what it would look like in a dark metallic blue?",
            "imageUrl": "https://placehold.co/600x400/666666/FFFFFF?text=Sample+Image+3",
            "postUrl": "#",
            "created_utc": time.time(),
            "created_date": datetime.now().isoformat(),
            "author": "mock_user_3",
            "score": 45,
            "num_comments": 8,
            "subreddit": "PhotoshopRequest"
        }
    ]

def get_photoshop_request_posts(limit=50, cache=True):
    """
    Fetches the latest posts from r/PhotoshopRequest that contain images.
    If Reddit API fails or is not configured, it falls back to a local cache.
    If cache is also unavailable, it returns mock data.
    """
    reddit = get_reddit_instance()

    # If Reddit credentials are not configured, go straight to cache/mock data
    if cache:
        cached_posts = load_posts_from_cache()
        return cached_posts if cached_posts else get_mock_posts()

    try:
        print("Attempting to fetch fresh posts from Reddit...")
        subreddit = reddit.subreddit("PhotoshopRequest")
        
        image_posts = []
        one_day_ago = time.time() - (24 * 60 * 60)

        for submission in subreddit.new(limit=limit):
            if submission.created_utc < one_day_ago:
                continue

            # Check for image URL
            image_url = None
            if hasattr(submission, 'url') and submission.url.endswith(('.jpg', '.jpeg', '.png')):
                image_url = submission.url
            elif hasattr(submission, 'preview'):
                try:
                    image_url = submission.preview['images'][0]['source']['url'].replace('&amp;', '&')
                except (KeyError, IndexError):
                    pass
            
            if image_url:
                post_data = {
                    "id": submission.id,
                    "title": submission.title,
                    "description": submission.selftext,
                    "imageUrl": image_url,
                    "postUrl": f"https://www.reddit.com{submission.permalink}",
                    "created_utc": submission.created_utc,
                    "created_date": datetime.fromtimestamp(submission.created_utc).isoformat(),
                    "author": submission.author.name if submission.author else "[deleted]",
                    "score": submission.score,
                    "num_comments": submission.num_comments,
                    "subreddit": submission.subreddit.display_name
                }
                image_posts.append(post_data)
        
        if image_posts:
            save_posts_to_cache(image_posts)
            return image_posts
        else:
            # If no new posts, try loading from cache, then mock
            print("No new image posts found on Reddit.")
            cached_posts = load_posts_from_cache()
            return cached_posts if cached_posts else get_mock_posts()

    except Exception as e:
        print(f"Failed to fetch from Reddit API: {e}. Falling back to cache.")
        cached_posts = load_posts_from_cache()
        return cached_posts if cached_posts else get_mock_posts()

