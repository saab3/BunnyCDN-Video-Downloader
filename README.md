# BunnyCDN Video Downloader Documentation

## Overview

This script is designed to download BunnyCDN-hosted videos from access-restricted websites. It connects to your existing Chrome browser session to access protected content that you have already authenticated to, then extracts and downloads the videos.

The primary use case is to download educational content, training videos, or other legitimate media hosted on BunnyCDN where:
1. The content is behind a login wall
2. You have legitimate access to the content
3. You want to store the videos locally for offline viewing

## Prerequisites

- Python 3.7 or higher
- Google Chrome browser
- Valid access to the website hosting the protected content

## Installation

1. Install required Python packages:

```bash
pip install selenium requests yt-dlp
```

2. Save the script to a file (e.g., `bunny_downloader.py`)

## Setting Up Chrome for Remote Debugging

**IMPORTANT**: Before running the script, you must start Chrome with remote debugging enabled:

### For Windows:
```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\selenium\chrome-profile"
```

### For macOS:
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="~/selenium-chrome-profile"
```

### For Linux:
```bash
google-chrome --remote-debugging-port=9222 --user-data-dir="~/selenium-chrome-profile"
```

The `--user-data-dir` parameter creates a new Chrome profile folder to store session data.

## Authentication

1. After launching Chrome with remote debugging, manually log in to the website containing the videos
2. Keep the Chrome browser open while running the script

## Usage

The script accepts the following parameters:

```
python bunny_downloader.py <main_url> <base_url> [-o OUTPUT_DIR] [-p PORT]
```

### Parameters:

- `main_url`: The URL of the page containing links to the videos
- `base_url`: A string filter to identify relevant links (e.g., "courses/python")
- `-o, --output`: Output directory for downloaded videos (default: current directory)
- `-p, --port`: Chrome debugging port (default: 9222)

### Example Usage:

```bash
# Download all videos from a course
python bunny_downloader.py "https://learning-site.com/my-courses" "courses/python-basics" -o "D:\Downloads\Python Course"

# Using a different debugging port
python bunny_downloader.py "https://academy.example.com/dashboard" "lessons" -p 9223 -o "~/Videos/Academy"
```

## How the Script Works

1. **Browser Connection**: Connects to your existing Chrome session via the debugging port
2. **Link Extraction**: Scans the main page for links containing the specified base URL
3. **Video Detection**: For each link, opens the page and searches for BunnyCDN video embed URLs
4. **DRM Handling**: Manages the BunnyCDN DRM protocol to prepare the video for download
5. **Download**: Uses yt-dlp to download the videos in the highest available quality
6. **Cleanup**: Preserves your original browser tab while closing any tabs opened by the script

## Troubleshooting

### "Failed to connect to Chrome on port 9222"
- Ensure Chrome is running with remote debugging enabled
- Check if the port is correct or try a different port

### "No links found matching the base URL"
- Check your base_url parameter - it should be a substring contained in the video page URLs
- Verify the main_url is loading correctly in Chrome

### "No BunnyCDN embed found"
- The video might not be using BunnyCDN, or the embed is loaded dynamically
- Try increasing the wait time in the script

### Error during video download
- BunnyCDN's DRM system might have changed
- Check if you can still view videos in the browser

## Limitations and Ethical Considerations

- This script is intended for personal use to download content you have legitimate access to
- Respect copyright and terms of service of the websites you're accessing
- The script may stop working if BunnyCDN changes their embed or DRM system
- Performance depends on your internet connection and the website's responsiveness

## Customization

You can modify the script to:
- Adjust wait times for slow-loading websites
- Add additional video embed detection methods
- Change the naming scheme for downloaded files
- Implement retry logic for failed downloads

## Technical Details

The script uses:
- Selenium WebDriver for browser automation
- Requests library for HTTP interactions 
- yt-dlp for the actual video downloading
- MD5 hashing to comply with BunnyCDN's DRM protocol

---

*Note: Use this script responsibly and only for content you have legitimate access to download.*
