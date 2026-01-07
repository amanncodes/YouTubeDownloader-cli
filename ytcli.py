import json
import sys
import threading
from pathlib import Path
from typing import List
from threading import Lock

import typer
from pytubefix import YouTube

app = typer.Typer(
    help="YouTubeDownloader-cli – download YouTube videos via JSON file or direct URL"
)

# ==========================================================
# GLOBALS
# ==========================================================
_progress_lock = Lock()


# ==========================================================
# TEXT SANITIZATION (WINDOWS SAFE)
# ==========================================================
def safe_text(text: str) -> str:
    """
    Convert text to ASCII-safe output for Windows terminals and filesystems.
    Unsupported characters are replaced with '?'.
    """
    return text.encode("ascii", errors="replace").decode("ascii")


# ==========================================================
# PROGRESS CALLBACK (ASCII ONLY)
# ==========================================================
def progress_callback(stream, chunk, bytes_remaining):
    with _progress_lock:
        total = stream.filesize
        if not total:
            return

        downloaded = total - bytes_remaining
        percent = (downloaded / total) * 100

        sys.stdout.write(
            f"\rDownloading: {percent:5.1f}% "
            f"({downloaded // 1024 // 1024}MB / {total // 1024 // 1024}MB)"
        )
        sys.stdout.flush()


# ==========================================================
# DOWNLOAD SINGLE VIDEO (HARDENED)
# ==========================================================
def download_video(url: str, output_dir: Path):
    print("\n> Initializing video")

    yt = YouTube(url, on_progress_callback=progress_callback)

    # Fail fast on live / upcoming streams
    if yt.vid_info.get("videoDetails", {}).get("isLive"):
        raise RuntimeError("Live or upcoming video")

    safe_title = safe_text(yt.title)
    print("> Title:", safe_title)

    stream = yt.streams.filter(
        progressive=True, file_extension="mp4"
    ).get_highest_resolution()

    if not stream:
        raise RuntimeError("No progressive MP4 stream available")

    output_dir.mkdir(parents=True, exist_ok=True)

    result = {}
    error = {}

    def _download():
        try:
            safe_filename = safe_title.replace(" ", "_")
            result["path"] = stream.download(
                output_dir,
                filename=safe_filename,
            )
        except Exception as e:
            error["err"] = e

    t = threading.Thread(target=_download, daemon=True)
    t.start()
    t.join(timeout=45)

    if t.is_alive():
        raise TimeoutError("Download stalled (no data received)")

    if error:
        raise error["err"]

    print("\n[OK] Download completed")
    print("Saved to:", Path(result["path"]).resolve())


# ==========================================================
# INPUT RESOLUTION
# ==========================================================
def resolve_input(arg: str) -> List[str]:
    """
    If arg is a file path, treat it as JSON input.
    Otherwise, treat arg as a single YouTube video URL.
    """
    path = Path(arg)

    # JSON file input
    if path.exists() and path.is_file():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "videos" not in data or not isinstance(data["videos"], list):
            raise ValueError("JSON file must contain a 'videos' list")

        return data["videos"]

    # Guard against playlist URLs
    if "playlist?list=" in arg:
        raise ValueError("Playlist URLs are not supported. Provide a video URL.")

    return [arg]


# ==========================================================
# CLI ENTRYPOINT
# ==========================================================
@app.command()
def main(
    input_arg: str = typer.Argument(
        ...,
        help="Path to JSON file or a single YouTube video URL",
    ),
    output: Path = typer.Option(
        Path("downloads"),
        "--output",
        "-o",
        help="Download directory",
    ),
):
    print("\n=== ytcli started ===")

    try:
        videos = resolve_input(input_arg)
    except Exception as e:
        print("\n[ERROR] Invalid input")
        print(e)
        raise typer.Exit(code=1)

    print("> Videos to process:", len(videos))
    print("> Output directory:", output.resolve())

    skipped = []

    for idx, url in enumerate(videos, start=1):
        print(f"\n[{idx}/{len(videos)}] Processing")

        try:
            download_video(url, output)
        except Exception as e:
            print("\n[WARN] Skipped:", e)
            skipped.append(f"{url} :: {e}")

    # SUMMARY
    print("\n=== SUMMARY ===")
    print("[OK] Downloaded:", len(videos) - len(skipped))
    print("[WARN] Skipped:", len(skipped))

    if skipped:
        skipped_file = output / "skipped.txt"
        with open(skipped_file, "w", encoding="utf-8") as f:
            for line in skipped:
                f.write(line + "\n")

        print("Skipped list saved to:", skipped_file.resolve())

    print("\n=== ytcli finished ===")


if __name__ == "__main__":
    app()
