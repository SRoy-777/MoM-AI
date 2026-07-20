class MoMViewer {
    constructor() {
        this.currentMoM = null;
        this.container = document.getElementById("mom-report-output");
    }

    render(momData) {
        this.currentMoM = momData;
        if (!this.container) return;

        const highlights = (momData.discussion_highlights || []).map(topic => `
            <div style="margin-bottom: 1.25rem;">
                <h4 style="color: var(--secondary); font-size: 1.05rem; margin-bottom: 0.5rem;">🔹 ${this._escapeHtml(topic.topic)}</h4>
                <ul style="padding-left: 1.25rem; color: var(--text-main); line-height: 1.7;">
                    ${(topic.points || []).map(pt => `<li>${this._escapeHtml(pt)}</li>`).join("")}
                </ul>
            </div>
        `).join("");

        const decisions = (momData.decisions || []).map(dec => `
            <li style="margin-bottom: 0.5rem; color: var(--success); font-weight: 500;">
                ✔ ${this._escapeHtml(dec)}
            </li>
        `).join("");

        const actionRows = (momData.action_items || []).map(item => {
            const pBadge = item.priority === "High" ? "badge-high" : (item.priority === "Low" ? "badge-low" : "badge-med");
            return `
                <tr>
                    <td style="font-weight: 500;">${this._escapeHtml(item.task)}</td>
                    <td><strong>${this._escapeHtml(item.assignee || "Unassigned")}</strong></td>
                    <td><span class="badge badge-dept">${this._escapeHtml(item.department || "General")}</span></td>
                    <td style="color: var(--warning); font-size: 0.85rem;">⏰ ${this._escapeHtml(item.timeframe || "ASAP")}</td>
                    <td><span class="badge ${pBadge}">${item.priority}</span></td>
                </tr>
            `;
        }).join("");

        this.container.innerHTML = `
            <div id="printable-mom">
                <!-- Header -->
                <div style="border-bottom: 2px solid var(--border-color); padding-bottom: 1rem; margin-bottom: 1.5rem;">
                    <h1 style="font-size: 1.8rem; font-weight: 700; color: #fff; margin-bottom: 0.5rem;">${this._escapeHtml(momData.title || "Minutes of Meeting")}</h1>
                    <div style="display: flex; gap: 2rem; color: var(--text-muted); font-size: 0.9rem;">
                        <div><strong>Date:</strong> ${this._escapeHtml(momData.date || "N/A")}</div>
                        <div><strong>Attendees:</strong> ${this._escapeHtml(momData.attendees || "N/A")}</div>
                    </div>
                </div>

                <!-- Executive Summary -->
                <div style="margin-bottom: 1.75rem; background: rgba(139, 92, 246, 0.05); padding: 1.25rem; border-radius: var(--radius-md); border-left: 4px solid var(--primary);">
                    <h3 style="font-size: 1.1rem; color: var(--primary); margin-bottom: 0.5rem;">📋 Executive Summary</h3>
                    <p style="line-height: 1.7; color: var(--text-main);">${this._escapeHtml(momData.executive_summary || "")}</p>
                </div>

                <!-- Discussion Highlights -->
                <div style="margin-bottom: 1.75rem;">
                    <h3 style="font-size: 1.2rem; color: #fff; margin-bottom: 1rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem;">📌 Discussion Highlights</h3>
                    ${highlights || "<p style='color: var(--text-muted);'>No detailed topics extracted.</p>"}
                </div>

                <!-- Decisions Made -->
                <div style="margin-bottom: 1.75rem;">
                    <h3 style="font-size: 1.2rem; color: #fff; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem;">🤝 Key Decisions</h3>
                    <ul style="list-style: none; padding: 0;">
                        ${decisions || "<p style='color: var(--text-muted);'>No binding decisions recorded.</p>"}
                    </ul>
                </div>

                <!-- Action Items Table -->
                <div style="margin-bottom: 1.5rem;">
                    <h3 style="font-size: 1.2rem; color: #fff; margin-bottom: 1rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem;">🚀 Action Items & Department Assignments</h3>
                    <table class="custom-table">
                        <thead>
                            <tr>
                                <th>Deliverable / Task</th>
                                <th>Assignee</th>
                                <th>Department</th>
                                <th>Target Timeframe</th>
                                <th>Priority</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${actionRows || "<tr><td colspan='5' style='text-align:center;'>No action items found.</td></tr>"}
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        document.getElementById("export-docx-btn").style.display = "inline-flex";
        document.getElementById("export-print-btn").style.display = "inline-flex";
    }

    _escapeHtml(str) {
        return (str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }
}
window.MoMViewer = MoMViewer;
