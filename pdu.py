
import json

# our PDUs
LOGIN_REQUEST = 1
LOGIN_RESPONSE = 2
CHAT_MESSAGE = 3
LOGOUT_MESSAGE = 4
ERROR_MESSAGE = 5
PING_MESSAGE = 6
VERSION_REQUEST = 7
VERSION_RESPONSE = 8

# enums
ERROR_SUDDEN_DISCONNECT = 1
ERROR_TIMEOUT = 2
ERROR_LOGIN_FROM_OTHER_LOCATION = 3
ERROR_UPDATE = 4
ERROR_UNSUPPORTED_VERSION = 5

# description for errors
ERROR_DESCRIPTIONS = {
    ERROR_SUDDEN_DISCONNECT: "Client disconnected suddenly",
    ERROR_TIMEOUT: "Session timed out due to inactivity",
    ERROR_LOGIN_FROM_OTHER_LOCATION: "Login attempt from another location",
    ERROR_UPDATE: "Client update required",
    ERROR_UNSUPPORTED_VERSION: "Incompatible version"
}

# actual message object, has message type, the payload which is a python dictionary
# and the size of the payload.
class Message:
    def __init__(self, mtype: int, payload: dict, version: str="1.0.0", sz:int = 0):
        self.mtype = mtype
        self.payload = payload
        self.version = version
        self.sz = len(json.dumps(payload).encode('utf-8'))
        
    # converts message into json object
    def to_json(self):
        return json.dumps({
            "mtype": self.mtype,
            "payload": self.payload,
            "version": self.version,
            "sz": self.sz
        })
    
    # gets back a message object from the json object
    @staticmethod
    def from_json(json_str):
        load = json.loads(json_str)
        return Message(load["mtype"], load["payload"], load.get("version", "1.0.0"))
    
    # converts json into bytes
    def to_bytes(self):
        return self.to_json().encode('utf-8')
    
    # converts bytes back to a message object
    @staticmethod
    def from_bytes(json_bytes):
        return Message.from_json(json_bytes.decode('utf-8'))

# checks the validity of the login request (less than 32 characters, and not empty)
def login_request(username: str, password: str):
    if len(username) > 32 or len(password) > 32:
        raise ValueError("Username and password must not exceed 32 characters.")
    if not username or not password:
        raise ValueError("Username or password cannot be empty")
    return Message(LOGIN_REQUEST, {"username": username, "password": password}) 

# method for sending login_response message
def login_response(auth: int, id: int):
    return Message(LOGIN_RESPONSE, {"auth": auth, "id": id})

# method for sending chat_message message
def chat_message(id: int, time: int, message: str):
    return Message(CHAT_MESSAGE, {"id": id, "time": time, "message": message})

# method for sending logout_message message
def logout_message(id: int):
    return Message(LOGOUT_MESSAGE, {"id": id})

# method for sending error_message message and for seeing description of the error code
def error_message(id: int, error_code: int, message: str):
    if error_code not in ERROR_DESCRIPTIONS:
        raise ValueError(f"Invalid error code: {error_code}")

    return Message(ERROR_MESSAGE, {"id": id, "error_code": error_code, "message": message})

# method for sending pings to server to check healthiness of client
def ping_message(id: int):
    return Message(PING_MESSAGE, {"id": id})

# method for sending a version request
def version_request(supported_versions: list[str]):
    return Message(VERSION_REQUEST, {"supported_versions": supported_versions})

# method for server relaying back a version response and success on negotiation
def version_response(selected_version: str, success: bool):
    return Message(VERSION_RESPONSE, {
        "selected_version": selected_version,
        "success": success
    })

# this is how we can send back to the client a failed versioning attempt
def error_unsupported_version():
    return error_message(-1, ERROR_UNSUPPORTED_VERSION, ERROR_DESCRIPTIONS[ERROR_UNSUPPORTED_VERSION])
