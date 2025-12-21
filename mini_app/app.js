/**
 * Telegram Mini App - Real-time Voice Assistant
 * Для голосового общения на стройплощадке
 */

// ============================================================================
// Константы и конфигурация
// ============================================================================

const CONFIG = {
    // WebSocket URL (замените на ваш сервер)
    WS_URL: window.location.hostname === 'localhost'
        ? 'ws://localhost:8080/stream/'
        : 'wss://websocket-proxy-production.up.railway.app/stream/',

    // Аудио параметры
    AUDIO: {
        sampleRate: 16000,        // Gemini требует 16kHz
        channelCount: 1,          // Mono
        chunkDuration: 100,       // Отправка каждые 100ms
        vadThreshold: 30,         // Порог обнаружения голоса
        noiseFilterFreq: 200      // Частота фильтра шума (Hz)
    }
};

// ============================================================================
// Глобальные переменные
// ============================================================================

let websocket = null;
let mediaRecorder = null;
let audioContext = null;
let analyser = null;
let microphone = null;
let isRecording = false;
let isBotSpeaking = false;
let audioQueue = [];
let latencyStart = null;

// Telegram Web App API
const tg = window.Telegram.WebApp;
tg.expand();
tg.ready();

const userId = tg.initDataUnsafe?.user?.id || 'demo_user';

// ============================================================================
// DOM элементы
// ============================================================================

const elements = {
    startBtn: document.getElementById('start-btn'),
    stopBtn: document.getElementById('stop-btn'),
    statusIndicator: document.getElementById('status-indicator'),
    statusText: document.getElementById('status-text'),
    userText: document.getElementById('user-text'),
    botText: document.getElementById('bot-text'),
    voiceActivity: document.getElementById('voice-activity'),
    waveformCanvas: document.getElementById('waveform'),
    latencyDisplay: document.getElementById('latency-display'),
    qualityDisplay: document.getElementById('quality-display'),
    functionCalls: document.getElementById('function-calls'),
    functionList: document.getElementById('function-list')
};

// ============================================================================
// WebSocket управление
// ============================================================================

function connectWebSocket() {
    const wsUrl = CONFIG.WS_URL + userId;

    updateStatus('connecting', 'Подключение к серверу...');

    websocket = new WebSocket(wsUrl);
    websocket.binaryType = 'arraybuffer';

    websocket.onopen = () => {
        console.log('✅ WebSocket connected');
        updateStatus('connected', 'Подключено ✓');
        elements.qualityDisplay.textContent = 'Отлично';

        // Вибрация при подключении
        if (tg.HapticFeedback) {
            tg.HapticFeedback.impactOccurred('medium');
        }
    };

    websocket.onmessage = async (event) => {
        if (event.data instanceof ArrayBuffer) {
            // Аудио данные от бота
            await playAudioChunk(event.data);

            // Измеряем задержку
            if (latencyStart) {
                const latency = Date.now() - latencyStart;
                elements.latencyDisplay.textContent = `${latency} ms`;
                latencyStart = null;
            }
        } else {
            // JSON сообщения
            const data = JSON.parse(event.data);
            handleServerMessage(data);
        }
    };

    websocket.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        updateStatus('error', 'Ошибка соединения');
        elements.qualityDisplay.textContent = 'Плохое';
    };

    websocket.onclose = () => {
        console.log('🔌 WebSocket closed');
        updateStatus('disconnected', 'Отключено');
        stopRecording();
    };
}

function handleServerMessage(data) {
    switch (data.type) {
        case 'ready':
            console.log('✅ Server ready');
            updateStatus('ready', 'Готов к разговору');
            break;

        case 'transcript':
            // Транскрипция текста
            if (data.role === 'bot') {
                elements.botText.textContent = data.text;
                isBotSpeaking = true;
            } else {
                elements.userText.textContent = data.text;
            }
            break;

        case 'turn_complete':
            isBotSpeaking = false;
            console.log('✅ Bot finished speaking');
            break;

        case 'function_call':
            // Вызов функции
            addFunctionCall(data.function_name, data.result);
            break;

        case 'error':
            console.error('❌ Server error:', data.message);
            updateStatus('error', `Ошибка: ${data.message}`);
            break;
    }
}

// ============================================================================
// Аудио захват (микрофон)
// ============================================================================

async function startRecording() {
    try {
        // Запрашиваем доступ к микрофону
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                sampleRate: CONFIG.AUDIO.sampleRate,
                channelCount: CONFIG.AUDIO.channelCount,
                echoCancellation: true,
                noiseSuppression: true,  // Базовое шумоподавление браузера
                autoGainControl: true
            }
        });

        // Создаём AudioContext для анализа и фильтрации
        audioContext = new AudioContext({ sampleRate: CONFIG.AUDIO.sampleRate });
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 2048;

        microphone = audioContext.createMediaStreamSource(stream);

        // Добавляем фильтр для шума стройплощадки
        const noiseFilter = audioContext.createBiquadFilter();
        noiseFilter.type = 'highpass';
        noiseFilter.frequency.value = CONFIG.AUDIO.noiseFilterFreq;

        // Подключаем: микрофон → фильтр → анализатор
        microphone.connect(noiseFilter);
        noiseFilter.connect(analyser);

        // MediaRecorder для отправки аудио
        mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus'
        });

        mediaRecorder.ondataavailable = async (event) => {
            if (event.data.size > 0 && websocket?.readyState === WebSocket.OPEN) {
                // Конвертируем в PCM и отправляем
                const arrayBuffer = await event.data.arrayBuffer();

                // Отмечаем время для измерения задержки
                latencyStart = Date.now();

                websocket.send(arrayBuffer);
            }
        };

        // Отправка чанков каждые 100ms
        mediaRecorder.start(CONFIG.AUDIO.chunkDuration);
        isRecording = true;

        // Запускаем визуализацию и VAD
        startVisualization();
        startVAD();

        // UI обновление
        elements.startBtn.style.display = 'none';
        elements.stopBtn.style.display = 'block';
        updateStatus('recording', 'Слушаю... 🎤');

        console.log('🎤 Recording started');

    } catch (error) {
        console.error('❌ Microphone error:', error);
        alert('Не удалось получить доступ к микрофону. Проверьте разрешения.');
        updateStatus('error', 'Ошибка микрофона');
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }

    if (microphone) {
        microphone.mediaStream.getTracks().forEach(track => track.stop());
    }

    if (audioContext) {
        audioContext.close();
    }

    isRecording = false;

    // UI обновление
    elements.startBtn.style.display = 'block';
    elements.stopBtn.style.display = 'none';
    elements.voiceActivity.classList.remove('active');
    updateStatus('connected', 'Разговор завершён');

    // Отправляем команду остановки на сервер
    if (websocket?.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({ type: 'stop' }));
    }

    console.log('🛑 Recording stopped');
}

// ============================================================================
// Voice Activity Detection (VAD)
// ============================================================================

function startVAD() {
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    function detectVoice() {
        if (!isRecording) return;

        analyser.getByteFrequencyData(dataArray);

        // Вычисляем среднюю громкость
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;

        // Обнаружение голоса
        if (average > CONFIG.AUDIO.vadThreshold) {
            elements.voiceActivity.classList.add('active');

            // Если бот говорит - прерываем его
            if (isBotSpeaking) {
                interruptBot();
            }
        } else {
            elements.voiceActivity.classList.remove('active');
        }

        requestAnimationFrame(detectVoice);
    }

    detectVoice();
}

function interruptBot() {
    console.log('⏸️ Interrupting bot');

    // Останавливаем воспроизведение
    audioQueue = [];
    isBotSpeaking = false;

    // Отправляем команду interruption
    if (websocket?.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({ type: 'interrupt' }));
    }

    // Вибрация
    if (tg.HapticFeedback) {
        tg.HapticFeedback.impactOccurred('light');
    }
}

// ============================================================================
// Визуализация звука
// ============================================================================

function startVisualization() {
    const canvas = elements.waveformCanvas;
    const ctx = canvas.getContext('2d');
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    function draw() {
        if (!isRecording) return;

        analyser.getByteTimeDomainData(dataArray);

        ctx.fillStyle = '#1e1e1e';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.lineWidth = 2;
        ctx.strokeStyle = '#00ff88';
        ctx.beginPath();

        const sliceWidth = canvas.width / dataArray.length;
        let x = 0;

        for (let i = 0; i < dataArray.length; i++) {
            const v = dataArray[i] / 128.0;
            const y = (v * canvas.height) / 2;

            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }

            x += sliceWidth;
        }

        ctx.lineTo(canvas.width, canvas.height / 2);
        ctx.stroke();

        requestAnimationFrame(draw);
    }

    draw();
}

// ============================================================================
// Воспроизведение аудио
// ============================================================================

async function playAudioChunk(arrayBuffer) {
    try {
        if (!audioContext || audioContext.state === 'closed') {
            audioContext = new AudioContext({ sampleRate: 24000 }); // Gemini выдаёт 24kHz
        }

        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        source.start();

        console.log(`🔊 Playing audio chunk: ${arrayBuffer.byteLength} bytes`);

    } catch (error) {
        console.error('❌ Audio playback error:', error);
    }
}

// ============================================================================
// Отображение вызовов функций
// ============================================================================

function addFunctionCall(functionName, result) {
    elements.functionCalls.style.display = 'block';

    const li = document.createElement('li');
    li.innerHTML = `
        <strong>${functionName}</strong>
        <span>${JSON.stringify(result)}</span>
    `;

    elements.functionList.appendChild(li);

    // Вибрация при вызове функции
    if (tg.HapticFeedback) {
        tg.HapticFeedback.notificationOccurred('success');
    }
}

// ============================================================================
// UI обновления
// ============================================================================

function updateStatus(state, text) {
    elements.statusText.textContent = text;
    elements.statusIndicator.className = `status-indicator ${state}`;
}

// ============================================================================
// Инициализация
// ============================================================================

// Обработчики кнопок
elements.startBtn.addEventListener('click', () => {
    connectWebSocket();
    setTimeout(startRecording, 1000); // Ждём подключения WebSocket
});

elements.stopBtn.addEventListener('click', () => {
    stopRecording();
    if (websocket) {
        websocket.close();
    }
});

// Telegram кнопка "Назад"
tg.BackButton.onClick(() => {
    stopRecording();
    if (websocket) {
        websocket.close();
    }
    tg.close();
});

tg.BackButton.show();

// Готово
console.log('🚀 Voice Assistant Mini App loaded');
console.log('👤 User ID:', userId);
