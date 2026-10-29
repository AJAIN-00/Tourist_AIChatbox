// Tamil Nadu Smart Tourist Guide - Client Scripting

document.addEventListener("DOMContentLoaded", () => {
    // 1. Dark Mode Toggle & Initialization
    initDarkMode();
    
    // 2. Main Page Specific Initializations
    if (document.getElementById("placesSearchInput")) {
        initPlacesSearch();
    }
    
    if (document.getElementById("chatMessages")) {
        initChatbot();
    }
    
    if (document.getElementById("weatherContainer")) {
        initWeatherDashboard();
    }
    
    if (document.getElementById("itineraryForm")) {
        initItineraryPlanner();
    }
    
    if (document.getElementById("qrcode")) {
        initQRCodeGenerator();
    }
});

// ==================== 1. DARK MODE ====================
function initDarkMode() {
    const toggleBtn = document.getElementById("darkModeToggle");
    if (!toggleBtn) return;
    
    // Check local storage or system preference
    const savedTheme = localStorage.getItem("theme");
    const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    
    if (savedTheme === "light" || (!savedTheme && !systemPrefersDark)) {
        document.body.classList.add("light-mode");
        toggleBtn.innerHTML = '<i class="bi bi-sun-fill text-warning"></i>';
    } else {
        document.body.classList.remove("light-mode");
        toggleBtn.innerHTML = '<i class="bi bi-moon-stars-fill text-primary"></i>';
    }
    
    toggleBtn.addEventListener("click", () => {
        document.body.classList.toggle("light-mode");
        const isLight = document.body.classList.contains("light-mode");
        localStorage.setItem("theme", isLight ? "light" : "dark");
        
        if (isLight) {
            toggleBtn.innerHTML = '<i class="bi bi-sun-fill text-warning"></i>';
        } else {
            toggleBtn.innerHTML = '<i class="bi bi-moon-stars-fill text-primary"></i>';
        }
    });
}

// ==================== 2. PLACES SEARCH & FILTER ====================
function initPlacesSearch() {
    const searchInput = document.getElementById("placesSearchInput");
    const cards = document.querySelectorAll(".place-grid-card");
    
    searchInput.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        
        cards.forEach(card => {
            const name = card.getAttribute("data-name").toLowerCase();
            const desc = card.getAttribute("data-desc").toLowerCase();
            
            if (name.includes(query) || desc.includes(query)) {
                card.style.display = "";
            } else {
                card.style.display = "none";
            }
        });
    });
}

// ==================== 3. CHATBOT AND SPEECH API ====================
function initChatbot() {
    const chatInput = document.getElementById("chatInput");
    const sendBtn = document.getElementById("sendBtn");
    const chatMessages = document.getElementById("chatMessages");
    const voiceBtn = document.getElementById("voiceBtn");
    const langSelect = document.getElementById("chatLanguageSelect");
    
    if (!chatInput || !sendBtn || !chatMessages) return;

    // Send Message Trigger
    const triggerSendMessage = () => {
        const text = chatInput.value.trim();
        if (!text) return;
        
        appendChatMessage("user", text);
        chatInput.value = "";
        
        // Show Typing Indicator
        const typingIndicator = appendTypingIndicator();
        
        // Call API
        fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: text,
                language: langSelect ? langSelect.value : "en"
            })
        })
        .then(res => res.json())
        .then(data => {
            typingIndicator.remove();
            if (data.error) {
                appendChatMessage("bot", "Sorry, I encountered an issue. " + data.error);
            } else {
                appendChatMessage("bot", data.response);
            }
        })
        .catch(err => {
            typingIndicator.remove();
            appendChatMessage("bot", "Connection failed. Please check your internet connection.");
            console.error(err);
        });
    };

    sendBtn.addEventListener("click", triggerSendMessage);
    chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            triggerSendMessage();
        }
    });

    // Web Speech API (Voice Input)
    if (voiceBtn && ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        
        recognition.continuous = false;
        recognition.interimResults = false;
        
        // Determine lang preference
        recognition.onstart = () => {
            voiceBtn.classList.add("active");
            voiceBtn.innerHTML = '<i class="bi bi-mic-fill"></i>';
        };
        
        recognition.onend = () => {
            voiceBtn.classList.remove("active");
            voiceBtn.innerHTML = '<i class="bi bi-mic"></i>';
        };
        
        recognition.onresult = (e) => {
            const speechResult = e.results[0][0].transcript;
            chatInput.value = speechResult;
            chatInput.focus();
        };
        
        recognition.onerror = (e) => {
            console.error("Speech Recognition Error:", e.error);
            voiceBtn.classList.remove("active");
            voiceBtn.innerHTML = '<i class="bi bi-mic"></i>';
        };

        voiceBtn.addEventListener("click", () => {
            // Pick language code
            const langCode = langSelect ? langSelect.value : "en";
            if (langCode === "ta") {
                recognition.lang = "ta-IN";
            } else if (langCode === "hi") {
                recognition.lang = "hi-IN";
            } else if (langCode === "te") {
                recognition.lang = "te-IN";
            } else {
                recognition.lang = "en-IN";
            }
            recognition.start();
        });
    } else if (voiceBtn) {
        // Remove or disable voice button if browser lacks support
        voiceBtn.title = "Voice Input not supported in this browser";
        voiceBtn.style.opacity = "0.5";
        voiceBtn.style.cursor = "not-allowed";
    }
}

/**
 * Safely append a chat message, escaping all text and rendering newlines as <br>.
 * This prevents XSS from LLM responses or user input being injected into the DOM.
 */
function appendChatMessage(sender, text) {
    const chatMessages = document.getElementById("chatMessages");
    if (!chatMessages) return;

    const bubble = document.createElement("div");
    bubble.className = `chat-bubble chat-bubble-${sender}`;

    // Split on newlines and insert text nodes + <br> elements to avoid innerHTML XSS
    const lines = String(text).split("\n");
    lines.forEach((line, idx) => {
        bubble.appendChild(document.createTextNode(line));
        if (idx < lines.length - 1) {
            bubble.appendChild(document.createElement("br"));
        }
    });

    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendTypingIndicator() {
    const chatMessages = document.getElementById("chatMessages");
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble chat-bubble-bot";
    bubble.innerHTML = `
        <div class="d-flex gap-1 align-items-center" style="min-width: 50px; height: 20px;">
            <div class="skeleton-line m-0" style="width: 10px; height: 10px; border-radius: 50%;"></div>
            <div class="skeleton-line m-0" style="width: 10px; height: 10px; border-radius: 50%;"></div>
            <div class="skeleton-line m-0" style="width: 10px; height: 10px; border-radius: 50%;"></div>
        </div>
    `;
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return bubble;
}

// ==================== 4. WEATHER DASHBOARD ====================
function initWeatherDashboard() {
    const weatherContainer = document.getElementById("weatherContainer");
    const cities = ["chennai", "coimbatore", "kanyakumari"];
    
    weatherContainer.innerHTML = "";
    
    cities.forEach(city => {
        // Append Skeleton Cards first
        const skeletonCard = document.createElement("div");
        skeletonCard.className = "col-lg-4 col-md-6 mb-4";
        skeletonCard.id = `weather-card-${city}`;
        skeletonCard.innerHTML = `
            <div class="glass-card p-4">
                <div class="skeleton-line" style="width: 50%;"></div>
                <div class="skeleton-line" style="width: 30%; height: 35px; margin: 15px 0;"></div>
                <div class="skeleton-line" style="width: 70%;"></div>
                <div class="skeleton-line" style="width: 90%;"></div>
                <div class="skeleton-line" style="width: 80%;"></div>
            </div>
        `;
        weatherContainer.appendChild(skeletonCard);
        
        // Fetch weather
        fetch(`/weather/${city}`)
            .then(res => res.json())
            .then(data => {
                const card = document.getElementById(`weather-card-${city}`);
                if (!card) return;

                // Build DOM safely to avoid XSS from server-returned strings
                const outer = document.createElement("div");
                outer.className = "glass-card p-4 h-100 d-flex flex-column justify-content-between";

                const inner = document.createElement("div");

                const header = document.createElement("div");
                header.className = "d-flex justify-content-between align-items-center mb-3";

                const cityEl = document.createElement("h3");
                cityEl.className = "mb-0";
                cityEl.textContent = data.city || city;
                header.appendChild(cityEl);

                if (data.icon && /^[a-zA-Z0-9]+$/.test(data.icon)) {
                    const img = document.createElement("img");
                    img.src = `https://openweathermap.org/img/wn/${data.icon}@2x.png`;
                    img.width = 50;
                    img.height = 50;
                    img.alt = data.condition || "weather icon";
                    header.appendChild(img);
                }
                inner.appendChild(header);

                const tempEl = document.createElement("div");
                tempEl.className = "weather-main-temp mb-2";
                tempEl.textContent = data.temperature || "--";
                inner.appendChild(tempEl);

                const descEl = document.createElement("div");
                descEl.className = "mb-3 text-capitalize font-weight-bold";
                descEl.style.color = "var(--secondary)";
                descEl.innerHTML = '<i class="bi bi-wind"></i> ';
                descEl.appendChild(document.createTextNode(
                    `${data.description || ""} | Humidity: ${data.humidity || "--"}`
                ));
                inner.appendChild(descEl);

                const recEl = document.createElement("p");
                recEl.className = "text-muted";
                recEl.style.fontSize = "0.92rem";
                recEl.textContent = data.recommendation || "";
                inner.appendChild(recEl);

                outer.appendChild(inner);

                if (data.is_mock) {
                    const badge = document.createElement("div");
                    badge.className = "badge bg-warning text-dark mt-3 py-2";
                    badge.textContent = data.note || "Demo Seasonal Weather";
                    outer.appendChild(badge);
                }

                card.innerHTML = "";
                card.appendChild(outer);
            })
            .catch(err => {
                const card = document.getElementById(`weather-card-${city}`);
                if (card) {
                    const wrap = document.createElement("div");
                    wrap.className = "glass-card p-4";
                    const h = document.createElement("h3");
                    h.className = "text-capitalize";
                    h.textContent = city;
                    const p = document.createElement("p");
                    p.className = "text-danger mt-3";
                    p.textContent = "Could not load weather info.";
                    wrap.appendChild(h);
                    wrap.appendChild(p);
                    card.innerHTML = "";
                    card.appendChild(wrap);
                }
                console.error("Weather fetch error:", err);
            });
    });
}

// ==================== 5. ITINERARY PLANNER ====================
function initItineraryPlanner() {
    const form = document.getElementById("itineraryForm");
    const resultDiv = document.getElementById("itineraryResult");
    const pdfBtn = document.getElementById("downloadPdfBtn");
    
    if (!form || !resultDiv) return;
    
    form.addEventListener("submit", (e) => {
        e.preventDefault();
        
        const city = document.getElementById("citySelect").value;
        const days = document.getElementById("daysSelect").value;
        
        // Show Skeletons — use textContent for city to prevent XSS (F-08)
        const skeletonWrapper = document.createElement('div');
        skeletonWrapper.className = 'glass-card p-5';
        const skeletonHeading = document.createElement('h3');
        skeletonHeading.className = 'mb-4';
        skeletonHeading.textContent = 'Planning your perfect trip to ' + city + '...';
        skeletonWrapper.appendChild(skeletonHeading);
        ['90%','85%','80%','95%','70%','85%'].forEach(w => {
            const d = document.createElement('div');
            d.className = 'skeleton-line';
            d.style.width = w;
            skeletonWrapper.appendChild(d);
        });
        resultDiv.innerHTML = '';
        resultDiv.appendChild(skeletonWrapper);
        
        if (pdfBtn) pdfBtn.style.display = "none";
        
        fetch(`/itinerary/${city}/${days}`)
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    // Use textContent to prevent XSS from server error messages (F-03)
                    resultDiv.innerHTML = '';
                    const errDiv = document.createElement('div');
                    errDiv.className = 'alert alert-danger';
                    errDiv.textContent = 'Error creating itinerary: ' + data.error;
                    resultDiv.appendChild(errDiv);
                } else {
                    // Render Markdown — sanitize with DOMPurify before innerHTML (F-03)
                    const parsedHtml = formatMarkdown(data.itinerary);
                    const safeHtml = (typeof DOMPurify !== 'undefined')
                        ? DOMPurify.sanitize(parsedHtml, { USE_PROFILES: { html: true } })
                        : parsedHtml.replace(/<script[\s\S]*?<\/script>/gi, '')
                                   .replace(/on\w+\s*=/gi, '');

                    // Build the outer card safely
                    const card = document.createElement('div');
                    card.className = 'glass-card p-4 p-md-5';
                    card.id = 'itineraryPrintArea';

                    const header = document.createElement('div');
                    header.className = 'd-flex justify-content-between align-items-start border-bottom pb-3 mb-4';

                    const titleWrap = document.createElement('div');
                    const h2 = document.createElement('h2');
                    h2.className = 'heading-serif mb-1';
                    h2.textContent = data.city + ' Travel Itinerary';   // textContent — safe
                    const badge = document.createElement('span');
                    badge.className = 'badge bg-primary px-3 py-2';
                    badge.textContent = data.days + '-Day Plan';         // textContent — safe
                    titleWrap.appendChild(h2);
                    titleWrap.appendChild(badge);

                    const genLabel = document.createElement('span');
                    genLabel.className = 'text-muted';
                    genLabel.style.fontSize = '0.85rem';
                    genLabel.textContent = 'Generated by TN Smart Guide';

                    header.appendChild(titleWrap);
                    header.appendChild(genLabel);
                    card.appendChild(header);

                    const body = document.createElement('div');
                    body.className = 'itinerary-md-body';
                    body.innerHTML = safeHtml;   // DOMPurify-sanitized HTML
                    card.appendChild(body);

                    resultDiv.innerHTML = '';
                    resultDiv.appendChild(card);

                    if (pdfBtn) {
                        pdfBtn.style.display = 'inline-flex';
                        pdfBtn.onclick = () => printItinerary(data.city, data.days);
                    }
                }
            })
            .catch(err => {
                resultDiv.innerHTML = `
                    <div class="alert alert-danger">
                        Connection issue. Could not connect to itinerary planner.
                    </div>
                `;
                console.error(err);
            });
    });
}

function formatMarkdown(markdownText) {
    // Basic regex formatting for headers, bold text and bullets
    let html = markdownText
        .replace(/^### (.*$)/gim, '<h4 class="mt-4 mb-2 heading-serif text-warning">$1</h4>')
        .replace(/^## (.*$)/gim, '<h3 class="mt-4 mb-3 heading-serif border-bottom pb-2" style="color: var(--secondary);">$1</h3>')
        .replace(/^# (.*$)/gim, '<h2 class="mb-4 heading-serif">$1</h2>')
        .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/gim, '<em>$1</em>')
        .replace(/^\s*-\s*(.*$)/gim, '<li class="mb-2 text-muted">$1</li>');
        
    // Wrap lists in ul
    // A simple parser check
    html = html.replace(/(<li>.*<\/li>)/gim, '<ul>$1</ul>');
    // Clean nested ul wraps
    html = html.replace(/<\/ul>\s*<ul>/gim, '');
    
    // Replace newlines with breaks outside tags
    return html.split("\n\n").map(para => {
        if (para.trim().startsWith("<h") || para.trim().startsWith("<u")) {
            return para;
        }
        return `<p class="text-muted">${para.replace(/\n/g, "<br>")}</p>`;
    }).join("");
}

function printItinerary(city, days) {
    const printContents = document.getElementById("itineraryPrintArea").innerHTML;
    const originalContents = document.body.innerHTML;
    
    // Set up print stylesheet or custom document layout
    const printWindow = window.open("", "_blank");
    printWindow.document.write(`
        <html>
            <head>
                <title>${city} ${days}-Day Itinerary</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
                <style>
                    body { font-family: 'Segoe UI', Arial, sans-serif; padding: 40px; color: #333; }
                    .heading-serif { font-family: Georgia, serif; }
                    .border-bottom { border-bottom: 2px solid #e63946 !important; }
                    h3 { color: #d90429; margin-top: 30px; }
                    h4 { color: #e76f51; }
                    ul { padding-left: 20px; }
                    li { margin-bottom: 8px; }
                    p { font-size: 1.05rem; line-height: 1.6; }
                    @media print {
                        .no-print { display: none; }
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    ${printContents}
                    <div class="mt-5 text-center text-muted border-top pt-3 no-print">
                        <button class="btn btn-primary px-4 py-2" onclick="window.print()">Confirm Print / PDF</button>
                    </div>
                </div>
            </body>
        </html>
    `);
    printWindow.document.close();
}

// ==================== 6. QR CODE GENERATION ====================
function initQRCodeGenerator() {
    const qrDiv = document.getElementById("qrcode");
    if (!qrDiv) return;
    
    // Load current page location
    const currentUrl = window.location.href;
    
    try {
        // Generates the QR Code inside the placeholder using qrcode.js loaded in template
        new QRCode(qrDiv, {
            text: currentUrl,
            width: 130,
            height: 130,
            colorDark : "#0f172a",
            colorLight : "#ffffff",
            correctLevel : QRCode.CorrectLevel.H
        });
    } catch (e) {
        console.error("QR Code generator failed to load library:", e);
        qrDiv.innerHTML = '<span class="text-danger">Failed to generate QR Code.</span>';
    }
}
