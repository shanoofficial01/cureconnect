/* CureConnect - Visual Identity System 
    Focus: Glassmorphism, Premium Typography, and Micro-interactions
*/

:root {
    --brand-blue: #2563eb;
    --emerald-safe: #10b981;
    --glass-bg: rgba(255, 255, 255, 0.7);
}

/* 1. Custom Smooth Scrolling & Scrollbar */
html {
    scroll-behavior: smooth;
}

::-webkit-scrollbar {
    width: 5px;
}

::-webkit-scrollbar-track {
    background: transparent;
}

::-webkit-scrollbar-thumb {
    background: #e2e8f0;
    border-radius: 10px;
}

.dark ::-webkit-scrollbar-thumb {
    background: #1e293b;
}

/* 2. Glassmorphic Navigation */
nav {
    backdrop-filter: blur(12px) saturate(180%);
    -webkit-backdrop-filter: blur(12px) saturate(180%);
}

/* 3. ChatGPT-style Chat Bubbles */
#chatWindow div {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

/* 4. The Shimmer Loading Effect (For Commercial Wait Times) */
.shimmer {
    background: linear-gradient(
        90deg, 
        rgba(255,255,255,0) 0%, 
        rgba(255,255,255,0.6) 50%, 
        rgba(255,255,255,0) 100%
    );
    background-color: #f1f5f9; /* Fallback for light mode */
    background-size: 200% 100%;
    animation: shimmer-swipe 1.6s infinite linear;
}

.dark .shimmer {
    background-color: #0f172a;
    background-image: linear-gradient(
        90deg, 
        rgba(15,23,42,0) 0%, 
        rgba(30,41,59,0.8) 50%, 
        rgba(15,23,42,0) 100%
    );
}

@keyframes shimmer-swipe {
    to { background-position: 200% 0; }
}

/* 5. Tab Transition Animations */
.view-section {
    transition: opacity 0.4s ease, transform 0.4s ease;
}

.active-tab svg {
    transform: translateY(-2px);
    filter: drop-shadow(0 4px 6px rgba(37, 99, 235, 0.3));
    transition: all 0.3s ease;
}

/* 6. Card Hover Effects */
.bg-white, .dark .bg-slate-900 {
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

#doctorGrid > div:hover {
    transform: translateY(-4px);
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

/* 7. Bottom Nav Icon Sizing for Mobile */
@media (max-width: 640px) {
    nav button span {
        font-size: 8px;
        letter-spacing: 0.05em;
    }
}

/* 8. Pulse for the Live Health Score */
.pulse-emerald {
    animation: pulse-ring 2s infinite;
}

@keyframes pulse-ring {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
    70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}
