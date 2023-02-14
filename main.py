import socket as sockets
import time
import traceback
import hashlib

import mysql.connector


# interface
class Resource:
    def use(self, data) -> None: # run critical code
        pass

    def finalize(self) -> None: # close any open buffers/connections
        pass

    def hash(self) -> str: # token
        pass

class MySQLResource(Resource):
    def __init__(self, host, database, user, password) -> None:
        super().__init__()
        self.host = host
        self.database = database
        self.connection = mysql.connector.connect(host=host, database=database, user=user, password=password)
        if self.connection.is_connected():
            print("Connected to MySQL, Server version: ", self.connection.get_server_info())

    def use(self, port_col_value):
        try:
            print(f"[critical] using mysql database...")
            cursor = self.connection.cursor()
            cursor.execute("INSERT INTO usage_history (machine_port) VALUES (%s)", (str(port_col_value), ))
            self.connection.commit()
        except KeyboardInterrupt as e:
            raise e
        except:
            print(traceback.format_exc())

    def finalize(self):
        if self.connection.is_connected:
            print("closing mysql connection")
            self.connection.close()

    def hash(self):
        return hashlib.sha1((self.host+':'+self.database).encode()).hexdigest()


def ring_loop(server_socket: sockets.socket, succ_port: int, resource: Resource):
    succ_soc = sockets.socket(sockets.AF_INET, sockets.SOCK_STREAM)
    while True:
        try:
            succ_soc.connect(('127.0.0.1', succ_port))
            break
        except:
            pass
    if 'y' == input("start using?(y/n):"):  # initial wheel push
        print("sending token to successor")
        succ_soc.send(resource.hash().encode())
    pred_soc, _ = server_socket.accept()
    our_port = server_socket.getsockname()[1]
    last_iteration_time = time.perf_counter()
    cycle_counter = 0
    try:
        while True:
            print(f"[cycle {cycle_counter:2d}] waiting token from predecessor")
            token = pred_soc.recv(1024).decode()
            if token == '':
                print('predecessor link terminated')
                break
            print(f"[cycle {cycle_counter:2d}] received from predecessor token {token}")
            if token == resource.hash():
                print(f"[cycle {cycle_counter:2d}] entering critical section")
                resource.use(our_port)
            print(f"[cycle {cycle_counter:2d}] sending to successor {succ_port} token {token}")
            succ_soc.send(token.encode())

            # reduce traffic, 2 seconds per iteration maximum
            delta_t = time.perf_counter() - last_iteration_time
            # if delta_t < 2:
            #     time.sleep(2 - delta_t)
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
    ring_loop(server_socket, succ_port, resource)
    server_socket.close()
finally:
    resource.finalize()
