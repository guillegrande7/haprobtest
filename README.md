# 🚛 HAPROBTEST: Inbound Carrier Sales

**HAPROBTEST** is an integrated automation solution designed for freight brokerages like Acme Logistics. It leverages Artificial Intelligence to handle carrier negotiations, ensure safety compliance, and provide real-time financial analytics through a centralized command center.

## 📋 Core Features

* **Autonomous Negotiation Agent:** Handles 24/7 carrier inquiries using natural language processing to close deals without human intervention.
* **Compliance Gatekeeper:** Mandatory **MC Number** verification at the start of every interaction to ensure carrier eligibility and prevent fraud.
* **Strategic Margin Shield:** Proprietary 3-round negotiation logic with a hard cap of a **15% rate increase** over the target price.
* **Analytics Dashboard:** Real-time visualization of "Close Efficiency," carrier sentiment, and brokerage volume.
* **Financial Precision:** All currency data is handled as **integers** to eliminate rounding errors and ensure accounting integrity.

## 🏗️ Data Architecture

The system utilizes a high-performance, lightweight file-based architecture, designed for rapid deployment and future SQL scalability:

* **`loads.json`**: The primary source of truth for available freight, including origins, destinations, and target rates.

| Field | Description |
| :--- | :--- |
| **`load_id`** | Unique identifier for the load. |
| **`origin`** | Starting location. |
| **`destination`** | Delivery location. |
| **`pickup_datetime`** | Scheduled date and time for pickup. |
| **`delivery_datetime`** | Scheduled date and time for delivery. |
| **`equipment_type`** | Type of equipment needed (e.g., Reefer, Dry Van). |
| **`loadboard_rate`** | Listed rate for the load (Target Price). |
| **`notes`** | Additional shipping information. |
| **`weight`** | Total load weight. |
| **`commodity_type`** | Type of goods being transported. |
| **`num_of_pieces`** | Number of individual items or pallets. |
| **`miles`** | Total distance to travel. |
| **`dimensions`** | Size measurements of the cargo. |

* **`calls_history.json`**: An append-only audit trail of all carrier interactions, negotiations, and final bookings.

| Field | Description |
| :--- | :--- |
| **`mc_number`** | Unique carrier identifier (FMCSA). Used for security and compliance checks. |
| **`booked`** | Binary status (1: Booked, 0: Lost). Drives efficiency KPIs. |
| **`sentiment`** | AI-detected tone (e.g., Happy, Neutral, Frustrated) to measure market health. |
| **`original_rate`** | The initial target broker offer. |
| **`final_rate`** | The actual agreed-upon rate after negotiation. |
| **`transcript_summary`** | AI-generated executive summary for rapid broker review of the conversation. |

## 🚀 Deployment & Installation

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/guillegrande7/haprobtest.git](https://github.com/guillegrande7/haprobtest.git)
    cd haprobtest
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Configuration:**
    Create a `.env` file or set a Railway environment variable:
    `API_KEY=YourAlphanumericKey`
    *(Note: Avoid special characters like # or @ to ensure URL compatibility)*.

4.  **Run the Server Locally:**
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```

## 🔌 API Endpoints

### 1. Load Management
* **`GET /search-load`**: Retrieves available loads from `loads.json`. 
* **Filtering**: Supports origin and destination queries used by the AI agent.
* **Authentication**: Requires `X-API-KEY` as Header.

### 2. Call Summary
* **`POST /call-end`**: Creates new entry for the audit trail (Dashboard).
* **Logging**: Automatically writes the call details to `call_history.json`.
* **Authentication**: Requires `X-API-KEY` as Header.

### 3. Dashboard (Human Interface)
* **`GET /dashboard`**: Returns the interactive HTML analytics suite. 
* **Authentication**: Requires `api_key_query` as a parameter.

## 🔒 Security & Access

Dashboard access is secured via API Key authentication. It can be accessed through security headers or via a URL query parameter for management convenience:

`https://haprobtest-production.up.railway.app/dashboard?api_key_query=YOUR_KEY`

---
*Developed for Acme Logistics*