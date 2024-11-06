import requests
import time
import string
from itertools import product
from datetime import datetime, timedelta
from collections import deque

# Configuration
USERNAME_LENGTH = 32  # Change this to check different lengths (3, 4, 5, etc.)
CHARACTERS = string.ascii_lowercase + string.digits  # 26 letters + 10 digits = 36 characters
REQUESTS_PER_MINUTE = 30  # Conservative rate limit

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
		response = session.get(url, headers=headers, timeout=10)
		print(f"{datetime.now().strftime('%H:%M:%S')} - Checked {username} - Status: {response.status_code}")

		if response.status_code == 404:
			return True  # Page not found, likely available

		# Check the response content for the specific "not found" message
		if "Sorry, nobody on Reddit goes by that name" in response.text:
			return True  # Username is available

		return False  # Username is taken or page exists but is suspended

	except Exception as e:
		print(f"Error checking {username}: {e}")
		time.sleep(30)
		return False


def find_available_usernames(max_checks=None):
	"""Generate and check username combinations with rate limiting"""
	available_usernames = []
	rate_limiter = RateLimiter(requests_per_minute=REQUESTS_PER_MINUTE)
	session = requests.Session()

	# Load previously checked usernames
	checked_usernames_file = f'checked_usernames_{USERNAME_LENGTH}char.txt'
	checked_usernames = load_checked_usernames(checked_usernames_file)

	total_combinations = TOTAL_POSSIBILITIES
	if max_checks:
		total_combinations = min(total_combinations, max_checks)

	estimated_minutes = total_combinations / REQUESTS_PER_MINUTE
	print(f"Starting search at {datetime.now().strftime('%H:%M:%S')}")
	print(f"Checking up to {total_combinations:,} usernames...")
	print(f"Estimated time: {estimated_minutes:.1f} minutes ({estimated_minutes/60:.1f} hours)")

	checked = 0
	start_time = time.time()

	try:
		for combo in product(CHARACTERS, repeat=USERNAME_LENGTH):
			username = ''.join(combo)

			# Skip already checked usernames
			if username in checked_usernames:
				continue

			checked += 1

			if check_username(username, rate_limiter, session):
				print(f"\nFound available username: {username}")
				available_usernames.append(username)

				# Save available username immediately
				with open(f'available_usernames_{USERNAME_LENGTH}char.txt', 'a') as f:
					f.write(f"{username}\n")

			# Log every checked username
			log_checked_username(username, checked_usernames_file)

			# Print progress every 10 checks
			if checked % 10 == 0:
				elapsed_time = time.time() - start_time
				rate = checked / elapsed_time if elapsed_time > 0 else 0
				time_remaining = (total_combinations - checked) / (rate if rate > 0 else 1)
				print(f"\nProgress: {checked:,}/{total_combinations:,} "
		  f"({(checked/total_combinations)*100:.1f}%) "
		  f"Rate: {rate:.1f} checks/second")
				print(f"Estimated time remaining: {time_remaining/60:.1f} hours")

			if max_checks and checked >= max_checks:
				break

	except KeyboardInterrupt:
		print("\nSearch interrupted by user")
	finally:
		session.close()

	return available_usernames


if __name__ == "__main__":
	# Show some calculations first
	print("\nTime estimates for full search:")
	print(f"At {REQUESTS_PER_MINUTE} requests per minute:")
	print(f"- Minutes: {TOTAL_POSSIBILITIES/REQUESTS_PER_MINUTE:.1f}")
	print(f"- Hours: {(TOTAL_POSSIBILITIES/REQUESTS_PER_MINUTE)/60:.1f}")
	print(f"- Days: {(TOTAL_POSSIBILITIES/REQUESTS_PER_MINUTE)/60/24:.1f}")

	# Ask how many to check
	max_checks = input(f"\nHow many usernames would you like to check? (max {TOTAL_POSSIBILITIES:,}): ")
	max_checks = int(max_checks) if max_checks else TOTAL_POSSIBILITIES

	print("\nStarting username search with conservative rate limiting...")
	available = find_available_usernames(max_checks=max_checks)

	print("\nSearch complete!")
	print(f"Found {len(available)} available usernames:")
	for username in available:
		print(username)
