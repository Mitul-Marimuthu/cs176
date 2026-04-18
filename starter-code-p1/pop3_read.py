#!/usr/bin/env python3

# Include needed libraries. Do _not_ include any libraries not included with
# Python3 (i.e. do not use `pip`).
import socket
import sys

BUFFER_SIZE = 4096
PASSWORD = 'password'

# Parse command-line arguments.
host     = sys.argv[1]
port     = int(sys.argv[2])
username = sys.argv[3]

# Establish a TCP connection with the POP3 server.
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host, port))

# Read greeting from the server.
data = s.recv(BUFFER_SIZE)
response = data.decode('utf-8')

if not response.startswith('+OK'):
    raise Exception('+OK not received from server.')

# Note: the POP3 spec requires every command to end with \r\n, not just \n.

# Log in with USER and PASS commands.
s.send(f"USER {username}\r\n".encode())
response = s.recv(BUFFER_SIZE).decode('utf-8')
if not response.startswith('+OK'):
    raise Exception("+OK reply not received from server") 

s.send(f"PASS {PASSWORD}\r\n".encode())
response = s.recv(BUFFER_SIZE).decode('utf-8')
if not response.startswith('+OK'):
    raise Exception("+OK reply not received from server") 

# Get the number of messages with the LIST command.
# Note: the LIST response spans multiple lines and ends with a line
# containing only '.'. Do not assume a fixed number of recv() calls will
# capture the full response — depending on the network, the entire response
# may arrive in a single recv() or be split across several. Accumulate data
# until you have seen the terminator.

s.send("LIST\r\n".encode())
full_response = ""
while True:
    chunk = s.recv(BUFFER_SIZE).decode('utf-8')
    full_response += chunk
    
    if "\r\n.\r\n" in full_response or full_response == ".\r\n":
        break

messages = full_response.splitlines()
n = len(messages)
# Retrieve and print each message with the RETR command.
# The same caveat about multi-line responses applies here.
# Print messages separated by a line containing only '---'.
for message in messages[1:n-1]:
    parts = message.split()
    if not parts: continue
    tag = parts[0]

    s.send(f"RETR {tag}\r\n".encode())

    full_email = ""
    while True:
        chunk = s.recv(BUFFER_SIZE).decode('utf-8')
        full_email += chunk
        if "\r\n.\r\n" in full_email or full_email.endswith(".\r\n"):
            break

    subject = "None"
    from_user = "None"
    to_user = "None"
    body = ""
    for line in full_email.splitlines():
        if line.lower().startswith("subject"):
            subject = line[8:]
        elif line.startswith("X-Peer"): continue
        elif line.startswith("X-Mail"):
            from_user = line[11:]
        elif line.startswith("X-Rcpt"):
            to_user = line[10:]
        elif line == ".": break
        elif not line.startswith("+OK"):
            body += (line + "\n")
    body = body[:-1]
    
    print(f"From: {from_user}")
    print(f"To: {to_user}")
    print(f"Subject: {subject}")
    print(body)
    print("---")

s.send("QUIT\r\n".encode())

# Close the socket when finished.
s.close()
