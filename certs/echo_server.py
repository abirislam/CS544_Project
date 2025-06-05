import asyncio
from typing import Coroutine,Dict
import json
from echo_quic import EchoQuicConnection, QuicStreamEvent
import pdu

clients = {}
id_tracker = 1

async def echo_server_proto(scope:Dict, conn:EchoQuicConnection):
        global id_tracker
        
        message:QuicStreamEvent = await conn.receive()
        dgram_in = pdu.Message.from_bytes(message.data)
        print("[svr] received message type: ", dgram_in.mtype)
        print("[svr] received message: ", dgram_in.payload)
        stream_id = message.stream_id

        if dgram_in.mtype == pdu.LOGIN_REQUEST:
                username = dgram_in.payload.get("username")
                password = dgram_in.payload.get("password")
                print(f"[svr] Login attempt by {username}")

                if username == "test_user" and password == "awesomepassword":
                        auth = 0
                        id = id_tracker
                        clients[id] = conn
                        id_tracker += 1
                else:
                        auth = 1
                        id = -1

                response = pdu.login_response(auth, id)
                await conn.send(QuicStreamEvent(stream_id, response.to_bytes(), False))
        
        elif dgram_in.mtype == pdu.CHAT_MESSAGE:
                id = dgram_in.payload.get("id")
                chat_msg = dgram_in.payload.get("message")
                print(f"[svr] Chat from {id}: {chat_msg}")

                # temporary
                await conn.send(QuicStreamEvent(stream_id, dgram_in.to_bytes(), False))

        elif dgram_in.mtype == pdu.LOGOUT_MESSAGE:
                id = dgram_in.payload.get("id")
                print(f"[svr] Logout by {id}")
                clients.pop(id)

        else:
                print("[svr] Ignoring unknown message:", dgram_in.mtype)


        # dgram_out = dgram_in
        # dgram_out.mtype |= pdu.MSG_TYPE_DATA_ACK
        # dgram_out.msg = "SVR-ACK: " + dgram_out.msg
        # rsp_msg = dgram_out.to_bytes()
        # rsp_evnt = QuicStreamEvent(stream_id, rsp_msg, False)
        # await conn.send(rsp_evnt)