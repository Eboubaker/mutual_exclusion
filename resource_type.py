import socket as sockets
import traceback
import hashlib
import mysql.connector
from cli_io import IO


class Resource:
    def use(self, data, log: IO) -> None:  # run critical code
        pass

    def finalize(self, log: IO) -> None:  # close any open buffers/connections
        pass

    def hash(self) -> str:  # token
        pass

class MySQLResource(Resource):
    def __init__(self, log: IO, host, database, user, password) -> None:
        super().__init__()
        self.host = host
        self.database = database
        self.connection = mysql.connector.connect(host=host, database=database, user=user, password=password)
        if self.connection.is_connected():
            log.write("Connected to MySQL, Server version: ", self.connection.get_server_info())

    def use(self, data, log: IO):
        port_col_value, text = data
        try:
            log.write(f"[critical] using mysql database...")
            cursor = self.connection.cursor()
            cursor.execute("SELECT counter from counter")
            result = cursor.fetchone()[0]
            cursor.execute("INSERT INTO usage_history (machine_port, data) VALUES (%s, %s)", (str(port_col_value), text))
            cursor.execute("UPDATE counter set counter=%s", (int(result + 1),))
            self.connection.commit()
        except KeyboardInterrupt as e:
            raise e
        except:
            log.write(traceback.format_exc())

    def finalize(self, log: IO):
        if self.connection.is_connected:
            log.write("closing mysql connection")
            self.connection.close()

    def hash(self):
        return hashlib.sha1((self.host+':'+self.database).encode()).hexdigest()


class FileResource(Resource):
    def __init__(self, log: IO, path: str) -> None:
        super().__init__()
        self.path = path

    def use(self, data, log: IO):
        port, text = data
        log.write(f"writing to file {self.path}, content: {port}: {text}")
        try:
            with open(self.path, 'w+a') as f:
                f.write(f'{port}: {text}\n')
        except KeyboardInterrupt as e:
            raise e
        except:
            log.write(traceback.format_exc())

    def finalize(self, log: IO):
        pass

    def hash(self):
        return hashlib.sha1((self.path).encode()).hexdigest()
