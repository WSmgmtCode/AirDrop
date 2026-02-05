import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, socketio_path='socket.io')
app.mount("/", socket_app)

@sio.event
async def connect(sid, environ):
    # Nginx経由のIP取得を強化
    headers = dict(environ.get('asgi.scope', {}).get('headers', []))
    xf = headers.get(b'x-forwarded-for', b'').decode()
    ip = xf.split(',')[0].strip() if xf else "unknown"
    
    # IPアドレスを部屋名にする
    await sio.enter_room(sid, ip)
    print(f"User {sid} joined room: {ip}")
    
    # 部屋の他のユーザーに通知
    await sio.emit("peer_joined", {"id": sid}, room=ip, skip_sid=sid)

@sio.event
async def message(sid, data):
    target = data.get('to')
    data['from_sid'] = sid
    if target:
        # 指定された相手にのみ送信（P2Pシグナリング）
        await sio.emit("message", data, to=target)
    else:
        # ターゲット不明時は同じ部屋（IP）全員に（Pingなど）
        rooms = [r for r in sio.rooms(sid) if r != sid]
        for room in rooms:
            await sio.emit("message", data, room=room, skip_sid=sid)

@sio.event
async def disconnect(sid):
    print(f"Disconnected: {sid}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8008)
