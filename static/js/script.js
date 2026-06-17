// =========================================================
// AGROSPHERE - script.js
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
    const title = document.getElementById('ann-title').value.trim();
    const category = document.getElementById('ann-category').value;
    const body = document.getElementById('ann-body').value.trim();
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
    const select = document.getElementById('expert-select-' + qid);
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
    const qid = btn.dataset.qid;
    const bid = btn.dataset.bid;
    const aid = btn.dataset.aid;
    const uid = btn.dataset.uid;

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
// Weather widget
// ---------------------------------------------------------
async function loadWeatherWidget() {
    try {
        const select = document.getElementById('district-select');
        const display = document.getElementById('weather-display');
        if (!select || !display) return;

        const res = await fetch('/api/districts');
        const districts = await res.json();

        select.innerHTML = '';
        districts.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d;
            opt.textContent = d;
            select.appendChild(opt);
        });

        const saved = localStorage.getItem('weatherDistrict');
        if (saved && districts.includes(saved)) select.value = saved;

        async function fetchWeather(district) {
            display.textContent = 'Loading weather...';
            try {
                const res = await fetch(`/api/weather?district=${encodeURIComponent(district)}`);
                const data = await res.json();
                const current = data.current_weather;
                const today = data.daily;
                display.innerHTML = `
                    <strong>${Math.round(current.temperature)}°C</strong>
                    <span style="color:#888;">
                        H:${Math.round(today.temperature_2m_max[0])}°
                        L:${Math.round(today.temperature_2m_min[0])}°
                        · ${today.precipitation_probability_max[0]}% rain
                    </span>
                `;
            } catch (err) {
                display.textContent = 'Weather unavailable';
            }
        }

        select.addEventListener('change', () => {
            localStorage.setItem('weatherDistrict', select.value);
            fetchWeather(select.value);
        });

        fetchWeather(select.value);
    } catch (err) {
        console.error('Weather widget error:', err);
    }
}

document.addEventListener('DOMContentLoaded', loadWeatherWidget);

// ---------------------------------------------------------
// User search
// ---------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    const userSearch = document.getElementById('user-search');
    if (!userSearch) return;
    userSearch.addEventListener('input', () => {
        const term = userSearch.value.toLowerCase().trim();
        document.querySelectorAll('.user-card').forEach(card => {
            const match =
                card.dataset.name.includes(term) ||
                card.dataset.email.includes(term) ||
                card.dataset.role.includes(term);
            card.style.display = match ? '' : 'none';
        });
    });
});

// Safe version — only runs if the element exists
const supportBtn = document.getElementById('supportBtn');
if (supportBtn) {
    supportBtn.onclick = function() {
        document.getElementById('supportModal').style.display = 'block';
    };
}


function togglePaymentFields(provider) {
    var momoField = document.getElementById('momo_field');
    var cardField = document.getElementById('card_field');
    
    if (provider === 'card') {
        momoField.style.display = 'none';
        cardField.style.display = 'block';
    } else {
        momoField.style.display = 'block';
        cardField.style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Automatically save text typed into forms so reloads don't destroy it
    const inputs = document.querySelectorAll('textarea, input[type="text"]');
    
    inputs.forEach(input => {
        // Unique key for local storage based on the page and input ID/name
        const storageKey = `draft_${window.location.pathname}_${input.name || input.id}`;
        
        // Restore saved draft if it exists
        if (localStorage.getItem(storageKey)) {
            input.value = localStorage.getItem(storageKey);
        }
        
        // Listen for typing and save it
        input.addEventListener('input', () => {
            localStorage.setItem(storageKey, input.value);
        });
        
        // Clear the draft when the form is actually submitted
        const form = input.closest('form');
        if (form) {
            form.addEventListener('submit', () => {
                localStorage.removeItem(storageKey);
            });
        }
    });
});