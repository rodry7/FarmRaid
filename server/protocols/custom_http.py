import json
import logging
import re

import httpx

from protocols.base import BaseProtocol

log = logging.getLogger(__name__)

TIMEOUT = 30


class CustomHTTPProtocol(BaseProtocol):
    name = "custom_http"
    display_name = "Custom HTTP"
    params_schema = {
        "url": {"type": "string", "label": "Submission URL"},
        "method": {
            "type": "string",
            "label": "HTTP Method",
            "default": "POST",
            "options": ["POST", "PUT", "GET"],
        },
        "body_template": {
            "type": "textarea",
            "label": "Request Body Template",
            "placeholder": '["flag1", "flag2"]',
            "description": (
                "Use {flags} as a placeholder. "
                "It will be replaced with a JSON array of flags, "
                "or with newline-separated flags if the template is not JSON."
            ),
        },
        "headers": {
            "type": "textarea",
            "label": "Headers (JSON object)",
            "placeholder": '{"Authorization": "Bearer TOKEN", "Content-Type": "application/json"}',
        },
        "accept_regex": {
            "type": "string",
            "label": "Accepted Response Regex",
            "placeholder": "accepted|correct",
        },
        "reject_regex": {
            "type": "string",
            "label": "Rejected Response Regex",
            "placeholder": "invalid|wrong|denied",
        },
    }

    async def submit(self, flags: list[str]) -> list[tuple[str, str, str]]:
        url: str = self.params.get("url", "")
        method: str = self.params.get("method", "POST").upper()
        body_template: str = self.params.get("body_template", "{flags}")
        raw_headers: str = self.params.get("headers", "{}")
        accept_pattern: str = self.params.get("accept_regex", "")
        reject_pattern: str = self.params.get("reject_regex", "")

        # Build headers
        try:
            headers: dict = json.loads(raw_headers) if raw_headers.strip() else {}
        except json.JSONDecodeError:
            headers = {}

        # Build body — replace {flags} with JSON array representation
        flags_json = json.dumps(flags)
        flags_newline = "\n".join(flags)

        # Try JSON substitution first; fall back to plain newline substitution.
        if "{flags}" in body_template:
            body_str = body_template.replace("{flags}", flags_json)
            try:
                json.loads(body_str)
                body_bytes = body_str.encode()
                if "Content-Type" not in headers:
                    headers["Content-Type"] = "application/json"
            except json.JSONDecodeError:
                body_bytes = body_template.replace("{flags}", flags_newline).encode()
        else:
            body_bytes = (
                body_template.encode() if body_template else flags_json.encode()
            )

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.request(
                    method, url, content=body_bytes, headers=headers
                )
                response_text = resp.text
        except Exception as exc:
            log.error("Custom HTTP submit failed: %s", exc)
            return [(f, "error", str(exc)) for f in flags]

        # Determine per-flag status from response text using regex.
        status = self._classify_response(response_text, accept_pattern, reject_pattern)

        # Return same status for all flags — custom protocol is inherently batch.
        return [(f, status, response_text[:200]) for f in flags]

    def _classify_response(self, text: str, accept_re: str, reject_re: str) -> str:
        if accept_re:
            try:
                if re.search(accept_re, text, re.IGNORECASE):
                    return "accepted"
            except re.error:
                pass
        if reject_re:
            try:
                if re.search(reject_re, text, re.IGNORECASE):
                    return "rejected"
            except re.error:
                pass
        return self.parse_verdict(text)
