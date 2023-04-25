import _thread
import datetime
import socket as sockets
import time
from typing import List
from BufferedSocketStream import BufferedSocketStream
from cli_io import IO, get_arg, get_argflag
from resource_type import *

cli = IO()
running = True

waiting_nodes: List[BufferedSocketStream] = []
aquired_permissions: List[BufferedSocketStream] = []

MESSAGE_TYPE_PERMISSION_REQUEST = 1
MESSAGE_TYPE_PERMISSION_GRANTED = 2

text_to_commit = ''
use_resource = False
our_request_time = '999999999999999999'
other_processes_ports = []


less_verbose_flag = get_argflag('less_verbose')
cli.ignore_debug(less_verbose_flag)

if get_argflag("use_db"):
    resource: Resource = MySQLResource(host='127.0.0.1', database='tp', user='root', password='toor', log=cli)
else:
    resource: Resource = FileResource(path='db.txt', log=cli)

h = 0
last_request_h = 0


def request_resource():
    global our_request_time, use_resource
    our_request_time = time = datetime.datetime.utcnow().strftime('%H:%M:%S.%f')

    for p in other_processes_ports:
        if not running:
            break
        cli.debug(f"will send MESSAGE(type=PERMISSION_REQUEST, port={our_port}, time={time}) to node {p}")
        with BufferedSocketStream(p) as node:
            node.send_int32(our_port)
            node.send_int32(MESSAGE_TYPE_PERMISSION_REQUEST)
            node.send_utf8(time)
    cli.write('Waiting for permission-replies')


def read_stdin():
    global use_resource, text_to_commit, running
    try:
        while running:
            if not use_resource:
                text_to_commit = cli.input(f"[node {our_port}] write to db: ", 'magenta')
                use_resource = True
                request_resource()
            else:
                time.sleep(.5)
    except KeyboardInterrupt:
        pass
    finally:
        running = False


def handle_node_message(port: int, stream: BufferedSocketStream):
    global our_request_time, use_resource
    cli.debug(f'[thread handler for {port}] node {port} connected')
    message_type = stream.read_int32()

    if message_type == MESSAGE_TYPE_PERMISSION_REQUEST:
        incoming_time = stream.read_utf8()
        cli.debug(f"[thread handler for {port}] got MESSAGE(type=PERMISSION_REQUEST, port={port}, time={incoming_time}) from node {port}")
        if use_resource and our_request_time < incoming_time:
            cli.debug(f"[thread handler for {port}] adding {port} to wainting list")
            waiting_nodes.append(port)
        else:
            cli.debug(f"[thread handler for {port}] will send MESSAGE(type=PERMISSION_GRANTED, port={our_port}) to node {port}")
            with BufferedSocketStream(port) as node:
                node.send_int32(our_port)
                node.send_int32(MESSAGE_TYPE_PERMISSION_GRANTED)
    elif message_type == MESSAGE_TYPE_PERMISSION_GRANTED:
        cli.debug(f"[thread handler for {port}] got MESSAGE(type=PERMISSION_GRANTED, port={port}) from node {port}")
        aquired_permissions.append(port)
        if len(aquired_permissions) == len(other_processes_ports):
            cli.debug('using resource')
            resource.use(data=(port, text_to_commit), log=cli)
            time.sleep(3)
            use_resource = False
            cli.debug(f'[thread handler for {port}] resoure released')
            cli.debug(f'[thread handler for {port}] will send PERMISSION_GRANTED to waiting nodes ({len(waiting_nodes)})')
            for p in waiting_nodes:
                cli.debug(f"[thread handler for {port}] will send MESSAGE(type=PERMISSION_GRANTED, port={our_port}) to node {p}")
                if not running:
                    break
                with BufferedSocketStream(p) as node:
                    node.send_int32(our_port)
                    node.send_int32(MESSAGE_TYPE_PERMISSION_GRANTED)
            waiting_nodes.clear()
            aquired_permissions.clear()
    else:
        cli.debug(f"[thread handler for {port}] got unkown message type: {message_type}")
    stream.close()


our_port = int(get_arg("our_port"))
other_processes_ports = [int(p) for p in get_arg("processes_ports").split(',')]

# our_port = 8888
# other_processes_ports = [8777,8886]

server_socket = sockets.create_server(address=('127.0.0.1', our_port), family=sockets.AF_INET, backlog=10)
_thread.start_new_thread(read_stdin, ())
server_socket.settimeout(2)

try:
    cli.debug(f"[server] listening on {server_socket.getsockname()}")
    while running:
        try:
            stream = BufferedSocketStream(server_socket.accept()[0])
        except sockets.timeout:
            continue
        port = stream.read_int32()
        cli.debug(f"[server] new connection from {port}")
        _thread.start_new_thread(handle_node_message, (port, stream))
except KeyboardInterrupt:  # Ctrl+c
    pass
finally:
    server_socket.close()
    resource.finalize(log=cli)
    running = False
