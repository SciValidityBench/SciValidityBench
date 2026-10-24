'use strict';

const examples = {
  inferential: {
    title: 'Inferential Ledger',
    description: 'Outcome selection and stopping rules determine which claim a reported result can support.',
    state: 'planned / selected',
    decision: 'confirm / explore',
    context: '# Inferential Ledger — schematic example\nReported result: p = 0.03\nThe outcome-selection history and stopping rule\ndetermine which scientific claim is licensed.',
    question: 'Can this result support a confirmatory claim?\nCompare the same result under the two histories\nin the State Difference tab.',
    a: ['Plan fixed in advance', ['Outcome preregistered', 'Fixed stopping rule', 'No outcome selection after inspection'], 'Confirmatory use'],
    b: ['Outcome selected after inspection', ['Twenty results inspected', 'Reported outcome selected afterward', 'Same reported p-value'], 'Exploratory use only']
  },
  blind: {
    title: 'Blind Memory',
    description: 'Access timing and disclosure history determine whether a plan remained insulated from outcomes.',
    state: 'locked / disclosed',
    decision: 'intact / compromised',
    context: '# Blind Memory — schematic example\nAn analysis plan is locked at time 4.\nAccess records show when outcome information\nwas disclosed to the analyst.',
    question: 'Was blinding intact when the plan was fixed?\nCompare disclosure before versus after the lock.',
    a: ['Outcome access after the lock', ['Plan locked at time 4', 'Outcome first accessed at time 6'], 'Blind intact'],
    b: ['Outcome access before the lock', ['Plan locked at time 4', 'Outcome accessed at time 2'], 'Blind compromised']
  },
  construct: {
    title: 'Construct Drift',
    description: 'Metric definitions, populations and replicate meaning govern which measurements can be compared.',
    state: 'definition / population',
    decision: 'compare / separate',
    context: '# Construct Drift — schematic example\nTwo records use the same metric name.\nComparability depends on the definition,\npopulation and replicate unit behind each record.',
    question: 'May the two measurements be combined?\nA shared metric name does not establish\na shared measurement contract.',
    a: ['Definitions agree', ['Same measurement definition', 'Matched population and replicate unit'], 'Comparable'],
    b: ['Definition changed', ['Same visible metric name', 'Different replicate unit or population'], 'Keep separate']
  },
  absence: {
    title: 'Absence Algebra',
    description: 'Attempt status and instrument outcome separate observed absence from a missing measurement.',
    state: 'observed / missing',
    decision: 'absence / unknown',
    context: '# Absence Algebra — schematic example\nNo positive signal appears in the record.\nAttempt status and instrument outcome determine\nwhether this is an observation or missing data.',
    question: 'Does the record establish observed absence\nwithin the stated detection limit,\nor is a valid measurement missing?',
    a: ['A valid screen completed', ['Instrument functioning', 'No signal within the detection limit'], 'Observed absence'],
    b: ['Measurement missing', ['Run not completed or instrument failed', 'No valid negative observation'], 'Do not infer absence']
  },
  sunk: {
    title: 'Sunk Cost Memory',
    description: 'Prospective value should stay stable when irrelevant historical investment changes.',
    state: 'past / future',
    decision: 'relevant / irrelevant',
    context: '# Sunk Cost Memory — schematic example\nProject A prospective value: 4\nProject B prospective value: 7\nHistorical investment is varied independently.',
    question: 'Which project has greater prospective value?\nChanging an irrelevant historical investment\nshould preserve the decision.',
    a: ['No prior investment in A', ['Prospective values: A = 4, B = 7', 'No historical investment recorded'], 'Choose B'],
    b: ['Large prior investment in A', ['Same prospective values: A = 4, B = 7', 'Past investment does not change future value'], 'Choose B']
  }
};

function updateModule(key) {
  const item = examples[key];
  if (!item) return;
  document.getElementById('stage-title').textContent = item.title;
  document.getElementById('stage-description').textContent = item.description;
  document.getElementById('stage-state').textContent = item.state;
  document.getElementById('stage-decision').textContent = item.decision;
  document.getElementById('example-context').textContent = item.context;
  document.getElementById('example-question').textContent = item.question;
  for (const side of ['a', 'b']) {
    const [title, facts, answer] = item[side];
    document.getElementById(`state-${side}-title`).textContent = title;
    document.getElementById(`state-${side}-answer`).textContent = answer;
    document.getElementById(`state-${side}-facts`).replaceChildren(...facts.map((fact) => {
      const li = document.createElement('li');
      li.textContent = fact;
      return li;
    }));
  }
}

function setupNavigation() {
  const nav = document.getElementById('nav');
  const toggle = document.querySelector('.nav-toggle');
  const progress = document.querySelector('.nav-progress');
  let previous = 0;
  const updateScrollState = () => {
    const current = window.scrollY;
    nav.classList.toggle('nav-hidden', current > previous && current > 90);
    previous = current;
    const max = document.documentElement.scrollHeight - window.innerHeight;
    progress?.style.setProperty('--scroll-progress', max > 0 ? String(current / max) : '0');
  };
  window.addEventListener('scroll', updateScrollState, { passive: true });
  updateScrollState();
  toggle.addEventListener('click', () => {
    const open = nav.classList.toggle('nav-open');
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
  });
  document.querySelectorAll('.nav-links a').forEach((link) => {
    link.addEventListener('click', () => {
      nav.classList.remove('nav-open');
      toggle.setAttribute('aria-expanded', 'false');
    });
  });
}

function setupMotion() {
  const finePointer = window.matchMedia('(pointer: fine)').matches;
  if (!finePointer) return;
  document.querySelectorAll('.button, .nav-paper').forEach((element) => {
    element.addEventListener('pointermove', (event) => {
      const rect = element.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - .5;
      const y = (event.clientY - rect.top) / rect.height - .5;
      element.style.transform = `translate(${x * 4}px, ${y * 3}px)`;
    });
    element.addEventListener('pointerleave', () => {
      element.style.transform = '';
    });
  });
}

function setupModules() {
  document.querySelectorAll('.module-item').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.module-item').forEach((item) => {
        const active = item === button;
        item.classList.toggle('active', active);
        item.setAttribute('aria-pressed', String(active));
      });
      updateModule(button.dataset.module);
    });
  });
}

function setupTabs() {
  document.querySelectorAll('.example-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.example-tab').forEach((item) => {
        const active = item === tab;
        item.classList.toggle('active', active);
        item.setAttribute('aria-selected', String(active));
      });
      document.querySelectorAll('.example-panel').forEach((panel) => {
        panel.classList.toggle('active', panel.dataset.panel === tab.dataset.tab);
      });
    });
  });
}

function setupCopy() {
  document.querySelectorAll('.copy-button').forEach((button) => {
    button.addEventListener('click', async () => {
      const source = document.getElementById(button.dataset.copy);
      try {
        await navigator.clipboard.writeText(source.textContent.trim());
        const original = button.textContent;
        button.textContent = 'Copied';
        button.classList.add('copied');
        window.setTimeout(() => {
          button.textContent = original;
          button.classList.remove('copied');
        }, 1500);
      } catch {
        const range = document.createRange();
        range.selectNodeContents(source);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
      }
    });
  });
}

function setupReveal() {
  const items = document.querySelectorAll('.reveal');
  items.forEach((item, index) => item.style.setProperty('--reveal-delay', `${Math.min(index % 6, 5) * 65}ms`));
  if (!('IntersectionObserver' in window)) {
    items.forEach((item) => item.classList.add('is-visible'));
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: .12 });
  items.forEach((item) => observer.observe(item));
}

function setupIdeaFlow() {
  const flow = document.getElementById('idea-flow');
  const replay = document.getElementById('idea-replay');
  if (!flow || !replay) return;
  const play = () => {
    flow.classList.remove('play');
    void flow.offsetWidth;
    flow.classList.add('play');
  };
  flow.classList.add('armed');
  if (!('IntersectionObserver' in window)) {
    play();
  } else {
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        play();
        observer.disconnect();
      }
    }, { threshold: .35 });
    observer.observe(flow);
  }
  replay.addEventListener('click', play);
}

document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupModules();
  setupTabs();
  setupCopy();
  setupReveal();
  setupIdeaFlow();
  setupMotion();
  updateModule('inferential');
});
