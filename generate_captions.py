"""
Generates an SRT subtitle file for the Demo 2 code walkthrough video.
Detects scene changes (new file opening in VS Code) and places the
narration text at each transition point.

Usage:
    python generate_captions.py "path/to/your/video.mp4" output.srt

Then import output.srt into CapCut (Import > Subtitles > SRT file).
"""

import sys
import cv2

# The 17 narration texts, IN ORDER, matching the walkthrough script
NARRATIONS = [
    "The project has two parts — a React frontend with Redux, and a Python FastAPI backend with LangGraph. Let me walk through the data flow from user input to form population.",

    "This is the heart of the AI pipeline — a LangGraph StateGraph. Each node is a distinct processing step. The entry point is input_router, which branches to extract_new or extract_correction. From there: merge state, classify, assess risk, check completeness, detect duplicates, suggest root cause, suggest CAPA, summarize, and finalize.",

    "This TypedDict is the shared state that flows through every node. Each node reads what it needs and writes back only its own slice. The graph wiring determines execution order.",

    "This is the conditional branch point. If the mode is correction, it routes to the correction extraction node. Otherwise, it routes to the new complaint extraction node.",

    "This node takes raw complaint text and calls Groq with a structured extraction prompt. It gets back field updates and confidence scores. It only writes extracted_updates — it never touches the form fields directly.",

    "The correction node is similar, but also receives the current form fields so the LLM knows what it's amending. Both nodes write only proposed updates — the actual merge happens next.",

    "The field schema tells the LLM exactly which keys to use. The rules enforce anti-hallucination — extract only what's in the text, don't invent values. The correction prompt returns only changed fields, or all fields if it's a completely different complaint.",

    "This node merges the AI's proposed updates into existing form fields. For corrections, it only overwrites fields the LLM explicitly returned. Unmentioned fields are preserved. This is the human-in-the-loop design.",

    "This node classifies the complaint — for example, Product Defect - Discoloration, or Foreign Matter Contamination. It uses the merged field state. If classification fails, it's non-fatal — the pipeline continues.",

    "Risk assessment uses the stronger model — gpt-oss-120b — because risk framing benefits from more reasoning. It generates severity, suggested next action, and the initial risk assessment. If the secondary model errors, it falls back to the primary.",

    "This is the Groq API wrapper. All nodes call this function with a system prompt, user prompt, and model name. The original gemma2-9b-it was decommissioned by Groq. gpt-oss-20b is the official replacement.",

    "This is the service layer — the bridge between the API and the graph. It creates a database record, calls run_complaint_graph, applies the result, logs audit entries, and returns a full ExtractionResponse. The correction function returns the same full shape — not just changed fields.",

    "The routes are intentionally thin. The process-text endpoint validates the request and delegates to the service layer. The chat endpoint does the same for corrections. No business logic lives here.",

    "The database uses SQLAlchemy with PostgreSQL. The Complaint model holds all form fields plus AI-generated fields. The AuditLog tracks every field change. The AIAssessment stores raw LLM output for each stage.",

    "These Pydantic schemas define the API response shape. ExtractionResponse is the full snapshot — fields, risk assessment, duplicates, CAPA, root cause. This is what the frontend receives.",

    "On the frontend, these functions make POST requests to the FastAPI endpoints. The Redux slice is the only place structured complaint state lives. applyExtraction merges the response into state — fields, risk, duplicates, CAPA. The same function is used by all three flows. The Copilot never writes to the form directly.",

    "To summarize: user input → Redux thunk → FastAPI route → service layer → LangGraph pipeline → Groq → full ExtractionResponse → applyExtraction → form updates. The form is never manually filled. Thank you.",
]

def format_timestamp(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

def detect_scene_changes(video_path, threshold=30.0, min_gap=2.0):
    """
    Detects scene changes by comparing consecutive frames.
    Returns a list of timestamps (in seconds) where the screen changed significantly.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ERROR: Could not open video: {video_path}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    print(f"Video: {video_path}")
    print(f"FPS: {fps:.1f}, Total frames: {total_frames}, Duration: {duration:.1f}s")

    # Sample every 0.5 seconds for speed
    sample_interval = max(1, int(fps * 0.5))

    prev_frame = None
    change_times = [0.0]  # Start caption at 0
    frame_idx = 0

    print("Detecting scene changes...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_interval == 0:
            # Downscale for speed
            small = cv2.resize(frame, (160, 90))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

            if prev_frame is not None:
                diff = cv2.absdiff(gray, prev_frame)
                score = diff.mean()

                timestamp = frame_idx / fps
                # Only register if enough time has passed since last change
                if score > threshold and (timestamp - change_times[-1]) >= min_gap:
                    change_times.append(timestamp)
                    print(f"  Scene change at {timestamp:.1f}s (score: {score:.1f})")

            prev_frame = gray

        frame_idx += 1

    cap.release()

    # Add end time
    change_times.append(duration)
    print(f"Detected {len(change_times) - 1} scene changes (including start).")
    return change_times, duration

def generate_srt(change_times, duration, output_path):
    """
    Generates an SRT file mapping each narration to a time segment.
    """
    num_captions = min(len(NARRATIONS), len(change_times) - 1)

    # If we detected fewer scene changes than narrations, distribute evenly
    if num_captions < len(NARRATIONS):
        print(f"WARNING: Detected {num_captions} scene changes but have {len(NARRATIONS)} narrations.")
        print("Some captions will be merged. Consider lowering the threshold.")
        # Merge remaining narrations into the last segment
        for i in range(num_captions, len(NARRATIONS)):
            NARRATIONS[num_captions - 1] += " " + NARRATIONS[i]

    lines = []
    subtitle_idx = 1

    for i in range(num_captions):
        start = change_times[i]
        # Each caption stays until the next scene change (or +8s max)
        end = change_times[i + 1] if i + 1 < len(change_times) else min(start + 8, duration)
        # Cap at 8 seconds so captions don't linger too long
        if end - start > 8:
            end = start + 8

        text = NARRATIONS[i]

        # Split long text into two lines for readability
        if len(text) > 80:
            mid = len(text) // 2
            # Find nearest space
            while mid < len(text) and text[mid] != ' ':
                mid += 1
            if mid < len(text):
                text = text[:mid].strip() + "\n" + text[mid:].strip()

        lines.append(str(subtitle_idx))
        lines.append(f"{format_timestamp(start)} --> {format_timestamp(end)}")
        lines.append(text)
        lines.append("")
        subtitle_idx += 1

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nSRT file generated: {output_path}")
    print(f"Total captions: {subtitle_idx - 1}")
    print(f"\nImport this SRT into CapCut:")
    print(f"  1. Open CapCut, import your video")
    print(f"  2. Click 'Import' > select the SRT file")
    print(f"  3. Or drag the SRT file directly onto the timeline")
    print(f"\nIf timing is off, adjust the threshold:")
    print(f"  python generate_captions.py video.mp4 output.srt 20  (lower = more sensitive)")
    print(f"  python generate_captions.py video.mp4 output.srt 40  (higher = less sensitive)")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_captions.py <video.mp4> <output.srt> [threshold]")
        print("  threshold: scene change sensitivity (default: 30, lower = more sensitive)")
        sys.exit(1)

    video_path = sys.argv[1]
    output_path = sys.argv[2]
    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 30.0

    change_times, duration = detect_scene_changes(video_path, threshold=threshold)
    generate_srt(change_times, duration, output_path)
