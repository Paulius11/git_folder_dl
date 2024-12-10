import os
import requests
import re
import argparse
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("github_downloader.log"), logging.StreamHandler()])
logger = logging.getLogger(__name__)

class GitHubDownloader:
    def __init__(self, github_url, dest_folder=os.getcwd(), token=None):
        logger.info(f"Initializing GitHubDownloader with URL: {github_url}, Destination: {dest_folder}")
        self.github_url = github_url
        self.dest_folder = dest_folder
        self.token = token
        self.owner, self.repo_name, self.branch, self.folder_path = self.extract_repo_info()

    def extract_repo_info(self):
        """
        Extract repository information (owner, repo_name, branch, folder_path) from a full GitHub URL.
        """
        logger.debug("Extracting repository information from URL...")
        match = re.match(r'https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.+)', self.github_url)
        if match:
            logger.info(f"Extracted owner: {match.group(1)}, repo: {match.group(2)}, branch: {match.group(3)}, folder: {match.group(4)}")
            return match.group(1), match.group(2), match.group(3), match.group(4)
        else:
            logger.error("Invalid URL format. Ensure it follows 'https://github.com/owner/repo/tree/branch/folder'.")
            raise ValueError("Invalid URL format. Ensure it follows 'https://github.com/owner/repo/tree/branch/folder'.")

    def handle_rate_limit(self, response):
        """
        Handle rate limiting by checking the rate limit headers and pausing if necessary.
        """
        remaining = int(response.headers.get('X-RateLimit-Remaining', 1))
        reset_time = int(response.headers.get('X-RateLimit-Reset', time.time()))

        logger.debug(f"Rate limit remaining: {remaining}")
        if remaining == 0:
            reset_in = reset_time - int(time.time())
            logger.warning(f"Rate limit exceeded. Sleeping for {reset_in} seconds.")
            logger.info("To avoid this in the future, authenticate using a GitHub personal access token (PAT).")
            logger.info("Generate a token here: https://github.com/settings/tokens")
            logger.info("Use the --token argument to provide your token when running the script.")
            time.sleep(reset_in + 5)

    def get_repo_branches(self):
        """
        Get a list of branches from the GitHub repository using GitHub API.
        """
        logger.debug("Fetching repository branches...")
        api_url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}/branches"
        headers = {'Authorization': f'token {self.token}'} if self.token else {}
        response = requests.get(api_url, headers=headers)
        self.handle_rate_limit(response)

        if response.status_code == 200:
            branches = [branch['name'] for branch in response.json()]
            logger.info(f"Branches fetched: {branches}")
            return branches
        else:
            logger.error(f"Failed to fetch branches. Status Code: {response.status_code}")
            raise ConnectionError(f"Unable to fetch branches. Status Code: {response.status_code}")

    def list_files_in_folder(self, folder_path):
        """
        List all files and folders in a given folder on GitHub repository using GitHub API.
        """
        logger.debug(f"Listing files in folder: {folder_path}")
        api_url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}/contents/{folder_path}?ref={self.branch}"
        headers = {'Authorization': f'token {self.token}'} if self.token else {}
        response = requests.get(api_url, headers=headers)
        self.handle_rate_limit(response)

        if response.status_code == 200:
            content = response.json()
            folders, files = [], []
            for item in content:
                if item['type'] == 'file':
                    files.append(item)
                elif item['type'] == 'dir':
                    folders.append(item['name'])
            logger.info(f"Files: {[file['name'] for file in files]}, Folders: {folders}")
            return folders, files
        else:
            logger.error(f"Failed to list contents for folder: {folder_path}. Status Code: {response.status_code}")
            raise ConnectionError(f"Unable to fetch contents for {folder_path}. Status Code: {response.status_code}")

    def download_file(self, file_url, dest_folder, filename):
        """
        Download a file from the given URL and save it to the specified destination folder.
        """
        logger.debug(f"Downloading file: {filename} from {file_url}")
        headers = {'Authorization': f'token {self.token}'} if self.token else {}
        response = requests.get(file_url, headers=headers)
        self.handle_rate_limit(response)
        response.raise_for_status()

        os.makedirs(dest_folder, exist_ok=True)
        dest_path = os.path.join(dest_folder, filename)
        with open(dest_path, 'wb') as f:
            f.write(response.content)
        logger.info(f"Downloaded: {filename} -> {dest_path}")

    def download_folder(self, folder_path, dest_folder):
        """
        Recursively download all files in a folder from a GitHub repository into the specified destination folder.
        """
        logger.debug(f"Downloading folder: {folder_path} to {dest_folder}")
        full_dest_folder = os.path.join(dest_folder, folder_path.split('/')[-1])
        os.makedirs(full_dest_folder, exist_ok=True)

        folders, files = self.list_files_in_folder(folder_path)
        for file in files:
            self.download_file(file['download_url'], full_dest_folder, file['name'])
        for subfolder in folders:
            self.download_folder(f"{folder_path}/{subfolder}", full_dest_folder)

    def run(self):
        """
        Run the download process.
        """
        logger.info(f"Starting download for '{self.folder_path}' from branch '{self.branch}'...")
        self.download_folder(self.folder_path, self.dest_folder)
        logger.info(f"All files from '{self.folder_path}' have been downloaded to '{self.dest_folder}'.")

    @staticmethod
    def run_interactive():
        """
        Run the script interactively, allowing the user to input details.
        """
        github_url = input("Enter the GitHub URL: ")
        dest_folder = input("Enter the destination folder (default is current directory): ") or os.getcwd()
        token = input("Enter your GitHub Personal Access Token (or press Enter to skip): ").strip() or None

        downloader = GitHubDownloader(github_url, dest_folder, token)

        logger.info(f"Fetching available branches for {downloader.repo_name}...")
        branches = downloader.get_repo_branches()
        logger.info(f"Available branches: {', '.join(branches)}")

        if downloader.branch not in branches:
            logger.warning(f"Invalid branch. Defaulting to '{branches[0]}'.")
            downloader.branch = branches[0]

        downloader.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download a specific folder from a GitHub repository.")
    parser.add_argument('github_url', type=str, nargs='?', help="The URL of the GitHub repository and folder.")
    parser.add_argument('--dest_folder', type=str, default=os.getcwd(), help="The destination folder (default is current directory).")
    parser.add_argument('--token', type=str, help="GitHub Personal Access Token for authentication.")
    parser.add_argument('--list_branches', action='store_true', help="List available branches.")
    args = parser.parse_args()

    if args.github_url:
        downloader = GitHubDownloader(args.github_url, args.dest_folder, args.token)
        if args.list_branches:
            branches = downloader.get_repo_branches()
            logger.info(f"Available branches: {', '.join(branches)}")
        else:
            downloader.run()
    else:
        GitHubDownloader.run_interactive()
