window.TMSidebar = class {
  constructor({ data, onSelect, onFilterChange }) {
    this.data = data;
    this.onSelect = onSelect;
    this.onFilterChange = onFilterChange;
    this.animals = data.animals;
    this.selectedId = null;
    this.liveMode = false;

    this.searchEl = document.getElementById('search');
    this.filtersEl = document.getElementById('filters');
    this.listEl = document.getElementById('list');
    this.listCountEl = document.getElementById('list-count');
    this.btnResetEl = document.getElementById('btn-reset');
    this.profileEl = document.getElementById('profile');

    this.filterValues = { species: '', sex: '', lifeStage: '', status: '' };
    this.searchTerm = '';

    this.buildFilters();
    this.bindEvents();
    this.renderList();
  }

  buildFilters() {
    const species = new Set();
    const sexes = new Set();
    const lifeStages = new Set();
    const statuses = new Set();

    this.animals.forEach(a => {
      species.add(a.commonName);
      sexes.add(a.sex);
      lifeStages.add(a.lifeStage);
      statuses.add(a.status);
    });

    const filterConfig = [
      { key: 'species', label: 'Species', values: [...species].sort() },
      { key: 'sex', label: 'Sex', values: [...sexes].sort() },
      { key: 'lifeStage', label: 'Life stage', values: [...lifeStages].sort() },
      { key: 'status', label: 'Status', values: [...statuses].sort() }
    ];

    this.filtersEl.innerHTML = '';
    filterConfig.forEach(cfg => {
      const select = TM.el('select', {
        dataset: { filterKey: cfg.key },
        html: `<option value="">All ${cfg.label}</option>${cfg.values.map(v => `<option value="${v}">${v}</option>`).join('')}`
      });
      const label = TM.el('label', { text: cfg.label });
      const wrapper = TM.el('div', { class: 'tm-filter' }, [label, select]);
      this.filtersEl.appendChild(wrapper);
    });
  }

  bindEvents() {
    this.searchEl.addEventListener('input', () => {
      this.searchTerm = this.searchEl.value.toLowerCase();
      this.applyFilters();
    });

    this.filtersEl.querySelectorAll('select').forEach(sel => {
      sel.addEventListener('change', () => {
        this.filterValues[sel.dataset.filterKey] = sel.value;
        this.applyFilters();
      });
    });

    this.btnResetEl.addEventListener('click', () => {
      this.reset();
    });
  }

  applyFilters() {
    const visible = this.getVisibleIds();
    this.renderList(visible);
    this.btnResetEl.style.display = this.isFilterActive() ? 'block' : 'none';
    this.onFilterChange(visible);
  }

  isFilterActive() {
    if (this.searchTerm) return true;
    return Object.values(this.filterValues).some(v => v !== '');
  }

  getVisibleIds() {
    return this.animals
      .filter(a => {
        if (this.searchTerm) {
          const match = a.name.toLowerCase().includes(this.searchTerm) ||
            a.commonName.toLowerCase().includes(this.searchTerm) ||
            a.scientificName.toLowerCase().includes(this.searchTerm);
          if (!match) return false;
        }
        if (this.filterValues.species && a.commonName !== this.filterValues.species) return false;
        if (this.filterValues.sex && a.sex !== this.filterValues.sex) return false;
        if (this.filterValues.lifeStage && a.lifeStage !== this.filterValues.lifeStage) return false;
        if (this.filterValues.status && a.status !== this.filterValues.status) return false;
        return true;
      })
      .map(a => a.id);
  }

  renderList(visibleIds) {
    const ids = visibleIds || this.getVisibleIds();
    this.listEl.innerHTML = '';
    ids.forEach(id => {
      const animal = this.animals.find(a => a.id === id);
      if (!animal) return;
      const lastPing = animal.pings[animal.pings.length - 1];
      const lastMs = lastPing ? TM.parseT(lastPing.t) : 0;
      const metrics = TM.metrics(animal.pings);

      const card = TM.el('div', {
        class: 'tm-list-card' + (this.selectedId === id ? ' tm-list-card--selected' : ''),
        dataset: { id },
        onclick: () => {
          this.select(id);
          this.onSelect(id);
        }
      }, [
        TM.el('div', { class: 'tm-list-card__stripe', style: `background:${animal.color}` }),
        TM.el('div', { class: 'tm-list-card__body' }, [
          TM.el('div', { class: 'tm-list-card__name' }, [
            TM.el('span', { text: animal.name }),
            TM.el('span', { class: `dot ${TM.STATUS[animal.status]}` })
          ]),
          TM.el('div', { class: 'tm-list-card__common', text: animal.commonName }),
          TM.el('div', { class: 'tm-list-card__meta' }, [
            TM.el('span', { text: lastMs ? TM.timeAgo(lastMs) : '—' }),
            TM.el('span', { text: metrics.miles ? `${TM.fmtInt(Math.round(metrics.miles))} mi` : '—' })
          ])
        ])
      ]);
      this.listEl.appendChild(card);
    });

    this.listCountEl.textContent = `${ids.length} of ${this.animals.length}`;
  }

  select(id) {
    this.selectedId = id;
    this.listEl.querySelectorAll('.tm-list-card').forEach(c => {
      c.classList.toggle('tm-list-card--selected', c.dataset.id === id);
    });
    if (!id) {
      this.profileEl.innerHTML = '';
      this.profileEl.setAttribute('aria-hidden', 'true');
    }
  }

  renderProfile(animal, metrics) {
    const lastPing = animal.pings[animal.pings.length - 1];
    const lastMs = lastPing ? TM.parseT(lastPing.t) : 0;

    const metricsBlock = TM.el('div', { class: 'tm-profile__metrics' }, [
      TM.el('div', { class: 'tm-profile__metric' }, [
        TM.el('span', { class: 'tm-profile__metric-value', text: TM.fmtInt(metrics.feet) }),
        TM.el('span', { class: 'tm-profile__metric-label', text: 'ft walked' }),
        TM.el('span', { class: 'tm-profile__metric-sub', text: `${TM.fmtInt(Math.round(metrics.miles))} mi` })
      ]),
      TM.el('div', { class: 'tm-profile__metric' }, [
        TM.el('span', { class: 'tm-profile__metric-value', text: metrics.avgMph ? metrics.avgMph.toFixed(1) : '—' }),
        TM.el('span', { class: 'tm-profile__metric-label', text: 'mph avg (on the move)' })
      ]),
      TM.el('div', { class: 'tm-profile__metric' }, [
        TM.el('span', { class: 'tm-profile__metric-value', text: metrics.topMph ? metrics.topMph.toFixed(1) : '—' }),
        TM.el('span', { class: 'tm-profile__metric-label', text: 'mph top speed' })
      ]),
      TM.el('div', { class: 'tm-profile__metric' }, [
        TM.el('span', { class: 'tm-profile__metric-value', text: TM.fmtInt(metrics.lastDistFeet) }),
        TM.el('span', { class: 'tm-profile__metric-label', text: 'ft last night' })
      ]),
      TM.el('div', { class: 'tm-profile__metric' }, [
        TM.el('span', { class: 'tm-profile__metric-value', text: TM.fmtInt(animal.stepsToday || 0) }),
        TM.el('span', { class: 'tm-profile__metric-label', text: 'Steps today' })
      ])
    ]);

    if (this.liveMode) {
      metricsBlock.appendChild(TM.el('div', { class: 'tm-profile__metric' }, [
        TM.el('span', { class: 'tm-profile__metric-value', text: metrics.currentSpeedMph ? metrics.currentSpeedMph.toFixed(1) : '0.0' }),
        TM.el('span', { class: 'tm-profile__metric-label', text: 'mph current speed' })
      ]));
    }

    const vitalsBlock = TM.el('div', { class: 'tm-profile__vitals' }, [
      TM.el('div', { class: 'tm-profile__vital' }, [TM.el('span', { class: 'tm-profile__vital-label', text: 'Sex' }), TM.el('span', { text: animal.sex })]),
      TM.el('div', { class: 'tm-profile__vital' }, [TM.el('span', { class: 'tm-profile__vital-label', text: 'Life stage' }), TM.el('span', { text: animal.lifeStage })]),
      TM.el('div', { class: 'tm-profile__vital' }, [TM.el('span', { class: 'tm-profile__vital-label', text: 'Length' }), TM.el('span', { text: `${animal.lengthCm} cm` })]),
      TM.el('div', { class: 'tm-profile__vital' }, [TM.el('span', { class: 'tm-profile__vital-label', text: 'Weight' }), TM.el('span', { text: `${animal.weightKg} kg` })]),
      TM.el('div', { class: 'tm-profile__vital' }, [TM.el('span', { class: 'tm-profile__vital-label', text: 'Tagged' }), TM.el('span', { text: `${animal.taggedDate} · ${animal.taggedLocation}` })]),
      TM.el('div', { class: 'tm-profile__vital' }, [TM.el('span', { class: 'tm-profile__vital-label', text: 'Home range' }), TM.el('span', { text: animal.homeRange })]),
      TM.el('div', { class: 'tm-profile__vital' }, [TM.el('span', { class: 'tm-profile__vital-label', text: 'Tagger' }), TM.el('span', { text: animal.tagger })])
    ]);

    const bioBlock = TM.el('p', { class: 'tm-profile__bio', text: animal.bio });

    // 14-day step sparkline
    const stepsByDay = animal.stepsByDay || [];
    const maxDay = stepsByDay.reduce((m, v) => v > m ? v : m, 0);
    const sparkBars = stepsByDay.map(v => {
      const h = maxDay === 0 ? 4 : Math.max(4, Math.round(v / maxDay * 100));
      return TM.el('span', { class: 'tm-spark-bar', style: `height:${h}%` });
    });
    const sparkBlock = TM.el('div', { class: 'tm-profile__spark' }, [
      TM.el('div', { class: 'tm-spark' }, sparkBars),
      TM.el('div', { class: 'tm-spark-caption', text: '14-day steps' })
    ]);

    const notesPanel = TM.el('div', { class: 'tm-profile__notes' });
    notesPanel.style.display = 'none';
    const renderNote = (text) => {
      notesPanel.innerHTML = '';
      notesPanel.style.display = 'block';
      notesPanel.appendChild(TM.el('button', {
        class: 'tm-profile__notes-close', text: '×',
        onclick: () => { notesPanel.style.display = 'none'; notesPanel.innerHTML = ''; }
      }));
      notesPanel.appendChild(TM.el('p', { class: 'tm-profile__notes-text', text: text }));
    };
    const claudeBtn = TM.el('button', {
      class: 'tm-profile__claude-btn',
      text: 'Ask Claude → Field Notes',
      onclick: async () => {
        claudeBtn.disabled = true;
        claudeBtn.textContent = 'Consulting Claude…';
        notesPanel.style.display = 'block';
        notesPanel.innerHTML = '<div class="tm-profile__notes-loading">Consulting Claude…</div>';
        let text;
        try { text = await TMClaude.fieldNotes(animal, metrics); }
        catch (e) { text = animal.note; }
        renderNote(text);
        claudeBtn.disabled = false;
        claudeBtn.textContent = 'Ask Claude → Field Notes';
      }
    });

    const closeBtn = TM.el('button', {
      class: 'tm-profile__close',
      text: '×',
      onclick: () => {
        this.select(null);
        this.onSelect(null);
      }
    });

    const photo = TM.el('img', { class: 'tm-profile__photo' });
    photo.src = 'assets/portraits/' + animal.id + '.jpg';
    photo.alt = '';

    this.profileEl.innerHTML = '';
    this.profileEl.appendChild(photo);
    this.profileEl.appendChild(TM.el('div', { class: 'tm-profile__header' }, [
      TM.el('h2', { text: animal.name }),
      TM.el('div', { class: 'tm-profile__subtitle' }, [
        TM.el('span', { text: `${animal.commonName} · ${animal.scientificName}` }),
        TM.el('span', { class: `tm-profile__status dot ${TM.STATUS[animal.status]}`, text: animal.status })
      ]),
      closeBtn
    ]));
    this.profileEl.appendChild(metricsBlock);
    this.profileEl.appendChild(sparkBlock);
    this.profileEl.appendChild(vitalsBlock);
    this.profileEl.appendChild(bioBlock);
    this.profileEl.appendChild(claudeBtn);
    this.profileEl.appendChild(notesPanel);
    this.profileEl.setAttribute('aria-hidden', 'false');
  }

  update(animal, metrics) {
    if (this.selectedId === animal.id) {
      this.renderProfile(animal, metrics);
    }
    this.renderList();
  }

  reset() {
    this.searchEl.value = '';
    this.searchTerm = '';
    this.filterValues = { species: '', sex: '', lifeStage: '', status: '' };
    this.filtersEl.querySelectorAll('select').forEach(sel => sel.value = '');
    this.btnResetEl.style.display = 'none';
    this.applyFilters();
  }
};
