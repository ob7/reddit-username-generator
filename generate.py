import requests
import time
import string
import re
import argparse
from bs4 import BeautifulSoup
from itertools import product
from datetime import datetime, timedelta
from collections import deque

# Configuration
USERNAME_LENGTH = 3  # Change this to check different lengths (3, 4, 5, etc.)
CHARACTERS = string.ascii_lowercase + string.digits  # 26 letters + 10 digits = 36 characters
REQUESTS_PER_MINUTE = 30  # Conservative rate limit
ARIA_LABEL_OCCURRENCE = 1

def load_checked_usernames(filename):
    """Load previously checked usernames from a file."""
    try:
        with open(filename, 'r') as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

def log_checked_username(username, filename):
    """Log a checked username to a file."""
    with open(filename, 'a') as f:
        f.write(f"{username}\n")


# Calculate total possibilities
TOTAL_POSSIBILITIES = len(CHARACTERS) ** USERNAME_LENGTH
print(f"Checking usernames of length {USERNAME_LENGTH}")
print(f"Using character set: {CHARACTERS}")
print(f"Total possible combinations: {TOTAL_POSSIBILITIES:,}")

class RateLimiter:
    def __init__(self, requests_per_minute):
        self.requests_per_minute = requests_per_minute
        self.request_times = deque(maxlen=requests_per_minute)
    
    def wait_if_needed(self):
        """Ensure we don't exceed our rate limit"""
        now = datetime.now()
        
        if len(self.request_times) < self.requests_per_minute:
            self.request_times.append(now)
            return
        
        oldest_request = self.request_times[0]
        time_passed = now - oldest_request
        
        if time_passed < timedelta(minutes=1):
            sleep_time = 60 - time_passed.total_seconds()
            print(f"Rate limiter sleeping for {sleep_time:.2f} seconds to respect rate limit.", flush=True)
            time.sleep(sleep_time)
        
        self.request_times.append(now)

def check_username(username, rate_limiter, session):
    """Check if a username is available on Reddit"""
    url = f"https://www.reddit.com/user/{username}"
    headers = {
        'User-Agent': 'Python/RequestsScript 1.0 (by u/YourRedditUsername) - Checking username availability',
    }
    
    rate_limiter.wait_if_needed()
    
    try:
        print(f"Requesting URL: {url}", flush=True)
        response = session.get(url, headers=headers, timeout=10)
        
        # Debugging the status code and response length
        print(f"Received response for {username} - Status: {response.status_code}, Content Length: {len(response.text)}", flush=True)
        
        # Save full content to a file for debugging
        debug_filename = f"debug_{username}.html"
        with open(debug_filename, 'w') as file:
            file.write(response.text)
        print(f"Saved HTML response to {debug_filename} for further inspection.", flush=True)
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Debugging the number of article tags found with aria-label
        articles = soup.find_all('article', {'aria-label': True})
        print(f"Found {len(articles)} <article> tags with 'aria-label' attribute", flush=True)

        target_index = ARIA_LABEL_OCCURRENCE - 1  # Convert to zero-based index
        if len(articles) > target_index:
            aria_label = articles[target_index]['aria-label']
            print(f"{ARIA_LABEL_OCCURRENCE}th <article> 'aria-label' content: {aria_label}", flush=True)
        else:
            aria_label = f"No {ARIA_LABEL_OCCURRENCE}th <article> with aria-label found"
            print(f"{ARIA_LABEL_OCCURRENCE}th <article> with 'aria-label' not found. Returning default message.", flush=True)
        
        # Display final output for the checked username
        print(f"{datetime.now().strftime('%H:%M:%S')} - Checked {username} - Status: {response.status_code} - {aria_label}", flush=True)
        
        # Check if the username is available based on response status
        if response.status_code == 404:
            print(f"Username {username} is likely available (404 not found)", flush=True)
            return True  # Page not found, likely available
            
        # Check the response content for a specific "not found" message
        if "Sorry, nobody on Reddit goes by that name" in response.text:
            print(f"Username {username} is available (text match)", flush=True)
            return True  # Username is available
        
        print(f"Username {username} is taken or page exists but is suspended.", flush=True)
        return False  # Username is taken or page exists but is suspended
    
    except Exception as e:
        print(f"Error checking {username}: {e}", flush=True)
        time.sleep(30)
        return False

def find_available_usernames(max_checks=None, specific_username=None):
    available_usernames = []
    rate_limiter = RateLimiter(requests_per_minute=REQUESTS_PER_MINUTE)
    session = requests.Session()
    
    print("Starting username availability check...", flush=True)
    
    if specific_username:
        # Directly check the specified username
        print(f"Checking specific username: {specific_username}", flush=True)
        if check_username(specific_username, rate_limiter, session):
            print(f"Available username found: {specific_username}", flush=True)
            available_usernames.append(specific_username)
        session.close()
        return available_usernames

    # If no specific username is given, proceed with regular checks
    print("Starting bulk username checks...", flush=True)
    for combo in product(CHARACTERS, repeat=USERNAME_LENGTH):
        username = ''.join(combo)
        if check_username(username, rate_limiter, session):
            available_usernames.append(username)
        
        if max_checks and len(available_usernames) >= max_checks:
            break
    
    session.close()
    return available_usernames

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check Reddit username availability.")
    parser.add_argument("-u", "--username", help="Specify a username to check")
    parser.add_argument("-m", "--max_checks", type=int, help="Specify maximum number of usernames to check")
    
    args = parser.parse_args()
    
    specific_username = args.username
    max_checks = args.max_checks if args.max_checks else TOTAL_POSSIBILITIES
    
    if specific_username:
        # Check only the specific username
        available = find_available_usernames(specific_username=specific_username)
    else:
        # Proceed with normal checks if no specific username is provided
        available = find_available_usernames(max_checks=max_checks)
    
    print("\nSearch complete!")
    print(f"Found {len(available)} available usernames:")
    for username in available:
        print(username)
