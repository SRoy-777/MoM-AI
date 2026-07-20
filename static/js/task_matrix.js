class TaskMatrixManager {
    constructor() {
        this.tasks = [];
        this.tableBody = document.getElementById("task-table-body");
    }

    addTask(taskObj) {
        this.tasks.push(taskObj);
        this.render();
    }

    removeTask(index) {
        this.tasks.splice(index, 1);
        this.render();
    }

    getTasks() {
        return this.tasks;
    }

    render() {
        if (!this.tableBody) return;
        this.tableBody.innerHTML = "";

        if (this.tasks.length === 0) {
            this.tableBody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">
                        No manual tasks added yet. Use the form above to assign action items.
                    </td>
                </tr>
            `;
            return;
        }

        this.tasks.forEach((t, index) => {
            const tr = document.createElement("tr");

            const priorityBadge = t.priority === "High" ? "badge-high" : (t.priority === "Low" ? "badge-low" : "badge-med");

            tr.innerHTML = `
                <td style="font-weight: 500;">${this._escapeHtml(t.task)}</td>
                <td>${this._escapeHtml(t.assignee || "Unassigned")}</td>
                <td><span class="badge badge-dept">${this._escapeHtml(t.department || "General")}</span></td>
                <td>${this._escapeHtml(t.timeframe || "ASAP")}</td>
                <td><span class="badge ${priorityBadge}">${t.priority}</span></td>
                <td>
                    <button class="btn-secondary" style="padding: 0.25rem 0.6rem; font-size: 0.75rem; color: var(--danger);" onclick="window.taskManager.removeTask(${index})">
                        Delete
                    </button>
                </td>
            `;
            this.tableBody.appendChild(tr);
        });
    }

    _escapeHtml(str) {
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }
}
window.TaskMatrixManager = TaskMatrixManager;
