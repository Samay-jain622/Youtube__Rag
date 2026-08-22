"""Download YouTube subtitles and turn them into overlapping documents."""

import json

import yt_dlp
from langchain_core.documents import Document

from src.utils.config import settings


def fetch_and_chunk(video_id: str) -> list[Document]:
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    subtitle_file = settings.knowledge_base_dir / f"{video_id}.en.json3"

    try:
        if not subtitle_file.exists():
            options = {
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en"],
                "subtitlesformat": "json3",
                "outtmpl": str(
                    settings.knowledge_base_dir / f"{video_id}.%(ext)s"
                ),
                "quiet": True,
            }
            with yt_dlp.YoutubeDL(options) as downloader:
                downloader.download([video_url])

        if not subtitle_file.exists():
            raise ValueError("Subtitles not found for this video")

        with subtitle_file.open("r", encoding="utf-8") as subtitle_stream:
            payload = json.load(subtitle_stream)

        segments = []
        for event in payload.get("events", []):
            if "segs" not in event:
                continue
            segments.append(
                {
                    "text": "".join(part["utf8"] for part in event["segs"]).strip(),
                    "start": event.get("tStartMs", 0) / 1000,
                    "duration": event.get("dDurationMs", 0) / 1000,
                }
            )

        if not segments:
            raise ValueError("Transcript is empty")

        documents = []
        window_size, overlap_size = 9, 3
        for index in range(0, len(segments), window_size - overlap_size):
            window = segments[index : index + window_size]
            documents.append(
                Document(
                    page_content=" ".join(segment["text"] for segment in window),
                    metadata={
                        "start": float(window[0]["start"]),
                        "duration": float(
                            sum(segment["duration"] for segment in window)
                        ),
                        "video_id": video_id,
                    },
                )
            )
        return documents
    except Exception as exc:
        message = str(exc)
        if "Private video" in message:
            raise ValueError("This video is private") from exc
        if "Video unavailable" in message:
            raise ValueError("Video does not exist") from exc
        raise ValueError(f"Failed to process video: {message}") from exc
