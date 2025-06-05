
import json

LOGIN_REQUEST = 1
LOGIN_RESPONSE = 2
CHAT_MESSAGE = 3
LOGOUT_MESSAGE = 4
ERROR_MESSAGE = 5

ERROR_SUDDEN_DISCONNECT = 1
ERROR_TIMEOUT = 2
ERROR_LOGIN_FROM_OTHER_LOCATION = 3
ERROR_UPDATE = 4

class Message:
    def __init__(self, mtype: int, payload: dict, sz:int = 0):
        self.mtype = mtype
        self.payload = payload
        # self.sz = len(self.msg)
        self.sz = len(json.dumps(payload).encode('utf-8'))
        
    def to_json(self):
        # return json.dumps(self.__dict__)    
        return json.dumps({
            "mtype": self.mtype,
            "payload": self.payload,
            "sz": self.sz
        })
    
    @staticmethod
    def from_json(json_str):
        # return Message(**json.loads(json_str))
        load = json.loads(json_str)
        return Message(load["mtype"], load["payload"])
    
    def to_bytes(self):
        # return json.dumps(self.__dict__).encode('utf-8')
        return self.to_json().encode('utf-8')
    
    @staticmethod
    def from_bytes(json_bytes):
        # return Message(**json.loads(json_bytes.decode('utf-8')))
        return Message.from_json(json_bytes.decode('utf-8'))

def login_request(username: str, password: str):
    return Message(LOGIN_REQUEST, {"username": username, "password": password}) 

def login_response(auth: int, id: int):
    return Message(LOGIN_RESPONSE, {"auth": auth, "id": id})

def chat_message(id: int, time: int, message: str):
    return Message(CHAT_MESSAGE, {"id": id, "time": time, "message": message})

def logout_message(id: int):
    return Message(LOGOUT_MESSAGE, {"id": id})

def error_message(id: int, error_code: int, message: str):
    return Message(ERROR_MESSAGE, {"id": id, "error_code": error_code, "message": message})
