
from typing import Dict
import json
from echo_quic import EchoQuicConnection, QuicStreamEvent
import pdu


async def echo_client_proto(scope:Dict, conn:EchoQuicConnection):
    
    #START CLIENT HERE
    print('[cli] starting client')

    # LOGIN_REQUEST
    login_message = pdu.login_request("test_user", "awesomepassword")
    
    new_stream_id = conn.new_stream()

    qs = QuicStreamEvent(new_stream_id, login_message.to_bytes(), False)
    await conn.send(qs)

    message:QuicStreamEvent = await conn.receive()
    response = pdu.Message.from_bytes(message.data)

    print('[cli] response type: ', response.mtype)
    print('[cli] payload: ', response.payload)
    #END CLIENT HERE
