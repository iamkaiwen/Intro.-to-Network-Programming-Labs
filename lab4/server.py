db_filename = "db.json"
linebreak = "\n"
welcome_msg = "********************************" + linebreak + "** Welcome to the BBS server. **" + linebreak + "********************************"
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

subscribe_cmd_args = {
    "subscribe" : 5,
    "unsubscribe" : 3,
    "list-sub" : 1
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
    "exit" : "exit",
    "subscribe" : "subscribe --board <board-name> --keyword <keyword>/subscribe --author <author-name> --keyword <keyword>",
    "unsubscribe" : "unsubscribe --board <board-name>/unsubscribe --author <author-name>",
    "list-sub" : "list-sub"
}

def str2bytes(input):
    return input.encode('ascii', 'ignore')

def bytes2str(input):
    return bytes.decode(input)

import json
db = {
    "users" : {},
    # key : username, value : {"email" : email, "passwd" : passwd}
    "boards" : {},
    # key : boardname, value : {"moderator" : moderator, "postids" : [postids]}
    "posts" : [{}],
    # post : {"postid" : postid, "boardname" : boardname, "author" : author, "title" : title, "date" : date, "content" : content, "comments" : [comment]}
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

subscribe_keywords = {}
# key : client_fd, value : {"board" : set((boardname, keyword)), "author" : set((authorname, keyword))}

board_subscriber = {}
# key : boardname, value : {"keyword" : set(client)}
# board_subscriber[boardname][keywords]

author_subscriber = {}
# key : author, value : {"keyword" : set(client)}
# author_subscriber[author][keywords]

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

            client.send(str2bytes(welcome_msg))

        else:
            client = obj
            client_fd = client.fileno()

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
                        
                        db["users"][username] = {
                            "email" : email,
                            "passwd" : passwd
                        }
                        resp = "Register successfully."
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
                        resp = "Welcome, " + username + "."
                        subscribe_keywords[client_fd] = {"board" : set(), "author" : set()}
                elif action == "logout":
                    if not client_username[client_fd]:
                        resp = "Please login first."
                    else:
                        username = client_username[client_fd]
                        active_user.remove(username)
                        client_username[client_fd] = ""

                        # unsubscribe
                        for (boardname, keyword) in subscribe_keywords[client_fd]["board"]:
                            board_subscriber[boardname][keyword].remove(client)
                        
                        for (author, keyword) in subscribe_keywords[client_fd]["author"]:
                            author_subscriber[author][keyword].remove(client)
                        del subscribe_keywords[client_fd]

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
                        # unsubscribe
                        for (boardname, keyword) in subscribe_keywords[client_fd]["board"]:
                            board_subscriber[boardname][keyword].remove(client)
                        
                        for (author, keyword) in subscribe_keywords[client_fd]["author"]:
                            author_subscriber[author][keyword].remove(client)
                        del subscribe_keywords[client_fd]

                    del client_username[client_fd]
                    client.send(str2bytes("Exit Success."))
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
                                        "postid" : len(db["posts"]),
                                        "boardname" : boardname,
                                        "author" : client_username[client_fd],
                                        "title" : title,
                                        "date" : '-'.join([str(localtime.tm_year), str(localtime.tm_mon).zfill(2), str(localtime.tm_mday).zfill(2)]),
                                        "content" : content,
                                        "comments" : []
                                    }
                                    db["boards"][boardname]["postids"].append(len(db["posts"]))
                                    db["posts"].append(post)
                                    resp = "Create post successfully."

                                    if boardname in board_subscriber:
                                        for keyword in board_subscriber[boardname]:
                                            if keyword in title:
                                                msg = "*" + boardname + " " + title + " \u002D by " + client_username[client_fd] + "*" + linebreak + prompt
                                                for subscriber in board_subscriber[boardname][keyword]:
                                                    subscriber.send(str2bytes(msg))
                                    
                                    if client_username[client_fd] in author_subscriber:
                                        for keyword in author_subscriber[client_username[client_fd]]:
                                            if keyword in title:
                                                msg = "*" + boardname + " " + title + " \u002D by " + client_username[client_fd] + "*" + linebreak + prompt
                                                for subscriber in author_subscriber[client_username[client_fd]][keyword]:
                                                    subscriber.send(str2bytes(msg))
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
                                post = db["posts"][postid]
                                resplist = []
                                resplist.append("\tAuthor\t:" + post["author"])
                                resplist.append("\tTitle\t:" + post["title"])
                                resplist.append("\tDate\t:" + post["date"])
                                resplist.append("\t--")
                                resplist.append("\t" + '\n\t'.join(post["content"].split('<br>')))
                                resplist.append("\t--")
                                for comment in post["comments"]:
                                    resplist.append("\t" + comment["user"] + ":" + comment["comment"])
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
                            elif db["posts"][postid]["author"] != client_username[client_fd]:
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
                        elif db["posts"][postid]["author"] != client_username[client_fd]:
                            resp = "Not the post owner."
                        else:
                            if "--title" in req_list:
                                new_title = req.split("--title ", 1)
                                db["posts"][postid]["title"] = new_title[1]
                            else:
                                new_content = req.split("--content ", 1)
                                db["posts"][postid]["content"] = new_content[1]
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
                            db["posts"][postid]["comments"].append({"user" : client_username[client_fd], "comment" : comment})
                            resp = "Comment successfully."
            elif action in subscribe_cmd_args:
                if len(req_list) < subscribe_cmd_args[action]:
                    resp = "Usage: " + cmd_format[action]
                elif not client_username[client_fd]:
                    resp = "Please login first."
                elif action == "subscribe":
                    if "--board" in req_list and "--keyword" in req_list:
                        tmp = req.split(" --board ", 1)[1]
                        boardname, keyword = tmp.split(" --keyword ", 1)
                        if (boardname, keyword) in subscribe_keywords[client_fd]["board"]:
                            resp = "Already subscribed"
                        else:
                            if boardname not in board_subscriber:
                                board_subscriber[boardname] = {}
                            
                            if keyword not in board_subscriber[boardname]:
                                board_subscriber[boardname][keyword] = set()

                            board_subscriber[boardname][keyword].add(client)
                            subscribe_keywords[client_fd]["board"].add((boardname, keyword))
                            resp = "Subscribe successfully"
                    elif "--author" in req_list and "--keyword" in req_list:
                        tmp = req.split(" --author ", 1)[1]
                        author, keyword = tmp.split(" --keyword ", 1)
                        if (author, keyword) in subscribe_keywords[client_fd]["author"]:
                            resp = "Already subscribed"
                        else:
                            if author not in author_subscriber:
                                author_subscriber[author] = {}
                            
                            if keyword not in author_subscriber[author]:
                                author_subscriber[author][keyword] = set()

                            author_subscriber[author][keyword].add(client)
                            subscribe_keywords[client_fd]["author"].add((author, keyword))
                            resp = "Subscribe successfully"
                    else:
                        resp = "Usage: " + cmd_format[action]
                elif action == "unsubscribe":
                    if "--board" in req_list:
                        boardname = req.split(" --board ", 1)[1]
                        unsubscribe_flag = False
                        tmp = subscribe_keywords[client_fd]["board"].copy()
                        for (tmp_boardname, keyword) in tmp:
                            if boardname == tmp_boardname:
                                unsubscribe_flag = True
                                subscribe_keywords[client_fd]["board"].remove((tmp_boardname, keyword))
                                board_subscriber[tmp_boardname][keyword].remove(client)
                        
                        if unsubscribe_flag:
                            resp = "Unsubscribe successfully"
                        else:
                            resp = "You haven't subscribed " + boardname
                    elif "--author" in req_list:
                        author = req.split(" --author ", 1)[1]
                        unsubscribe_flag = False
                        tmp = subscribe_keywords[client_fd]["author"].copy()
                        for (tmp_author, keyword) in tmp:
                            if author == tmp_author:
                                unsubscribe_flag = True
                                subscribe_keywords[client_fd]["author"].remove((tmp_author, keyword))
                                author_subscriber[tmp_author][keyword].remove(client)
                        
                        if unsubscribe_flag:
                            resp = "Unsubscribe successfully"
                        else:
                            resp = "You haven't subscribed " + author
                    else:
                        resp = "Usage: " + cmd_format[action]
                elif action == "list-sub":
                    if subscribe_keywords[client_fd]["board"]:
                        resp += "Board: "
                        tmp = {} # key : boardname, value : output_string 
                        for (boardname, keyword) in subscribe_keywords[client_fd]["board"]:
                            if boardname not in tmp:
                                tmp[boardname] = boardname + ": " + keyword
                            else:
                                tmp[boardname] += ", " + keyword
                        resp += '; '.join(tmp.values())

                    if subscribe_keywords[client_fd]["author"]:
                        if resp:
                            resp += linebreak
                        resp += "Author: "
                        tmp = {} # key : author, value : output_string 
                        for (author, keyword) in subscribe_keywords[client_fd]["author"]:
                            if author not in tmp:
                                tmp[author] = author + ": " + keyword
                            else:
                                tmp[author] += ", " + keyword
                        resp += '; '.join(tmp.values())
            else:
                resp = "Command doesn't exist"

            json.dump(db, open(db_filename, 'w'))
            client.send(str2bytes(resp))