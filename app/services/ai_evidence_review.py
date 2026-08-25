"""
AI-assisted evidence review.

Reads an uploaded evidence file (PDF or image) alongside the control it was
mapped to, and asks Claude whether the file actually demonstrates the control
is satisfied. Returns a suggested verdict + confidence + rationale for a
human reviewer to confirm — it never sets Evidence.status itself.

Inert until ANTHROPIC_API_KEY is set: review_evidence() returns None
immediately if no credential is configured, so the upload/review flow is
unaffected until this is turned on. See MIGRC-Compliance-AI-Setup notes in
the project (or the seed script comments) for how to enable it.
"""
import os
import base64
import logging

logger = logging.getLogger(__name__)

# Only these are passed to Claude today - it needs a document/image content
# block, and Anthropic's API accepts PDFs and images that way. Office docs
# (doc/docx/xlsx/csv) would need text extraction first; not implemented yet.
SUPPORTED_MEDIA = {
    'pdf': ('document', 'application/pdf'),
    'png': ('image', 'image/png'),
    'jpg': ('image', 'image/jpeg'),
    'jpeg': ('image', 'image/jpeg'),
}

REVIEW_TOOL = {
    "name": "submit_evidence_review",
    "description": "Report whether the uploaded evidence file demonstrates that the compliance control is satisfied.",
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["Approved", "Rejected", "Needs Human Review"],
                "description": "Approved if the file clearly satisfies the control's evidence requirement, "
                               "Rejected if it clearly does not, Needs Human Review if it's ambiguous or the "
                               "file isn't the kind of evidence the control calls for.",
            },
            "confidence": {
                "type": "number",
                "description": "Confidence in this verdict, from 0.0 to 1.0.",
            },
            "rationale": {
                "type": "string",
                "description": "1-3 sentences citing specifically what the evidence does or doesn't show.",
            },
        },
        "required": ["status", "confidence", "rationale"],
        "additionalProperties": False,
    },
    "strict": True,
}


def _client():
    if not os.environ.get('ANTHROPIC_API_KEY'):
        return None
    import anthropic
    return anthropic.Anthropic()


def review_evidence(evidence, control, upload_folder):
    """
    Returns {"status": ..., "confidence": ..., "rationale": ...} or None.

    None means "no suggestion" - either AI review isn't configured, the file
    type isn't reviewable yet, or the API call failed. Callers should treat
    None as a no-op, not an error.
    """
    client = _client()
    if client is None:
        return None

    ext = (evidence.file_type or '').lower()
    if ext not in SUPPORTED_MEDIA or not evidence.file_path:
        return None

    file_path = os.path.join(upload_folder, evidence.file_path)
    if not os.path.exists(file_path):
        return None

    block_type, media_type = SUPPORTED_MEDIA[ext]
    with open(file_path, 'rb') as f:
        data = base64.standard_b64encode(f.read()).decode('utf-8')

    prompt = (
        f"Control {control.code}: {control.title}\n"
        f"Requirement: {control.description or 'No additional description provided.'}\n"
        f"Evidence requirement: {control.evidence_requirement or 'Not specified.'}\n\n"
        f"Evidence title: {evidence.title}\n"
        f"Evidence description: {evidence.description or 'None provided.'}\n\n"
        "Review the attached file against the control's requirement above. "
        "Call submit_evidence_review with your verdict."
    )

    try:
        response = client.messages.create(
            model="claude-opus-5",
            max_tokens=1024,
            tools=[REVIEW_TOOL],
            tool_choice={"type": "tool", "name": "submit_evidence_review"},
            messages=[{
                "role": "user",
                "content": [
                    {"type": block_type, "source": {"type": "base64", "media_type": media_type, "data": data}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
    except Exception:
        logger.exception("AI evidence review call failed for evidence_id=%s", evidence.id)
        return None

    if response.stop_reason == "refusal":
        logger.warning("AI evidence review refused for evidence_id=%s", evidence.id)
        return None

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_evidence_review":
            return block.input
    return None
