
from typing import Dict
import json
from echo_quic import EchoQuicConnection, QuicStreamEvent
import pdu
from time import time


async def echo_client_proto(scope:Dict, conn:EchoQuicConnection):
    
    #START CLIENT HERE
    print('[cli] starting client')

    # LOGIN_REQUEST
    login_message = pdu.login_request("test_user", "awesomepassword")
    new_stream_id = conn.new_stream()
    qs = QuicStreamEvent(new_stream_id, login_message.to_bytes(), False)
    await conn.send(qs)

    # LOGIN_RESPONSE
    message:QuicStreamEvent = await conn.receive()
    response = pdu.Message.from_bytes(message.data)

    print('[cli] response type: ', response.mtype)
    print('[cli] payload: ', response.payload)

    if response.mtype != pdu.LOGIN_RESPONSE or response.payload.get("auth") != 0:
        print("[cli] Login failed.")
        return
    
    id = response.payload["id"]

    # CHAT_MESSAGE
    some_id = 5577
    chat = "HELLO I AM THE CLIENT!"
    current_time = int(time())
    chat_msg = pdu.chat_message(id, current_time, chat)

    await conn.send(QuicStreamEvent(new_stream_id, chat_msg.to_bytes(), False))

    chat_response: QuicStreamEvent = await conn.receive()
    chat_response_msg = pdu.Message.from_bytes(chat_response.data)

    print('[cli] chat response type: ', chat_response_msg.mtype)
    print('[cli] chat payload: ', chat_response_msg.payload)

    # LOGOUT_MESSAGE
    logout = pdu.logout_message(some_id)
    logout_event = QuicStreamEvent(conn.new_stream(), logout.to_bytes(), False)
    await conn.send(logout_event)

    print('[cli] sent logout message')

    # ERROR_MESSAGE
    

    #END CLIENT HERE
