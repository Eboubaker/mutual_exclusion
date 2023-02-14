import socket as sockets
import time
import traceback
import hashlib
import _thread
import mysql.connector
import os
from cli_io import IO

# interface
class Resource:
    def use(self, data) -> None: # run critical code
        pass

    def finalize(self) -> None: # close any open buffers/connections
        pass

    def hash(self) -> str: # token
        pass

text_to_commit = ''
use_resource_next_cycle = False
running = True
cli = IO()
class MySQLResource(Resource):
    def __init__(self, host, database, user, password) -> None:
        super().__init__()
        self.host = host
        self.database = database
        self.connection = mysql.connector.connect(host=host, database=database, user=user, password=password)
        if self.connection.is_connected():
            cli.write("Connected to MySQL, Server version: ", self.connection.get_server_info())

    def use(self, data):
        port_col_value, text = data
        try:
            cli.write(f"[critical] using mysql database...")
            cursor = self.connection.cursor()
            cursor.execute("INSERT INTO usage_history (machine_port, data) VALUES (%s, %s)", (str(port_col_value), text))
            self.connection.commit()
        except KeyboardInterrupt as e:
            raise e
        except:
            cli.write(traceback.format_exc())

    def finalize(self):
        if self.connection.is_connected:
            cli.write("closing mysql connection")
            self.connection.close()

    def hash(self):
        return hashlib.sha1((self.host+':'+self.database).encode()).hexdigest()

def read_stdin():
    global use_resource_next_cycle, text_to_commit, running
    try:
        while running:
            if not use_resource_next_cycle:
                text_to_commit = cli.input("write to db: ", 'magenta')
                use_resource_next_cycle = True
            else:
                time.sleep(.5)
    except KeyboardInterrupt:
        pass
    finally:
        running = False

def ring_loop(server_socket: sockets.socket, succ_port: int, resource: Resource):
    global use_resource_next_cycle, text_to_commit, running
    succ_soc = sockets.socket(sockets.AF_INET, sockets.SOCK_STREAM)
    while running:
        try:succ_soc.connect(('127.0.0.1', succ_port));break
        except:pass
    if '1' == os.environ.get('RING_START', ''):  # initial wheel push
        cli.write("sending token to successor")
        succ_soc.send(resource.hash().encode())
    cli.write('waiting predecessor connection')
    pred_soc, _ = server_socket.accept() # accept predecessor connection
    our_port = server_socket.getsockname()[1]
    last_iteration_time = time.perf_counter()
    cycle_counter = 0
    _thread.start_new_thread(read_stdin, ())  # start reading user input
    try:
        while running:
            cli.write(f"[cycle {cycle_counter:2d}] waiting token from predecessor")
            token = pred_soc.recv(1024).decode()
            if token == '':
                cli.write('predecessor link terminated')
                break
            cli.write(f"[cycle {cycle_counter:2d}] received from predecessor token {token}")
            if token == resource.hash() and use_resource_next_cycle:
                cli.write(f"[cycle {cycle_counter:2d}] entering critical section")
                resource.use([our_port, text_to_commit])
                use_resource_next_cycle = False
            cli.write(f"[cycle {cycle_counter:2d}] sending to successor {succ_port} token {token}")
            succ_soc.send(token.encode())

            # reduce traffic, 2 seconds per iteration maximum
            delta_t = time.perf_counter() - last_iteration_time
            if delta_t < 2:
                time.sleep(2 - delta_t)
            last_iteration_time = time.perf_counter()
            cycle_counter += 1
    except KeyboardInterrupt:  # Ctrl+c
        pass


resource: Resource = MySQLResource(host='127.0.0.1', database='tp', user='root', password='toor')
try:
    our_port = int(input("our_port="))
    server_socket = sockets.socket(sockets.AF_INET, sockets.SOCK_STREAM)
    server_socket.bind(('127.0.0.1', our_port))
    server_socket.listen()
    succ_port = int(input("successor_port="))
    running = True
    ring_loop(server_socket, succ_port, resource)
finally:
    server_socket.close()
    resource.finalize()
    running = False
