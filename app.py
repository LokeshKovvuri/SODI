from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'random-video-chat-secret'

# Use threading mode for maximum compatibility (no gevent/eventlet needed)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# In-memory storage (no data persisted to disk = privacy friendly)
waiting_users = []
rooms = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print(f'[+] User connected: {request.sid}')

@socketio.on('find_partner')
def handle_find_partner():
    user_sid = request.sid
    print(f'[?] {user_sid} is looking for a partner')

    if user_sid in waiting_users:
        waiting_users.remove(user_sid)

    if len(waiting_users) > 0:
        partner_sid = waiting_users.pop(0)
        room_id = str(uuid.uuid4())
        rooms[room_id] = [user_sid, partner_sid]

        join_room(room_id, sid=user_sid)
        join_room(room_id, sid=partner_sid)

        emit('matched', {'room': room_id, 'initiator': True}, to=user_sid)
        emit('matched', {'room': room_id, 'initiator': False}, to=partner_sid)
        print(f'[✓] Matched {user_sid} <-> {partner_sid} in room {room_id}')
    else:
        waiting_users.append(user_sid)
        emit('waiting')
        print(f'[~] {user_sid} added to waiting queue. Queue size: {len(waiting_users)}')

@socketio.on('signal')
def handle_signal(data):
    room_id = data.get('room')
    signal_data = data.get('signal')

    if room_id and room_id in rooms:
        users = rooms[room_id]
        partner_sid = users[0] if users[1] == request.sid else users[1]
        emit('signal', {'signal': signal_data}, to=partner_sid)

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

@socketio.on('disconnect')
def handle_disconnect():
    user_sid = request.sid
    print(f'[-] User disconnected: {user_sid}')

    if user_sid in waiting_users:
        waiting_users.remove(user_sid)

    room_to_remove = None
    for room_id, users in rooms.items():
        if user_sid in users:
            room_to_remove = room_id
            partner_sid = users[0] if users[1] == user_sid else users[1]
            emit('partner_left', to=partner_sid)
            break

    if room_to_remove:
        del rooms[room_to_remove]

if __name__ == '__main__':
    print('🚀 Starting Random Video Chat signaling server...')
    print('🌍 Open http://localhost:5000 in your browser')
    # allow_unsafe_werkzeug is required to suppress the dev server warning in threading mode
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)