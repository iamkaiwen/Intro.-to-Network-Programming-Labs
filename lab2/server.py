db_filename = "db.json"
linebreak = "\n"
welcome_msg = "********************************" + linebreak + "** Welcome to the BBS server. **" + linebreak + "********************************" + linebreak
prompt = "% "
user_cmd_args = {
    "register" : 4,
    "login" : 3,
    "logout" : 1,
    "whoami" : 1,
    "exit" : 1
}
post_cmd_args = {
    "create-board" : 2,
    "create-post" : 6,
    "list-board" : 1,
    "list-post" : 2,
    "read" : 2,
    "delete-post" : 2,
    "update-post" : 4,
    "comment" : 3
}
cmd_format = {
    "register" : "register <username> <email> <password>",
    "login" : "login <username> <password>",
    "logout" : "logout",
    "whoami" : "whoami",
    "create-board" : "create-board <name>",
    "create-post" : "create-post <board-name> --title <title> --content <content>",
    "list-board" : "list-board ##<key>",
    "list-post" : "list-post <board-name> ##<key>",
    "read" : "read <post-id>",
    "delete-post" : "delete-post <post-id>",
    "update-post" : "update-post <post-id> --title/content <new>",
    "comment" : "comment <post-id> <comment>",
    "exit" : "exit"
}

def str2bytes(input):
    return str.encode(input)

def bytes2str(input):
    return bytes.decode(input)

import json
db = {
    "users" : {},
    # key : username, value : [email, passwd]
    "boards" : {},
    # key : boardname, value : {"moderator" : moderator, "postids" : [postids]}
    "posts" : [[]],
    # post : [boardname, author, title, date, content , [comment]]
    # comment : [user, comment]
    "deleted" : []
}
try:
    with open(db_filename , 'r') as json_file:
        db = json.loads(json_file.read())
        json_file.close()
except Exception as e:
    print("Create New Database")
    
client_username = {}
# key : client_fd, value : username/empty string

active_user = set()
# username

import select
import socket
import sys
import time

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

            client.send(str2bytes(welcome_msg + prompt))
        
        else:
            client = obj
            client_fd = client.fileno()

            req = bytes2str(client.recv(1024))[:-1]
            req_list = req.split()

            if not req_list:
                continue

            action = req_list[0]
            resp = ""

            if action in user_cmd_args:
                if len(req_list) != user_cmd_args[action]:
                    resp = "Usage: " + cmd_format[action]
                elif action == "register":
                    username = req_list[1]
                    if username in db["users"]:
                        resp = "Username is already used."
                    else:
                        email = req_list[2]
                        passwd = req_list[3]
                        db["users"][username] = [email, passwd]
                        resp = "Register successfully."
                elif action == "login":
                    username = req_list[1]
                    passwd = req_list[2]
                    if client_username[client_fd]:
                        resp = "Please logout first."
                    elif username not in db["users"]:
                        resp = "Login failed."
                    elif passwd != db["users"][username][1]:
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
            elif action in post_cmd_args:
                if action == "create-board":
                    if len(req_list) != post_cmd_args[action]:
                        resp = "Usage: " + cmd_format[action]
                    else:
                        boardname = req_list[1]
                        if boardname in db["boards"]:
                            resp = "Board already exist."
                        elif not client_username[client_fd]:
                            resp = "Please login first."
                        else:
                            db["boards"][boardname] = {"moderator" : client_username[client_fd], "postids" : []}
                            resp = "Create board successfully."
                elif action == "create-post":
                    if len(req_list) < post_cmd_args[action]:
                        resp = "Usage: " + cmd_format[action]
                    else:
                        boardname = req_list[1]

                        tmplist = req.split("--title ", 1)
                        if len(tmplist) < 2:
                            resp = "Usage: " + cmd_format[action]
                        else:
                            tmplist = tmplist[1].split(" --content ", 1)
                            if len(tmplist) < 2:
                                resp = "Usage: " + cmd_format[action]
                            else:
                                title = tmplist[0]
                                content = tmplist[1]
                                if boardname not in db["boards"]:
                                    resp = "Board does not exist."
                                elif not client_username[client_fd]:
                                    resp = "Please login first."
                                else:
                                    localtime = time.localtime()
                                    post = [
                                        boardname,
                                        client_username[client_fd],
                                        title,
                                        '-'.join([str(localtime.tm_year), str(localtime.tm_mon).zfill(2), str(localtime.tm_mday).zfill(2)]),
                                        content,
                                        []
                                    ]
                                    db["boards"][boardname]["postids"].append(len(db["posts"]))
                                    db["posts"].append(post)
                                    resp = "Create post successfully."
                elif action == "list-board":
                    key = ""
                    tmplist = req.split("##", 1)
                    if len(tmplist) == 2:
                        key = tmplist[1]

                    resplist = [("Index", "Name", "Moderator")]
                    for boardname, info in db["boards"].items():
                        if key in boardname:
                            resplist.append((str(len(resplist)), boardname, info["moderator"]))

                    resp = linebreak.join(["{:<20s}{:<20s}{:<20s}".format(item[0], item[1], item[2]) for item in resplist])
                elif action == "list-post":
                    if len(req_list) < post_cmd_args[action]:
                        resp = "Usage: " + cmd_format[action]
                    else:
                        boardname = req_list[1]
                        if boardname not in db["boards"]:
                            resp = "Board does not exist."
                        else:
                            key = ""
                            tmplist = req.split("##", 1)
                            if len(tmplist) == 2:
                                key = tmplist[1]
                            
                            resplist = [("ID", "Title", "Author", "Date")]
                            for postid in db["boards"][boardname]["postids"]:
                                if key in db["posts"][postid][2] and postid not in db["deleted"]:
                                    title = db["posts"][postid][2]
                                    author = db["posts"][postid][1]
                                    date = db["posts"][postid][3][-5:]
                                    date = date.replace('-', '/')
                                    resplist.append((str(len(resplist)), title, author, date))

                            resp = linebreak.join(["{:<20s}{:<20s}{:<20s}{:<20s}".format(item[0], item[1], item[2], item[3]) for item in resplist])
                elif action == "read":
                    if len(req_list) < post_cmd_args[action]:
                        resp = "Usage: " + cmd_format[action]
                    else:
                        if not req_list[1].isdigit():
                            resp = "Usage: " + cmd_format[action]
                        else:
                            postid = int(req_list[1])
                            if postid >= len(db["posts"]) or postid in db["deleted"]:
                                resp = "Post does not exist."
                            else:
                                resplist = []
                                resplist.append("Author  :" + db["posts"][postid][1])
                                resplist.append("Title   :" + db["posts"][postid][2])
                                resplist.append("Date    :" + db["posts"][postid][3])
                                resplist.append("--")
                                resplist.extend(db["posts"][postid][4].split('<br>'))
                                resplist.append("--")
                                for comment in db["posts"][postid][5]:
                                    resplist.append(comment[0] + ": " + comment[1])

                                resp = linebreak.join(resplist)
                elif action == "delete-post":
                    if len(req_list) < post_cmd_args[action]:
                        resp = "Usage: " + cmd_format[action]
                    else:
                        if not req_list[1].isdigit():
                            resp = "Usage: " + cmd_format[action]
                        else:
                            postid = int(req_list[1])
                            if not client_username[client_fd]:
                                resp = "Please login first."
                            elif postid >= len(db["posts"]) or postid in db["deleted"]:
                                resp = "Post does not exist."
                            elif db["posts"][postid][1] != client_username[client_fd]:
                                resp = "Not the post owner."
                            else:
                                db["deleted"].append(postid)
                                resp = "Delete successfully."
                elif action == "update-post":
                    if len(req_list) < post_cmd_args[action]:
                        resp = "Usage: " + cmd_format[action]
                    elif "--title" not in req_list and "--content" not in req_list:
                        resp = "Usage: " + cmd_format[action]
                    elif not req_list[1].isdigit():
                        resp = "Usage: " + cmd_format[action]
                    else:
                        postid = int(req_list[1])
                        if not client_username[client_fd]:
                            resp = "Please login first."
                        elif postid >= len(db["posts"]) or postid in db["deleted"]:
                            resp = "Post does not exist."
                        elif db["posts"][postid][1] != client_username[client_fd]:
                            resp = "Not the post owner."
                        else:
                            if "--title" in req_list:
                                new_title = req.split("--title ", 1)
                                db["posts"][postid][2] = new_title[1]
                            else:
                                new_content = req.split("--content ", 1)
                                db["posts"][postid][4] = new_content[1]
                            resp = "Update successfully."
                elif action == "comment":
                    if len(req_list) < post_cmd_args[action]:
                        resp = "Usage: " + cmd_format[action]
                    elif not req_list[1].isdigit():
                        resp = "Usage: " + cmd_format[action]
                    else:
                        postid = int(req_list[1])
                        comment = req.split(None, 2)[2]
                        if not client_username[client_fd]:
                            resp = "Please login first."
                        elif postid >= len(db["posts"]) or postid in db["deleted"]:
                            resp = "Post does not exist."
                        else:
                            db["posts"][postid][5].append([client_username[client_fd], comment])
                            resp = "Comment successfully."
            else:
                resp = "Command doesn't exist"

            json.dump(db, open(db_filename, 'w'))
            client.send(str2bytes(str(resp) + linebreak + prompt))