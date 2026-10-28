const els = {
  sessionName: document.getElementById('sessionName'),
  connectBtn: document.getElementById('connectBtn'),
  primaryActionBtn: document.getElementById('primaryActionBtn'),
  muteBtn: document.getElementById('muteBtn'),
  secondaryMuteBtn: document.getElementById('secondaryMuteBtn'),
  pttBtn: document.getElementById('pttBtn'),
  secondaryPttBtn: document.getElementById('secondaryPttBtn'),
  saveSessionBtn: document.getElementById('saveSessionBtn'),
  loadSessionBtn: document.getElementById('loadSessionBtn'),
  statusBadge: document.getElementById('statusBadge'),
  liveLabel: document.getElementById('liveLabel'),
  phaseCaption: document.getElementById('phaseCaption'),
  stateLabel: document.getElementById('stateLabel'),
  warningText: document.getElementById('warningText'),
  durationValue: document.getElementById('durationValue'),
  micStateValue: document.getElementById('micStateValue'),
  footerStatus: document.getElementById('footerStatus'),
  memoryStatusSummary: document.getElementById('memoryStatusSummary'),
  toolStatusSummary: document.getElementById('toolStatusSummary'),
  logStatusSummary: document.getElementById('logStatusSummary'),
  userTranscript: document.getElementById('userTranscript'),
  agentTranscript: document.getElementById('agentTranscript'),
  toolCalls: document.getElementById('toolCalls'),
  conversation: document.getElementById('conversation'),
  status: document.getElementById('status'),
  messages: document.getElementById('messages'),
  emptyTranscript: document.getElementById('emptyTranscript'),
  transcriptTab: document.getElementById('transcriptTab'),
  guideTab: document.getElementById('guideTab'),
  transcriptPanel: document.getElementById('transcriptPanel'),
  guidePanel: document.getElementById('guidePanel'),
  autoscrollBtn: document.getElementById('autoscrollBtn'),
  orbVisual: document.getElementById('orbVisual'),
  waveMeter: document.getElementById('waveMeter'),
};

const WAVE_BARS = 20;
for (let i = 0; i < WAVE_BARS; i++) {
  const bar = document.createElement('i');
  bar.style.height = '6px';
  els.waveMeter.appendChild(bar);
}

const state = {
  ws: null,
  sessionId: null,
  audioContext: null,
  mediaStream: null,
  mediaSource: null,
  processor: null,
  nextPlaybackTime: 0,
  inputBuffer: [],
  outputChunks: 0,
  muted: false,
  connected: false,
  connecting: false,
  lastError: '',
  currentUserDelta: '',
  currentAgentDelta: '',
  conversation: [],
  toolCalls: [],
  pendingRollover: false,
  bootstrap: null,
  volume: 0,
  speaking: false,
  startMs: null,
  timer: null,
  autoScroll: true,
  holdToTalk: false,
};

function nowLabel(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

function setStatus(text) {
  els.statusBadge.textContent = text;
  els.liveLabel.textContent = text;
  els.footerStatus.textContent = text;
}

function updateWave() {
  const bars = [...els.waveMeter.children];
  bars.forEach((bar, i) => {
    const active = (state.connected || state.connecting) ? 4 + Math.sin(i * 1.4 + state.outputChunks * 0.2) ** 2 * (8 + state.volume * 24) : 6;
    bar.style.height = `${active}px`;
  });
}

function syncButtons() {
  const live = state.connected;
  els.connectBtn.textContent = live ? 'Disconnect' : 'Connect';
  els.primaryActionBtn.textContent = live ? 'Disconnect' : 'Start';
  const mutedLabel = state.muted ? 'Unmute' : 'Mute';
  els.muteBtn.textContent = mutedLabel;
  els.secondaryMuteBtn.textContent = mutedLabel;
  const pttLabel = state.holdToTalk ? 'Release to Stop' : 'Hold to Talk';
  els.pttBtn.textContent = pttLabel;
  els.secondaryPttBtn.textContent = pttLabel;
  els.micStateValue.textContent = live ? (state.muted ? 'muted' : state.holdToTalk ? 'push-to-talk' : 'microphone on') : 'disconnected';
  els.orbVisual.style.setProperty('--voice-scale', String(1 + state.volume * 0.08));
}

function renderMessages() {
  const entries = [];
  for (const item of state.conversation) {
    if (!['user', 'agent'].includes(item.role)) continue;
    entries.push({ role: item.role, text: item.content, partial: false });
  }
  if (state.currentUserDelta) entries.push({ role: 'user', text: state.currentUserDelta, partial: true });
  if (state.currentAgentDelta) entries.push({ role: 'agent', text: state.currentAgentDelta, partial: true });

  els.messages.innerHTML = '';
  els.emptyTranscript.style.display = entries.length ? 'none' : 'flex';
  for (const m of entries) {
    const box = document.createElement('div');
    box.className = `message ${m.role}`;
    box.innerHTML = `
      <div class="message-heading">
        <span class="message-avatar ${m.role === 'agent' ? 'ai-avatar' : ''}">${m.role === 'agent' ? 'AI' : 'U'}</span>
        <span>${m.role === 'agent' ? 'Assistant' : 'You'}</span>
        ${m.partial ? '<span class="partial-indicator">speaking</span>' : ''}
      </div>
      <p></p>
    `;
    box.querySelector('p').textContent = m.text;
    els.messages.appendChild(box);
  }
  if (state.autoScroll) {
    els.transcriptPanel.scrollTop = els.transcriptPanel.scrollHeight;
  }
}

function renderSecondaryPanels() {
  const userLines = state.conversation.filter((e) => e.role === 'user').map((e) => e.content);
  const agentLines = state.conversation.filter((e) => e.role === 'agent').map((e) => e.content);
  if (els.userTranscript) {
    els.userTranscript.textContent = [...userLines, state.currentUserDelta].filter(Boolean).join('\n');
  }
  if (els.agentTranscript) {
    els.agentTranscript.textContent = [...agentLines, state.currentAgentDelta].filter(Boolean).join('\n');
  }
  els.toolCalls.textContent = state.toolCalls.length
    ? state.toolCalls.map((t) => JSON.stringify(t, null, 2)).join('\n\n')
    : 'No tool calls yet.';
  els.conversation.textContent = state.conversation.length
    ? state.conversation.map((e) => `${e.role}: ${typeof e.content === 'string' ? e.content : JSON.stringify(e.content)}`).join('\n')
    : 'No conversation yet.';

  const statusLines = [];
  statusLines.push(`session: ${state.sessionId || 'n/a'}`);
  statusLines.push(`connected: ${state.connected}`);
  statusLines.push(`muted: ${state.muted}`);
  statusLines.push(`push_to_talk: ${state.holdToTalk}`);
  statusLines.push(`output chunks: ${state.outputChunks}`);
  statusLines.push(`memory loaded: ${Boolean(state.bootstrap?.memory_context_loaded)}`);
  statusLines.push(`rollovers: ${state.bootstrap?.rollovers ?? 0}`);
  els.status.textContent = statusLines.join('\n');

  els.memoryStatusSummary.textContent = Boolean(state.bootstrap?.memory_context_loaded)
    ? `Loaded memory context for ${state.sessionId}. Rollovers: ${state.bootstrap?.rollovers ?? 0}.`
    : 'No memory context loaded yet.';
  els.toolStatusSummary.textContent = state.toolCalls.length
    ? `Latest tool: ${state.toolCalls[state.toolCalls.length - 1].name || 'tool'}.`
    : 'No tool calls yet.';
  els.logStatusSummary.textContent = state.bootstrap?.output_dir
    ? `Logs are being written under ${state.bootstrap.output_dir}.`
    : 'Session logs are written locally once connected.';
}

function render() {
  updateWave();
  syncButtons();
  renderMessages();
  renderSecondaryPanels();
}

function base64ToInt16Array(base64) {
  const binary = atob(base64);
  const len = binary.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) bytes[i] = binary.charCodeAt(i);
  return new Int16Array(bytes.buffer);
}

function int16ToBase64(int16) {
  const bytes = new Uint8Array(int16.buffer);
  let binary = '';
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

function downsample(input, inputRate, outputRate) {
  if (outputRate === inputRate) return input;
  const ratio = inputRate / outputRate;
  const newLength = Math.round(input.length / ratio);
  const result = new Float32Array(newLength);
  let offsetResult = 0;
  let offsetBuffer = 0;
  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let accum = 0;
    let count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < input.length; i++) {
      accum += input[i];
      count++;
    }
    result[offsetResult] = count ? accum / count : 0;
    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }
  return result;
}

function floatToInt16(float32) {
  const out = new Int16Array(float32.length);
  let sum = 0;
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    sum += s * s;
  }
  state.volume = Math.min(1, Math.sqrt(sum / Math.max(float32.length, 1)) * 6);
  return out;
}

async function api(path, payload) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return await res.json();
}

async function bootstrapSession() {
  const sessionId = (els.sessionName.value || `browser-${Date.now()}`).trim();
  state.sessionId = sessionId;
  state.bootstrap = await api('/api/session/bootstrap', { session_id: sessionId });
  state.conversation = [...(state.bootstrap.conversation || [])];
  state.toolCalls = [...(state.bootstrap.tool_calls || [])];
  return state.bootstrap;
}

async function logEvent(role, content, extra = null) {
  if (!state.sessionId) return;
  await api('/api/session/event', {
    session_id: state.sessionId,
    role,
    content,
    extra,
  });
}

function enqueuePlayback(int16) {
  if (!state.audioContext) return;
  const float = new Float32Array(int16.length);
  let sum = 0;
  for (let i = 0; i < int16.length; i++) {
    float[i] = int16[i] / 32768;
    sum += float[i] * float[i];
  }
  state.speaking = true;
  state.volume = Math.min(1, Math.sqrt(sum / Math.max(float.length, 1)) * 8);
  const buffer = state.audioContext.createBuffer(1, float.length, 24000);
  buffer.copyToChannel(float, 0);
  const source = state.audioContext.createBufferSource();
  source.buffer = buffer;
  source.connect(state.audioContext.destination);
  const now = state.audioContext.currentTime;
  if (!state.nextPlaybackTime || state.nextPlaybackTime < now) {
    state.nextPlaybackTime = now + 0.03;
  }
  source.start(state.nextPlaybackTime);
  state.nextPlaybackTime += buffer.duration;
  source.onended = () => {
    state.speaking = false;
    state.volume *= 0.35;
    render();
  };
  state.outputChunks += 1;
}

function updateStateLabels() {
  if (state.connecting) {
    setStatus('connecting');
    els.phaseCaption.textContent = 'Connecting';
    els.stateLabel.textContent = 'Connecting to the local realtime session';
    els.warningText.textContent = state.lastError || 'Browser-owned audio avoids the PyAudio playback path.';
    return;
  }
  if (state.connected) {
    setStatus(state.speaking ? 'speaking' : 'listening');
    els.phaseCaption.textContent = state.speaking ? 'Speaking' : 'Listening';
    els.stateLabel.textContent = state.speaking ? 'Assistant is responding' : 'Ready for your next turn';
    els.warningText.textContent = state.muted ? 'Microphone is muted.' : state.holdToTalk ? 'Hold-to-talk is active.' : 'Natural full-duplex session is live.';
    return;
  }
  setStatus('idle');
  els.phaseCaption.textContent = 'Idle';
  els.stateLabel.textContent = 'Ready to connect';
  els.warningText.textContent = state.lastError || 'Use the browser path when local desktop playback is unreliable.';
}

function handleMessage(data) {
  const type = data.type;
  if (type === 'conversation.item.input_audio_transcription.delta') {
    state.currentUserDelta += data.delta || '';
  } else if (type === 'conversation.item.input_audio_transcription.completed') {
    const transcript = data.transcript || '';
    if (transcript) {
      state.conversation.push({ role: 'user', content: transcript });
      logEvent('user', transcript).catch(console.error);
    }
    state.currentUserDelta = '';
  } else if (type === 'response.output_audio_transcript.delta') {
    state.currentAgentDelta += data.delta || '';
  } else if (type === 'response.output_audio_transcript.done') {
    const transcript = data.transcript || '';
    if (transcript) {
      state.conversation.push({ role: 'agent', content: transcript });
      logEvent('agent', transcript).catch(console.error);
    }
    state.currentAgentDelta = '';
  } else if (type === 'response.output_audio.delta' && data.delta) {
    enqueuePlayback(base64ToInt16Array(data.delta));
  } else if (type === 'response.function_call_arguments.done') {
    const name = data.name || '';
    const args = data.arguments ? JSON.parse(data.arguments) : {};
    api('/api/tool-call', {
      session_id: state.sessionId,
      name,
      arguments: args,
    }).then(async (result) => {
      state.toolCalls.push({ name, arguments: args, result });
      render();
      await state.ws.send(JSON.stringify({
        type: 'conversation.item.create',
        item: {
          type: 'function_call_output',
          status: 'completed',
          call_id: data.call_id,
          name,
          arguments: JSON.stringify(args),
          output: JSON.stringify(result),
        },
      }));
      if (result.client_action === 'rollover_after_response') {
        state.pendingRollover = true;
      }
    }).catch(console.error);
  } else if (type === 'input_audio_buffer.speech_stopped') {
    state.ws.send(JSON.stringify({ type: 'input_audio_buffer.commit', event_id: crypto.randomUUID() })).catch(console.error);
  } else if (type === 'response.done') {
    if (state.pendingRollover) {
      state.pendingRollover = false;
      reconnectWithCarryover().catch(console.error);
      return;
    }
  } else if (type === 'error') {
    const message = data.error?.message || 'unknown error';
    if (message.toLowerCase().includes('step budget exhausted')) {
      api('/api/tool-call', {
        session_id: state.sessionId,
        name: 'compact_conversation_context',
        arguments: { focus: message },
      }).then((result) => {
        state.toolCalls.push({ name: 'compact_conversation_context', arguments: { focus: message }, result });
        reconnectWithCarryover().catch(console.error);
      }).catch(console.error);
    }
  }
  updateStateLabels();
  render();
}

async function connectRealtime() {
  const bootstrap = state.bootstrap || await bootstrapSession();
  state.connecting = true;
  state.lastError = '';
  updateStateLabels();
  render();
  state.ws = new WebSocket(bootstrap.ws_url);
  state.ws.onopen = () => {
    state.connected = true;
    state.connecting = false;
    if (!state.startMs) startTimer();
    updateStateLabels();
    state.ws.send(JSON.stringify({
      type: 'session.update',
      event_id: crypto.randomUUID(),
      session: {
        audio: {
          input: { format: { type: 'audio/pcm', rate: 24000 } },
          output: { format: 'pcm16' },
        },
        instructions: bootstrap.instructions,
        tools: bootstrap.tools,
      },
    }));
    render();
  };
  state.ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleMessage(data);
  };
  state.ws.onclose = () => {
    state.connected = false;
    state.connecting = false;
    state.speaking = false;
    state.lastError = state.lastError || 'Realtime socket closed.';
    updateStateLabels();
    render();
  };
  state.ws.onerror = () => {
    state.connecting = false;
    state.lastError = 'Realtime websocket connection failed.';
    setStatus('error');
    updateStateLabels();
    render();
  };
}

async function reconnectWithCarryover() {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.close();
  }
  state.bootstrap = await bootstrapSession();
  await connectRealtime();
}

async function startAudio() {
  if (!state.audioContext) {
    state.audioContext = new AudioContext();
  }
  await state.audioContext.resume();
  if (!state.mediaStream) {
    state.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    state.mediaSource = state.audioContext.createMediaStreamSource(state.mediaStream);
    state.processor = state.audioContext.createScriptProcessor(4096, 1, 1);
    state.mediaSource.connect(state.processor);
    state.processor.connect(state.audioContext.destination);
    state.processor.onaudioprocess = (event) => {
      if (!state.connected || !state.ws || state.ws.readyState !== WebSocket.OPEN || state.muted || state.holdToTalk) return;
      const input = event.inputBuffer.getChannelData(0);
      const down = downsample(input, state.audioContext.sampleRate, 24000);
      const sum = down.reduce((acc, v) => acc + v * v, 0);
      state.volume = Math.min(1, Math.sqrt(sum / Math.max(down.length, 1)) * 8);
      state.inputBuffer.push(...down);
      while (state.inputBuffer.length >= 1920) {
        const chunk = state.inputBuffer.splice(0, 1920);
        const int16 = floatToInt16(Float32Array.from(chunk));
        state.ws.send(JSON.stringify({ type: 'input_audio_buffer.append', event_id: crypto.randomUUID(), audio: int16ToBase64(int16) }));
      }
      render();
    };
  }
}

function sendManualChunk() {
  if (!state.connected || !state.ws || state.ws.readyState !== WebSocket.OPEN || !state.audioContext || !state.mediaStream) return;
}

function startTimer() {
  state.startMs = Date.now();
  if (state.timer) clearInterval(state.timer);
  state.timer = setInterval(() => {
    if (!state.startMs) return;
    els.durationValue.textContent = nowLabel((Date.now() - state.startMs) / 1000);
  }, 1000);
}

function stopTimer() {
  if (state.timer) clearInterval(state.timer);
  state.timer = null;
  state.startMs = null;
  els.durationValue.textContent = '00:00';
}

async function stopSession() {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify({ type: 'session.close', event_id: crypto.randomUUID() }));
    state.ws.close();
  }
  state.connected = false;
  state.connecting = false;
  state.speaking = false;
  state.pendingRollover = false;
  stopTimer();
  updateStateLabels();
  render();
}

function switchTab(tab) {
  const transcript = tab === 'transcript';
  els.transcriptTab.classList.toggle('is-active', transcript);
  els.guideTab.classList.toggle('is-active', !transcript);
  els.transcriptPanel.classList.toggle('is-active', transcript);
  els.guidePanel.classList.toggle('is-active', !transcript);
}

function toggleAutoscroll() {
  state.autoScroll = !state.autoScroll;
  els.autoscrollBtn.textContent = state.autoScroll ? 'Pause scroll' : 'Resume scroll';
  els.autoscrollBtn.setAttribute('aria-pressed', String(!state.autoScroll));
  render();
}

async function connectOrDisconnect() {
  try {
    if (!state.connected) {
      await bootstrapSession();
      state.lastError = '';
      setStatus('requesting mic');
      await startAudio();
      await connectRealtime();
    } else {
      await stopSession();
    }
  } catch (err) {
    console.error(err);
    state.lastError = err.message;
    setStatus(`error: ${err.message}`);
    updateStateLabels();
    render();
  }
}

function setMuted(next) {
  state.muted = next;
  updateStateLabels();
  render();
}

function setHoldToTalk(next) {
  state.holdToTalk = next;
  updateStateLabels();
  render();
}

els.connectBtn.addEventListener('click', connectOrDisconnect);
els.primaryActionBtn.addEventListener('click', connectOrDisconnect);
els.muteBtn.addEventListener('click', () => setMuted(!state.muted));
els.secondaryMuteBtn.addEventListener('click', () => setMuted(!state.muted));
els.autoscrollBtn.addEventListener('click', toggleAutoscroll);
els.transcriptTab.addEventListener('click', () => switchTab('transcript'));
els.guideTab.addEventListener('click', () => switchTab('guide'));

for (const btn of [els.pttBtn, els.secondaryPttBtn]) {
  btn.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    setHoldToTalk(true);
  });
  btn.addEventListener('pointerup', (e) => {
    e.preventDefault();
    setHoldToTalk(false);
  });
  btn.addEventListener('pointerleave', () => setHoldToTalk(false));
}

els.saveSessionBtn.addEventListener('click', async () => {
  if (!state.sessionId) return;
  const blob = new Blob([JSON.stringify({ sessionId: state.sessionId }, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${state.sessionId}.voicechat-session.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

els.loadSessionBtn.addEventListener('click', async () => {
  const name = (els.sessionName.value || '').trim();
  if (!name) return;
  state.bootstrap = await bootstrapSession();
  updateStateLabels();
  render();
});

(async function init() {
  const params = new URLSearchParams(window.location.search);
  const session = params.get('session');
  if (session) els.sessionName.value = session;
  switchTab('transcript');
  updateStateLabels();
  render();
})();
