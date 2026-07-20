class AudioStreamRecorder {
    constructor() {
        this.isRecording = false;
        this.mediaStream = null;
        this.audioContext = null;
        this.analyser = null;
        this.recognition = null;
        this.startTime = null;
        this.timerInterval = null;
        this.fullTranscript = "";

        this.onTranscriptUpdate = null;
    }

    async startCapture() {
        try {
            // Request System / Teams Tab audio capture or Microphone fallback
            let stream = null;
            if (navigator.mediaDevices.getDisplayMedia) {
                try {
                    stream = await navigator.mediaDevices.getDisplayMedia({
                        video: true,
                        audio: {
                            echoCancellation: true,
                            noiseSuppression: true,
                            sampleRate: 44100
                        }
                    });
                } catch (e) {
                    console.warn("Display media cancelled or unsupported, falling back to mic:", e);
                }
            }

            if (!stream) {
                stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            }

            this.mediaStream = stream;
            this.isRecording = true;
            this.startTime = Date.now();
            this._startTimer();
            this._initWaveform(stream);
            this._initSpeechRecognition();

            return true;
        } catch (err) {
            console.error("Error starting audio capture:", err);
            alert("Could not access audio device: " + err.message);
            return false;
        }
    }

    stopCapture() {
        this.isRecording = false;
        if (this.timerInterval) clearInterval(this.timerInterval);
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
        }
        if (this.recognition) {
            this.recognition.stop();
        }
    }

    _startTimer() {
        const timerDisplay = document.getElementById("timer-display");
        this.timerInterval = setInterval(() => {
            if (!this.isRecording) return;
            const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
            const hrs = String(Math.floor(elapsed / 3600)).padStart(2, "0");
            const mins = String(Math.floor((elapsed % 3600) / 60)).padStart(2, "0");
            const secs = String(elapsed % 60).padStart(2, "0");
            if (timerDisplay) timerDisplay.textContent = `${hrs}:${mins}:${secs}`;
        }, 1000);
    }

    _initWaveform(stream) {
        const canvas = document.getElementById("waveform");
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.analyser = this.audioContext.createAnalyser();
        const source = this.audioContext.createMediaStreamSource(stream);
        source.connect(this.analyser);

        this.analyser.fftSize = 64;
        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const draw = () => {
            if (!this.isRecording) {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                return;
            }
            requestAnimationFrame(draw);
            this.analyser.getByteFrequencyData(dataArray);

            ctx.fillStyle = "rgba(10, 12, 16, 0.4)";
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            const barWidth = (canvas.width / bufferLength) * 2.5;
            let x = 0;

            for (let i = 0; i < bufferLength; i++) {
                const barHeight = (dataArray[i] / 255) * canvas.height;
                const gradient = ctx.createLinearGradient(0, canvas.height, 0, 0);
                gradient.addColorStop(0, "#8b5cf6");
                gradient.addColorStop(1, "#06b6d4");

                ctx.fillStyle = gradient;
                ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
                x += barWidth + 2;
            }
        };
        draw();
    }

    _initSpeechRecognition() {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRec) {
            console.warn("Speech Recognition API not supported in this browser. Please use Chrome/Edge.");
            return;
        }

        this.recognition = new SpeechRec();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = "en-US";

        this.recognition.onresult = (event) => {
            let interimTranscript = "";
            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    const finalSegment = event.results[i][0].transcript.trim();
                    const timeStamp = new Date().toLocaleTimeString();
                    this.fullTranscript += `\n[${timeStamp}] ${finalSegment}`;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }
            if (this.onTranscriptUpdate) {
                this.onTranscriptUpdate(this.fullTranscript, interimTranscript);
            }
        };

        this.recognition.onend = () => {
            if (this.isRecording) {
                // Auto-restart recognition if continuous stream ended
                try { this.recognition.start(); } catch (e) {}
            }
        };

        try { this.recognition.start(); } catch (e) {}
    }
}
window.AudioStreamRecorder = AudioStreamRecorder;
