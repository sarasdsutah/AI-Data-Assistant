from __future__ import annotations

import html
import json
import os
import tempfile
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote_plus, urlparse

from product_insights_assistant.analysis import generate_insights
from product_insights_assistant.data import load_csv_rows, preview_csv, summarize_csv


DEFAULT_QUESTION = "Based on this dataset and the business context, what should we do next?"


def render_page(
    *,
    result: dict[str, object] | None = None,
    error: str = "",
    question: str = DEFAULT_QUESTION,
    business_context: str = "",
    model: str = "",
    dataset_name: str = "",
    dataset_preview: str = "",
    dataset_summary: dict[str, object] | None = None,
) -> str:
    analysis_html = ""
    if result:
        analysis = result.get("analysis", {})
        analysis_html = f"""
        <section class="panel output">
          <h2>Analysis Output</h2>
          <div class="meta">Mode: <strong>{html.escape(str(result.get("mode", "unknown")))}</strong></div>
          <pre>{html.escape(json.dumps(analysis, indent=2))}</pre>
        </section>
        """

    preview_html = ""
    if dataset_preview or dataset_summary:
        preview_html = f"""
        <section class="panel preview">
          <h2>Dataset Preview</h2>
          <div class="meta">{html.escape(dataset_name or "Uploaded dataset")}</div>
          <pre>{html.escape(dataset_preview or "No preview available.")}</pre>
          <h3>Summary</h3>
          <pre>{html.escape(json.dumps(dataset_summary or {}, indent=2))}</pre>
        </section>
        """

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Product Insights Assistant</title>
  <style>
    :root {{
      --bg: #f3efe6;
      --card: rgba(255,255,255,0.82);
      --ink: #1d2a38;
      --accent: #b44c2f;
      --accent-2: #1f6b5d;
      --line: rgba(29,42,56,0.14);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Iowan Old Style", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(180,76,47,0.18), transparent 30%),
        radial-gradient(circle at bottom right, rgba(31,107,93,0.18), transparent 32%),
        linear-gradient(180deg, #f7f2e8 0%, var(--bg) 100%);
    }}
    .shell {{
      width: min(1180px, calc(100vw - 32px));
      margin: 24px auto 40px;
    }}
    .hero {{
      padding: 28px 28px 18px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(2rem, 5vw, 3.6rem);
      line-height: 0.95;
      letter-spacing: -0.04em;
    }}
    .sub {{
      max-width: 720px;
      margin: 0;
      font-size: 1.05rem;
      line-height: 1.5;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1.05fr 0.95fr;
      gap: 18px;
      align-items: start;
    }}
    .panel {{
      background: var(--card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: 0 18px 60px rgba(29,42,56,0.08);
      padding: 22px;
    }}
    form {{
      display: grid;
      gap: 14px;
    }}
    label {{
      display: grid;
      gap: 6px;
      font-size: 0.95rem;
      font-weight: 700;
    }}
    input[type="text"], textarea, input[type="file"] {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 14px;
      font: inherit;
      background: rgba(255,255,255,0.9);
      color: var(--ink);
    }}
    textarea {{
      min-height: 120px;
      resize: vertical;
    }}
    button {{
      border: 0;
      border-radius: 999px;
      background: linear-gradient(135deg, var(--accent), #d07a4a);
      color: white;
      padding: 12px 18px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      justify-self: start;
    }}
    h2, h3 {{
      margin-top: 0;
    }}
    .meta {{
      color: rgba(29,42,56,0.7);
      margin-bottom: 10px;
    }}
    pre {{
      margin: 0;
      padding: 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(249,246,239,0.95);
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.9rem;
      line-height: 1.45;
    }}
    .error {{
      margin-bottom: 14px;
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(180,76,47,0.12);
      border: 1px solid rgba(180,76,47,0.2);
      color: #7f2e1a;
    }}
    @media (max-width: 900px) {{
      .grid {{ grid-template-columns: 1fr; }}
      .hero {{ padding-inline: 4px; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <h1>AI Product Insights Assistant</h1>
      <p class="sub">Upload a CSV, describe the business context, and ask a product question. The app summarizes the dataset and returns an analysis grounded in the uploaded data plus your context.</p>
    </section>
    <section class="grid">
      <section class="panel">
        <h2>Inputs</h2>
        {"<div class='error'>" + html.escape(error) + "</div>" if error else ""}
        <form action="/analyze" method="post" enctype="multipart/form-data">
          <label>
            Dataset CSV
            <input type="file" name="dataset" accept=".csv,text/csv" required>
          </label>
          <label>
            Business Context
            <textarea name="business_context" placeholder="Explain what this dataset represents, what the business cares about, and any important definitions.">{html.escape(business_context)}</textarea>
          </label>
          <label>
            Analysis Question
            <textarea name="question" placeholder="What do you want the assistant to answer?">{html.escape(question)}</textarea>
          </label>
          <label>
            OpenAI Model (optional)
            <input type="text" name="model" value="{html.escape(model)}" placeholder="e.g. gpt-4.1">
          </label>
          <button type="submit">Analyze Dataset</button>
        </form>
      </section>
      {preview_html or '<section class="panel"><h2>Dataset Preview</h2><p class="meta">Upload a CSV to inspect its shape and run analysis.</p></section>'}
    </section>
    {analysis_html}
  </main>
</body>
</html>"""


class ProductInsightsHandler(BaseHTTPRequestHandler):
    docs_path = Path("knowledge")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/":
            self.send_error(404, "Not Found")
            return
        message = parse_qs(parsed.query).get("error", [""])[0]
        self._send_html(
            render_page(
                error=message,
            )
        )

    def do_POST(self) -> None:
        if self.path != "/analyze":
            self.send_error(404, "Not Found")
            return

        form = self._parse_form_data()
        file_info = form.get("dataset")
        if not file_info or not isinstance(file_info, dict) or "content" not in file_info:
            self._send_html(render_page(error="Please upload a CSV dataset."))
            return

        question = str(form.get("question", DEFAULT_QUESTION)).strip() or DEFAULT_QUESTION
        business_context = str(form.get("business_context", "")).strip()
        model = str(form.get("model", "")).strip()
        dataset_name = os.path.basename(str(file_info.get("filename", "uploaded.csv")))

        with tempfile.NamedTemporaryFile("wb", suffix=".csv", delete=False) as handle:
            handle.write(file_info["content"])
            temp_path = Path(handle.name)

        try:
            rows = load_csv_rows(temp_path)
            dataset_preview = preview_csv(rows)
            dataset_summary = summarize_csv(rows)
            result = generate_insights(
                temp_path,
                self.docs_path if self.docs_path.exists() else None,
                question,
                business_context=business_context,
                model=model or None,
            )
            self._send_html(
                render_page(
                    result=result,
                    question=question,
                    business_context=business_context,
                    model=model,
                    dataset_name=dataset_name,
                    dataset_preview=dataset_preview,
                    dataset_summary=dataset_summary,
                )
            )
        except Exception as exc:
            self._send_html(
                render_page(
                    error=str(exc),
                    question=question,
                    business_context=business_context,
                    model=model,
                )
            )
        finally:
            temp_path.unlink(missing_ok=True)

    def _send_html(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _parse_form_data(self) -> dict[str, object]:
        content_type = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)

        if content_type.startswith("multipart/form-data"):
            return _parse_multipart(content_type, body)
        if content_type.startswith("application/x-www-form-urlencoded"):
            return _parse_urlencoded(body)
        return {}


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    server = HTTPServer(("127.0.0.1", port), ProductInsightsHandler)
    print(f"Serving AI Product Insights Assistant on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()


def _parse_multipart(content_type: str, body: bytes) -> dict[str, object]:
    message_bytes = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    message = BytesParser(policy=default).parsebytes(message_bytes)
    parsed: dict[str, object] = {}

    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        if filename:
            parsed[name] = {"filename": filename, "content": payload}
        else:
            parsed[name] = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    return parsed


def _parse_urlencoded(body: bytes) -> dict[str, object]:
    parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
    return {key: unquote_plus(values[0]) if values else "" for key, values in parsed.items()}
