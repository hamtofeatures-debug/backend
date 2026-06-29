// =========================================================
// AGROSPHERE - script.js  (fixed — no duplicate blocks)
// =========================================================

const CURRENT_USER_ID = parseInt(document.body.dataset.userId || '0', 10);

// ---------------------------------------------------------
// Section navigation
// ---------------------------------------------------------
function showSection(id, btn) {
    document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.sidebar nav a').forEach(a => a.classList.remove('active'));
    const sec = document.getElementById('section-' + id);
    if (sec) sec.classList.add('active');
    if (btn) btn.classList.add('active');
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.nav-link[data-section]').forEach(link => {
        link.addEventListener('click', () => showSection(link.dataset.section, link));
    });

    document.querySelectorAll('[data-goto]').forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.dataset.goto;
            const navLink = document.querySelector(`.nav-link[data-section="${target}"]`);
            showSection(target, navLink);
        });
    });
});

// ---------------------------------------------------------
// Media preview
// ---------------------------------------------------------
function previewMedia(event, targetId, type) {
    const preview = document.getElementById(targetId);
    if (!preview) return;
    preview.innerHTML = '';
    const files = event.target.files;
    for (let i = 0; i < files.length; i++) {
        const reader = new FileReader();
        reader.onload = function (e) {
            const el = document.createElement(type === 'video' ? 'video' : 'img');
            el.src = e.target.result;
            if (type === 'video') el.muted = true;
            preview.appendChild(el);
        };
        reader.readAsDataURL(files[i]);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input[type="file"][data-preview]').forEach(input => {
        input.addEventListener('change', (e) =>
            previewMedia(e, input.dataset.preview, input.dataset.previewType || 'image')
        );
    });
});

// ---------------------------------------------------------
// Generic fetch helpers
// ---------------------------------------------------------
async function postJSON(url, data) {
    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!res.ok) {
            const text = await res.text();
            throw new Error(`Server returned ${res.status}: ${text}`);
        }
        return await res.json();
    } catch (err) {
        console.error('postJSON error:', err);
        alert('Something went wrong: ' + err.message);
        throw err;
    }
}

async function postForm(url, formElement) {
    try {
        const res = await fetch(url, {
            method: 'POST',
            body: new FormData(formElement)
        });
        if (!res.ok) {
            const text = await res.text();
            throw new Error(`Server returned ${res.status}: ${text}`);
        }
        return await res.json();
    } catch (err) {
        console.error('postForm error:', err);
        alert('Something went wrong: ' + err.message);
        throw err;
    }
}

async function postEmpty(url) {
    try {
        const res = await fetch(url, { method: 'POST' });
        if (!res.ok) {
            const text = await res.text();
            throw new Error(`Server returned ${res.status}: ${text}`);
        }
        return await res.json().catch(() => ({}));
    } catch (err) {
        console.error('postEmpty error:', err);
        alert('Something went wrong: ' + err.message);
        throw err;
    }
}

// ---------------------------------------------------------
// Admin actions
// ---------------------------------------------------------
function postAnnouncement() {
    const title    = document.getElementById('ann-title').value.trim();
    const category = document.getElementById('ann-category').value;
    const body     = document.getElementById('ann-body').value.trim();
    if (!title || !body) { alert('Title and message are required.'); return; }
    postJSON('/admin/announcements', { admin_id: CURRENT_USER_ID, title, category, body })
        .then(() => location.reload());
}

function approveAnswer(qid) {
    postJSON(`/admin/questions/${qid}/approve`, {}).then(() => location.reload());
}

function rejectAnswer(qid) {
    const note = prompt('Note for the expert (optional):', 'Please revise your answer.');
    postJSON(`/admin/questions/${qid}/reject`, { note: note || '' }).then(() => location.reload());
}

function businessAction(bid, action) {
    postEmpty(`/admin/business/${bid}/${action}`).then(() => location.reload());
}

function verifyBusiness(bid) {
    postEmpty(`/admin/verify-business/${bid}`).then(() => location.reload());
}

function confirmPayment(bid) {
    postEmpty(`/admin/business/${bid}/confirm-payment`).then(() => location.reload());
}

function assignExpert(qid) {
    const select   = document.getElementById('expert-select-' + qid);
    const expertId = select ? select.value : null;
    if (!expertId) { alert('Please select an expert first'); return; }
    postJSON(`/admin/assign-expert/${qid}`, { expert_id: expertId })
        .then(() => location.reload());
}

// ---------------------------------------------------------
// Expert actions
// ---------------------------------------------------------
function submitAnswer(qid) {
    const textarea = document.getElementById('answer-' + qid);
    if (!textarea) return;
    const answer = textarea.value.trim();
    if (!answer) { alert('Please write an answer.'); return; }
    postJSON(`/expert/answer/${qid}`, { answer, expert_id: CURRENT_USER_ID })
        .then(() => location.reload());
}

// ---------------------------------------------------------
// Star rating
// ---------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-question-id]').forEach(group => {
        const qid = group.dataset.questionId;
        group.querySelectorAll('.star').forEach(star => {
            star.addEventListener('click', () => {
                postJSON(`/api/rate/${qid}`, { stars: star.dataset.value })
                    .then(() => {
                        const value = parseInt(star.dataset.value, 10);
                        group.querySelectorAll('.star').forEach(s => {
                            s.style.color = parseInt(s.dataset.value, 10) <= value ? '#f0a500' : '';
                        });
                    });
            });
        });
    });
});

// ---------------------------------------------------------
// Single unified click handler
// ---------------------------------------------------------
document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;

    const action = btn.dataset.action;
    const qid    = btn.dataset.qid;
    const bid    = btn.dataset.bid;
    const aid    = btn.dataset.aid;
    const uid    = btn.dataset.uid;

    switch (action) {
        case 'assign':
            assignExpert(qid);
            break;
        case 'approve':
            approveAnswer(qid);
            break;
        case 'reject':
            rejectAnswer(qid);
            break;
        case 'submit-answer':
            submitAnswer(qid);
            break;
        case 'post-announcement':
            postAnnouncement();
            break;
        case 'biz-approve':
            businessAction(bid, 'approve');
            break;
        case 'biz-reject':
            businessAction(bid, 'reject');
            break;
        case 'verify-biz':
            verifyBusiness(bid);
            break;
        case 'confirm-payment':
            confirmPayment(bid);
            break;
        case 'approve-article':
            postEmpty(`/admin/articles/${aid}/approve`).then(() => location.reload());
            break;
        case 'reject-article':
            postEmpty(`/admin/articles/${aid}/reject`).then(() => location.reload());
            break;
        case 'verify-user':
            postEmpty(`/admin/user/${uid}/verify`).then(() => location.reload());
            break;
        case 'suspend-user':
            postEmpty(`/admin/user/${uid}/suspend`).then(() => location.reload());
            break;
        case 'delete-user':
            if (!confirm('Are you sure you want to permanently delete this user? This cannot be undone.')) return;
            postEmpty(`/admin/user/${uid}/delete`).then(() => {
                const card = document.getElementById(`user-card-${uid}`);
                if (card) card.remove();
            });
            break;
        default:
            console.warn('Unknown data-action:', action);
    }
});

// ---------------------------------------------------------
// Form submit (AJAX forms only)
// ---------------------------------------------------------
document.addEventListener('submit', (e) => {
    const form = e.target;
    if (!form.matches('[data-ajax-form]')) return;
    e.preventDefault();
    postForm(form.getAttribute('action'), form).then((resp) => {
        if (resp && resp.redirect) window.location.href = resp.redirect;
        else location.reload();
    });
});

// ---------------------------------------------------------
// Draft autosave (localStorage)
// ---------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    const inputs = document.querySelectorAll('textarea, input[type="text"]');
    inputs.forEach(input => {
        const storageKey = `draft_${window.location.pathname}_${input.name || input.id}`;
        if (localStorage.getItem(storageKey)) {
            input.value = localStorage.getItem(storageKey);
        }
        input.addEventListener('input', () => {
            localStorage.setItem(storageKey, input.value);
        });
        const form = input.closest('form');
        if (form) {
            form.addEventListener('submit', () => {
                localStorage.removeItem(storageKey);
            });
        }
    });
});

// ---------------------------------------------------------
// Payment fields toggle
// ---------------------------------------------------------
function togglePaymentFields(provider) {
    const momoField = document.getElementById('momo_field');
    const cardField = document.getElementById('card_field');
    if (provider === 'card') {
        if (momoField) momoField.style.display = 'none';
        if (cardField) cardField.style.display = 'block';
    } else {
        if (momoField) momoField.style.display = 'block';
        if (cardField) cardField.style.display = 'none';
    }
}

// =========================================================
// Info Cards — Weather + Market Prices (SINGLE copy)
// =========================================================

const _cardLoaded = { weather: false, market: false };
const _cardOpen   = { weather: false, market: false };

function toggleInfoCard(type) {
    if (_cardOpen[type]) {
        collapseInfoCard(null, type);
    } else {
        expandInfoCard(type);
    }
}

function expandInfoCard(type) {
    const card         = document.getElementById('card-' + type);
    const defaultView  = document.getElementById('card-' + type + '-default');
    const expandedView = document.getElementById('card-' + type + '-expanded');
    if (!card || !defaultView || !expandedView) return;

    const other = type === 'weather' ? 'market' : 'weather';
    if (_cardOpen[other]) collapseInfoCard(null, other);

    defaultView.style.display  = 'none';
    expandedView.style.display = 'block';
    card.classList.add('is-expanded');
    _cardOpen[type] = true;

    if (!_cardLoaded[type]) {
        if (type === 'weather') _fetchWeatherCard();
        if (type === 'market')  _fetchMarketCard();
    }
}

function collapseInfoCard(event, type) {
    if (event) event.stopPropagation();
    const card         = document.getElementById('card-' + type);
    const defaultView  = document.getElementById('card-' + type + '-default');
    const expandedView = document.getElementById('card-' + type + '-expanded');
    if (!card) return;

    if (defaultView)  defaultView.style.display  = 'block';
    if (expandedView) expandedView.style.display = 'none';
    card.classList.remove('is-expanded');
    _cardOpen[type] = false;
}

// ── Weather ──────────────────────────────────────────────
function _fetchWeatherCard() {
    fetch('/api/weather-info')
        .then(r => r.json())
        .then(data => {
            _cardLoaded.weather = true;
            const content = document.getElementById('weather-card-content');
            const dateEl  = document.getElementById('weather-card-date');
            if (!content) return;

            if (!data.success) {
                content.innerHTML = _dcError('Could not load weather data.');
                return;
            }

            if (dateEl) dateEl.textContent = data.date ? '— ' + data.date : '';

            let html = '';

            if (data.overview || data.outlook) {
                html += '<div class="dc-weather-overview">';
                if (data.overview) html += '<strong>' + _esc(data.overview) + '</strong>';
                if (data.outlook)  html += _esc(data.outlook);
                html += '</div>';
            }

            if (data.cities && data.cities.length > 0) {
                html += '<div class="dc-weather-grid">';
                data.cities.forEach(c => {
                    const icon = _weatherIcon(c.condition);
                    html += '<div class="dc-city-card">'
                        + '<div class="dc-city-card__name">' + _esc(c.city) + '</div>'
                        + '<div class="dc-city-card__cond">' + icon + ' ' + _esc(c.condition || '—') + '</div>'
                        + '<div class="dc-city-card__temp-today">' + _esc(c.today.temp || '—') + '</div>'
                        + (c.tomorrow.temp
                            ? '<div class="dc-city-card__temp-tmr">Tmr: ' + _esc(c.tomorrow.temp) + '</div>'
                            : '')
                        + '</div>';
                });
                html += '</div>';
            } else {
                html += '<p style="font-size:12px;color:#aaa;text-align:center;padding:16px 0;">No city data at this time.</p>';
            }

            content.innerHTML = html;
        })
        .catch(() => {
            _cardLoaded.weather = false;
            const content = document.getElementById('weather-card-content');
            if (content) content.innerHTML = _dcError('Network error. Try again.');
        });
}

function _weatherIcon(cond) {
    if (!cond) return '🌡';
    const c = cond.toLowerCase();
    if (c.includes('sunny') && c.includes('interval')) return '⛅';
    if (c.includes('sunny') || c.includes('clear'))    return '☀️';
    if (c.includes('shower') || c.includes('rain'))    return '🌧';
    if (c.includes('thunder') || c.includes('storm'))  return '⛈';
    if (c.includes('cloud'))                           return '☁️';
    if (c.includes('wind'))                            return '💨';
    if (c.includes('fog') || c.includes('mist'))       return '🌫';
    return '🌤';
}

// ── Market Prices ─────────────────────────────────────────
function _fetchMarketCard() {
    fetch('/api/market-prices')
        .then(r => r.json())
        .then(data => {
            _cardLoaded.market = true;
            const content = document.getElementById('market-card-content');
            if (!content) return;

            if (!data.success) {
                content.innerHTML = _dcError('Could not load market prices.');
                return;
            }

            if (!data.categories || data.categories.length === 0) {
                content.innerHTML = '<p style="font-size:12px;color:#aaa;text-align:center;padding:16px 0;">No price data at this time.</p>';
                return;
            }

            let html = '';
            data.categories.forEach(cat => {
                html += '<div class="dc-market-cat">'
                    + '<div class="dc-market-cat__title">' + _esc(cat.category) + '</div>'
                    + '<table class="dc-market-table"><thead><tr>';

                (cat.columns || []).forEach(col => {
                    html += '<th>' + _esc(col) + '</th>';
                });
                html += '</tr></thead><tbody>';

                (cat.items || []).forEach(item => {
                    html += '<tr>';
                    if (item.entry !== undefined) {
                        html += '<td colspan="' + (cat.columns || ['Entry']).length + '">' + _esc(item.entry) + '</td>';
                    } else {
                        (cat.columns || []).forEach(col => {
                            html += '<td>' + _esc(item[col] || '—') + '</td>';
                        });
                    }
                    html += '</tr>';
                });

                html += '</tbody></table></div>';
            });

            content.innerHTML = html;
        })
        .catch(() => {
            _cardLoaded.market = false;
            const content = document.getElementById('market-card-content');
            if (content) content.innerHTML = _dcError('Network error. Try again.');
        });
}

function filterMarketCard(query) {
    const q       = query.toLowerCase().trim();
    const content = document.getElementById('market-card-content');
    if (!content) return;

    content.querySelectorAll('.dc-market-table tbody tr').forEach(row => {
        const match = q === '' || row.textContent.toLowerCase().includes(q);
        row.classList.toggle('dc-hidden', !match);
    });

    content.querySelectorAll('.dc-market-cat').forEach(cat => {
        const visible = cat.querySelectorAll('.dc-market-table tbody tr:not(.dc-hidden)');
        cat.style.display = (q !== '' && visible.length === 0) ? 'none' : '';
    });
}

// ── Shared helpers ────────────────────────────────────────
function _dcError(msg) {
    return '<div class="dc-error"><span>⚠️</span>' + msg + '</div>';
}

function _esc(str) {
    return String(str)
        .replace(/&/g,  '&amp;')
        .replace(/</g,  '&lt;')
        .replace(/>/g,  '&gt;')
        .replace(/"/g,  '&quot;');
}


(function () {
  'use strict';

  // ── After the page renders, detect which post bodies actually
  //    overflow 3 lines and only then reveal their "Read more" button.
  //    This avoids showing a Read More link on short posts.
  function pcardInitClamps() {
    document.querySelectorAll('.pcard__text--clamped').forEach(function (el) {
      var isOverflowing = el.scrollHeight > el.clientHeight + 1;
      var id = el.id.replace('pcard-text-', '');
      var btn = document.getElementById('pcard-rmb-' + id);
      if (btn) btn.hidden = !isOverflowing;
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', pcardInitClamps);
  } else {
    pcardInitClamps();
  }

  // Re-check on resize (text reflow can change overflow state)
  var resizeTimer;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(pcardInitClamps, 200);
  });

  // ── Read more / show less ──
  window.pcardToggleText = function (id) {
    var el = document.getElementById('pcard-text-' + id);
    var btn = document.getElementById('pcard-rmb-' + id);
    if (!el || !btn) return;

    var expanded = el.classList.contains('pcard__text--expanded');
    if (expanded) {
      el.classList.remove('pcard__text--expanded');
      el.classList.add('pcard__text--clamped');
      btn.textContent = 'Read more';
    } else {
      el.classList.remove('pcard__text--clamped');
      el.classList.add('pcard__text--expanded');
      btn.textContent = 'Show less';
    }
  };

  // ── Three-dot menu ──
  window.pcardToggleMenu = function (id, evt) {
    if (evt) evt.stopPropagation();
    document.querySelectorAll('.pcard__menu').forEach(function (m) {
      if (m.id !== 'pcard-menu-' + id) m.classList.remove('pcard__menu--open');
    });
    var menu = document.getElementById('pcard-menu-' + id);
    if (menu) menu.classList.toggle('pcard__menu--open');
  };

  document.addEventListener('click', function () {
    document.querySelectorAll('.pcard__menu').forEach(function (m) {
      m.classList.remove('pcard__menu--open');
    });
  });

  // ── Fully wired-up actions matching AGROSPHERE routing standards ──
  
  window.pcardLike = function (id, btnEl) {
    // Optimistic UI updates
    btnEl.classList.toggle('pcard__action-btn--liked');
    
    postEmpty('/api/posts/' + id + '/like')
      .then(resp => {
        // If your backend tracks and returns total counts dynamically
        const label = btnEl.querySelector('span');
        if (label && resp && resp.likes_count !== undefined) {
          label.innerHTML = resp.likes_count > 0 ? `Like · ${resp.likes_count}` : 'Like';
        }
      })
      .catch(() => {
        // Revert UI if network request fails
        btnEl.classList.toggle('pcard__action-btn--liked');
      });
  };

  window.pcardComment = function (id) {
    // Redirects to dedicated post viewport / comment engagement thread
    window.location.href = '/posts/' + id;
  };

  window.pcardShare = function (id, btnEl) {
  var text = btnEl && btnEl.dataset ? btnEl.dataset.shareText : '';
  if (navigator.share) {
    navigator.share({ text: text }).catch(function () {});
  } else if (navigator.clipboard) {
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard!');
  }
};

  window.pcardReport = function (id) {
    if (!confirm('Report this post for moderation review?')) return;
    
    postEmpty('/api/posts/' + id + '/report')
      .then(() => {
        alert('Report sent. Thank you for keeping AGROSPHERE safe.');
      })
      .catch(err => console.error('Failed to register post report:', err));
  };

  window.pcardEdit = function (id) {
    window.location.href = '/posts/' + id + '/edit';
  };

  window.pcardDelete = function (id) {
    if (!confirm('Delete this post? This cannot be undone.')) return;
    
    postEmpty('/api/posts/' + id + '/delete')
      .then(() => {
        const card = document.getElementById('pcard-' + id);
        if (card) {
          card.remove();
        }
      })
      .catch(err => console.error('Failed to delete post:', err));
  };

})();