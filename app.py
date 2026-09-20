from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'random-video-chat-secret'

# Use threading mode for maximum compatibility (no gevent/eventlet needed)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ============================================================
# In-memory storage (no data persisted to disk = privacy first)
# ============================================================
waiting_users = []   # List of user session IDs waiting to be matched
rooms = {}           # room_id -> [user1_sid, user2_sid]
reports = []         # List of report dicts (kept in memory only)


@app.route('/')
def index():
    return render_template('index.html')


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
    if user_sid in waiting_users:
        waiting_users.remove(user_sid)

    # Find any room this user was in and clean it up
    room_to_remove = None
    for room_id, users in rooms.items():
        if user_sid in users:
            room_to_remove = room_id
            partner_sid = users[0] if users[1] == user_sid else users[1]
            emit('partner_left', to=partner_sid)
            break

    if room_to_remove:
        del rooms[room_to_remove]


# ============================================================
# Matchmaking
# ============================================================
@socketio.on('find_partner')
def handle_find_partner():
    user_sid = request.sid
    print(f'[?] {user_sid} is looking for a partner')

    # Remove from queue if already there
    if user_sid in waiting_users:
        waiting_users.remove(user_sid)

    if len(waiting_users) > 0:
        # Match with first waiting user
        partner_sid = waiting_users.pop(0)

        # Create unique room
        room_id = str(uuid.uuid4())
        rooms[room_id] = [user_sid, partner_sid]

        # Join both users to the room
        join_room(room_id, sid=user_sid)
        join_room(room_id, sid=partner_sid)

        # First user = initiator (creates WebRTC offer)
        emit('matched', {'room': room_id, 'initiator': True}, to=user_sid)
        emit('matched', {'room': room_id, 'initiator': False}, to=partner_sid)

        print(f'[✓] Matched {user_sid} <-> {partner_sid} in room {room_id}')
    else:
        # No one waiting, add to queue
        waiting_users.append(user_sid)
        emit('waiting')
        print(f'[~] {user_sid} added to waiting queue. Queue size: {len(waiting_users)}')


# ============================================================
# WebRTC signaling relay
# ============================================================
@socketio.on('signal')
def handle_signal(data):
    """Relay WebRTC signaling (offer, answer, ICE) to partner"""
    room_id = data.get('room')
    signal_data = data.get('signal')

    if room_id and room_id in rooms:
        users = rooms[room_id]
        partner_sid = users[0] if users[1] == request.sid else users[1]
        emit('signal', {'signal': signal_data}, to=partner_sid)


# ============================================================
# Room cleanup (user clicked End or Next)
# ============================================================
@socketio.on('leave_room')
def handle_leave_room(data):
    user_sid = request.sid
    room_id = data.get('room')

    if room_id and room_id in rooms:
        users = rooms[room_id]
        partner_sid = users[0] if users[1] == user_sid else users[1]
        emit('partner_left', to=partner_sid)
        del rooms[room_id]
        print(f'[x] Room {room_id} closed by {user_sid}')


# ============================================================
# Safety: Report handler
# ============================================================
@socketio.on('report_user')
def handle_report(data):
    """Log abuse reports (in-memory only, no permanent storage)"""
    user_sid = request.sid
    room_id = data.get('room')
    reason = data.get('reason', 'unspecified')

    # Store in memory (resets on server restart — no permanent data)
    reports.append({
        'reporter': user_sid,
        'room': room_id,
        'reason': reason
    })

    # Log to console — visible in Render logs
    print(f'[🚨 REPORT] {user_sid} reported partner in room {room_id}. Reason: {reason}')
    print(f'[📊 STATS] Total reports this session: {len(reports)}')

    # Immediately disconnect both users from the room
    if room_id and room_id in rooms:
        users = rooms[room_id]
        partner_sid = users[0] if users[1] == user_sid else users[1]
        emit('reported', {'by': user_sid}, to=partner_sid)
        emit('report_confirmed', to=user_sid)
        del rooms[room_id]
    else:
        # Room already gone; just confirm
        emit('report_confirmed', to=user_sid)


# ============================================================
# Optional: Health check endpoint for uptime monitors
# ============================================================
@app.route('/health')
def health():
    return {
        'status': 'ok',
        'waiting_users': len(waiting_users),
        'active_rooms': len(rooms),
        'reports_session': len(reports)
    }


if __name__ == '__main__':
    print('🚀 Starting Random Video Chat signaling server...')
    print('🌍 Open http://localhost:5000 in your browser')
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)