from flask import Flask, render_template, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room
import uuid

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'random-video-chat-secret'

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ============================================================
# In-memory storage (no persistence, privacy first)
# ============================================================
waiting_users = []       # List of {sid, tag} waiting to be matched
rooms = {}               # room_id -> {'users': [sid1, sid2], 'tag': str}
reports = []             # List of {reporter, room, reason, tag}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')


@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')


@app.route('/static/icons/<path:filename>')
def icons(filename):
    return send_from_directory('static/icons', filename)


@app.route('/health')
def health():
    return {
        'status': 'ok',
        'waiting_users': len(waiting_users),
        'active_rooms': len(rooms),
        'reports_session': len(reports)
    }


# ============================================================
# Connection lifecycle
# ============================================================
@socketio.on('connect')
def handle_connect():
    print(f'[+] User connected: {request.sid}')


@socketio.on('disconnect')
def handle_disconnect():
    user_sid = request.sid
    print(f'[-] User disconnected: {user_sid}')

    # Remove from waiting queue
    waiting_users[:] = [u for u in waiting_users if u['sid'] != user_sid]

    # Cleanup any active room
    room_to_remove = None
    for room_id, room in rooms.items():
        if user_sid in room['users']:
            room_to_remove = room_id
            partner_sid = room['users'][0] if room['users'][1] == user_sid else room['users'][1]
            emit('partner_left', to=partner_sid)
            break

    if room_to_remove:
        del rooms[room_to_remove]


# ============================================================
# Matchmaking (with interest tag filtering)
# ============================================================
@socketio.on('find_partner')
def handle_find_partner(data):
    user_sid = request.sid
    tag = (data or {}).get('tag', 'any')
    print(f'[?] {user_sid} is looking for a partner (tag: {tag})')

    # Remove user from queue if already there
    waiting_users[:] = [u for u in waiting_users if u['sid'] != user_sid]

    # Find a partner: same tag OR 'any' matches anyone
    partner_entry = None
    partner_index = -1

    for i, u in enumerate(waiting_users):
        if tag == 'any' or u['tag'] == 'any' or u['tag'] == tag:
            partner_entry = u
            partner_index = i
            break

    if partner_entry:
        # Match found
        waiting_users.pop(partner_index)
        partner_sid = partner_entry['sid']
        matched_tag = tag if tag != 'any' else partner_entry['tag']

        room_id = str(uuid.uuid4())
        rooms[room_id] = {'users': [user_sid, partner_sid], 'tag': matched_tag}

        join_room(room_id, sid=user_sid)
        join_room(room_id, sid=partner_sid)

        emit('matched', {'room': room_id, 'initiator': True, 'tag': matched_tag}, to=user_sid)
        emit('matched', {'room': room_id, 'initiator': False, 'tag': matched_tag}, to=partner_sid)

        print(f'[✓] Matched {user_sid} <-> {partner_sid} in room {room_id} (tag: {matched_tag})')
    else:
        # No match yet, add to queue
        waiting_users.append({'sid': user_sid, 'tag': tag})
        emit('waiting', {'tag': tag})
        print(f'[~] {user_sid} added to waiting queue. Queue size: {len(waiting_users)}')


# ============================================================
# WebRTC signaling relay
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
        del rooms[room_id]
        print(f'[x] Room {room_id} closed by {user_sid}')


# ============================================================
# Safety: Report handler
# ============================================================
@socketio.on('report_user')
def handle_report(data):
    user_sid = request.sid
    room_id = data.get('room')
    reason = data.get('reason', 'unspecified')

    tag = rooms.get(room_id, {}).get('tag', 'unknown') if room_id else 'unknown'

    reports.append({
        'reporter': user_sid,
        'room': room_id,
        'reason': reason,
        'tag': tag
    })

    print(f'[🚨 REPORT] {user_sid} reported partner in room {room_id} (tag: {tag}). Reason: {reason}')
    print(f'[📊 STATS] Total reports this session: {len(reports)}')

    if room_id and room_id in rooms:
        users = rooms[room_id]['users']
        partner_sid = users[0] if users[1] == user_sid else users[1]
        emit('reported', {'by': user_sid}, to=partner_sid)
        emit('report_confirmed', to=user_sid)
        del rooms[room_id]
    else:
        emit('report_confirmed', to=user_sid)


if __name__ == '__main__':
    print('🚀 Starting Random Video Chat signaling server...')
    print('🌍 Open http://localhost:5000 in your browser')
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)