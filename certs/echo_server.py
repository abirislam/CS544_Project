import asyncio
from typing import Coroutine,Dict
import json
from echo_quic import EchoQuicConnection, QuicStreamEvent
import pdu
from time import time

clients = {}
id_tracker = 1
users = set()
SERVER_SUPPORTED_VERSIONS = ["1.2", "1.1", "1.0"]

# Allows server to access client states
class ClientStateForServer:
    DISCONNECTED = "DISCONNECTED"
    CONNECTED = "CONNECTED"
    AUTHENTICATED = "AUTHENTICATED"
    CHATTING = "CHATTING"
    LOGGED_OUT = "LOGGED_OUT"

# Method to create a session object for each client attempting to connect
class ClientSession:
    def __init__(self, id, conn, username):
        self.id = id
        self.conn = conn
        self.username = username
        self.state = ClientStateForServer.CONNECTED
        self.last_activity = time()

    # helper method to change client's time since last message (helps with idling)
    def change_activity(self):
        self.last_activity = time()

    # transition between our DFA states
    def transition_state(self, new_state):
        print(f"[svr] Client {self.id} transitioning from {self.state} to {new_state}")
        self.state = new_state

# A way for the server to send error messages to specific client
async def send_error(conn, stream_id, client_id, error_code, message):
    error_msg = pdu.error_message(client_id, error_code, message)
    await conn.send(QuicStreamEvent(stream_id, error_msg.to_bytes(), False))
    print(f"[svr] Sent error {error_code} to client {client_id}: {message}")

# Proposal detailed a timeout for clients, this method checks that clients have not disappeared
# after 300 seconds
async def remove_inactive_clients():
    current_time = time()
    inactive_clients = []

    # finds which clients have been inactive for more than 300 seconds and stages them
    # for timing out
    for client_id, session in clients.items():
        if current_time - session.last_activity > 300:
            inactive_clients.append(client_id)

    # times out all staged clients
    for client_id in inactive_clients:
        session = clients[client_id]
        print(f"[svr] Timing out client {client_id} for inactivity")
    
        try:
            await send_error(session.conn, 0, client_id, pdu.ERROR_TIMEOUT, 
                "Session timed out due to inactivity")
        except:
            pass
            
        users.discard(session.username)
        session.transition_state(ClientStateForServer.DISCONNECTED)
        del clients[client_id]

# the main builk of the code
async def echo_server_proto(scope:Dict, conn:EchoQuicConnection):
    # create new session id for each client starting at 1
    global id_tracker
    current_client_id = None
    session = None

    # while loop for chatting
    try:
        while True:
            # this part checks if any clients are idling / disconnected somehow
            # this is necessary because if a client disconnects the server needs to know
            # so the client can try to login again and not get the 
            # LOGIN_FROM_OTHER_LOCATION error message
            try:
                message:QuicStreamEvent = await asyncio.wait_for(conn.receive(), timeout=1.0)
                if message is None:
                    raise ConnectionResetError("Connection closed by client")
            except asyncio.TimeoutError:
                continue
            # we had a connection time out here, perhaps by using ctrl+c
            except Exception as e:
                print(f"[svr] Connection error: {e}")
                if current_client_id and current_client_id in clients:
                    print(f"[svr] Client {current_client_id} disconnected unexpectedly")
                    session = clients[current_client_id]
                    users.discard(session.username)
                    session.transition_state(ClientStateForServer.DISCONNECTED)
                    del clients[current_client_id]
                break

            # read the message from the client
            dgram_in = pdu.Message.from_bytes(message.data)
            print("[svr] received message type: ", dgram_in.mtype)
            print("[svr] received message: ", dgram_in.payload)
            stream_id = message.stream_id

            # check the client's versions
            # and compare it against the server's versions
            if dgram_in.mtype == pdu.VERSION_REQUEST:
                client_versions = dgram_in.payload.get("supported_versions", [])
                print(f"[svr] Client supports versions: {client_versions}")

                # for-else bc its easy, check versions in client, check versions in server
                # if theres a match use it
                for version in client_versions:
                    if version in SERVER_SUPPORTED_VERSIONS:
                        selected_version = version
                        print(f"[svr] Agreed on version {selected_version}")
                        response = pdu.version_response(selected_version, True)
                        await conn.send(QuicStreamEvent(stream_id, response.to_bytes(), False))
                        break
                else:
                    print(f"[svr] No compatible version found with client")
                    await conn.send(QuicStreamEvent(stream_id, pdu.error_unsupported_version().to_bytes(), False))
                    break


            # checks if the message is a LOGIN_REQUEST
            # authenticates the user
            # currently hardcoded in 2 users, user1 and user2
            # assigns ID after login
            elif dgram_in.mtype == pdu.LOGIN_REQUEST:
                username = dgram_in.payload.get("username")
                password = dgram_in.payload.get("password")
                print(f"[svr] Login attempt by {username}")

                # checks if a login attempt is already logged in, and if so block it
                if username in users:
                    await send_error(conn, stream_id, -1, pdu.ERROR_LOGIN_FROM_OTHER_LOCATION,
                                        "User already logged in from another location")
                    continue

                # credential checker, and assign new id to verified login
                if (username == "user1" and password == "pass1") or (username == "user2" and password == "pass2"):
                    auth = 0
                    current_client_id = id_tracker

                    session = ClientSession(current_client_id, conn, username)
                    session.transition_state(ClientStateForServer.AUTHENTICATED)
                    clients[current_client_id] = session
                    users.add(username)
                    id_tracker += 1

                    print(f"[svr] Login successful for {username}; assigned ID: {current_client_id}")

                else:
                    auth = 1
                    current_client_id = -1
                    print(f"[svr] Login failed for {username}")

                # send the response back to client
                response = pdu.login_response(auth, current_client_id)
                await conn.send(QuicStreamEvent(stream_id, response.to_bytes(), False))
        
            # if the message is a chat_message
            # get the client's id and the chat message
            # display it on server side
            # parrot it back to client so server doesn't have to type
            elif dgram_in.mtype == pdu.CHAT_MESSAGE:
                client_id = dgram_in.payload.get("id")
                chat_msg = dgram_in.payload.get("message")

                if client_id not in clients:
                    await send_error(conn, stream_id, client_id, pdu.ERROR_SUDDEN_DISCONNECT,
                                "Client session not found")
                    continue

                session = clients[client_id]
                session.change_activity()
                session.transition_state(ClientStateForServer.CHATTING)

                print(f"[svr] Chat from {session.username}: {chat_msg}")
                
                # parrot back chat to client
                await conn.send(QuicStreamEvent(stream_id, dgram_in.to_bytes(), False))

            # logout message for when client does !exit or !quit
            elif dgram_in.mtype == pdu.LOGOUT_MESSAGE:
                client_id = dgram_in.payload.get("id")
                print(f"[svr] Logout by {client_id}")

                if client_id in clients:
                    session = clients[client_id]
                    session.transition_state(ClientStateForServer.LOGGED_OUT)
                    users.discard(session.username)
                    print(f"[svr] Client {session.username} logged out")
                    del clients[client_id]
                else:
                    print(f"[svr] Logout request for unknown client {client_id}")
            
                break

            # error messages for error handling
            elif dgram_in.mtype == pdu.ERROR_MESSAGE:
                client_id = dgram_in.payload.get("id")
                error_code = dgram_in.payload.get("error_code")
                error_msg = dgram_in.payload.get("message")
                
                print(f"[svr] Received error from client {client_id}: {error_code} | {error_msg}")
                
                if client_id in clients:
                    session = clients[client_id]
                    
                    if error_code == pdu.ERROR_SUDDEN_DISCONNECT:
                        print(f"[svr] Client {client_id} reported sudden disconnect")
                        users.discard(session.username)
                        session.transition_state(ClientStateForServer.DISCONNECTED)
                        del clients[client_id]
                        break

            # checks for PING MESSAGES
            # clients send a ping every 10s to show that they are a healthy connection
            # if not healthy they are taken down
            elif dgram_in.mtype == pdu.PING_MESSAGE:
                client_id = dgram_in.payload.get("id")

                if client_id in clients:
                    session = clients[client_id]
                    session.change_activity()
                    print(f"[svr] Ping received from client {session.username}")

            else:
                print("[svr] Ignoring unknown message:", dgram_in.mtype)

    # handles any exceptions that rise up in the server protocol
    # disconnects the user
    except Exception as e:
        print(f"[svr] Exception in server protocol: {e}")

        if current_client_id and current_client_id in clients:
            session = clients[current_client_id]
            users.discard(session.username)
            session.transition_state(ClientStateForServer.DISCONNECTED)
            del clients[current_client_id]
            print(f"[svr] removed session for client {current_client_id}")
        elif session is not None:
            users.discard(session.username)
            print(f"[svr] removed session for {session.username}")

        print("[svr] Connection ended")