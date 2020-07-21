import boto3
import json
import os
import socket
import sys
import tempfile

def str2bytes(input):
    return str.encode(input)

def bytes2str(input):
    return bytes.decode(input)

s3 = boto3.resource('s3')

host = str(sys.argv[1])
port = int(sys.argv[2])

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((host, port))

response = bytes2str(client.recv(4096))
print(response) #welcome msg

def upload_object(bucketname, data, filename):
    with tempfile.NamedTemporaryFile(mode='w', dir='.', suffix='.json', delete=False) as fp:
        json.dump(data, fp)
        tfname = fp.name
    
    s3.Bucket(bucketname).upload_file(tfname, filename + '.json') # Non-blocking???
    os.remove(tfname)

def get_object(bucket_name, key):
    obj = s3.Object(bucket_name=bucket_name, key=key + '.json')
    return obj

def eval_object(bucket_name, key):
    obj = get_object(bucket_name, key)
    return eval(obj.get()["Body"].read().decode())

def register(bucketname):
    s3.create_bucket(Bucket=bucketname)
    mails = {"mails" : []}
    upload_object(bucketname, mails, "mails")

def login(bucketname):
    return s3.Bucket(bucketname)

def create_post(bucketname, data):
    upload_object(bucketname, data, str(data["postid"]))

def read_post(data):
    post = eval_object(data["bucketname"], str(data["postid"]))
    print("\tAuthor\t:" + post["author"])
    print("\tTitle\t:" + post["title"])
    print("\tDate\t:" + post["date"])
    print("\t--")
    print("\t" + '\n\t'.join(post["content"].split('<br>')))
    print("\t--")
    for comment in post["comments"]:
        print("\t" + comment["user"] + ":" + comment["comment"])

def delete_post(data):
    obj = get_object(data["bucketname"], str(data["postid"]))
    obj.delete()

def update_post(data):
    post = eval_object(data["bucketname"], str(data["postid"]))

    if "title" in data:
        post["title"] = data["title"]
    
    if "content" in data:
        post["content"] = data["content"]
    
    if "comments" in data:
        post["comments"].extend(data["comments"])
    
    bucketname = post["bucketname"]
    upload_object(bucketname, post, str(post["postid"]))

def sent_mail(data):
    bucketname = data["bucketname"]
    del data["bucketname"]

    mails = eval_object(bucketname, "mails")

    mails["mails"].append(data)

    upload_object(bucketname, mails, "mails")

def retr_mail(bucketname, data):
    mails = eval_object(bucketname, "mails")
    mail = mails["mails"][data["mailid"]]
    print("\tSubject\t:" + mail["subject"])
    print("\tFrom\t:" + mail["from"])
    print("\tDate\t:" + mail["date"])
    print("\t--")
    print("\t" + '\n\t'.join(mail["content"].split('<br>')))

def delete_mail(bucketname, data):
    mails = eval_object(bucketname, "mails")
    del mails["mails"][data["mailid"]]

    upload_object(bucketname, mails, "mails")

while True:
    cmd = raw_input("% ")

    cmdlist = cmd.split()
    if len(cmdlist) == 0:
        continue
    else:
        action = cmdlist[0]

    client.send(str2bytes(cmd))
    
    resp = bytes2str(client.recv(4096))
    resplist = resp.split(';')
    msg = resplist[0]
    metadata = eval(resplist[1]) if len(resplist) > 1 else {}

    if action == "register":
        if "bucketname" in metadata:
            register(metadata["bucketname"])
    
    if action == "login":
        if "bucketname" in metadata:
            client_bucketname = metadata["bucketname"]
            client_bucket = login(client_bucketname)
            # print("[Success] Get Bucket!")
    
    if action == "create-post":
        if "postid" in metadata:
            create_post(client_bucketname, metadata)
            # print("[Success] Create Post!")
    
    if action == "read":
        if "postid" in metadata:
            read_post(metadata)
            msg = ""
            # print("[Success] Read Post!")
    
    if action == "delete-post":
        if "postid" in metadata:
            delete_post(metadata)
            # print("[Success] Delete Post!")
    
    if action == "update-post" or action == "comment":
        if "postid" in metadata:
            update_post(metadata)
            # print("[Success] Update Post!")
    
    if action == "mail-to":
        if "subject" in metadata:
            sent_mail(metadata)
            # print("[Success] Sent Mail!")
    
    if action == "retr-mail":
        if "mailid" in metadata:
            retr_mail(client_bucketname, metadata)
            msg = ""
            # print("[Success] Retr Mail!")

    if action == "delete-mail":
        if "mailid" in metadata:
            delete_mail(client_bucketname, metadata)
            # print("[Success] Delete Mail!")

    if action == "exit":
        break
    
    if msg:
        print(msg)