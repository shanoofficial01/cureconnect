function resolveApiBaseUrl() {
    const { protocol, hostname } = window.location;

    if (protocol === "file:" || !hostname) {
        return "http://localhost:8000";
    }

    const apiProtocol = protocol === "https:" ? "https:" : "http:";
    return `${apiProtocol}//${hostname}:8000`;
}

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

const App = {
    config: {
        apiUrl: resolveApiBaseUrl(),
        defaultCity: "Chennai",
        blockedReportTerms: [
            "cureconnect",
            "prescripto",
            "prescripto pro",
            "app name",
            "application",
            "dashboard",
            "login",
            "profile"
        ]
    },

    state: {
        user: null,
        activeTab: 'home',
        activeGroup: null,
        groupRefreshInterval: null,
        healthNews: [],
        doctorDirectory: {}
    },

    socket: null,
    _filteredLoad: false,

    init() {
        console.log("CureConnect Initializing...");

        const token = sessionStorage.getItem("access_token");
        const username = sessionStorage.getItem("username");

        this.bindGlobalEvents();
        this.renderVoiceControls();
        this.updateVoiceUI("idle");

        if (token && username) {
            this.state.user = username;
            document.getElementById('authScreen').classList.add('hidden');
            document.getElementById('mainApp').classList.remove('hidden');
            document.getElementById('dispName').innerText = username;
            document.getElementById('profileName').innerText = username;
            this.switchTab('home');
            return;
        }

        this.switchTab('home');
    },

    bindGlobalEvents() {
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                this.closeDoctorModal();
            }
        });
    },

    renderVoiceControls() {
        const controls = document.getElementById("voiceControlButtons");
        if (!controls) return;

        controls.innerHTML = voiceModeEnabled
            ? `
                <button id="voiceStartBtn" onclick="startRecording()" class="rounded-2xl border border-emerald-100 bg-white px-4 py-3 text-sm font-semibold text-[var(--accent-deep)] transition hover:border-emerald-200 hover:bg-emerald-50">
                    Start Recording
                </button>
                <button id="voiceStopBtn" onclick="stopRecording()" class="rounded-2xl border border-amber-100 bg-white px-4 py-3 text-sm font-semibold text-amber-700 transition hover:border-amber-200 hover:bg-amber-50">
                    Stop Recording
                </button>
                <button id="voiceDisableBtn" onclick="App.disableVoiceMode()" class="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50">
                    Stop Voice Mode
                </button>
            `
            : `
                <button id="voiceEnableBtn" onclick="App.enableVoiceMode()" class="rounded-2xl border border-emerald-100 bg-white px-4 py-3 text-sm font-semibold text-[var(--accent-deep)] transition hover:border-emerald-200 hover:bg-emerald-50">
                    Start Voice Mode
                </button>
            `;
    },

    switchTab(tabId) {
        this.state.activeTab = tabId;

        document.querySelectorAll('.view-section')
            .forEach(section => section.classList.remove('active'));

        document.getElementById(`view-${tabId}`)?.classList.add('active');

        document.querySelectorAll('nav button')
            .forEach(btn => btn.classList.remove('active-tab'));

        document.getElementById(`tab-${tabId}`)?.classList.add('active-tab');
        document.getElementById(`tab-${tabId}-mobile`)?.classList.add('active-tab');

        if (tabId === 'home') {
            this.loadCityHealth();
            this.loadHealthNews();
        }
        if (tabId === 'groups') this.fetchUserGroups();
        if (tabId === 'doctors' && !this._filteredLoad) this.fetchDoctors();
    },

    async handleLogin() {
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value.trim();

        if (username.length < 3 || password.length < 3) {
            alert("Enter valid username and password");
            return;
        }

        const res = await fetch(`${this.config.apiUrl}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        if (!res.ok) {
            alert("Invalid credentials");
            return;
        }

        const data = await res.json();
        sessionStorage.setItem("access_token", data.access_token);
        sessionStorage.setItem("refresh_token", data.refresh_token);
        sessionStorage.setItem("username", username);

        this.state.user = username;
        document.getElementById('authScreen').classList.add('hidden');
        document.getElementById('mainApp').classList.remove('hidden');
        document.getElementById('dispName').innerText = username;
        document.getElementById('profileName').innerText = username;

        this.switchTab('home');
    },

    async handleRegister() {
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value.trim();

        if (username.length < 3 || password.length < 3) {
            alert("Enter valid username and password");
            return;
        }

        const res = await fetch(`${this.config.apiUrl}/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        if (!res.ok) {
            alert("User already exists");
            return;
        }

        alert("Registered successfully! Now login.");
    },

    renderSymptomTrendChart(symptomData) {
        const ctx = document.getElementById("symptomTrendChart");
        if (!ctx || typeof Chart === "undefined") return;

        if (window.symptomChart && typeof window.symptomChart.destroy === "function") {
            window.symptomChart.destroy();
        }

        const labels = [
            "12AM", "1AM", "2AM", "3AM", "4AM", "5AM",
            "6AM", "7AM", "8AM", "9AM", "10AM", "11AM",
            "12PM", "1PM", "2PM", "3PM", "4PM", "5PM",
            "6PM", "7PM", "8PM", "9PM", "10PM", "11PM"
        ];

        const colors = ["#127c71", "#2563eb", "#10b981", "#0f766e", "#4f8df7"];

        const datasets = symptomData.map((symptom, index) => ({
            label: symptom.name.replace("_", " "),
            data: symptom.values,
            borderColor: colors[index % colors.length],
            backgroundColor: `${colors[index % colors.length]}22`,
            fill: true,
            tension: 0.38,
            pointRadius: 3,
            pointHoverRadius: 5,
            borderWidth: 3,
            pointBackgroundColor: "#ffffff",
            pointBorderWidth: 2
        }));

        window.symptomChart = new Chart(ctx, {
            type: "line",
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        top: 14,
                        right: 14,
                        bottom: 10,
                        left: 6
                    }
                },
                interaction: {
                    mode: "index",
                    intersect: false
                },
                plugins: {
                    legend: {
                        position: "top",
                        labels: {
                            usePointStyle: true,
                            boxWidth: 12,
                            padding: 18,
                            color: "#405265",
                            font: {
                                size: 12,
                                weight: "600"
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: "rgba(15, 23, 42, 0.92)",
                        titleColor: "#f8fafc",
                        bodyColor: "#e2e8f0",
                        cornerRadius: 16,
                        padding: 12,
                        displayColors: true,
                        boxPadding: 4,
                        titleFont: {
                            size: 12,
                            weight: "700"
                        },
                        bodyFont: {
                            size: 12
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: {
                            color: "#6b7c8f",
                            maxRotation: 0,
                            autoSkip: true
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0,
                            color: "#6b7c8f",
                            padding: 10
                        },
                        grid: { color: "rgba(18, 124, 113, 0.10)" }
                    }
                }
            }
        });
    },

    enableVoiceMode() {
        voiceModeEnabled = true;
        this.renderVoiceControls();
        this.updateVoiceUI("idle");
    },

    disableVoiceMode() {
        voiceModeEnabled = false;
        if (recorder && recorder.state === "recording") {
            recorder.onstop = null;
            recorder.stop();
        }
        isRecording = false;
        setVoiceProcessing(false);
        chunks = [];
        recorder = null;
        this.updateVoiceUI("idle");
        this.renderVoiceControls();

        stopMicStream();
    },

    async handleChatSubmit() {
        const input = document.getElementById('chatInput');
        const text = input.value.trim();
        if (!text || isChatSubmitting) return;

        isChatSubmitting = true;
        this.appendMessage('user', text);
        input.value = '';

        const thinkingId = this.appendMessage('ai', 'Thinking...');

        try {
            const username = sessionStorage.getItem("username");
            const response = await this.authFetch(`${this.config.apiUrl}/predict`, {
                method: 'POST',
                body: JSON.stringify({
                    symptoms: [text],
                    user_id: username
                })
            });

            const data = await response.json();

            if (data.followup_question) {
                this.updateMessage(thinkingId, data.followup_question);
                if (voiceModeEnabled) {
                    this.deepgramSpeak(data.followup_question);
                }
                return;
            }

            const message = `${data.explanation || "Based on your symptoms:"} I recommend consulting a ${data.specialist}. (Confidence: ${data.confidence})`;
            this.updateMessage(thinkingId, message);
            if (voiceModeEnabled) {
                this.deepgramSpeak(message);
            }

            this._filteredLoad = true;
            const docRes = await fetch(`${this.config.apiUrl}/doctors?specialty=${data.specialist_key}`);
            const docData = await docRes.json();
            this.appendDoctorCards(docData.doctors || []);
            this._filteredLoad = false;
        } catch (error) {
            this._filteredLoad = false;
            this.updateMessage(thinkingId, "Backend connection error.");
        } finally {
            isChatSubmitting = false;
        }
    },

    appendMessage(role, text) {
        const container = document.getElementById('chatWindow');
        const div = document.createElement('div');

        div.className = role === 'user'
            ? "mb-3 ml-auto max-w-[85%] rounded-[24px] rounded-br-md bg-[linear-gradient(135deg,#127c71,#19a08d)] px-4 py-3 text-sm leading-6 text-white shadow-lg shadow-emerald-100"
            : "mb-3 max-w-[85%] rounded-[24px] rounded-bl-md bg-[var(--bg-soft)] px-4 py-3 text-sm leading-6 text-slate-700";

        div.innerText = text;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        return div;
    },

    resetChat() {
        const chat = document.getElementById("chatWindow");
        chat.innerHTML = `
            <div class="rounded-2xl bg-[var(--bg-soft)] p-4 text-sm leading-6 text-slate-500">
                Conversation reset. Describe symptoms again.
            </div>
        `;
    },

    updateMessage(element, text) {
        if (element) element.innerText = text;
    },

    async deepgramSpeak(text) {
        try {
            isAISpeaking = true;
            stopRecording();
            this.updateVoiceUI("idle");

            const res = await fetch(`${this.config.apiUrl}/text-to-voice`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text })
            });

            if (!res.ok) {
                isAISpeaking = false;
                return;
            }

            const audioBlob = await res.blob();
            if (!audioBlob || audioBlob.size === 0) {
                isAISpeaking = false;
                return;
            }

            const audio = new Audio(URL.createObjectURL(audioBlob));
            audio.oncanplaythrough = () => audio.play();
            audio.onended = () => {
                isAISpeaking = false;
                this.updateVoiceUI("idle");
            };
            audio.onerror = () => {
                isAISpeaking = false;
                this.updateVoiceUI("idle");
            };
        } catch (err) {
            console.error("deepgramSpeak error:", err);
            isAISpeaking = false;
            this.updateVoiceUI("idle");
        }
    },

    async fetchDoctorsBySpecialty(specialtyKey) {
        const grid = document.getElementById('doctorGrid');
        grid.innerHTML = "<p class='rounded-3xl bg-white p-5 text-sm text-slate-500 shadow-sm'>Loading doctors...</p>";

        try {
            const response = await fetch(`${this.config.apiUrl}/doctors?specialty=${specialtyKey}`);
            const data = await response.json();

            if (!data.doctors || data.doctors.length === 0) {
                grid.innerHTML = "<p class='rounded-3xl bg-white p-5 text-sm text-slate-500 shadow-sm'>No doctors found for this specialty.</p>";
                return;
            }

            this.renderDoctors(data.doctors);
        } catch (error) {
            grid.innerHTML = "<p class='rounded-3xl bg-rose-50 p-5 text-sm text-rose-600'>Failed to load doctors.</p>";
        }
    },

    renderDoctors(doctors) {
        const grid = document.getElementById('doctorGrid');
        this.cacheDoctors(doctors);
        grid.innerHTML = doctors.map(doc => `
            <article
                class="cursor-pointer rounded-[28px] border border-[rgba(18,124,113,0.10)] bg-white p-5 shadow-sm transition hover:-translate-y-1 hover:shadow-lg"
                onclick="App.openDoctorModal('${escapeHtml(this.getDoctorId(doc))}')"
            >
                <div class="flex items-start gap-4">
                    <img class="doctor-card-image" src="${escapeHtml(doc.image)}" alt="${escapeHtml(doc.name)}">
                    <div class="min-w-0 flex-1">
                        <div class="flex flex-wrap items-start justify-between gap-3">
                            <div>
                                <p class="text-xs uppercase tracking-[0.22em] text-slate-400">Specialist</p>
                                <h4 class="mt-2 text-xl font-semibold text-slate-900">${escapeHtml(doc.name)}</h4>
                            </div>
                            <div class="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                                ${doc.rating} rating
                            </div>
                        </div>
                        <p class="mt-3 text-sm font-medium capitalize text-[var(--accent-deep)]">${escapeHtml(doc.specialty.replaceAll("_", " "))}</p>
                        <p class="mt-2 text-sm text-slate-500">${escapeHtml(doc.hospital || "Care Center")}</p>
                        <p class="mt-1 text-sm text-slate-500">${escapeHtml(doc.location)}</p>
                    </div>
                </div>
                <div class="mt-5 flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span class="text-xs uppercase tracking-[0.2em] text-slate-400">Consultation</span>
                    <span class="text-sm font-semibold text-slate-900">INR ${doc.fees}</span>
                </div>
                <div class="mt-3 flex items-center justify-between text-xs uppercase tracking-[0.18em] text-slate-400">
                    <span>${escapeHtml(doc.gender || "Doctor")}</span>
                    <span>${escapeHtml(this.config.defaultCity)}</span>
                </div>
            </article>
        `).join('');
    },

    formatDoctorCard(doc) {
        const doctorId = this.getDoctorId(doc);
        return `
            <div
                class="cursor-pointer rounded-[24px] border border-[rgba(18,124,113,0.10)] bg-white p-4 shadow-sm transition hover:-translate-y-1 hover:shadow-lg"
                onclick="App.openDoctorModal('${escapeHtml(doctorId)}')"
            >
                <div class="flex items-start gap-3">
                    <img class="doctor-card-image h-14 w-14 rounded-2xl" src="${escapeHtml(doc.image)}" alt="${escapeHtml(doc.name)}">
                    <div class="min-w-0 flex-1">
                        <div class="flex items-start justify-between gap-3">
                            <div>
                                <div class="text-base font-semibold text-slate-900">${escapeHtml(doc.name)}</div>
                                <div class="mt-1 text-sm capitalize text-[var(--accent-deep)]">${escapeHtml(doc.specialty.replaceAll("_", " "))}</div>
                            </div>
                            <div class="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700">
                                ${doc.rating}
                            </div>
                        </div>
                        <div class="mt-3 text-sm text-slate-500">${escapeHtml(doc.hospital || "Care Center")}</div>
                        <div class="mt-1 text-sm text-slate-500">${escapeHtml(doc.location)}</div>
                        <div class="mt-2 text-sm font-medium text-slate-800">INR ${doc.fees}</div>
                    </div>
                </div>
            </div>
        `;
    },

    appendDoctorCards(doctors) {
        const container = document.getElementById('chatWindow');
        const wrapper = document.createElement("div");
        wrapper.className = "mb-3 max-w-[92%] rounded-[26px] bg-white p-4 shadow-sm";
        this.cacheDoctors(doctors);

        wrapper.innerHTML = doctors.length
            ? `
                <div class="mb-3 flex items-center justify-between gap-3">
                    <div>
                        <div class="text-xs uppercase tracking-[0.22em] text-slate-400">Care options</div>
                        <div class="mt-1 text-lg font-semibold text-slate-900">Available Doctors</div>
                    </div>
                    <div class="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                        ${doctors.length} matches
                    </div>
                </div>
                ${doctors.map(doc => this.formatDoctorCard(doc)).join("")}
            `
            : `
                <div class="rounded-2xl bg-[var(--bg-soft)] p-4 text-sm text-slate-500">
                    No doctors were found for this recommendation.
                </div>
            `;

        container.appendChild(wrapper);
        container.scrollTop = container.scrollHeight;
    },

    getDoctorId(doc) {
        return String(doc.id || doc.name || Math.random()).toLowerCase().replace(/\s+/g, "_");
    },

    cacheDoctors(doctors = []) {
        doctors.forEach((doc) => {
            const doctorId = this.getDoctorId(doc);
            this.state.doctorDirectory[doctorId] = {
                ...doc,
                id: doctorId,
                contact: doc.contact || "+91 98765 43210"
            };
        });
    },

    openDoctorModal(doctorId) {
        const doctor = this.state.doctorDirectory[doctorId];
        const modal = document.getElementById("doctorDetailModal");
        const content = document.getElementById("doctorModalContent");

        if (!doctor || !modal || !content) return;

        const specialty = String(doctor.specialty || "general_physician").replaceAll("_", " ");
        content.innerHTML = `
            <div class="grid gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
                <div class="rounded-[28px] bg-white/10 p-4 backdrop-blur-sm">
                    <img class="h-64 w-full rounded-[24px] object-cover shadow-lg shadow-slate-900/20" src="${escapeHtml(doctor.image)}" alt="${escapeHtml(doctor.name)}">
                </div>
                <div>
                    <div class="flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <p class="text-xs uppercase tracking-[0.28em] text-white/65">Doctor profile</p>
                            <h3 class="mt-2 text-3xl font-semibold text-white">${escapeHtml(doctor.name)}</h3>
                            <p class="mt-3 text-base capitalize text-emerald-100">${escapeHtml(specialty)}</p>
                        </div>
                        <div class="rounded-full bg-white/12 px-4 py-2 text-sm font-semibold text-white/90">
                            ${escapeHtml(String(doctor.rating || "N/A"))} rating
                        </div>
                    </div>

                    <div class="mt-6 grid gap-3 sm:grid-cols-2">
                        <div class="rounded-2xl bg-white/10 px-4 py-3">
                            <div class="text-xs uppercase tracking-[0.2em] text-white/55">Hospital</div>
                            <div class="mt-2 text-sm font-medium text-white">${escapeHtml(doctor.hospital || "Care Center")}</div>
                        </div>
                        <div class="rounded-2xl bg-white/10 px-4 py-3">
                            <div class="text-xs uppercase tracking-[0.2em] text-white/55">Location</div>
                            <div class="mt-2 text-sm font-medium text-white">${escapeHtml(doctor.location || this.config.defaultCity)}</div>
                        </div>
                        <div class="rounded-2xl bg-white/10 px-4 py-3">
                            <div class="text-xs uppercase tracking-[0.2em] text-white/55">Consultation Fee</div>
                            <div class="mt-2 text-sm font-medium text-white">INR ${escapeHtml(String(doctor.fees || "N/A"))}</div>
                        </div>
                        <div class="rounded-2xl bg-white/10 px-4 py-3">
                            <div class="text-xs uppercase tracking-[0.2em] text-white/55">Gender</div>
                            <div class="mt-2 text-sm font-medium text-white">${escapeHtml(doctor.gender || "Not specified")}</div>
                        </div>
                        <div class="rounded-2xl bg-white/10 px-4 py-3 sm:col-span-2">
                            <div class="text-xs uppercase tracking-[0.2em] text-white/55">Contact</div>
                            <div class="mt-2 text-sm font-medium text-white">${escapeHtml(doctor.contact)}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        modal.classList.remove("hidden");
        document.body.classList.add("overflow-hidden");
    },

    closeDoctorModal() {
        const modal = document.getElementById("doctorDetailModal");
        if (!modal) return;
        modal.classList.add("hidden");
        document.body.classList.remove("overflow-hidden");
    },

    updateVoiceUI(state = "idle") {
        const indicator = document.getElementById("voiceStatus");
        const startButton = document.getElementById("voiceStartBtn");
        const stopButton = document.getElementById("voiceStopBtn");
        const disableButton = document.getElementById("voiceDisableBtn");
        const enableButton = document.getElementById("voiceEnableBtn");

        if (!indicator) return;

        if (state === "listening") {
            indicator.textContent = "Listening...";
            indicator.className = "rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700";
        } else if (state === "processing") {
            indicator.textContent = "Processing...";
            indicator.className = "rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-700";
        } else {
            indicator.textContent = voiceModeEnabled ? "Voice mode is active. Use Start Recording when you're ready." : "Voice mode is off. Tap Start Voice Mode to begin.";
            indicator.className = "rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-500";
        }

        if (enableButton) {
            enableButton.disabled = isVoiceProcessing || isAISpeaking;
            enableButton.classList.toggle("opacity-60", enableButton.disabled);
            enableButton.classList.toggle("cursor-not-allowed", enableButton.disabled);
        }

        if (startButton) {
            startButton.disabled = isRecording || isVoiceProcessing || isAISpeaking;
            startButton.classList.toggle("opacity-60", startButton.disabled);
            startButton.classList.toggle("cursor-not-allowed", startButton.disabled);
        }

        if (stopButton) {
            stopButton.disabled = !isRecording || isVoiceProcessing;
            stopButton.classList.toggle("opacity-60", stopButton.disabled);
            stopButton.classList.toggle("cursor-not-allowed", stopButton.disabled);
        }

        if (disableButton) {
            disableButton.disabled = isVoiceProcessing;
            disableButton.classList.toggle("opacity-60", disableButton.disabled);
            disableButton.classList.toggle("cursor-not-allowed", disableButton.disabled);
        }
    },

    normalizeSymptomToken(value) {
        return String(value || "")
            .toLowerCase()
            .replace(/[^a-z,\s_-]/g, " ")
            .replace(/\s+/g, " ")
            .trim();
    },

    sanitizeSymptoms(symptomsArray) {
        const removedTerms = [];
        const cleanedSymptoms = symptomsArray
            .map(symptom => this.normalizeSymptomToken(symptom))
            .filter(symptom => {
                if (!symptom) return false;

                const isBlocked = this.config.blockedReportTerms.some(term => symptom.includes(term));
                if (isBlocked) {
                    removedTerms.push(symptom);
                    return false;
                }

                return true;
            });

        return {
            cleanedSymptoms: [...new Set(cleanedSymptoms)],
            removedTerms
        };
    },

    setCommunityWarning(message = "") {
        const warning = document.getElementById("communityWarning");
        if (!warning) return;

        if (!message) {
            warning.textContent = "";
            warning.classList.add("hidden");
            return;
        }

        warning.textContent = message;
        warning.classList.remove("hidden");
    },

    clearCommunityInput() {
        const input = document.getElementById("communitySymptoms");
        if (input) input.value = "";
    },

    async submitReport(symptomsArray) {
        try {
            const { cleanedSymptoms, removedTerms } = this.sanitizeSymptoms(symptomsArray);

            if (removedTerms.length > 0) {
                this.setCommunityWarning(`Ignored non-medical terms: ${removedTerms.join(", ")}`);
            } else {
                this.setCommunityWarning("");
            }

            if (cleanedSymptoms.length === 0) {
                alert("Please enter valid symptoms only (e.g., fever, cough).");
                return;
            }

            const response = await this.authFetch(`${this.config.apiUrl}/report`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symptoms: cleanedSymptoms,
                    city: this.config.defaultCity
                })
            });

            if (!response.ok) {
                const err = await response.json();
                alert(err.detail || "Failed to submit report");
                return;
            }

            const data = await response.json();
            const health = data.updated_city_health;
            if (health) this.updateCityUI(health);
            this.clearCommunityInput();
        } catch (error) {
            console.error("Submit error:", error);
            alert("Network or frontend error");
        }
    },

    async loadCityHealth() {
        try {
            const response = await fetch(`${this.config.apiUrl}/city-health/${this.config.defaultCity}`);
            const data = await response.json();
            this.updateCityUI(data);
        } catch (error) {
            console.error("City health load failed", error);
        }
    },

    async loadHealthNews() {
        const feed = document.getElementById('newsFeed');
        if (!feed) return;

        feed.innerHTML = `
            <div class="rounded-2xl bg-white p-4 text-sm leading-6 text-slate-500 shadow-sm">
                Loading live global health news...
            </div>
        `;

        try {
            const debugEl = document.getElementById('newsDebug');
            if (debugEl) {
                debugEl.textContent = `Requesting ${this.config.apiUrl}/news/health`;
            }

            const response = await fetch(`${this.config.apiUrl}/news/health`);
            if (!response.ok) {
                throw new Error(`News API returned ${response.status}`);
            }
            const data = await response.json();
            this.state.healthNews = data.articles || [];
            this.renderHealthNews(this.state.healthNews, data.message, data.configured !== false);

            if (debugEl) {
                debugEl.textContent = `Loaded ${this.state.healthNews.length} headlines from ${this.config.apiUrl}/news/health`;
            }
        } catch (error) {
            console.error("Health news load failed", error);
            this.renderHealthNews([], `Failed to load live health news. ${error.message || ""}`.trim(), true);

            const debugEl = document.getElementById('newsDebug');
            if (debugEl) {
                debugEl.textContent = `News request failed: ${error.message || error}`;
            }
        }
    },

    renderHealthNews(articles, message = "", isConfigured = true) {
        const feed = document.getElementById('newsFeed');
        if (!feed) return;

        if (!articles || articles.length === 0) {
            const detail = message || (isConfigured
                ? "No live health headlines are available right now."
                : "Add a news API key to enable the global health feed.");

            feed.innerHTML = `
                <div class="rounded-2xl bg-white p-4 text-sm leading-6 text-slate-500 shadow-sm">
                    ${detail}
                </div>
            `;
            return;
        }

        feed.innerHTML = articles.slice(0, 5).map(article => {
            const published = article.published_at
                ? new Date(article.published_at).toLocaleString()
                : "Latest";

            return `
                <article class="rounded-[24px] border border-[rgba(18,124,113,0.08)] bg-white p-4 shadow-sm">
                    <div class="flex items-center justify-between gap-3">
                        <div class="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                            ${escapeHtml(article.source || "Health News")}
                        </div>
                        <div class="text-xs uppercase tracking-[0.18em] text-slate-400">
                            ${escapeHtml(published)}
                        </div>
                    </div>
                    <h4 class="mt-3 text-base font-semibold leading-6 text-slate-900">${escapeHtml(article.title)}</h4>
                    <p class="mt-2 text-sm leading-6 text-slate-500">${escapeHtml(article.description || "")}</p>
                    <a
                        class="mt-4 inline-flex rounded-2xl bg-[var(--bg-soft)] px-4 py-2 text-sm font-semibold text-[var(--accent-deep)] transition hover:bg-emerald-50"
                        href="${escapeHtml(article.url)}"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        Read article
                    </a>
                </article>
            `;
        }).join('');
    },

    updateCityUI(health) {
        document.getElementById('healthScore').innerText = health.health_score;

        if (document.getElementById('healthStatus')) {
            document.getElementById('healthStatus').innerText = health.status;
        }

        const list = document.getElementById("diseaseList");
        if (list && health.top_diseases) {
            list.innerHTML = "";
            health.top_diseases.forEach(([name, count]) => {
                const li = document.createElement("li");
                li.innerHTML = `
                    <div class="flex items-center justify-between rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3">
                        <span class="font-medium text-slate-700">${name}</span>
                        <span class="rounded-full bg-white px-3 py-1 text-sm font-bold text-slate-900 shadow-sm">${count}</span>
                    </div>
                `;
                list.appendChild(li);
            });
        }

        if (health.symptom_trends && health.symptom_trends.length > 0) {
            this.renderSymptomTrendChart(health.symptom_trends);
        }
    },

    async requestJoin(groupId) {
        await this.authFetch(`${this.config.apiUrl}/groups/request`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ group_id: groupId })
        });

        alert("Join request sent!");
    },

    async resetConversation() {
        await this.authFetch(`${this.config.apiUrl}/predict`, {
            method: "POST",
            body: JSON.stringify({
                symptoms: ["reset"],
                user_id: sessionStorage.getItem("username")
            })
        });

        this.resetChat();
    },

    async viewRequests(groupId) {
        const res = await fetch(`${this.config.apiUrl}/groups/requests/${groupId}`);
        const requests = await res.json();

        if (!requests.length) {
            alert("No pending requests.");
            return;
        }

        const list = requests.map(r => `${r.user_id}`).join("\n");
        const approveUser = prompt(`Pending Requests:\n${list}\n\nEnter username to approve:`);
        if (!approveUser) return;

        await fetch(`${this.config.apiUrl}/groups/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                group_id: groupId,
                user_id: approveUser
            })
        });

        alert("User approved!");
        this.fetchUserGroups();
    },

    async fetchUserGroups() {
        const container = document.getElementById('groupList');
        container.innerHTML = "<div class='rounded-3xl bg-white p-5 text-sm text-slate-500 shadow-sm'>Loading groups...</div>";

        const res = await fetch(`${this.config.apiUrl}/groups/all`);
        const groups = await res.json();

        if (!groups.length) {
            container.innerHTML = "<p class='rounded-3xl bg-white p-5 text-sm text-slate-500 shadow-sm'>No groups available.</p>";
            return;
        }

        container.innerHTML = groups.map(g => {
            const isMember = g.members.includes(this.state.user);
            const isAdmin = g.created_by === this.state.user;

            let actionButton = "";
            if (isMember) {
                actionButton = `
                    <button onclick="App.openGroup('${g.id}', '${g.name}')"
                            class="rounded-2xl bg-[linear-gradient(135deg,var(--accent),#19a08d)] px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-emerald-200">
                        Open
                    </button>
                `;
            } else {
                actionButton = `
                    <button onclick="App.requestJoin('${g.id}')"
                            class="rounded-2xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-emerald-100">
                        Request to Join
                    </button>
                `;
            }

            let adminPanel = "";
            if (isAdmin) {
                adminPanel = `
                    <button onclick="App.viewRequests('${g.id}')"
                            class="rounded-2xl bg-rose-50 px-4 py-2.5 text-sm font-semibold text-rose-600">
                        View Requests
                    </button>
                `;
            }

            return `
                <div class="rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm">
                    <div class="flex items-start justify-between gap-4">
                        <div>
                            <div class="text-xs uppercase tracking-[0.22em] text-slate-400">Support group</div>
                            <h4 class="mt-2 text-lg font-semibold text-slate-900">${g.name}</h4>
                        </div>
                        <div class="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">${g.members.length} members</div>
                    </div>
                    <div class="mt-4 flex flex-wrap items-center gap-2">
                        ${actionButton}
                        ${adminPanel}
                    </div>
                </div>
            `;
        }).join('');
    },

    async showCreateGroupForm() {
        const name = prompt("Enter group name:");
        if (!name) return;

        await this.authFetch(`${this.config.apiUrl}/groups/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                disease_tag: ""
            })
        });

        this.fetchUserGroups();
    },

    renderGroupMessage(message, sender) {
        const ownMessage = sender === this.state.user;
        return `
            <div class="mb-3 flex ${ownMessage ? 'justify-end' : 'justify-start'}">
                <div class="${ownMessage ? 'bg-[linear-gradient(135deg,#127c71,#19a08d)] text-white' : 'bg-[var(--bg-soft)] text-slate-700'} max-w-[85%] rounded-[22px] px-4 py-3 text-sm leading-6 shadow-sm">
                    <div class="mb-1 text-xs font-semibold uppercase tracking-[0.18em] ${ownMessage ? 'text-white/75' : 'text-slate-400'}">${sender}</div>
                    <div>${message}</div>
                </div>
            </div>
        `;
    },

    openGroup(groupId, groupName) {
        this.state.activeGroup = groupId;
        document.getElementById('activeGroupName').innerText = groupName;
        document.getElementById('groupChatPanel').classList.remove('hidden');
        document.getElementById('groupChatWindow').innerHTML = "";
        this.loadGroupMessages();

        if (this.socket) {
            this.socket.close();
        }

        const token = sessionStorage.getItem("access_token");
        this.socket = new WebSocket(`ws://localhost:8000/ws/groups/${groupId}?token=${token}`);

        this.socket.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            const container = document.getElementById('groupChatWindow');
            container.innerHTML += this.renderGroupMessage(msg.message, msg.sender);
            container.scrollTop = container.scrollHeight;
        };

        this.socket.onclose = () => {
            console.log("WebSocket disconnected");
        };

        this.socket.onerror = (error) => {
            console.error("WebSocket error:", error);
        };
    },

    async loadGroupMessages() {
        if (!this.state.activeGroup) return;

        const res = await fetch(`${this.config.apiUrl}/groups/messages/${this.state.activeGroup}`);
        const messages = await res.json();
        const container = document.getElementById('groupChatWindow');

        container.innerHTML = messages.map(m => this.renderGroupMessage(m.message, m.sender)).join('');
        container.scrollTop = container.scrollHeight;
    },

    async sendGroupMessage() {
        const input = document.getElementById("groupMessageInput");
        const message = input.value.trim();
        if (!message || !this.socket) return;

        this.socket.send(JSON.stringify({ message }));
        input.value = "";
    },

    async authFetch(url, options = {}) {
        if (url.includes("/auth/login") || url.includes("/auth/register")) {
            return fetch(url, options);
        }

        let token = sessionStorage.getItem("access_token");
        if (!token) {
            alert("Session expired. Please login again.");
            window.location.reload();
            return;
        }

        options.headers = {
            ...(options.headers || {}),
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
        };

        let response = await fetch(url, options);

        if (response.status === 401) {
            const refresh = sessionStorage.getItem("refresh_token");
            if (!refresh) {
                alert("Session expired. Please login again.");
                sessionStorage.clear();
                window.location.reload();
                return;
            }

            const refreshRes = await fetch(`${this.config.apiUrl}/auth/refresh`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ refresh_token: refresh })
            });

            if (!refreshRes.ok) {
                alert("Session expired. Please login again.");
                sessionStorage.clear();
                window.location.reload();
                return;
            }

            const data = await refreshRes.json();
            sessionStorage.setItem("access_token", data.access_token);
            sessionStorage.setItem("refresh_token", data.refresh_token);
            options.headers["Authorization"] = `Bearer ${data.access_token}`;
            response = await fetch(url, options);
        }

        return response;
    },

    async fetchDoctors() {
        const grid = document.getElementById('doctorGrid');
        grid.innerHTML = "<div class='rounded-3xl bg-white p-5 text-sm text-slate-500 shadow-sm'>Loading doctors...</div>";

        try {
            const res = await fetch(`${this.config.apiUrl}/doctors`);
            const data = await res.json();

            if (!data.doctors || data.doctors.length === 0) {
                grid.innerHTML = "<p class='rounded-3xl bg-white p-5 text-sm text-slate-500 shadow-sm'>No doctors available.</p>";
                return;
            }

            this.renderDoctors(data.doctors);
        } catch (err) {
            grid.innerHTML = "<p class='rounded-3xl bg-rose-50 p-5 text-sm text-rose-600'>Failed to load doctors.</p>";
        }
    }
};

let globalMicStream = null;
let recorder = null;
let isRecording = false;
let isAISpeaking = false;
let voiceModeEnabled = false;
let micInitialized = false;
let chunks = [];
let isVoiceProcessing = false;
let isChatSubmitting = false;

App.init();

window.switchTab = (id) => App.switchTab(id);
window.handleLogin = () => App.handleLogin();
window.handleChatSubmit = () => App.handleChatSubmit();
window.closeDoctorModal = () => App.closeDoctorModal();

function stopMicStream() {
    if (globalMicStream) {
        globalMicStream.getTracks().forEach(track => track.stop());
        globalMicStream = null;
    }
    micInitialized = false;
}

function setVoiceProcessing(value) {
    isVoiceProcessing = value;
    App.updateVoiceUI(value ? "processing" : (isRecording ? "listening" : "idle"));
}

async function startRecording() {
    if (!voiceModeEnabled || isAISpeaking || isRecording || isVoiceProcessing) return;

    try {
        if (!micInitialized) {
            globalMicStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            micInitialized = true;
        }

        chunks = [];
        recorder = new MediaRecorder(globalMicStream, {
            mimeType: "audio/webm;codecs=opus",
            audioBitsPerSecond: 16000
        });

        recorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                chunks.push(e.data);
            }
        };

        recorder.onstop = async () => {
            isRecording = false;
            App.updateVoiceUI("processing");

            try {
                const blob = new Blob(chunks, { type: "audio/webm" });
                if (!blob.size) {
                    setVoiceProcessing(false);
                    return;
                }

                const formData = new FormData();
                formData.append("file", blob, "audio.webm");
                setVoiceProcessing(true);

                const res = await fetch(`${App.config.apiUrl}/voice-to-text`, {
                    method: "POST",
                    body: formData
                });

                if (!res.ok) {
                    console.error("Voice transcription API error:", res.status);
                    return;
                }

                const data = await res.json();
                if (!data.text || data.text.trim() === "") {
                    setVoiceProcessing(false);
                    stopMicStream();
                    return;
                }

                document.getElementById("chatInput").value = data.text;
                if (!voiceModeEnabled) {
                    setVoiceProcessing(false);
                    stopMicStream();
                    return;
                }

                await App.handleChatSubmit();
            } catch (err) {
                console.error("Transcription failed:", err);
            } finally {
                setVoiceProcessing(false);
                stopMicStream();
                recorder = null;
            }
        };

        recorder.start(250);
        isRecording = true;
        App.updateVoiceUI("listening");
    } catch (err) {
        console.error("Mic access error:", err);
        isRecording = false;
        setVoiceProcessing(false);
        stopMicStream();
    }
}

function stopRecording() {
    if (isRecording && recorder && recorder.state === "recording") {
        recorder.stop();
    }
}
