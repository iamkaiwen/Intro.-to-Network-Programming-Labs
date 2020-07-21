db_filename = "db.json"
linebreak = "\n"
respbreak = ';'
welcome_msg = "********************************" + linebreak + "** Welcome to the BBS server. **" + linebreak + "********************************"
# prompt = "% "
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
mail_cmd_args = {
    "mail-to" : 6,
    "list-mail" : 1,
    "retr-mail" : 2,
    "delete-mail" : 2
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
    "mail-to" : "mail-to <username> --subject <subject> --content <content>",
    "list-mail" : "list-mail",
    "retr-mail" : "retr-mail <mail#>",
    "delete-mail" : "delete-mail <mail#>",
    "exit" : "exit"
}

def str2bytes(input):
    return input.encode('ascii', 'ignore')

def bytes2str(input):
    return bytes.decode(input)

import json
db = {
    "users" : {},
    # key : username, value : {"email" : email, "passwd" : passwd, "bucketname" : bucketname, "mails" : [mail]}
    # mail : {"subject": subject, "from": from, "date": date}
    # mail : {"subject": subject, "from": from, "date": date, "content": content}
    "boards" : {},
    # key : boardname, value : {"moderator" : moderator, "postids" : [postids]}
    "posts" : [{}],
    # post : {"bucketname" : bucketname, "postid" : postid, "boardname" : boardname, "author" : author, "title" : title, "date" : date}
    # post : {"bucketname" : bucketname, "postid" : postid, "boardname" : boardname, "author" : author, "title" : title, "date" : date, "content" : content, "comments" : [comment]}
    # comment : {"user" : user, "comment" : comment}
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

            # client.send(str2bytes(welcome_msg + prompt))
            client.send(str2bytes(welcome_msg))
        
        else:
            client = obj
            client_fd = client.fileno()

            # req = bytes2str(client.recv(1024))[:-1]
            req = bytes2str(client.recv(1024))
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
                        bucketname = username.lower() + '-' + str(abs(hash(username + time.ctime())))
                        db["users"][username] = {
                            "email" : email,
                            "passwd" : passwd,
                            "bucketname" : bucketname,
                            "mails" : []
                        }
                        resp = "Register successfully." + respbreak + str({"bucketname" : bucketname})
                elif action == "login":
                    username = req_list[1]
                    passwd = req_list[2]
                    if client_username[client_fd]:
                        resp = "Please logout first."
                    elif username not in db["users"]:
                        resp = "Login failed."
                    elif passwd != db["users"][username]["passwd"]:
                        resp = "Login failed."
                    elif username in active_user:
                        resp = "Please logout first."
                    else:
                        active_user.add(username)
                        client_username[client_fd] = username
                        resp = "Welcome, " + username + "." + respbreak + str({"bucketname" : db["users"][username]["bucketname"]})
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
                        resp = client_username[client_fd]
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
                                    post = {
                                        "bucketname" : db["users"][client_username[client_fd]]["bucketname"],
                                        "postid" : len(db["posts"]),
                                        "boardname" : boardname,
                                        "author" : client_username[client_fd],
                                        "title" : title,
                                        "date" : '-'.join([str(localtime.tm_year), str(localtime.tm_mon).zfill(2), str(localtime.tm_mday).zfill(2)])
                                    }
                                    db["boards"][boardname]["postids"].append(len(db["posts"]))
                                    db["posts"].append(post.copy())
                                    post["content"] = content
                                    post["comments"] = []
                                    resp = "Create post successfully." + respbreak + str(post)
                elif action == "list-board":
                    key = ""
                    tmplist = req.split("##", 1)
                    if len(tmplist) == 2:
                        key = tmplist[1]

                    resplist = [("Index", "Name", "Moderator")]
                    for boardname, info in db["boards"].items():
                        if key in boardname:
                            resplist.append((str(len(resplist)), boardname, info["moderator"]))

                    resp = linebreak.join(["\t{:<s}\t{:<s}\t{:<s}".format(item[0], item[1], item[2]) for item in resplist])
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
                                if key in db["posts"][postid]["title"] and postid not in db["deleted"]:
                                    title = db["posts"][postid]["title"]
                                    author = db["posts"][postid]["author"]
                                    date = db["posts"][postid]["date"][-5:]
                                    date = date.replace('-', '/')
                                    resplist.append((str(postid), title, author, date))

                            resp = linebreak.join(["\t{:<s}\t{:<s}\t{:<s}\t{:<s}".format(item[0], item[1], item[2], item[3]) for item in resplist])
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
                                resp = "Success." + respbreak + str(db["posts"][postid])
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
                            elif db["posts"][postid]["author"] != client_username[client_fd]:
                                resp = "Not the post owner."
                            else:
                                db["deleted"].append(postid)
                                resp = "Delete successfully." + respbreak + str(db["posts"][postid])
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
                        elif db["posts"][postid]["author"] != client_username[client_fd]:
                            resp = "Not the post owner."
                        else:
                            if "--title" in req_list:
                                new_title = req.split("--title ", 1)
                                db["posts"][postid]["title"] = new_title[1]
                                post = db["posts"][postid]
                            else:
                                new_content = req.split("--content ", 1)
                                post = db["posts"][postid].copy()
                                post["content"] = new_content[1]
                            resp = "Update successfully." + respbreak + str(post)
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
                            post = db["posts"][postid].copy()
                            post["comments"] = [{"user" : client_username[client_fd], "comment" : comment}]
                            resp = "Comment successfully." + respbreak + str(post)
            elif action in mail_cmd_args:
                if not client_username[client_fd]:
                    resp = "Please login first."
                elif action == "mail-to":
                    if len(req_list) < mail_cmd_args[action]:
                        resp = "Usage: " + cmd_format[action]
                    else:
                        tousername = req_list[1]

                        tmplist = req.split("--subject ", 1)
                        if len(tmplist) < 2:
                            resp = "Usage: " + cmd_format[action]
                        else:
                            tmplist = tmplist[1].split(" --content ", 1)
                            if len(tmplist) < 2:
                                resp = "Usage: " + cmd_format[action]
                            else:
                                subject = tmplist[0]
                                content = tmplist[1]
                                if tousername not in db["users"]:
                                    resp = tousername + " does not exist."
                                else:
                                    localtime = time.localtime()
                                    mail = {
                                        "subject": subject,
                                        "from": client_username[client_fd],
                                        "date" : '-'.join([str(localtime.tm_year), str(localtime.tm_mon).zfill(2), str(localtime.tm_mday).zfill(2)])
                                    }
                                    db["users"][tousername]["mails"].append(mail.copy())
                                    mail["content"] = content
                                    mail["bucketname"] = db["users"][tousername]["bucketname"]
                                    resp = "Sent successfully." + respbreak + str(mail)
                elif action == "list-mail":
                    if len(req_list) < mail_cmd_args[action]:
                        resp = "Usage: " + cmd_format[action]
                    else:
                        username = client_username[client_fd]
                        resplist = [("ID", "Subject", "From", "Date")]
                        for mails in db["users"][username]["mails"]:
                            Subject = mails["subject"]
                            From = mails["from"]
                            Date = mails["date"][-5:]
                            Date = Date.replace('-', '/')
                            resplist.append((str(len(resplist)), Subject, From, Date))

                        resp = linebreak.join(["\t{:<s}\t{:<s}\t{:<s}\t{:<s}".format(item[0], item[1], item[2], item[3]) for item in resplist])
                elif action == "retr-mail":
                    if len(req_list) < mail_cmd_args[action]:
                        resp = "Usage: " + cmd_format[action]
                    else:
                        username = client_username[client_fd]
                        mailid = int(req_list[1]) - 1
                        if mailid >= len(db["users"][username]["mails"]):
                            resp = "No such mail."
                        else:
                            ret = {
                                "mailid" : mailid
                            }
                            resp = "Success." + respbreak + str(ret)
                elif action == "delete-mail":
                    if len(req_list) < mail_cmd_args[action]:
                        resp = "Usage: " + cmd_format[action]
                    else:
                        username = client_username[client_fd]
                        mailid = int(req_list[1])
                        if mailid > len(db["users"][username]["mails"]):
                            resp = "No such mail."
                        else:
                            ret = {
                                "mailid" : mailid
                            }
                            del db["users"][username]["mails"][mailid - 1]
                            resp = "Mail deleted." + respbreak + str(ret)
            else:
                resp = "Command doesn't exist"

            json.dump(db, open(db_filename, 'w'))
            # client.send(str2bytes(str(resp) + linebreak + prompt))
            client.send(str2bytes(str(resp)))