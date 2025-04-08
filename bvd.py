import re
import sys
import time
import argparse
from urllib.parse import urlparse
from hashlib import md5
from html import unescape
from random import random

import requests
import yt_dlp
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class BunnyVideoDRM:
    """Handles the BunnyCDN video DRM and download functionality"""
    user_agent = {
        "sec-ch-ua": '"Google Chrome";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
    }

    def __init__(self, referer, embed_url, name="", path=""):
        self.session = requests.Session()
        self.session.headers.update(self.user_agent)

        self.referer = referer
        self.embed_url = embed_url
        self.guid = urlparse(embed_url).path.split("/")[-1]
        self.path = path if path else "."

        # Set up headers for different request types
        self.headers = {
            "embed": {
                "authority": "iframe.mediadelivery.net",
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "cache-control": "no-cache",
                "pragma": "no-cache",
                "referer": referer,
                "sec-fetch-dest": "iframe",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "cross-site",
                "upgrade-insecure-requests": "1",
            },
            "ping|activate": {
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "cache-control": "no-cache",
                "origin": "https://iframe.mediadelivery.net",
                "pragma": "no-cache",
                "referer": "https://iframe.mediadelivery.net/",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
            },
            "playlist": {
                "authority": "iframe.mediadelivery.net",
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "cache-control": "no-cache",
                "pragma": "no-cache",
                "referer": embed_url,
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
            },
        }

        # Initialize video metadata
        self._fetch_video_metadata()

        # Set file name
        if name:
            self.file_name = f"{name}.mp4"
        else:
            # Extract name from page title if available
            try:
                file_name_unescaped = re.search(r'og:title" content="(.*?)"', self.embed_page).group(1)
                file_name_escaped = unescape(file_name_unescaped)
                self.file_name = re.sub(r"\.[^.]*$.*", ".mp4", file_name_escaped)
                if not self.file_name.endswith(".mp4"):
                    self.file_name += ".mp4"
            except:
                # Use a fallback name based on GUID
                self.file_name = f"video_{self.guid}.mp4"

    def _fetch_video_metadata(self):
        """Fetch video metadata from the embed page"""
        try:
            # Get the embed page
            embed_response = self.session.get(self.embed_url, headers=self.headers["embed"])
            self.embed_page = embed_response.text

            # Extract server ID
            server_match = re.search(r"https://video-(.*?)\.mediadelivery\.net", self.embed_page)
            if not server_match:
                raise Exception("Failed to extract server ID from embed page")
            self.server_id = server_match.group(1)

            # Update headers with server ID
            self.headers["ping|activate"].update({"authority": f"video-{self.server_id}.mediadelivery.net"})

            # Extract context ID and secret
            context_match = re.search(r'contextId=(.*?)&secret=(.*?)"', self.embed_page)
            if not context_match:
                raise Exception("Failed to extract context ID and secret from embed page")
            self.context_id, self.secret = context_match.group(1), context_match.group(2)

        except Exception as e:
            print(f"Error fetching video metadata: {e}")
            raise

    def prepare_dl(self):
        """Prepare video for downloading by activating the DRM and getting video metadata"""
        try:
            # Function to ping the server
            def ping(time_val, paused, res):  # Changed parameter name from time to time_val
                md5_hash = md5(f"{self.secret}_{self.context_id}_{time_val}_{paused}_{res}".encode("utf8")).hexdigest()
                params = {"hash": md5_hash, "time": time_val, "paused": paused, "chosen_res": res}
                self.session.get(
                    f"https://video-{self.server_id}.mediadelivery.net/.drm/{self.context_id}/ping",
                    params=params, headers=self.headers["ping|activate"]
                )

            # Function to activate the video
            def activate():
                self.session.get(
                    f"https://video-{self.server_id}.mediadelivery.net/.drm/{self.context_id}/activate",
                    headers=self.headers["ping|activate"]
                )

            # Function to get the main playlist
            def main_playlist():
                params = {"contextId": self.context_id, "secret": self.secret}
                response = self.session.get(
                    f"https://iframe.mediadelivery.net/{self.guid}/playlist.drm",
                    params=params, headers=self.headers["playlist"]
                )
                resolutions = re.findall(r"\s*(.*?)\s*/video\.drm", response.text)[::-1]
                if not resolutions:
                    raise Exception("No resolutions found in playlist")
                return resolutions[0]  # Return highest resolution

            # Function to get the video playlist
            def video_playlist(resolution):
                params = {"contextId": self.context_id}
                self.session.get(
                    f"https://iframe.mediadelivery.net/{self.guid}/{resolution}/video.drm",
                    params=params, headers=self.headers["playlist"]
                )

            # Execute the DRM preparation sequence
            ping(time_val=0, paused="true", res="0")  # Changed time to time_val
            activate()
            resolution = main_playlist()
            video_playlist(resolution)

            # Simulate video playback to keep the DRM happy
            for i in range(0, 29, 4):
                ping(time_val=i + round(random(), 6), paused="false", res=resolution.split("x")[-1])  # Changed time to time_val

            return resolution

        except Exception as e:
            print(f"Error preparing download: {e}")
            raise

    def download(self):
        """Download the video using yt-dlp"""
        try:
            print(f"Preparing video for download...")
            resolution = self.prepare_dl()

            url = f"https://iframe.mediadelivery.net/{self.guid}/{resolution}/video.drm?contextId={self.context_id}"
            print(f"Download URL: {url}")

            ydl_opts = {
                "http_headers": {
                    "Referer": self.embed_url,
                    "User-Agent": self.user_agent["user-agent"],
                },
                "concurrent_fragment_downloads": 10,
                "nocheckcertificate": True,
                "outtmpl": self.file_name,
                "restrictfilenames": True,
                "windowsfilenames": True,
                "nopart": True,
                "paths": {
                    "home": self.path,
                    "temp": f".{self.file_name}",
                },
                "retries": 5,
                "extractor_retries": 5,
                "fragment_retries": 10,
                "skip_unavailable_fragments": False,
                "no_warnings": True,
            }

            print(f"Starting download: {self.file_name}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            print(f"Successfully downloaded: {self.file_name}")
            return True

        except Exception as e:
            print(f"Error downloading video: {e}")
            return False
        finally:
            self.session.close()

class ChromeBrowser:
    """Manages interaction with existing Chrome instance"""

    def __init__(self, debug_port=9222):
        """Connect to existing Chrome instance with remote debugging enabled"""
        try:
            options = Options()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")

            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 15)

            # Verify connection
            current_url = self.driver.current_url
            print(f"Successfully connected to Chrome on port {debug_port}")
            print(f"Current page: {current_url}")

            # Save original window handle
            self.original_handle = self.driver.current_window_handle
            print(f"Original window handle: {self.original_handle}")

        except Exception as e:
            print(f"Failed to connect to Chrome on port {debug_port}")
            print(f"Ensure Chrome is running with: --remote-debugging-port={debug_port}")
            print(f"Error details: {e}")
            sys.exit(1)

    def open_new_tab(self, url=None):
        """Open a new tab and optionally navigate to a URL"""
        try:
            # Record current handles
            original_handles = self.driver.window_handles

            # Open new tab
            self.driver.execute_script("window.open('about:blank');")
            time.sleep(1)  # Give browser time to open new tab

            # Get new handles
            new_handles = self.driver.window_handles
            new_tabs = [h for h in new_handles if h not in original_handles]

            if not new_tabs:
                print("Warning: Failed to create new tab, using current tab")
                new_tab = self.driver.current_window_handle
            else:
                new_tab = new_tabs[0]
                self.driver.switch_to.window(new_tab)

            # Navigate to URL if provided
            if url:
                print(f"Navigating to: {url}")
                self.driver.get(url)
                time.sleep(2)  # Wait for initial page load

            return new_tab
        except Exception as e:
            print(f"Error opening new tab: {e}")
            # Try to get back to original tab
            self._ensure_on_original_tab()
            return None

    def close_tab(self, tab_handle=None):
        """Close the specified tab or current tab if none specified"""
        if not tab_handle:
            tab_handle = self.driver.current_window_handle

        try:
            # Don't close the original tab
            if tab_handle == self.original_handle:
                print("Not closing original tab")
                return

            # Close tab and switch back to original
            self.driver.switch_to.window(tab_handle)
            self.driver.close()
            self.driver.switch_to.window(self.original_handle)
        except Exception as e:
            print(f"Error closing tab: {e}")
            self._ensure_on_original_tab()

    def _ensure_on_original_tab(self):
        """Make sure we're on the original tab"""
        try:
            # Check if original handle still exists
            handles = self.driver.window_handles
            if self.original_handle in handles:
                self.driver.switch_to.window(self.original_handle)
            else:
                # If original is gone, use the first available tab
                self.driver.switch_to.window(handles[0])
                self.original_handle = handles[0]
        except Exception as e:
            print(f"Error switching to original tab: {e}")

    def get_page_links(self, url, base_url):
        """Load a page and extract all links containing the base_url"""
        tab_handle = None
        try:
            # Open new tab for this operation
            tab_handle = self.open_new_tab(url)
            if not tab_handle:
                return []

            print(f"Extracting links from {url} containing '{base_url}'...")

            # Wait for page to load properly
            time.sleep(3)

            # Find all links
            links = []
            elements = self.driver.find_elements(By.TAG_NAME, "a")

            for element in elements:
                try:
                    href = element.get_attribute("href")
                    if href and base_url in href:
                        links.append(href)
                except Exception:
                    continue

            unique_links = list(set(links))
            print(f"Found {len(unique_links)} unique links containing '{base_url}'")
            return unique_links

        except Exception as e:
            print(f"Error extracting links from {url}: {e}")
            return []
        finally:
            if tab_handle:
                self.close_tab(tab_handle)

    def find_bunny_embed_url(self, page_url):
        """Load a page and find the BunnyCDN video embed URL"""
        tab_handle = None
        try:
            # Open new tab for this operation
            tab_handle = self.open_new_tab(page_url)
            if not tab_handle:
                return None

            print(f"Looking for video embed in {page_url}...")

            # Wait for page to load
            time.sleep(3)

            # Try multiple methods to find the embed URL
            embed_url = None

            # Method 1: Look for iframes
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    src = iframe.get_attribute("src")
                    if src and "iframe.mediadelivery.net/embed" in src:
                        # Get base URL without query parameters
                        embed_url = src.split('?')[0]
                        print(f"Found embed URL in iframe: {embed_url}")
                        break
            except Exception as e:
                print(f"Error finding iframe: {e}")

            # Method 2: Check page source
            if not embed_url:
                try:
                    page_source = self.driver.page_source
                    embed_match = re.search(r'(https://iframe\.mediadelivery\.net/embed/[^"\'?]+)', page_source)
                    if embed_match:
                        embed_url = embed_match.group(1)
                        print(f"Found embed URL in page source: {embed_url}")
                except Exception as e:
                    print(f"Error searching page source: {e}")

            # Method 3: Check for data attributes
            if not embed_url:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-src], [data-video-src]")
                    for element in elements:
                        data_src = element.get_attribute("data-src") or element.get_attribute("data-video-src")
                        if data_src and "iframe.mediadelivery.net/embed" in data_src:
                            embed_url = data_src.split('?')[0]
                            print(f"Found embed URL in data attribute: {embed_url}")
                            break
                except Exception as e:
                    print(f"Error checking data attributes: {e}")

            if not embed_url:
                print(f"No BunnyCDN embed found in {page_url}")

            return embed_url

        except Exception as e:
            print(f"Error finding embed URL in {page_url}: {e}")
            return None
        finally:
            if tab_handle:
                self.close_tab(tab_handle)

    def cleanup(self):
        """Clean up browser resources without closing the original window"""
        try:
            # Get all window handles
            handles = self.driver.window_handles

            # Close all tabs except the original
            for handle in handles:
                if handle != self.original_handle:
                    self.driver.switch_to.window(handle)
                    self.driver.close()

            # Switch back to original tab
            self.driver.switch_to.window(self.original_handle)
            print("Browser cleanup complete, original tab preserved")
        except Exception as e:
            print(f"Error during browser cleanup: {e}")
            self._ensure_on_original_tab()

def download_videos(main_url, base_url, output_path="", debug_port=9222):
    """Main function to extract links and download videos"""
    browser = None
    try:
        # Connect to Chrome
        browser = ChromeBrowser(debug_port=debug_port)

        # Extract all links from main page
        page_links = browser.get_page_links(main_url, base_url)

        if not page_links:
            print("No links found matching the base URL. Please check your parameters.")
            return

        successful_downloads = 0
        failed_downloads = 0

        # Process each link
        for i, page_url in enumerate(page_links, 1):
            print(f"\n[{i}/{len(page_links)}] Processing: {page_url}")

            # Find video embed URL
            embed_url = browser.find_bunny_embed_url(page_url)
            if not embed_url:
                print(f"Skipping {page_url} - no embed URL found")
                failed_downloads += 1
                continue

            # Create a filename from the URL
            path_parts = urlparse(page_url).path.strip('/').split('/')
            name = path_parts[-1] if path_parts else f"video_{i}"
            name = name.replace('-', '_').replace('.', '_')  # Clean up filename

            # Download the video
            try:
                video = BunnyVideoDRM(
                    referer=page_url,
                    embed_url=embed_url,
                    name=name,
                    path=output_path
                )

                if video.download():
                    successful_downloads += 1
                else:
                    failed_downloads += 1

            except Exception as e:
                print(f"Error downloading video from {page_url}: {str(e)}")
                failed_downloads += 1

        # Show summary
        print(f"\nDownload summary:")
        print(f"Total links found: {len(page_links)}")
        print(f"Successfully downloaded: {successful_downloads}")
        print(f"Failed: {failed_downloads}")

    except Exception as e:
        print(f"Error in download process: {e}")
    finally:
        if browser:
            browser.cleanup()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download BunnyCDN videos from multiple pages")
    parser.add_argument("main_url", help="URL of the webpage containing links")
    parser.add_argument("base_url", help="Base URL to filter links by")
    parser.add_argument("-o", "--output", help="Output directory for downloaded videos", default=".")
    parser.add_argument("-p", "--port", type=int, help="Chrome debugging port (default: 9222)", default=9222)

    args = parser.parse_args()

    print("BunnyCDN Video Downloader")
    print(f"Main URL: {args.main_url}")
    print(f"Base URL filter: {args.base_url}")
    print(f"Output directory: {args.output}")
    print(f"Chrome debugging port: {args.port}")
    print("-" * 50)

    download_videos(
        args.main_url,
        args.base_url,
        args.output,
        debug_port=args.port
    )
