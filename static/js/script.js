// =========================================================
// AGROSPHERE - script.js
// Shared dashboard logic for Admin, Expert, Farmer, Business
// =========================================================

// CURRENT_USER_ID is read from a data attribute on <body>
// Add this to <body> in every dashboard template:
//   <body data-user-id="{{ current_user.id }}">
const CURRENT_USER_ID = parseInt(document.body.dataset.userId || '0', 10);

// ---------------------------------------------------------
// Section navigation (sidebar tabs)
// ---------------------------------------------------------
function showSection(id, btn) {
    document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.sidebar nav a').forEach(a => a.classList.remove('active'));
    const sec = document.getElementById('section-' + id);
    if (sec) sec.classList.add('active');
    if (btn) btn.classList.add('active');
}

// Wire up nav links automatically via data-section attribute
// Template change: <a class="nav-link" data-section="overview">
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.nav-link[data-section]').forEach(link => {
        link.addEventListener('click', () => showSection(link.dataset.section, link));
    });

    // Quick action buttons with data-goto + data-nav-index
    document.querySelectorAll('[data-goto]').forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.dataset.goto;
            const navLink = document.querySelector(`.nav-link[data-section="${target}"]`);
            showSection(target, navLink);
        });
    });
});

// ---------------------------------------------------------
// Media preview (photos/videos before upload)
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

// Auto-wire any file input with data-preview + data-preview-type
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input[type="file"][data-preview]').forEach(input => {
        input.addEventListener('change', (e) =>
            previewMedia(e, input.dataset.preview, input.dataset.previewType || 'image')
        );
    });
});

// ---------------------------------------------------------
// Generic helpers
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

// ===========================================================
// ADMIN DASHBOARD ACTIONS
// ===========================================================

// --- Post Announcement ---
function postAnnouncement() {
    const titleEl = document.getElementById('ann-title');
    const catEl = document.getElementById('ann-category');
    const bodyEl = document.getElementById('ann-body');

    const title = titleEl.value.trim();
    const category = catEl.value;
    const body = bodyEl.value.trim();

    if (!title || !body) {
        alert('Title and message are required.');
        return;
    }

    postJSON('/admin/announcements', {
        admin_id: CURRENT_USER_ID,
        title,
        category,
        body
    }).then(() => location.reload());
}

// --- Assign Expert to a Question ---
// Template change: <button data-action="assign" data-qid="{{ q.id }}">Assign</button>

// --- Approve / Reject Answer (Pending Review) ---
function approveAnswer(qid) {
    postJSON(`/admin/questions/${qid}/approve`, {})
        .then(() => location.reload());
}

function rejectAnswer(qid) {
    const note = prompt('Note for the expert (optional):', 'Please revise your answer.');
    postJSON(`/admin/questions/${qid}/reject`, { note: note || '' })
        .then(() => location.reload());
}

// --- Business actions ---
function businessAction(bid, action) {
    postEmpty(`/admin/business/${bid}/${action}`).then(() => location.reload());
}

function verifyBusiness(bid) {
    postEmpty(`/admin/verify-business/${bid}`).then(() => location.reload());
}

function confirmPayment(bid) {
    postEmpty(`/admin/business/${bid}/confirm-payment`).then(() => location.reload());
}

// ===========================================================
// EXPERT DASHBOARD ACTIONS
// ===========================================================

function submitAnswer(qid) {
    const textarea = document.getElementById('answer-' + qid);
    if (!textarea) return;
    const answer = textarea.value.trim();
    if (!answer) {
        alert('Please write an answer.');
        return;
    }
    postJSON(`/expert/answer/${qid}`, { answer, expert_id: CURRENT_USER_ID })
        .then(() => location.reload());
}

// ===========================================================
// FARMER DASHBOARD ACTIONS
// ===========================================================

// Star rating for Public Q&A
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-question-id]').forEach(group => {
        const qid = group.dataset.questionId;
        group.querySelectorAll('.star').forEach(star => {
            star.addEventListener('click', () => {
                postJSON(`/api/rate/${qid}`, { stars: star.dataset.value })
                    .then(() => {
                        // visual feedback: fill stars up to clicked value
                        const value = parseInt(star.dataset.value, 10);
                        group.querySelectorAll('.star').forEach(s => {
                            s.style.color = parseInt(s.dataset.value, 10) <= value ? '#f0a500' : '';
                        });
                    });
            });
        });
    });
});

// ===========================================================
// EVENT DELEGATION FOR ALL ACTION BUTTONS
// ===========================================================
// Instead of broken inline onclick="...(q.id)" / "...('q.id')",
// templates should use data attributes, e.g.:
//
//   <button class="btn-sm btn-green" data-action="assign" data-qid="{{ q.id }}">Assign</button>
//   <button class="btn-sm btn-green" data-action="approve" data-qid="{{ q.id }}">Approve & Publish</button>
//   <button class="btn-sm btn-danger" data-action="reject" data-qid="{{ q.id }}">Reject</button>
//   <button class="btn-sm btn-green" data-action="biz-approve" data-bid="{{ b.id }}">Approve</button>
//   <button class="btn-sm btn-danger" data-action="biz-reject" data-bid="{{ b.id }}">Reject</button>
//   <button class="btn-sm" data-action="verify-biz" data-bid="{{ b.id }}">Grant Blue Tick</button>
//   <button class="btn-sm" data-action="confirm-payment" data-bid="{{ b.id }}">Confirm Payment</button>
//   <button class="btn-sm btn-green" data-action="submit-answer" data-qid="{{ q.id }}">Submit Answer</button>
//   <button class="btn-primary" data-action="post-announcement">Post Announcement</button>

document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;

    const action = btn.dataset.action;
    const qid = btn.dataset.qid;
    const bid = btn.dataset.bid;

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
        default:
            console.warn('Unknown data-action:', action);
            case 'approve-article':
    postEmpty(`/admin/articles/${btn.dataset.aid}/approve`).then(() => location.reload());
    break;
case 'reject-article':
    postEmpty(`/admin/articles/${btn.dataset.aid}/reject`).then(() => location.reload());
    break;
    }
});

// ===========================================================
// FARMER: Ask an Expert / Create Post forms (with file uploads)
// ===========================================================
// Template change for forms with file inputs that need AJAX submit:
//   <form data-ajax-form action="{{ url_for('farmer.ask_question') }}" method="POST" enctype="multipart/form-data">
//
// If you prefer normal full-page form submission (simplest, works fine
// with Flask redirects), you can OMIT data-ajax-form entirely and let
// the browser submit normally. The handler below only intercepts forms
// that explicitly opt in.

document.addEventListener('submit', (e) => {
    const form = e.target;
    if (!form.matches('[data-ajax-form]')) return; // let normal forms submit normally

    e.preventDefault();
    const url = form.getAttribute('action');

    postForm(url, form).then((resp) => {
        if (resp && resp.redirect) {
            window.location.href = resp.redirect;
        } else {
            location.reload();
        }
    });
});

// ===========================================================
// BUSINESS DASHBOARD: Create Post
// ===========================================================
// Fix for the business "Create a Post" form which currently has
// action="#" and does nothing on submit.
//
// Template change:
//   <form data-ajax-form action="{{ url_for('business.create_post') }}"
//         method="POST" enctype="multipart/form-data">
//
// (Make sure a real `business.create_post` Flask route exists that
// accepts title, description, photos[], videos[] via request.files
// and request.form, and returns JSON like {"success": true}.)

