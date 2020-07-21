db_filename = "db.json"
prompt = "% "
cmd_args = {
    "register" : 4,
    "login" : 3,
    "logout" : 1,
    "whoami" : 1,
    "exit" : 1
}
cmd_format = {
    "register" : "register <username> <email> <password>",
    "login" : "login <username> <password>",
    "logout" : "logout",
    "whoami" : "whoami",
    "exit" : "exit"
}

def str2bytes(input):
    return str.encode(input)

def bytes2str(input):
    return bytes.decode(input)

import json
db = {}
# key : username, value : [email, passwd]
try:
    with open(db_filename , 'r') as json_file:
        db = json.loads(json_file)
        json_file.close()
except:
    print("Create New Database")
    
client_username = {}
# key : client_fd, value : username/empty string

active_user = set()
# username

import select
import socket
import sys

master = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
port_no = int(sys.argv[1])

master.bind(('localhost', port_no))

master.listen(15)

inputs = [master]

while True:
    readable, writeable, execuable = select.select(inputs, [], [])
    
    for obj in readable:
        if obj is master:
            client, client_addr = master.accept()
            inputs.append(client)

            client_fd = client.fileno()
            client_username[client_fd] = ""

            print("New connection." + " " + str(client_addr))

            client.send(str2bytes(prompt))
        
        else:
            client = obj
            client_fd = client.fileno()

            req = bytes2str(client.recv(1024))
            req_list = req.split()

            if not req_list:
                continue

            action = req_list[0]
            resp = ""

            if action not in cmd_args:
                resp = "Command doesn't exist"
            elif len(req_list) != cmd_args[action]:
                resp = "Usage: " + cmd_format[action]
            else:
                if action == "register":
                    username = req_list[1]
                    if username in db:
                        resp = "Username is already used."
                    else:
                        email = req_list[2]
                        passwd = req_list[3]
                        db[username] = [email, passwd]
                        resp = "Register successfully."
                        json.dump(db, open(db_filename, 'w'))
                elif action == "login":
                    username = req_list[1]
                    passwd = req_list[2]
                    if client_username[client_fd]:
                        resp = "Please logout first."
                    elif username not in db:
                        resp = "Login failed."
                    elif passwd != db[username][1]:
                        resp = "Login failed."
                    elif username in active_user:
                        resp = "Please logout first."
                    else:
                        active_user.add(username)
                        client_username[client_fd] = username
                        resp = "Welcome, " + username + "."
                elif action == "logout":
                    if not client_username[client_fd]:
                        resp = "Please login first."
                    else:
                        username = client_username[client_fd]
                        active_user.remove(username)
                        client_username[client_fd] = ""
                        resp = "Bye, " + username + "."
                elif action == "whoami":
                    if not client_username[client_fd]:
                        resp = "Please login first."
                    else:
                        resp = client_username[client_fd] + "."
                elif action == "exit":
                    inputs.remove(client)

                    username = client_username[client_fd]
                    if username:
                        active_user.remove(username)

                    del client_username[client_fd]
                    client.close()
                    continue

            client.send(str2bytes(resp + "\n" + prompt))