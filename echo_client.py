
from typing import Dict
import json
from echo_quic import EchoQuicConnection, QuicStreamEvent
import pdu
from time import time
import asyncio

# this is from our DFA, describes all possible states
class ClientState:
    DISCONNECTED = "DISCONNECTED"
    INITIAL = "INITIAL"
    CONNECTED = "CONNECTED"
    REQUEST = "REQUEST"
    READY = "READY"
    CHATTING = "CHATTING"
    CLOSED = "CLOSED"

# chatclient object, we use this to track the state of each client
class ChatClient:
    def __init__(self):
        self.state = ClientState.DISCONNECTED
        self.id = None
        self.conn = None
        self.stream_id = None

    # transition state method, we can change states using this
    def transition_state(self, new_state):
        print(f"[cli] transitioning from {self.state} to {new_state}")
        self.state = new_state

    # error handling for the errors defined in our PDU
    async def handle_error(self, error_msg):
        error_code = error_msg.payload.get("error_code")
        error_text = error_msg.payload.get("message")
        print(f"[cli] Error received [{error_code}]: {error_text}")

        if error_code == pdu.ERROR_SUDDEN_DISCONNECT:
            print("[cli] Server detected sudden disconnect")
            self.transition_state(ClientState.DISCONNECTED)
            
        elif error_code == pdu.ERROR_TIMEOUT:
            print("[cli] Session timed out due to inactivity")
            self.transition_state(ClientState.DISCONNECTED)
            
        elif error_code == pdu.ERROR_LOGIN_FROM_OTHER_LOCATION:
            print("[cli] Login detected from another location")
            self.transition_state(ClientState.DISCONNECTED)
            
        elif error_code == pdu.ERROR_UPDATE:
            print("[cli] Client update required")
            self.transition_state(ClientState.DISCONNECTED)
            return False
            
        return True

# this waits for user input from each client
async def get_user_input(prompt):
    wait = asyncio.get_event_loop()
    return await wait.run_in_executor(None, input, prompt)

# this is a much needed method that helps check whether each connection is healthy or not
# for example, if you hit ctrl+c while in a client, this lets the server find out that
# the client is no longer responsive because it hasn't received a ping 
async def ping_loop(conn, client_id):
    try:
        while True:
            await asyncio.sleep(10)
            ping = pdu.ping_message(client_id)
            await conn.send(QuicStreamEvent(0, ping.to_bytes(), False))
    except asyncio.CancelledError:
        print("[cli] Ping cancelled")
    except Exception as e:
        print(f"[cli] Ping error: {e}")

# starts the client, sends login_request, handles login_response
# while loop for chatting once authenticated
async def echo_client_proto(scope:Dict, conn:EchoQuicConnection):
    client = ChatClient()
    client.conn = conn

    try:
        #START CLIENT HERE
        print("[cli] starting client")
        client.transition_state(ClientState.INITIAL)

        # clients supported versions, can change for version negotiation testing
        supported_versions = ["1.2", "1.1", "1.0"]
        # supported_versions = ["0"]
        version_request = pdu.version_request(supported_versions)

        print("[cli] Sending version request")
        new_stream_id = conn.new_stream()
        await conn.send(QuicStreamEvent(new_stream_id, version_request.to_bytes(), False))

        # get the VERSION_RESPONSE from the server
        message = await conn.receive()
        response = pdu.Message.from_bytes(message.data)

        # response if we negotiate on a version
        if response.mtype == pdu.VERSION_RESPONSE:
            selected_version = response.payload.get("version")
            print(f"[cli] Negotiated protocol version: {selected_version}")
        
        # if something goes wrong in version negotiation, just in case
        elif response.mtype == pdu.ERROR_MESSAGE:
            await client.handle_error(response)
            return
        else:
            print("[cli] Unexpected message type during version negotiation")
            return

        # LOGIN_REQUEST
        # allows user to enter user/pass and attempt to login
        client.transition_state(ClientState.CONNECTED)
        username = await get_user_input("Username: ")
        password = await get_user_input("Password: ")
        print("[cli] Sending login request")
        login_message = pdu.login_request(username, password)
        client.transition_state(ClientState.REQUEST)
        new_stream_id = conn.new_stream()
        qs = QuicStreamEvent(new_stream_id, login_message.to_bytes(), False)
        await conn.send(qs)

        # gets the result of the login attempt from the server
        # LOGIN_RESPONSE
        message:QuicStreamEvent = await conn.receive()
        response = pdu.Message.from_bytes(message.data)

        print("[cli] response type: ", response.mtype)
        print("[cli] payload: ", response.payload)

        # if error, handle it
        if response.mtype == pdu.ERROR_MESSAGE:
            await client.handle_error(response)
            return
        
        # if its not a login response, just disconnect user
        if response.mtype != pdu.LOGIN_RESPONSE:
            print(f"[cli] unknwon response type: {response.mtype}")
            client.transition_state(ClientState.DISCONNECTED)
            return

        # if bad credentials, disconnect them
        if response.payload.get("auth") != 0:
            print("[cli] login failed, bad credentials.")
            client.transition_state(ClientState.DISCONNECTED)
            return
        
        # else they successfully logged in!
        client.id = response.payload["id"]
        client.transition_state(ClientState.READY)
        print(f"[cli] Login successful, assigned ID: {client.id}")
        ping_task = asyncio.create_task(ping_loop(conn, client.id))

        # CHAT_MESSAGE
        print("[cli] Entering chat mode")
        print("Enter messages to chat. Type \"!quit\" or \"!exit\" to logout")
        client.transition_state(ClientState.CHATTING)

        # infinite loop while chatting until we !quit or !exit or disconnect somehow
        while True:
            try:
                # just a cool way to show/prompt the user for input
                chat_input = await get_user_input('> ')

                # this is how they can logout
                if chat_input.lower() in ['!quit', '!exit']:
                    print('[cli] Exiting chat...')
                    break

                # ignore empty messages
                if not chat_input.strip():
                    continue

                # get the time and send the chat message
                current_time = int(time())
                chat_msg = pdu.chat_message(client.id, current_time, chat_input)

                await conn.send(QuicStreamEvent(new_stream_id, chat_msg.to_bytes(), False))

                chat_response: QuicStreamEvent = await conn.receive()
                chat_response_msg = pdu.Message.from_bytes(chat_response.data)

                if chat_response_msg.mtype == pdu.ERROR_MESSAGE:
                    await client.handle_error(chat_response_msg)
                    return
                
                print("[cli] server response: ", chat_response_msg.payload)

            except KeyboardInterrupt:
                print("[cli] kbd interrupt by user")
                break
            except Exception as e:
                print(f"[cli] Error while chatting: {e}")
                break

        # this triggers when we do !exit or !quit, if we hit ctrl+c, then we immediately
        # go to disconnected state
        # LOGOUT_MESSAGE
        print("[cli] sending logout")
        logout = pdu.logout_message(client.id)
        logout_event = QuicStreamEvent(conn.new_stream(), logout.to_bytes(), False)
        ping_task.cancel()
        await conn.send(logout_event)

        client.transition_state(ClientState.CLOSED)
        print("[cli] logged out")
        # ERROR_MESSAGE

    except Exception as e:
        print(f"[cli] Exception: {e}")
        client.transition_state(ClientState.DISCONNECTED)

    #END CLIENT HERE