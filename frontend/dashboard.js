
const $ = (id) => document.getElementById(id);

// ======================================================
// CONFIGURATION
// ======================================================

const DEFAULT_API_URL =
    "https://intelligent-grievance-rag-system.onrender.com";

let tickets = [];
let selectedTicket = null;
let isConnected = false;

// Keep the API key only for the current browser session.
const savedKey = sessionStorage.getItem("grievance_api_key") || "";

// Initialize API URL and saved API key.
$("apiUrl").value = DEFAULT_API_URL;
$("apiKey").value = savedKey;

// ======================================================
// API CONFIGURATION
// ======================================================

function apiBase() {
    return $("apiUrl").value.trim().replace(/\/+$/, "");
}

function getApiKey() {
    return $("apiKey").value.trim();
}

function headers(json = false) {
    const h = {
        "X-API-Key": getApiKey()
    };

    if (json) {
        h["Content-Type"] = "application/json";
    }

    return h;
}

// ======================================================
// API REQUEST HANDLER
// ======================================================

async function request(path, options = {}) {
    const url = apiBase() + path;

    let response;

    try {
        response = await fetch(url, {
            ...options,
            headers: {
                ...headers(options.body !== undefined),
                ...(options.headers || {})
            }
        });
    } catch (error) {
        console.error("Network/API connection error:", error);

        throw new Error(
            "Cannot reach the backend. Check the Render URL, " +
            "backend status and CORS configuration."
        );
    }

    const raw = await response.text();

    let data;

    try {
        data = raw ? JSON.parse(raw) : {};
    } catch {
        data = raw;
    }

    if (!response.ok) {
        const detail =
            typeof data === "object" && data !== null
                ? data.detail
                : data;

        if (response.status === 401) {
            throw new Error(
                "Invalid API key. Check the API_KEY configured in Render."
            );
        }

        if (response.status === 403) {
            throw new Error(
                "Access forbidden. Check your backend permissions."
            );
        }

        if (response.status === 404) {
            throw new Error(
                typeof detail === "string"
                    ? detail
                    : "Requested resource not found."
            );
        }

        throw new Error(
            detail || `Backend request failed (${response.status}).`
        );
    }

    return data;
}

// ======================================================
// USER NOTIFICATIONS
// ======================================================

function toast(message, error = false) {
    const el = $("toast");

    el.textContent = message;
    el.className = "toast show" + (error ? " error" : "");

    setTimeout(() => {
        el.className = "toast";
    }, 3500);
}

// ======================================================
// SAFE HTML OUTPUT
// ======================================================

function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

// ======================================================
// DATE FORMATTING
// ======================================================

function date(value) {
    if (!value) return "—";

    let d;

    if (typeof value === "number" ||
        /^\d+(\.\d+)?$/.test(String(value))) {
        d = new Date(Number(value) * 1000);
    } else {
        d = new Date(value);
    }

    if (Number.isNaN(d.getTime())) {
        return esc(value);
    }

    return d.toLocaleString();
}

// ======================================================
// STATUS FORMATTING
// ======================================================

function statusLabel(status) {
    return {
        needs_review: "Needs review",
        new: "Ready to resolve",
        resolved: "Resolved"
    }[status] || status || "Unknown";
}

// ======================================================
// CONFIDENCE FORMATTING
// ======================================================

function confidence(value) {
    const number = Number(value);

    if (!Number.isFinite(number)) return "0%";

    return Math.round(
        Math.max(0, Math.min(1, number)) * 100
    ) + "%";
}

// ======================================================
// RENDER DASHBOARD
// ======================================================

function render() {
    $("totalCount").textContent = tickets.length;

    $("reviewCount").textContent =
        tickets.filter(t => t.status === "needs_review").length;

    $("newCount").textContent =
        tickets.filter(t => t.status === "new").length;

    $("resolvedCount").textContent =
        tickets.filter(t => t.status === "resolved").length;

    const query = $("searchInput").value.trim().toLowerCase();
    const status = $("statusFilter").value;

    const filtered = tickets.filter(t => {
        const matchesStatus =
            status === "all" || t.status === status;

        const searchableText = [
            t.id,
            t.category,
            t.priority,
            t.source,
            t.text
        ].join(" ").toLowerCase();

        return matchesStatus && searchableText.includes(query);
    });

    $("ticketRows").innerHTML = filtered.length
        ? filtered.map(t => `
            <tr>
                <td>
                    <div class="case-id">
                        #GR-${String(t.id).padStart(4, "0")}
                    </div>
                    <div class="case-date">
                        ${date(t.created)}
                    </div>
                </td>

                <td>${esc(t.category || "Unclassified")}</td>

                <td>
                    <span class="pill p-${esc(
                        (t.priority || "low").toLowerCase()
                    )}">
                        ${esc(t.priority || "—")}
                    </span>
                </td>

                <td>
                    <span class="confidence">
                        ${confidence(t.confidence)}
                    </span>
                </td>

                <td>
                    <span class="pill s-${esc(t.status)}">
                        ${esc(statusLabel(t.status))}
                    </span>
                </td>

                <td>${esc(t.source || "—")}</td>

                <td>
                    <button class="view-btn" data-id="${esc(t.id)}">
                        View details →
                    </button>
                </td>
            </tr>
        `).join("")
        : `
            <tr>
                <td colspan="7" class="empty">
                    No grievances match this filter.
                </td>
            </tr>
        `;

    document.querySelectorAll(".view-btn[data-id]").forEach(button => {
        button.addEventListener("click", () => {
            openTicket(Number(button.dataset.id));
        });
    });
}

// ======================================================
// BACKEND HEALTH CHECK
// ======================================================

async function checkHealth() {
    let response;

    try {
        response = await fetch(apiBase() + "/health", {
            method: "GET"
        });
    } catch (error) {
        throw new Error(
            "Cannot reach Render. Check whether the backend is running."
        );
    }

    if (!response.ok) {
        throw new Error(
            `Backend health check failed (${response.status}).`
        );
    }

    return await response.json();
}

// ======================================================
// CONNECT TO BACKEND
// ======================================================

async function connect() {
    const apiKey = getApiKey();

    if (!apiBase()) {
        toast("Please enter your backend API URL.", true);
        return;
    }

    if (!apiKey) {
        toast("Please enter your API key.", true);
        return;
    }

    const connectButton = $("connectBtn");

    connectButton.disabled = true;

    $("connection").className = "connection";
    $("connection").lastElementChild.textContent = "Connecting…";

    try {
        // Step 1: Check backend availability.
        const health = await checkHealth();

        if (!health.ok) {
            throw new Error("Backend health check returned an unhealthy status.");
        }

        // Step 2: Verify API key and retrieve tickets.
        const result = await request("/tickets?limit=200");

        if (!Array.isArray(result)) {
            throw new Error(
                "Unexpected response from /tickets. Check the backend API."
            );
        }

        tickets = result;
        render();

        // Step 3: Save key only after successful authentication.
        sessionStorage.setItem("grievance_api_key", apiKey);

        isConnected = true;

        $("connection").className = "connection online";
        $("connection").lastElementChild.textContent = "API connected";

        $("kbStatus").textContent =
            `Knowledge base: ${health.kb_chunks ?? "—"} chunks`;

        $("lastUpdated").textContent =
            "Updated " + new Date().toLocaleTimeString();

        toast("Dashboard connected successfully.");

    } catch (error) {
        isConnected = false;

        tickets = [];
        render();

        $("connection").className = "connection offline";
        $("connection").lastElementChild.textContent =
            "Connection failed";

        $("kbStatus").textContent =
            "Knowledge base: unavailable";

        console.error("Connection failed:", error);

        toast(error.message, true);

    } finally {
        connectButton.disabled = false;
    }
}

// ======================================================
// LOAD TICKETS
// ======================================================

async function loadTickets() {
    if (!isConnected) {
        throw new Error("Connect to the backend first.");
    }

    const result = await request("/tickets?limit=200");

    if (!Array.isArray(result)) {
        throw new Error("Invalid ticket data received from backend.");
    }

    tickets = result;

    render();

    $("lastUpdated").textContent =
        "Updated " + new Date().toLocaleTimeString();
}

// ======================================================
// OPEN TICKET DETAILS
// ======================================================

async function openTicket(id) {
    try {
        selectedTicket = await request(`/tickets/${id}`);

        const t = selectedTicket;

        $("modalTitle").textContent =
            `Grievance #GR-${String(t.id).padStart(4, "0")}`;

        $("modalBody").innerHTML = `
            <div class="detail-grid">

                <div class="detail-box">
                    <small>Category</small>
                    <b>${esc(t.category)}</b>
                </div>

                <div class="detail-box">
                    <small>Priority</small>
                    <b>${esc(t.priority)}</b>
                </div>

                <div class="detail-box">
                    <small>Confidence</small>
                    <b>${confidence(t.confidence)}</b>
                </div>

                <div class="detail-box">
                    <small>Status</small>
                    <b>${esc(statusLabel(t.status))}</b>
                </div>

                <div class="detail-box">
                    <small>Source</small>
                    <b>${esc(t.source)}</b>
                </div>

                <div class="detail-box">
                    <small>Received</small>
                    <b>${date(t.created)}</b>
                </div>

            </div>

            <div class="detail-block">
                <h3>GRIEVANCE MESSAGE</h3>
                <p>${esc(t.text)}</p>
            </div>

            <div class="detail-block">
                <h3>AI-GENERATED RESPONSE · EDIT BEFORE APPROVAL</h3>
                <textarea
                    class="reply-editor"
                    id="replyEditor"
                >${esc(t.reply || "")}</textarea>
            </div>

            ${
                t.status === "resolved"
                    ? `<p class="muted">
                        This ticket is already marked as resolved.
                       </p>`
                    : `
                        <div class="modal-actions">
                            <button class="btn btn-dark" id="closeTicket">
                                Close
                            </button>

                            <button class="btn btn-primary" id="approveBtn">
                                Approve & resolve
                            </button>
                        </div>
                    `
            }
        `;

        $("ticketModal").classList.remove("hidden");

        $("closeTicket")?.addEventListener("click", closeModal);

        $("approveBtn")?.addEventListener(
            "click",
            approveTicket
        );

    } catch (error) {
        toast(error.message, true);
    }
}

// ======================================================
// CLOSE TICKET MODAL
// ======================================================

function closeModal() {
    $("ticketModal").classList.add("hidden");
}

// ======================================================
// APPROVE AND RESOLVE TICKET
// ======================================================

async function approveTicket() {
    if (!selectedTicket) return;

    const reply = $("replyEditor").value.trim();

    if (!reply) {
        toast("Please enter a response before approval.", true);
        return;
    }

    const confirmed = confirm(
        "Approve this response and mark the grievance as resolved? " +
        "For Gmail tickets, this may send an email reply."
    );

    if (!confirmed) return;

    const button = $("approveBtn");

    button.disabled = true;
    button.textContent = "Approving…";

    try {
        await request(
            `/tickets/${selectedTicket.id}/approve`,
            {
                method: "POST",
                body: JSON.stringify({ reply })
            }
        );

        closeModal();

        await loadTickets();

        toast("Ticket approved and marked resolved.");

    } catch (error) {
        toast(error.message, true);

    } finally {
        button.disabled = false;
        button.textContent = "Approve & resolve";
    }
}

// ======================================================
// SUBMIT GRIEVANCE
// ======================================================

async function submitGrievance(event) {
    event.preventDefault();

    const text = $("grievanceText").value.trim();

    if (text.length < 3) {
        toast("Please enter a valid grievance.", true);
        return;
    }

    if (text.length > 20000) {
        toast("Grievance exceeds the maximum allowed length.", true);
        return;
    }

    const button = event.submitter;

    button.disabled = true;
    button.textContent = "Analyzing…";

    try {
        const result = await request(
            "/grievance",
            {
                method: "POST",
                body: JSON.stringify({
                    text: text,
                    source: "dashboard"
                })
            }
        );

        $("grievanceText").value = "";

        await loadTickets();

        toast(`Grievance analyzed. Ticket #${result.id} created.`);

        await openTicket(result.id);

    } catch (error) {
        toast(error.message, true);

    } finally {
        button.disabled = false;
        button.innerHTML =
            'Analyze grievance <span>→</span>';
    }
}

// ======================================================
// EVENT LISTENERS
// ======================================================

$("connectBtn").addEventListener("click", connect);

$("refreshBtn").addEventListener("click", async () => {
    try {
        await loadTickets();
        toast("Dashboard refreshed.");
    } catch (error) {
        toast(error.message, true);
    }
});

$("searchInput").addEventListener("input", render);

$("statusFilter").addEventListener("change", render);

$("closeModal").addEventListener("click", closeModal);

$("ticketModal").addEventListener("click", event => {
    if (event.target === $("ticketModal")) {
        closeModal();
    }
});

$("grievanceForm").addEventListener(
    "submit",
    submitGrievance
);

// ======================================================
// INITIALIZATION
// ======================================================

$("connection").className = "connection offline";
$("connection").lastElementChild.textContent =
    "Enter API key";

$("kbStatus").textContent =
    "Knowledge base: not connected";

if (savedKey) {
    connect();
}
