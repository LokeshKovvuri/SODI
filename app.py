from flask import Flask, render_template, request, send_from_directory, jsonify
from flask_socketio import SocketIO, emit, join_room
from datetime import datetime, timedelta
from collections import defaultdict, deque
import uuid, json, os, secrets

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'random-video-chat-secret'

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ============================================================
# Config & persistent storage
# ============================================================
BANS_FILE = 'bans.json'
STATS_FILE = 'stats.json'

# Auto-generate a random admin password on first run
ADMIN_PASSWORD_FILE = 'admin_config.json'
if os.path.exists(ADMIN_PASSWORD_FILE):
    with open(ADMIN_PASSWORD_FILE) as f:
        ADMIN_PASSWORD = json.load(f).get('password')
else:
    ADMIN_PASSWORD = secrets.token_urlsafe(12)
    with open(ADMIN_PASSWORD_FILE, 'w') as f:
        json.dump({'password': ADMIN_PASSWORD}, f)
    print(f'🔑 ADMIN PASSWORD (save this!): {ADMIN_PASSWORD}')
    print(f'🔗 Admin URL: /admin?pw={ADMIN_PASSWORD}')

# ============================================================
# In-memory runtime state
# ============================================================
waiting_users = []       # list of {sid, tag}
rooms = {}               # room_id -> {'users': [s1, s2], 'tag': str, 'started': ts}
reports = []             # recent reports (session-only)
chat_history = defaultdict(list)  # room_id -> list of {from, text, ts}

# Analytics
analytics = {
    'total_connections': 0,
    'total_matches': 0,
    'total_sessions': 0,
    'total_reports': 0,
    'peak_online': 0,
    'started_at': datetime.utcnow().isoformat(),
    'session_durations': deque(maxlen=200),
    'tag_counts': defaultdict(int),
    'hourly_connections': defaultdict(int),
    'online_now': 0,
    'unique_ips_today': set(),
    'daily_active': defaultdict(int)  # date -> count
}

# Load bans
def load_bans():
    if os.path.exists(BANS_FILE):
        try:
            with open(BANS_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_bans(bans):
    with open(BANS_FILE, 'w') as f:
        json.dump(bans, f, indent=2)

bans = load_bans()  # ip -> {reason, until, ts}

def is_banned(ip):
    entry = bans.get(ip)
    if not entry:
        return False
    if entry.get('until') is None:
        return True  # permanent
    try:
        until = datetime.fromisoformat(entry['until'])
        if datetime.utcnow() < until:
            return True
        else:
            del bans[ip]
            save_bans(bans)
            return False
    except Exception:
        return False

def get_client_ip():
    # Render passes real IP via X-Forwarded-For
    fwd = request.headers.get('X-Forwarded-For', '')
    if fwd:
        return fwd.split(',')[0].strip()
    return request.remote_addr or 'unknown'


# ============================================================
# Routes
# ============================================================
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/admin')
def admin():
    pw = request.args.get('pw', '')
    if pw != ADMIN_PASSWORD:
        return 'Forbidden', 403
    return render_template('admin.html')


@app.route('/api/admin/stats')
def admin_stats():
    pw = request.args.get('pw', '')
    if pw != ADMIN_PASSWORD:
        return jsonify({'error': 'forbidden'}), 403

    # Average session duration
    durs = list(analytics['session_durations'])
    avg_dur = sum(durs) / len(durs) if durs else 0

    return jsonify({
        'online_now': analytics['online_now'],
        'waiting': len(waiting_users),
        'active_rooms': len(rooms),
        'total_connections': analytics['total_connections'],
        'total_matches': analytics['total_matches'],
        'total_sessions': analytics['total_sessions'],
        'total_reports': analytics['total_reports'],
        'peak_online': analytics['peak_online'],
        'avg_session_seconds': round(avg_dur, 1),
        'started_at': analytics['started_at'],
        'tag_counts': dict(analytics['tag_counts']),
        'hourly_connections': dict(analytics['hourly_connections']),
        'daily_active': dict(analytics['daily_active']),
        'unique_ips_today': len(analytics['unique_ips_today']),
        'recent_reports': reports[-20:][::-1],
        'bans': bans,
        'waiting_tags': [u['tag'] for u in waiting_users]
    })


@app.route('/api/admin/ban', methods=['POST'])
def admin_ban():
    data = request.json or {}
    pw = data.get('pw', '')
    if pw != ADMIN_PASSWORD:
        return jsonify({'error': 'forbidden'}), 403

    ip = data.get('ip', '').strip()
    reason = data.get('reason', 'Banned by admin')
    duration_hours = data.get('duration_hours', 0)  # 0 = permanent

    if not ip:
        return jsonify({'error': 'no ip'}), 400

    until = None
    if duration_hours > 0:
        until = (datetime.utcnow() + timedelta(hours=duration_hours)).isoformat()

    bans[ip] = {
        'reason': reason,
        'until': until,
        'ts': datetime.utcnow().isoformat()
    }
    save_bans(bans)
    return jsonify({'ok': True})


@app.route('/api/admin/unban', methods=['POST'])
def admin_unban():
    data = request.json or {}
    pw = data.get('pw', '')
    if pw != ADMIN_PASSWORD:
        return jsonify({'error': 'forbidden'}), 403

    ip = data.get('ip', '').strip()
    if ip in bans:
        del bans[ip]
        save_bans(bans)
        return jsonify({'ok': True})
    return jsonify({'error': 'not found'}), 404


@app.route('/api/admin/ban_user', methods=['POST'])
def admin_ban_user():
    """Ban an IP that is currently in a room (from report view)."""
    data = request.json or {}
    pw = data.get('pw', '')
    if pw != ADMIN_PASSWORD:
        return jsonify({'error': 'forbidden'}), 403

    ip = data.get('ip', '').strip()
    reason = data.get('reason', 'Banned from report')
    if not ip:
        return jsonify({'error': 'no ip'}), 400

    bans[ip] = {
        'reason': reason,
        'until': None,
        'ts': datetime.utcnow().isoformat()
    }
    save_bans(bans)
    return jsonify({'ok': True})


@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'online': analytics['online_now'],
        'waiting': len(waiting_users),
        'rooms': len(rooms),
        'bans': len(bans),
        'reports_session': len(reports)
    })


@app.route('/stats')
def public_stats():
    """Public stats page (no sensitive data)."""
    return jsonify({
        'online_now': analytics['online_now'],
        'total_matches': analytics['total_matches'],
        'active_rooms': len(rooms),
        'uptime_since': analytics['started_at']
    })


@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')


@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')


@app.route('/static/icons/<path:filename>')
def icons(filename):
    return send_from_directory('static/icons', filename)


# ============================================================
# Socket: connection lifecycle
# ============================================================
@socketio.on('connect')
def handle_connect():
    ip = get_client_ip()
    if is_banned(ip):
        emit('banned', {'reason': bans[ip]['reason']})
        return False  # reject connection

    analytics['total_connections'] += 1
    analytics['online_now'] += 1
    analytics['peak_online'] = max(analytics['peak_online'], analytics['online_now'])
    hour = datetime.utcnow().strftime('%H')
    analytics['hourly_connections'][hour] += 1
    today = datetime.utcnow().strftime('%Y-%m-%d')
    analytics['daily_active'][today] += 1
    analytics['unique_ips_today'].add(ip)

    print(f'[+] {request.sid} connected (ip: {ip}). Online: {analytics["online_now"]}')


@socketio.on('disconnect')
def handle_disconnect():
    user_sid = request.sid
    analytics['online_now'] = max(0, analytics['online_now'] - 1)

    waiting_users[:] = [u for u in waiting_users if u['sid'] != user_sid]

    room_to_remove = None
    for room_id, room in rooms.items():
        if user_sid in room['users']:
            room_to_remove = room_id
            partner_sid = room['users'][0] if room['users'][1] == user_sid else room['users'][1]
            emit('partner_left', to=partner_sid)
            break

    if room_to_remove:
        _finalize_room(room_to_remove)

    print(f'[-] {user_sid} disconnected. Online: {analytics["online_now"]}')


def _finalize_room(room_id):
    if room_id not in rooms:
        return
    room = rooms[room_id]
    started = room.get('started')
    if started:
        try:
            start_ts = datetime.fromisoformat(started)
            dur = (datetime.utcnow() - start_ts).total_seconds()
            analytics['session_durations'].append(dur)
        except Exception:
            pass
    analytics['total_sessions'] += 1
    chat_history.pop(room_id, None)
    del rooms[room_id]


# ============================================================
# Socket: matchmaking
# ============================================================
@socketio.on('find_partner')
def handle_find_partner(data):
    user_sid = request.sid
    tag = (data or {}).get('tag', 'any')
    print(f'[?] {user_sid} looking for partner (tag: {tag})')

    waiting_users[:] = [u for u in waiting_users if u['sid'] != user_sid]

    partner_entry = None
    partner_index = -1
    for i, u in enumerate(waiting_users):
        if tag == 'any' or u['tag'] == 'any' or u['tag'] == tag:
            partner_entry = u
            partner_index = i
            break

    if partner_entry:
        waiting_users.pop(partner_index)
        partner_sid = partner_entry['sid']
        matched_tag = tag if tag != 'any' else partner_entry['tag']

        room_id = str(uuid.uuid4())
        rooms[room_id] = {
            'users': [user_sid, partner_sid],
            'tag': matched_tag,
            'started': datetime.utcnow().isoformat()
        }
        chat_history[room_id] = []

        join_room(room_id, sid=user_sid)
        join_room(room_id, sid=partner_sid)

        emit('matched', {'room': room_id, 'initiator': True, 'tag': matched_tag}, to=user_sid)
        emit('matched', {'room': room_id, 'initiator': False, 'tag': matched_tag}, to=partner_sid)

        analytics['total_matches'] += 1
        analytics['tag_counts'][matched_tag] += 1
        print(f'[✓] Matched {user_sid} <-> {partner_sid} (tag: {matched_tag})')
    else:
        waiting_users.append({'sid': user_sid, 'tag': tag})
        emit('waiting', {'tag': tag})


# ============================================================
# Socket: signaling
# ============================================================
@socketio.on('signal')
def handle_signal(data):
    room_id = data.get('room')
    signal_data = data.get('signal')
    if room_id and room_id in rooms:
        users = rooms[room_id]['users']
        partner_sid = users[0] if users[1] == request.sid else users[1]
        emit('signal', {'signal': signal_data}, to=partner_sid)


@socketio.on('leave_room')
def handle_leave_room(data):
    user_sid = request.sid
    room_id = data.get('room')
    if room_id and room_id in rooms:
        users = rooms[room_id]['users']
        partner_sid = users[0] if users[1] == user_sid else users[1]
        emit('partner_left', to=partner_sid)
        _finalize_room(room_id)


# ============================================================
# Socket: chat history log
# ============================================================
@socketio.on('chat_log')
def handle_chat_log(data):
    room_id = data.get('room')
    msg = data.get('text', '')[:500]
    if room_id and room_id in rooms:
        chat_history[room_id].append({
            'from': request.sid,
            'text': msg,
            'ts': datetime.utcnow().isoformat()
        })
        if len(chat_history[room_id]) > 100:
            chat_history[room_id] = chat_history[room_id][-100:]


# ============================================================
# Socket: report
# ============================================================
@socketio.on('report_user')
def handle_report(data):
    user_sid = request.sid
    room_id = data.get('room')
    reason = data.get('reason', 'unspecified')
    partner_ip = data.get('partner_ip', '')  # optional, sent by client

    tag = rooms.get(room_id, {}).get('tag', 'unknown') if room_id else 'unknown'
    chat_snippet = chat_history.get(room_id, [])[-10:] if room_id else []

    report_entry = {
        'reporter': user_sid,
        'reporter_ip': get_client_ip(),
        'room': room_id,
        'reason': reason,
        'tag': tag,
        'ts': datetime.utcnow().isoformat(),
        'chat_snippet': chat_snippet
    }
    reports.append(report_entry)
    analytics['total_reports'] += 1

    print(f'[🚨 REPORT] {user_sid} reported partner. Reason: {reason}')
    print(f'[📊 STATS] Total reports this session: {len(reports)}')

    if room_id and room_id in rooms:
        users = rooms[room_id]['users']
        partner_sid = users[0] if users[1] == user_sid else users[1]
        emit('reported', {'by': user_sid}, to=partner_sid)
        emit('report_confirmed', to=user_sid)
        _finalize_room(room_id)
    else:
        emit('report_confirmed', to=user_sid)


if __name__ == '__main__':
    print('🚀 Starting Random Video Chat server...')
    print(f'🔑 Admin: http://localhost:5000/admin?pw={ADMIN_PASSWORD}')
    print('🌍 App:   http://localhost:5000')
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)