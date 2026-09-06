# Invoice Chaser — Testing Guide

This document explains how to run the local validation script and verify that the main Invoice Chaser features are working as expected.

---

## Prerequisites
Before running the tests, complete the project setup described in the main `README.md`. 

The `README.md` contains the required installation steps and general project setup. This document focuses specifically on testing and validation.

---

## Running the Validation
From the project root directory, run:
```bash
python src/run_dry.py
```

The script runs the validation pipeline using the local test data and prints the results to the terminal. 

*Note: The AWS Bedrock backend and Strands SDK are not required for this local validation. The purpose of the dry run is to check data processing, calculations, invoice classification, and generated output.*

---

## Validation Checklist

### 1. Invoice Classification
Check the invoice classifications printed in the terminal. The system should behave as follows:

*   **Paid Invoices**
    *   Paid invoices should be skipped by the follow-up process.
    *   No risk tier should be assigned.
    *   No reminder or escalation message should be generated.
*   **Slightly Overdue Invoices**
    *   The invoice should receive a low-urgency classification.
    *   A **Gentle** reminder should be generated.
    *   The message should remain friendly and appropriate for a minor delay.
*   **Severely Overdue Invoices**
    *   The invoice should receive a higher-urgency classification.
    *   An **Urgent** follow-up should be generated.
    *   Where appropriate, the system should recommend an installment payment plan.

### 2. Metric Calculations
Check the calculated values shown in the terminal output.

*   **Risk Score**  
    Confirm that the assigned risk level matches the invoice’s `DaysLate` value. The expected risk categories are:
    *   Low
    *   Medium
    *   High
*   **Cash Flow Forecast**  
    Confirm that the forecast contains two separate scenarios:
    *   Best Case
    *   Worst Case  
    *Note: The two scenarios should produce different projected outcomes based on the underlying invoice data.*
*   **Impact Calculator**  
    Check that the potential loss reduction is calculated correctly. Where the test data supports a reduction, the result should contain a valid, non-zero value.

### 3. Generated Text
Review the following sections in the terminal output:
*   Weekly Brief
*   Decision Explainer

Check that the generated content:
*   Is easy to read.
*   Uses consistent formatting.
*   Is grammatically correct.
*   Matches the invoice’s risk level and current status.
*   Uses an appropriate level of urgency.

---

## Demo Test Cases
The following three invoices were selected from our real output metrics as examples for the 5-minute hackathon demonstration.

### Sample A — Gentle Follow-up
*   **Invoice ID:** `3037486776`
*   **Days Late:** 1
*   **Reasoning:** This invoice was due on February 28, 2013, and was one day overdue in the March 1 snapshot. It demonstrates how the system handles a minor delay without immediately escalating the situation or alienating reliable clients.
*   **Expected Behavior:** The system should generate a Gentle follow-up with a friendly, low-pressure tone (e.g., *“No rush, just flagging it…”*).

### Sample B — Polite Follow-up
*   **Invoice ID:** `2538593943`
*   **Days Late:** 11
*   **Reasoning:** This invoice demonstrates the next stage of the follow-up process. At 11 days overdue, the system moves beyond a simple reminder to a direct, professional business check-in.
*   **Expected Behavior:** The system should generate a more structured payment reminder, ask for an expected payment timeline, and maintain a professional tone without triggering the highest urgency level.

### Sample C — Urgent Escalation / Payment Plan Candidate
*   **Invoice ID:** `5364802553`
*   **Days Late:** 31
*   **Reasoning:** This invoice represents a serious overdue case involving a high-risk customer. It is intended to demonstrate the full end-to-end escalation process and complex backend features on camera.
*   **Expected Behavior:** The system should identify the increased financial exposure, assign a higher risk level, generate an Urgent follow-up warning about possible further escalation, and dynamically recommend a structured installment payment plan.

---

## Expected Progression
The three demo cases show how the system dynamically shifts its response strategy as an outstanding invoice becomes more overdue:

| Invoice ID | Days Late | Expected Response |
| :--- | :--- | :--- |
| `3037486776` | 1 day | Gentle follow-up |
| `2538593943` | 11 days | Polite, structured follow-up |
| `5364802553` | 31 days | Urgent escalation / installment payment plan |

This progression can be highlighted during the demo walkthrough to show judges exactly how Invoice Chaser adjusts its automated strategies based on the age and risk profile of an outstanding balance.

