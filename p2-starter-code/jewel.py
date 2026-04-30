#!/usr/bin/env python3

import os
import select
import socket
import sys

from file_reader import FileReader

MIME_TYPES = {
    '.html': 'text/html',
    '.css':  'text/css',
    '.png':  'image/png',
    '.jpg':  'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif':  'image/gif',
}


def get_mime(path):
    _, ext = os.path.splitext(path)
    return MIME_TYPES.get(ext.lower(), 'application/octet-stream') # default return so that response doesn't break


def build_response(status_code, status_text, headers, body=b''):
    lines = f'HTTP/1.1 {status_code} {status_text}\r\n'
    for k, v in headers.items():
        lines += f'{k}: {v}\r\n'
    lines += '\r\n'
    return lines.encode('utf-8') + body


def error_response(status_code, status_text, include_body=True):
    body = f'<html><body><h1>{status_code} {status_text}</h1></body></html>'.encode('utf-8')
    return build_response(status_code, status_text, {
        'Content-Type': 'text/html',
        'Content-Length': len(body),
        'Connection': 'close',
    }, body if include_body else b'')


def parse_request(data):
    try:
        text = data.decode('utf-8', errors='replace')
    except Exception:
        return None

    header_end = text.find('\r\n\r\n')
    if header_end == -1:
        return None

    lines = text[:header_end].split('\r\n')
    if not lines:
        return None

    fields = lines[0].split()
    if len(fields) < 2:
        return None

    method = fields[0]
    path = fields[1]
    if '?' in path:
        path = path[:path.index('?')]

    headers = {}
    for line in lines[1:]:
        if ':' in line:
            k, _, v = line.partition(':')
            headers[k.strip().lower()] = v.strip()

    cookies = []
    if 'cookie' in headers:
        for c in headers['cookie'].split(';'):
            cookies.append(c.strip().encode('utf-8'))

    return {'method': method, 'path': path, 'headers': headers, 'cookies': cookies}


def handle_request(req, reader, root_dir, addr):
    method  = req['method']
    path    = req['path']
    cookies = req['cookies']
    addr_str = f'{addr[0]}:{addr[1]}'

    print(f'[REQU] [{addr_str}] {method} request for {path}')

    if method not in ('GET', 'HEAD'):
        print(f'[ERRO] [{addr_str}] {method} request returned error 501')
        return error_response(501, 'Not Implemented'), True  # True = close after

    full_path = os.path.realpath(os.path.join(root_dir, path.lstrip('/')))
    mime = 'text/html' if os.path.isdir(full_path) else get_mime(path)

    if method == 'GET':
        content = reader.get(path, cookies)
        if content is None:
            print(f'[ERRO] [{addr_str}] GET request returned error 404')
            return error_response(404, 'Not Found'), False
        return build_response(200, 'OK', {
            'Content-Type': mime,
            'Content-Length': len(content),
        }, content), False

    # HEAD
    size = reader.head(path, cookies)
    if size is None:
        print(f'[ERRO] [{addr_str}] HEAD request returned error 404')
        return error_response(404, 'Not Found', include_body=False), False
    return build_response(200, 'OK', {
        'Content-Type': mime,
        'Content-Length': size,
    }), False


def main():
    if len(sys.argv) < 3:
        print('Usage: jewel.py <port> <root_dir>')
        sys.exit(1)

    port     = int(sys.argv[1])
    root_dir = sys.argv[2]
    reader   = FileReader(root_dir)

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(('0.0.0.0', port))
    server_sock.listen(50)
    server_sock.setblocking(False)

    # socket -> [buffer: bytes, address: tuple]
    clients = {}

    while True:
        read_list = [server_sock] + list(clients.keys())
        try:
            readable, _, exceptional = select.select(read_list, [], read_list)
        except Exception:
            continue

        for sock in exceptional:
            if sock in clients:
                del clients[sock]
            sock.close()

        for sock in readable:
            if sock is server_sock:
                try:
                    conn, addr = server_sock.accept()
                    conn.setblocking(False)
                    clients[conn] = [b'', addr]
                    print(f'[CONN] Connection from {addr[0]} on port {addr[1]}')
                except Exception:
                    pass
                continue

            if sock not in clients:
                continue

            buf, addr = clients[sock]
            try:
                data = sock.recv(4096)
            except Exception:
                del clients[sock]
                sock.close()
                continue

            if not data:
                del clients[sock]
                sock.close()
                continue

            buf += data
            close_conn = False

            header_end = buf.find(b'\r\n\r\n')
            while header_end != -1:
                request_bytes = buf[:header_end + 4]
                buf = buf[header_end + 4:]

                req = parse_request(request_bytes)
                if req is None:
                    addr_str = f'{addr[0]}:{addr[1]}'
                    print(f'[ERRO] [{addr_str}] unknown request returned error 400')
                    try:
                        sock.sendall(error_response(400, 'Bad Request'))
                    except Exception:
                        pass
                    close_conn = True
                    break

                response, force_close = handle_request(req, reader, root_dir, addr)
                try:
                    sock.sendall(response)
                except Exception:
                    close_conn = True
                    break

                if force_close or req['headers'].get('connection', '').lower() == 'close':
                    close_conn = True
                    break

                header_end = buf.find(b'\r\n\r\n')

            if close_conn:
                if sock in clients:
                    del clients[sock]
                sock.close()
            else:
                clients[sock][0] = buf


if __name__ == '__main__':
    main()
