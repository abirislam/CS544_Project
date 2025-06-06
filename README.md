# CS544_Project

## About
- Client & Server both written in Python
- This is a chatting protocol
- The client(s) send messages to the server and the server parrots them back
- Server binds to hardcoded port: 55667, and client defaults to this
- Server runs on localhost, and client defaults to this
- When running the server, you can change the port using -p, and the address to listen on using -l
- When running the client, you can change the port using -p, and address using -s

## Running The Application
- This program uses the skeleton code provided by the professor
- You can install the requirements by running `pip3 install -r requirements.txt`
- Afterwards you can run the application by using the command for python for your given system, followed by `echo.py` and `server` or `client` depending on which you're running first
- Example commandline arguments for client and server (on linux):
- `python3 echo.py server -l 127.0.0.1 -p 55667`
- `python3 echo.py client -s 127.0.0.1 -p 55667`
- `python3 echo.py server`
- `python3 echo.py client`
- Once both server and client are up running (server should be running first), the client and server will do version negotiation
- If you want to test out the negotiation, you can just check echo_client.py and comment/uncomment out the code thats there
- The client will prompt you to login
- There are 2 login credentials you can use: 
- Username: user1, Password: pass1
- Username: user2, Password: pass2
- You can even login with both of these clients at the same time (so would need 3 terminal windows open -> one for server, one for user1, one for user2)

## Extra Credit
- GitHub Repo
- Server handles more than one client at the same time
- Update of protocol specification summary (see below)

## Update of Protocol Specification Summary
While building the protocol, I noticed the need for another way to determine if a client disconnected. Users are able to kill the terminal at any time using ctrl+c , but there wasnt a way for the server to detect that. Because of that, I modified the PDU to include a PING_MESSAGE. This message would let the client ping the server every 10 seconds to show that it is a healthy connection. The server would see that the client is pinging and knows that the client is healthy. 

Before this, a client could exit using ctrl+c and the server would still believe that the client is connected. This is a problem because the server has a list of currently logged in users, and when a user tries to login it will reply that the client is already logged in from another location, as defined in my proposal. Because of this, I had situations where the client was clearly disconnected, but the server thought the connection was healthy. After implementing the PING_MESSAGE, this fixed the issue.

Also, I realized my proposal did not actually have a way of tracking the version. Because of this I had to modify my Message object to include a version attribute to keep track of the version. Furthermore, to allow for version negotiating, I needed to add new message types into my PDU as well. This would be VERSION_REQUEST and VERSION_RESPONSE.

For extensbility, one could try to add client to server to client chatting and not just client/server chatting. 

## Improvements Over Proposal
We now have a PING_MESSAGE mechanism to detect any disconnected clients

## Extensibility
- group chats
- typing indicators (x person is typing)
- client to client communication (with server in the middle of course)