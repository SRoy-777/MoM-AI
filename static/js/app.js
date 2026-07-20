document.addEventListener("DOMContentLoaded", () => {
    // 1. Instances
    window.recorder = new AudioStreamRecorder();
    window.taskManager = new TaskMatrixManager();
    window.momViewer = new MoMViewer();

    // 2. Tab Navigation
    const navBtns = document.querySelectorAll(".nav-btn");
    const tabContents = document.querySelectorAll(".tab-content");

    navBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");

            navBtns.forEach(b => b.classList.remove("active"));
            tabContents.forEach(c => c.classList.remove("active"));

            btn.classList.add("active");
            document.getElementById(targetTab).classList.add("active");
        });
    });

    // 3. API Key LocalStorage
    const keyInput = document.getElementById("gemini-key-input");
    const saveKeyBtn = document.getElementById("save-key-btn");
    const savedKey = localStorage.getItem("MOM_AI_GEMINI_KEY");

    if (savedKey) {
        keyInput.value = savedKey;
    }

    saveKeyBtn.addEventListener("click", () => {
        const val = keyInput.value.trim();
        if (val) {
            localStorage.setItem("MOM_AI_GEMINI_KEY", val);
            alert("Gemini API Key saved locally!");
        } else {
            localStorage.removeItem("MOM_AI_GEMINI_KEY");
            alert("API Key cleared.");
        }
    });

    // 4. Audio Recorder Controls
    const toggleRecordBtn = document.getElementById("toggle-record-btn");
    const recordStatus = document.getElementById("recording-status");
    const transcriptBox = document.getElementById("transcript-container");
    const wordCountDisplay = document.getElementById("word-count");
    const clearTranscriptBtn = document.getElementById("clear-transcript-btn");

    toggleRecordBtn.addEventListener("click", async () => {
        if (!window.recorder.isRecording) {
            const success = await window.recorder.startCapture();
            if (success) {
                toggleRecordBtn.classList.add("recording");
                recordStatus.textContent = "Live Capturing Teams Audio...";
                recordStatus.style.color = "var(--danger)";
            }
        } else {
            window.recorder.stopCapture();
            toggleRecordBtn.classList.remove("recording");
            recordStatus.textContent = "Capture Paused";
            recordStatus.style.color = "var(--text-muted)";
        }
    });

    window.recorder.onTranscriptUpdate = (fullText, interimText) => {
        let displayHtml = "";
        const lines = fullText.trim().split("\n").filter(l => l.length > 0);
        
        lines.forEach(line => {
            displayHtml += `<div class="transcript-entry">${escapeHtml(line)}</div>`;
        });

        if (interimText) {
            displayHtml += `<div class="transcript-entry" style="opacity: 0.6; font-style: italic;">... ${escapeHtml(interimText)}</div>`;
        }

        transcriptBox.innerHTML = displayHtml;
        transcriptBox.scrollTop = transcriptBox.scrollHeight;

        const wordCount = fullText.split(/\s+/).filter(w => w.length > 0).length;
        const estTokens = Math.round(wordCount * 1.3);
        wordCountDisplay.textContent = `Word count: ${wordCount.toLocaleString()} words (~${estTokens.toLocaleString()} tokens)`;
    };

    clearTranscriptBtn.addEventListener("click", () => {
        window.recorder.fullTranscript = "";
        transcriptBox.innerHTML = `<div class="transcript-entry" style="color: var(--text-dim);">[System] Transcript cleared. Listening...</div>`;
        wordCountDisplay.textContent = "Word count: 0 words (~0 tokens)";
    });

    // 5. Teams Guest Bot Join
    const joinBotBtn = document.getElementById("join-bot-btn");
    const teamsUrlInput = document.getElementById("teams-url-input");

    joinBotBtn.addEventListener("click", async () => {
        const url = teamsUrlInput.value.trim();
        if (!url) {
            alert("Please enter a valid MS Teams Meeting URL.");
            return;
        }

        joinBotBtn.textContent = "Joining...";
        try {
            const formData = new FormData();
            formData.append("meeting_url", url);
            const res = await fetch("/api/teams-bot/join", { method: "POST", body: formData });
            const data = await res.json();

            if (data.success) {
                joinBotBtn.textContent = "Bot Launching...";
                joinBotBtn.style.background = "var(--primary)";

                const sessionId = data.session_id;
                const pollInterval = setInterval(async () => {
                    try {
                        const statusRes = await fetch(`/api/teams-bot/status?session_id=${sessionId}`);
                        const statusData = await statusRes.json();
                        if (statusData.success && statusData.session) {
                            const sess = statusData.session;
                            if (sess.status === "waiting_in_lobby_or_joined") {
                                joinBotBtn.textContent = "Waiting in Lobby / Joined";
                                joinBotBtn.style.background = "var(--success)";
                                clearInterval(pollInterval);
                            } else if (sess.status === "error") {
                                joinBotBtn.textContent = "Join Failed";
                                joinBotBtn.style.background = "var(--danger)";
                                clearInterval(pollInterval);
                            } else {
                                const lastLog = sess.log && sess.log.length > 0 ? sess.log[sess.log.length - 1] : sess.status;
                                joinBotBtn.textContent = lastLog.substring(0, 30) + "...";
                            }
                        }
                    } catch (err) {}
                }, 2000);
            } else {
                alert("Error joining Teams meeting: " + data.error);
                joinBotBtn.textContent = "Join Bot";
            }
        } catch (e) {
            alert("Failed to contact bot service: " + e.message);
            joinBotBtn.textContent = "Join Bot";
        }
    });

    // 6. Task Matrix Entry Form
    const taskForm = document.getElementById("task-matrix-form");
    taskForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const desc = document.getElementById("task-desc").value.trim();
        const assignee = document.getElementById("task-assignee").value.trim();
        const dept = document.getElementById("task-dept").value;
        const timeframe = document.getElementById("task-timeframe").value.trim();
        const priority = document.getElementById("task-priority").value;

        if (!desc) return;

        window.taskManager.addTask({
            task: desc,
            assignee: assignee || "Unassigned",
            department: dept,
            timeframe: timeframe || "ASAP",
            priority: priority,
            status: "Pending"
        });

        document.getElementById("task-desc").value = "";
        document.getElementById("task-assignee").value = "";
        document.getElementById("task-timeframe").value = "";
    });

    // 7. Generate MoM AI Trigger
    const generateMomBtn = document.getElementById("generate-mom-btn");
    generateMomBtn.addEventListener("click", async () => {
        const apiKey = keyInput.value.trim() || localStorage.getItem("MOM_AI_GEMINI_KEY") || "";

        const transcript = window.recorder.fullTranscript;
        const humanNotes = document.getElementById("human-notes-textarea").value;
        const manualTasks = window.taskManager.getTasks();
        const title = document.getElementById("meeting-title-input").value.trim() || "Executive Meeting Minutes";
        const date = document.getElementById("meeting-date-input").value || new Date().toISOString().split("T")[0];
        const attendees = document.getElementById("meeting-attendees-input").value.trim() || "Leadership & Project Teams";

        if (!transcript && !humanNotes && manualTasks.length === 0) {
            alert("Please capture audio, type notes, or add task items before generating MoM.");
            return;
        }

        generateMomBtn.innerHTML = `<div class="spinner"></div> Processing 4-Hour Context...`;
        generateMomBtn.disabled = true;

        try {
            const payload = {
                transcript: transcript,
                human_notes: humanNotes,
                manual_tasks: manualTasks,
                meeting_title: title,
                meeting_date: date,
                attendees: attendees,
                api_key: apiKey
            };

            const res = await fetch("/api/generate-mom", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (data.success) {
                window.momViewer.render(data.mom);
            } else {
                alert("Error generating MoM: " + data.error);
            }
        } catch (err) {
            alert("API connection failed: " + err.message);
        } finally {
            generateMomBtn.innerHTML = `<span>✨</span> Generate MoM with AI`;
            generateMomBtn.disabled = false;
        }
    });

    // 8. Exports
    const exportDocxBtn = document.getElementById("export-docx-btn");
    const exportPrintBtn = document.getElementById("export-print-btn");

    exportDocxBtn.addEventListener("click", async () => {
        if (!window.momViewer.currentMoM) return;
        try {
            const res = await fetch("/api/export-docx", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(window.momViewer.currentMoM)
            });
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `MoM_${window.momViewer.currentMoM.title || 'Report'}.docx`;
            a.click();
        } catch (e) {
            alert("Export error: " + e.message);
        }
    });

    exportPrintBtn.addEventListener("click", () => {
        window.print();
    });

    function escapeHtml(str) {
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }
});
