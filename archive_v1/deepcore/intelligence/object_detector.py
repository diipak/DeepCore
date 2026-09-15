from abc import ABC, abstractmethod
import re
from typing import List, Dict, Any, Optional

class BaseDetector(ABC):
    @abstractmethod
    def detect(self, text: str) -> List[Dict[str, Any]]:
        """Scan text and return detected objects."""
        pass


class YouTubeDetector(BaseDetector):
    def detect(self, text: str) -> List[Dict[str, Any]]:
        urls = re.findall(r'https?://[^\s()<>\[\]]+', text)
        detections = []
        for url in urls:
            while url and url[-1] in (".", ",", ")", "]", "}", "!", "?", ";", ":", "*", "_"):
                url = url[:-1]
            
            video_id = None
            # Standard watch URL: youtube.com/watch?v=...
            match = re.search(r'(?:youtube\.com/watch\?v=|youtube\.com/watch\?.*&v=)([a-zA-Z0-9_-]{11})(?![a-zA-Z0-9_-])', url)
            if match:
                video_id = match.group(1)
            else:
                # Short URL: youtu.be/...
                match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})(?![a-zA-Z0-9_-])', url)
                if match:
                    video_id = match.group(1)
                else:
                    # Embed URL: youtube.com/embed/...
                    match = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]{11})(?![a-zA-Z0-9_-])', url)
                    if match:
                        video_id = match.group(1)
                    else:
                        # Shorts URL: youtube.com/shorts/...
                        match = re.search(r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})(?![a-zA-Z0-9_-])', url)
                        if match:
                            video_id = match.group(1)
            
            if video_id:
                detections.append({
                    "type": "youtube",
                    "url": url,
                    "confidence": 1.0,
                    "meta": {
                        "video_id": video_id
                    }
                })
        return detections


class GitHubDetector(BaseDetector):
    def detect(self, text: str) -> List[Dict[str, Any]]:
        urls = re.findall(r'https?://[^\s()<>\[\]]+', text)
        detections = []
        for url in urls:
            while url and url[-1] in (".", ",", ")", "]", "}", "!", "?", ";", ":", "*", "_"):
                url = url[:-1]
                
            match = re.match(r'^https?://(?:www\.)?github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)', url)
            if match:
                user, repo = match.group(1), match.group(2)
                exclude_list = {
                    "features", "pulls", "issues", "marketplace", "explore", "trending",
                    "pricing", "security", "login", "signup", "about", "contact",
                    "careers", "press", "blog", "shop", "orgs", "settings", "notifications"
                }
                if user.lower() not in exclude_list:
                    detections.append({
                        "type": "github",
                        "url": f"https://github.com/{user}/{repo}",
                        "confidence": 1.0,
                        "meta": {
                            "user": user,
                            "repo": repo
                        }
                    })
        return detections


class WebDetector(BaseDetector):
    def detect(self, text: str) -> List[Dict[str, Any]]:
        urls = re.findall(r'https?://[^\s()<>\[\]]+', text)
        detections = []
        
        youtube_detector = YouTubeDetector()
        github_detector = GitHubDetector()
        
        for url in urls:
            while url and url[-1] in (".", ",", ")", "]", "}", "!", "?", ";", ":", "*", "_"):
                url = url[:-1]
                
            # Skip if matched by YouTube or GitHub detectors
            if youtube_detector.detect(url) or github_detector.detect(url):
                continue
                
            detections.append({
                "type": "web",
                "url": url,
                "confidence": 1.0
            })
        return detections


class ObjectDetector:
    def __init__(self):
        self.detectors = [
            YouTubeDetector(),
            GitHubDetector(),
            WebDetector()
        ]

    def detect_objects(self, text: str) -> List[Dict[str, Any]]:
        all_detections = []
        seen_urls = set()
        
        for detector in self.detectors:
            for item in detector.detect(text):
                url = item["url"]
                if url not in seen_urls:
                    seen_urls.add(url)
                    all_detections.append(item)
                    
        return all_detections
