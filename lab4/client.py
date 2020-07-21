import socket
import sys
import threading

def str2bytes(input):
    return str.encode(input)

def bytes2str(input):
    return bytes.decode(input)

host = str(sys.argv[1])
port = int(sys.argv[2])

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((host, port))

def send(connection):
    while True:
        cmd = input("% ")
        cmdlist = cmd.split()
        if len(cmdlist) == 0:
            continue
        else:
            action = cmdlist[0]
            connection.send(str2bytes(cmd))
            break

while True:
    resp = bytes2str(client.recv(4096))
    if resp == "Exit Success.":
        break
    else:
        # if subscribe
        if " - by " in resp:
            print(resp, end="")
        else:
            print(resp)
            send_thread = threading.Thread(target = send, args = (client,))
            send_thread.start()