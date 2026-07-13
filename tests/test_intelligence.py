import pytest
from deepcore.intelligence.object_detector import ObjectDetector, YouTubeDetector, GitHubDetector, WebDetector
from deepcore.core.concepts.service import is_valid_concept_candidate, is_technical_term

def test_youtube_detector():
    detector = YouTubeDetector()
    text = (
        "Check this watch link https://youtube.com/watch?v=dQw4w9WgXcQ. "
        "Also this short link https://youtu.be/dQw4w9WgXcQ?t=10, "
        "and a shorts URL https://youtube.com/shorts/dQw4w9WgXcQ."
    )
    detections = detector.detect(text)
    assert len(detections) == 3
    for det in detections:
        assert det["type"] == "youtube"
        assert det["meta"]["video_id"] == "dQw4w9WgXcQ"


def test_github_detector():
    detector = GitHubDetector()
    text = (
        "Repo link: https://github.com/user/repo-name "
        "Another: http://www.github.com/another-user/another-repo/blob/main/README.md "
        "Ignore this: https://github.com/features or https://github.com/settings"
    )
    detections = detector.detect(text)
    assert len(detections) == 2
    assert detections[0]["meta"]["user"] == "user"
    assert detections[0]["meta"]["repo"] == "repo-name"
    assert detections[1]["meta"]["user"] == "another-user"
    assert detections[1]["meta"]["repo"] == "another-repo"


def test_web_detector_exclusions():
    detector = WebDetector()
    text = (
        "Check https://google.com for info. "
        "Also https://github.com/user/repo (should be skipped). "
        "Also https://youtube.com/watch?v=dQw4w9WgXcQ (should be skipped)."
    )
    detections = detector.detect(text)
    assert len(detections) == 1
    assert detections[0]["type"] == "web"
    assert detections[0]["url"] == "https://google.com"


def test_object_detector_deduplication():
    detector = ObjectDetector()
    text = (
        "Link https://google.com. Same link https://google.com."
    )
    detections = detector.detect_objects(text)
    assert len(detections) == 1
    assert detections[0]["url"] == "https://google.com"


def test_concept_cleanup_validation():
    # Valid concepts
    assert is_valid_concept_candidate("Docker") is True
    assert is_valid_concept_candidate("Machine Learning") is True
    assert is_valid_concept_candidate("Tailscale") is True
    assert is_valid_concept_candidate("RAG") is True

    # Bad concepts
    assert is_valid_concept_candidate("abc123") is False
    assert is_valid_concept_candidate("5S8Z") is False
    assert is_valid_concept_candidate("VeU6gs") is False
    assert is_valid_concept_candidate("watch?v=") is False
    assert is_valid_concept_candidate("https://youtube.com") is False
    assert is_valid_concept_candidate("a") is False  # below length 3

    # Technical terms
    assert is_technical_term("GPT4") is True
    assert is_technical_term("React19") is True
    assert is_technical_term("2FA") is True
    assert is_technical_term("abc123") is False
    assert is_technical_term("5S8Z") is False
