"""
app.py (webapp)
-----------------
Flask backend for the custom-designed Invoice Chaser website. Serves the
static frontend and a small JSON API that wraps the same Python logic
used by the CLI / Strands agent — no AWS needed for any of this.

Run locally with: python webapp/app.py
Deploy free on Render.com (or Railway) pointing at this file.
"""

import sys
import os
import uuid
import traceback
from datetime import date

import pandas as pd
from flask import Flask, request, jsonify, send_from_directory

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from data_loader import load_invoices, get_open_invoices, DEFAULT_DATA_PATH
from client_risk import compute_client_risk
from reminder_writer import draft_reminder
from payment_plan import draft_payment_plan_offer
from engine import bundle_from_open_df

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path="/static",
    template_folder=os.path.join(BASE_DIR, "templates"),
)

# In-memory store for uploaded files between the "columns" and "compute"
# steps. Fine for a demo; a production app would use real session storage.
UPLOAD_CACHE = {}


def _error_response(exc: Exception, status: int = 500):
    """
    Every /api/* route returns this shape on failure so the frontend's
    fetch() calls always get parseable JSON with an .error field —
    never Flask's default HTML error page.
    """
    app.logger.error("API error: %s\n%s", exc, traceback.format_exc())
    return jsonify({"error": str(exc) or "Something went wrong on the server."}), status


@app.route("/")
def index():
    return send_from_directory(app.template_folder, "index.html")


@app.route("/api/sample")
def api_sample():
    try:
        snapshot = request.args.get("snapshot", "2013-03-01")
        df = load_invoices(str(DEFAULT_DATA_PATH))
        open_df = get_open_invoices(df, snapshot)
        risk_df = compute_client_risk(df, snapshot)
        as_of_ts = pd.Timestamp(snapshot)
        bundle = bundle_from_open_df(open_df, as_of_ts, risk_df)
        return jsonify(bundle)
    except Exception as e:
        return _error_response(e)


@app.route("/api/upload/columns", methods=["POST"])
def api_upload_columns():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        f = request.files["file"]
        if not f.filename:
            return jsonify({"error": "No file selected"}), 400

        ext = ".xlsx" if f.filename.lower().endswith((".xlsx", ".xls")) else ".csv"
        token = str(uuid.uuid4())
        tmp_path = f"/tmp/invoice_chaser_{token}{ext}"
        f.save(tmp_path)
        UPLOAD_CACHE[token] = tmp_path

        try:
            raw_df = pd.read_excel(tmp_path) if ext != ".csv" else pd.read_csv(tmp_path)
        except Exception as e:
            return jsonify({"error": f"Couldn't read that file: {e}"}), 400

        if raw_df.empty or len(raw_df.columns) == 0:
            return jsonify({"error": "That file doesn't seem to have any columns we can map."}), 400

        return jsonify({
            "token": token,
            "columns": list(raw_df.columns),
            "preview": raw_df.head(8).fillna("").astype(str).to_dict(orient="records"),
        })
    except Exception as e:
        return _error_response(e)


@app.route("/api/upload/compute", methods=["POST"])
def api_upload_compute():
    try:
        data = request.get_json(silent=True) or {}
        token = data.get("token")
        tmp_path = UPLOAD_CACHE.get(token)
        if not tmp_path or not os.path.exists(tmp_path):
            return jsonify({"error": "Upload session expired — please re-upload your file."}), 400

        required = ["customer_col", "amount_col", "id_col", "due_col"]
        missing = [k for k in required if not data.get(k)]
        if missing:
            return jsonify({"error": f"Please choose a column for: {', '.join(missing)}."}), 400

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

        if work.empty:
            return jsonify({"error": "No usable rows after mapping — check the amount and due-date columns."}), 400

        today = pd.Timestamp(date.today())
        work["DaysOverdue"] = (today - work["DueDate"]).dt.days
        work["IsOverdue"] = work["DaysOverdue"] > 0

        bundle = bundle_from_open_df(work, today, None)
        return jsonify(bundle)
    except Exception as e:
        return _error_response(e)


@app.route("/api/reminder", methods=["POST"])
def api_reminder():
    try:
        d = request.get_json(silent=True) or {}
        message = draft_reminder(
            customer=d["customer"], invoice_number=d["invoice_number"], amount=d["amount"],
            due_date=d["due_date"], days_overdue=d["days_overdue"], tier=d["tier"],
        )
        return jsonify({"message": message})
    except Exception as e:
        return _error_response(e)


@app.route("/api/payment-plan", methods=["POST"])
def api_payment_plan():
    try:
        d = request.get_json(silent=True) or {}
        message = draft_payment_plan_offer(
            customer=d["customer"], invoice_number=d["invoice_number"], amount=d["amount"],
            days_overdue=d["days_overdue"], num_installments=d.get("num_installments", 3),
        )
        return jsonify({"message": message})
    except Exception as e:
        return _error_response(e)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)