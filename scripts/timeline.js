window.TMTimeline = class {
  constructor({ minMs, maxMs, onChange }) {
    this._minMs = minMs;
    this._maxMs = maxMs;
    this._onChange = onChange;
    this._currentMs = maxMs;
    this._playing = false;
    this._enabled = true;
    this._speed = 1;
    this._rafId = null;
    this._startTime = null;
    this._startMs = null;

    this._range = document.getElementById('tl-range');
    this._playBtn = document.getElementById('tl-play');
    this._currentEl = document.getElementById('tl-current');
    this._startEl = document.getElementById('tl-start');
    this._endEl = document.getElementById('tl-end');
    this._speedBtns = document.querySelectorAll('#tl-speed button[data-speed]');

    this._startEl.textContent = TM.fmtDateTime(minMs);
    this._endEl.textContent = TM.fmtDateTime(maxMs);
    this._updateDisplay();

    this._range.addEventListener('input', () => {
      if (!this._enabled) return;
      this._currentMs = this._sliderToMs(parseInt(this._range.value, 10));
      this._updateDisplay();
      this._onChange(this._currentMs);
    });

    this._playBtn.addEventListener('click', () => {
      if (this._playing) {
        this.pause();
      } else {
        this._play();
      }
    });

    this._speedBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        this._speedBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this._speed = parseFloat(btn.dataset.speed);
      });
    });
  }

  value() {
    return this._currentMs;
  }

  setValueMs(ms) {
    if (!this._enabled) return;
    this._currentMs = Math.max(this._minMs, Math.min(this._maxMs, ms));
    this._range.value = this._msToSlider(this._currentMs);
    this._updateDisplay();
  }

  isPlaying() {
    return this._playing;
  }

  pause() {
    this._playing = false;
    if (this._rafId) {
      cancelAnimationFrame(this._rafId);
      this._rafId = null;
    }
    this._playBtn.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20"><path d="M8 5v14l11-7z" fill="currentColor"/></svg>';
    this._startTime = null;
    this._startMs = null;
  }

  setEnabled(enabled) {
    this._enabled = enabled;
    this._range.disabled = !enabled;
    if (!enabled) {
      this.pause();
    }
  }

  _play() {
    if (!this._enabled) return;
    if (this._currentMs >= this._maxMs) {
      this._currentMs = this._minMs;
      this._range.value = this._msToSlider(this._currentMs);
      this._updateDisplay();
      this._onChange(this._currentMs);
    }
    this._playing = true;
    this._playBtn.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" fill="currentColor"/></svg>';
    this._startTime = performance.now();
    this._startMs = this._currentMs;
    this._tick();
  }

  _tick() {
    if (!this._playing) return;
    const elapsed = performance.now() - this._startTime;
    const totalSpan = this._maxMs - this._minMs;
    const durationMs = 28000 / this._speed;
    const progress = Math.min(elapsed / durationMs, 1);
    this._currentMs = this._startMs + (totalSpan * progress);
    if (this._currentMs >= this._maxMs) {
      this._currentMs = this._maxMs;
      this._range.value = this._msToSlider(this._currentMs);
      this._updateDisplay();
      this._onChange(this._currentMs);
      this.pause();
      return;
    }
    this._range.value = this._msToSlider(this._currentMs);
    this._updateDisplay();
    this._onChange(this._currentMs);
    this._rafId = requestAnimationFrame(() => this._tick());
  }

  _sliderToMs(val) {
    return this._minMs + (val / 1000) * (this._maxMs - this._minMs);
  }

  _msToSlider(ms) {
    return Math.round(((ms - this._minMs) / (this._maxMs - this._minMs)) * 1000);
  }

  _updateDisplay() {
    this._currentEl.textContent = TM.fmtDateTime(this._currentMs);
  }
};
