"""CLI for Seedance 2.0 video generation."""

import argparse
import json
import sys

from servers.ai_film import schemas, seedance, store


def _output(data: dict | list, pretty: bool = False) -> None:
    indent = 2 if pretty else None
    print(json.dumps(data, indent=indent, default=str, ensure_ascii=False))


def _task_to_dict(task: schemas.VideoTask) -> dict:
    return task.model_dump(mode="json")


def cmd_generate(args: argparse.Namespace) -> None:
    image_urls = args.image_url or []
    video_urls = args.video_url or []
    audio_urls = args.audio_url or []

    try:
        provider_task_id = seedance.create_video_task(
            args.prompt,
            image_urls=image_urls,
            video_urls=video_urls,
            audio_urls=audio_urls,
            ratio=args.ratio,
            duration=args.duration,
            generate_audio=args.audio,
            watermark=args.watermark,
        )
    except RuntimeError as e:
        _output({"error": str(e)})
        sys.exit(1)

    task = schemas.VideoTask(
        id=store.new_task_id(),
        provider_task_id=provider_task_id,
        prompt=args.prompt,
        image_urls=image_urls,
        video_urls=video_urls,
        audio_urls=audio_urls,
        ratio=args.ratio,
        duration=args.duration,
        generate_audio=args.audio,
        watermark=args.watermark,
    )
    store.save_video_task(task)
    _output(
        {"id": task.id, "provider_task_id": provider_task_id, "status": task.status.value},
        pretty=args.pretty,
    )


def _try_download(task_id: str, result: dict, updates: dict) -> None:
    """Download video locally if succeeded and video_url present."""
    if result.get("status") == "succeeded" and result.get("video_url"):
        try:
            local_path = seedance.download_video(result["video_url"], task_id)
            updates["local_path"] = local_path
            print(f"Video saved to: {local_path}", file=sys.stderr)
        except Exception as e:
            print(f"Download failed: {e}", file=sys.stderr)


def cmd_status(args: argparse.Namespace) -> None:
    task = store.resolve_task(args.task_id)
    if task is None:
        _output({"error": f"Task not found: {args.task_id}"})
        sys.exit(1)

    try:
        result = seedance.get_task_status(task.provider_task_id)
    except RuntimeError as e:
        _output({"error": str(e)})
        sys.exit(1)

    updates: dict = {"status": result["status"]}
    if result.get("video_url"):
        updates["video_url"] = result["video_url"]
    if result.get("error"):
        updates["error"] = result["error"]
    if not task.local_path:
        _try_download(task.id, result, updates)

    updated = store.update_video_task(task.id, **updates)
    _output(_task_to_dict(updated) if updated else {"error": "Failed to update task"}, pretty=args.pretty)


def cmd_wait(args: argparse.Namespace) -> None:
    task = store.resolve_task(args.task_id)
    if task is None:
        _output({"error": f"Task not found: {args.task_id}"})
        sys.exit(1)

    try:
        result = seedance.poll_video_task(task.provider_task_id)
    except RuntimeError as e:
        _output({"error": str(e)})
        sys.exit(1)

    updates: dict = {"status": result["status"]}
    if result.get("video_url"):
        updates["video_url"] = result["video_url"]
    if result.get("error"):
        updates["error"] = result["error"]
    _try_download(task.id, result, updates)

    updated = store.update_video_task(task.id, **updates)
    _output(_task_to_dict(updated) if updated else {"error": "Failed to update task"}, pretty=args.pretty)


def cmd_list(args: argparse.Namespace) -> None:
    tasks = store.list_video_tasks(status=args.status)
    _output([_task_to_dict(t) for t in tasks], pretty=args.pretty)


def main() -> None:
    parser = argparse.ArgumentParser(prog="tyrannus-ai-film", description="Seedance 2.0 video generation CLI")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    sub = parser.add_subparsers(dest="command", required=True)

    # generate
    gen = sub.add_parser("generate", help="Submit a video generation task")
    gen.add_argument("--prompt", required=True, help="Video prompt text")
    gen.add_argument("--image-url", action="append", default=None, help="Reference image URL (repeatable)")
    gen.add_argument("--video-url", action="append", default=None, help="Reference video URL (repeatable)")
    gen.add_argument("--audio-url", action="append", default=None, help="Reference audio URL (repeatable)")
    gen.add_argument("--ratio", default="16:9", help="Aspect ratio (default: 16:9)")
    gen.add_argument("--duration", type=int, default=5, help="Duration in seconds (default: 5)")
    gen.add_argument("--audio", action="store_true", help="Generate audio")
    gen.add_argument("--watermark", action="store_true", help="Add watermark")

    # status
    st = sub.add_parser("status", help="Check task status (one-shot)")
    st.add_argument("task_id", help="Local task ID or provider task ID")

    # wait
    wt = sub.add_parser("wait", help="Wait for task completion (blocking poll)")
    wt.add_argument("task_id", help="Local task ID or provider task ID")

    # list
    ls = sub.add_parser("list", help="List video tasks")
    ls.add_argument("--status", default=None, choices=["queued", "running", "succeeded", "failed", "timeout"],
                    help="Filter by status")

    args = parser.parse_args()
    {
        "generate": cmd_generate,
        "status": cmd_status,
        "wait": cmd_wait,
        "list": cmd_list,
    }[args.command](args)


if __name__ == "__main__":
    main()
