# GitHub Folder Downloader

This script allows you to download a specific folder from a GitHub repository, including all its contents.

## Features
- Download specific folders from a repository.
- Handles GitHub API rate limits.
- Supports interactive and non-interactive modes.
- Authentication support with Personal Access Token.

## Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/Paulius11/git_folderdl
   pip install -r requirements.txt

## Usage
```bash
python main.py <github_url> [--dest_folder <destination>] [--token <token>] [--list_branches]
```
## Example
```bash
python main.py https://github.com/owner/repo/tree/branch/folder
```
