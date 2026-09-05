"""
app.py (webapp)
-----------------
Flask backend for the custom-designed Invoice Chaser website. Serves the
static frontend and a small JSON API that wraps the same Python logic
used by the CLI / Strands agent. Most routes need no AWS; POST /api/chat
is the exception — it forwards the question to invoice_agent in src/agent.py.

Run locally with: python webapp/app.py
Deploy free on Render.com (or Railway) pointing at this file.
"""

import sys
import os
import uuid
import tempfile
from datetime import date

import pandas as pd
from flask import Flask, request, jsonify, send_from_directory

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from data_loader import load_invoices, get_open_invoices, DEFAULT_DATA_PATH
from client_risk import compute_client_risk
from reminder_writer import draft_reminder
from translations import draft_reminder_multilingual, SUPPORTED_LANGUAGES
from payment_plan import draft_payment_plan_offer
from engine import bundle_from_open_df

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path="/static",
    template_folder=os.path.join(BASE_DIR, "templates"),
)

# Limit upload size to 16 MB
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

# In-memory store for uploaded files between the "columns" and "compute"
# steps. Fine for a demo; a production app would use real session storage.
UPLOAD_CACHE = {}


@app.route("/")
def index():
    return send_from_directory(app.template_folder, "index.html")


@app.route("/api/sample")
def api_sample():
    snapshot = request.args.get("snapshot", "2013-03-01")
    df = load_invoices(str(DEFAULT_DATA_PATH))
    open_df = get_open_invoices(df, snapshot)
    risk_df = compute_client_risk(df, snapshot)
    as_of_ts = pd.Timestamp(snapshot)
    bundle = bundle_from_open_df(open_df, as_of_ts, risk_df)
    return jsonify(bundle)


@app.route("/api/upload/columns", methods=["POST"])
def api_upload_columns():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    f = request.files["file"]
    filename = f.filename or ""
    lower_fn = filename.lower()
    ALLOWED_EXT = (".csv", ".xlsx", ".xls")
    if not any(lower_fn.endswith(e) for e in ALLOWED_EXT):
        return jsonify({"error": "Unsupported file type — upload .csv or .xlsx/.xls"}), 400

    ext = ".xlsx" if lower_fn.endswith((".xlsx", ".xls")) else ".csv"
    token = str(uuid.uuid4())

    # use system temp dir for cross-platform compatibility
    tmp_dir = tempfile.gettempdir()
    tmp_path = os.path.join(tmp_dir, f"invoice_chaser_{token}{ext}")
    f.save(tmp_path)
    UPLOAD_CACHE[token] = tmp_path

    try:
        raw_df = pd.read_excel(tmp_path) if ext != ".csv" else pd.read_csv(tmp_path)
    except Exception as e:
        # cleanup on failure
        UPLOAD_CACHE.pop(token, None)
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return jsonify({"error": f"Couldn't read that file: {e}"}), 400

    return jsonify({
        "token": token,
        "columns": list(raw_df.columns),
        "preview": raw_df.head(8).fillna("").astype(str).to_dict(orient="records"),
    })


@app.route("/api/upload/compute", methods=["POST"])
def api_upload_compute():
    data = request.get_json()
    token = data.get("token")
    tmp_path = UPLOAD_CACHE.get(token)
    if not tmp_path or not os.path.exists(tmp_path):
        return jsonify({"error": "Upload session expired — please re-upload your file."}), 400

    try:
        raw_df = pd.read_excel(tmp_path) if tmp_path.endswith(".xlsx") else pd.read_csv(tmp_path)

        work = pd.DataFrame({
            "customerID": raw_df[data["customer_col"]],
            "invoiceNumber": raw_df[data["id_col"]].astype(str),
            "InvoiceAmount": pd.to_numeric(raw_df[data["amount_col"]], errors="coerce"),
            "DueDate": pd.to_datetime(raw_df[data["due_col"]], errors="coerce"),
        })

        paid_col = data.get("paid_col")
        if paid_col:
            paid_series = raw_df[paid_col].astype(str).str.strip().str.lower()
            is_paid = paid_series.isin(["yes", "true", "1", "paid", "y"])
            work = work[~is_paid]

        work = work.dropna(subset=["DueDate", "InvoiceAmount"])

        today = pd.Timestamp(date.today())
        work["DaysOverdue"] = (today - work["DueDate"]).dt.days
        work["IsOverdue"] = work["DaysOverdue"] > 0

        bundle = bundle_from_open_df(work, today, None)
        return jsonify(bundle)
    except Exception as e:
        return jsonify({"error": f"Couldn't process uploaded file: {e}"}), 400
    finally:
        # always clean up temporary file and cache entry
        cached = UPLOAD_CACHE.pop(token, None)
        if cached and os.path.exists(cached):
            try:
                os.remove(cached)
            except Exception:
                pass


@app.route("/api/languages")
def api_languages():
    return jsonify(SUPPORTED_LANGUAGES)


@app.route("/api/reminder", methods=["POST"])
def api_reminder():
    d = request.get_json()
    language = d.get("language", "en")
    if language == "en":
        message = draft_reminder(
            customer=d["customer"], invoice_number=d["invoice_number"], amount=d["amount"],
            due_date=d["due_date"], days_overdue=d["days_overdue"], tier=d["tier"],
        )
    else:
        message = draft_reminder_multilingual(
            customer=d["customer"], invoice_number=d["invoice_number"], amount=d["amount"],
            due_date=d["due_date"], days_overdue=d["days_overdue"], tier=d["tier"],
            language=language,
        )
    return jsonify({"message": message})


@app.route("/api/payment-plan", methods=["POST"])
def api_payment_plan():
    d = request.get_json()
    message = draft_payment_plan_offer(
        customer=d["customer"], invoice_number=d["invoice_number"], amount=d["amount"],
        days_overdue=d["days_overdue"], num_installments=d.get("num_installments", 3),
    )
    return jsonify({"message": message})



@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Pass a user's question to the Strands/Bedrock agent and return its reply."""
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Missing 'question' in JSON body."}), 400

    try:
        # Import here so the rest of the webapp still starts without AWS / strands.
        from agent import invoice_agent
        response = invoice_agent(question)
    except Exception as e:
        return jsonify({"error": f"Agent failed: {e}"}), 502

    return jsonify({"answer": str(response)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
