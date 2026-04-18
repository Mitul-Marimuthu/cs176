#!/usr/bin/env python3

# Include needed libraries. Do _not_ include any libraries not included with
# Python3 (i.e. do not use `pip`).
import socket
import sys

# parses each line as a different message to be sent through the network
# adds a dot at the beginning of lines that start with a dot so that
# the server doesn't prematurely end the message. 
def dot_stuff(body):
    lines = body.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    return '\r\n'.join('.' + l if l.startswith('.') else l for l in lines)

BUFFER_SIZE = 4096

# Parse command-line arguments.
host    = sys.argv[1]
port    = int(sys.argv[2])
from_addr = sys.argv[3]
to_addr   = sys.argv[4]
subject   = sys.argv[5]

# Read the email body from standard input.
body = sys.stdin.read()

# Establish a TCP connection with the SMTP server.
# host_IP = socket.gethostbyname(host)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
s.connect((host, port))

# Read greeting from the server.
data = s.recv(BUFFER_SIZE)
response = data.decode('utf-8')

if not response.startswith('220'):
    raise Exception('220 reply not received from server.')

# Note: the SMTP spec requires every command to end with \r\n, not just \n.
# This applies to commands (HELO, MAIL FROM, etc.) and to the message headers
# and body sent after DATA.

# Send HELO command and get server response.
s.sendall('HELO client\r\n'.encode())
response = s.recv(BUFFER_SIZE).decode('utf-8')
# print(response)
if not response.startswith('250'):
    raise Exception('250 reply not received from server.')

# Send MAIL FROM command.
s.sendall(f"MAIL FROM: <{from_addr}>\r\n".encode())
response = s.recv(BUFFER_SIZE).decode('utf-8')
if not response.startswith('250'):
    raise Exception('250 reply not received from server')

# Send RCPT TO command.
s.sendall(f"RCPT TO: <{to_addr}>\r\n".encode())
response = s.recv(BUFFER_SIZE).decode('utf-8')
if not response.startswith('250'):
    raise Exception('250 reply not received from server')

# Send DATA command.
s.sendall("DATA\r\n".encode())
response = s.recv(BUFFER_SIZE).decode('utf-8')
if not response.startswith('354'):
    raise Exception('354 reply not received from server')

# Send message headers and body.
s.sendall(f"Subject: {subject}\r\n\r\n{dot_stuff(body)}\r\n.\r\n".encode())

# Response may arrive in multiple chunks for larger messages. 
data=  ""
while True:
    chunk = s.recv(BUFFER_SIZE).decode('utf-8')
    if not chunk:
        break
    data += chunk
    lines = data.splitlines()
    if lines:
        last = lines[-1]
        # Complete when last line is "NNN <text>" (space = final line)
        if len(last) >= 4 and last[3] == ' ' and data.endswith("\r\n"):
            break


if not last.startswith('250'):
    raise Exception('Server failed to confirm message receipt')

# Send QUIT command.
s.sendall("QUIT\r\n".encode())

# Close the socket when finished.
s.close()
