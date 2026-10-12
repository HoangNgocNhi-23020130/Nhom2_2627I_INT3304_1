// ===== PHẦN 2: ÂM THANH =====
let audioCtx = null;
let isSoundOn = true;

function initAudio() {
    if (!audioCtx) {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) audioCtx = new AudioContext();
    }
}

function toggleSound() {
    isSoundOn = !isSoundOn;
    const icon = document.getElementById('soundIcon');
    icon.className = isSoundOn ? 'fa-solid fa-volume-high text-sky-400' : 'fa-solid fa-volume-xmark text-slate-500';
}

function playTone(freq, type = 'sine', duration = 0.1, gainVal = 0.15) {
    if (!isSoundOn) return;
    initAudio();
    if (!audioCtx) return;
    if (audioCtx.state === 'suspended') audioCtx.resume();

    try {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = type;
        osc.frequency.setValueAtTime(freq, audioCtx.currentTime);

        gain.gain.setValueAtTime(gainVal, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);

        osc.connect(gain);
        gain.connect(audioCtx.destination);

        osc.start();
        osc.stop(audioCtx.currentTime + duration);
    } catch (e) {}
}

function playMoveSound() { playTone(440, 'sine', 0.08, 0.12); }
function playCaptureSound() {
    playTone(160, 'sawtooth', 0.15, 0.22);
    setTimeout(() => playTone(320, 'triangle', 0.12, 0.18), 60);
}
function playWinSound() {
    [523.25, 659.25, 783.99, 1046.50].forEach((n, i) => {
        setTimeout(() => playTone(n, 'triangle', 0.3, 0.25), i * 110);
    });
}
function playReadySound() { playTone(587.33, 'triangle', 0.15, 0.2); }
function playSelectSound() { playTone(880, 'sine', 0.04, 0.08); }
