import socket as sockets
from typing import Union


class BufferedSocketStream:
    """
    reconnect_attempts set to 0 to disable autoreconnect
    """

    def __init__(self, address: Union[tuple[str, int], int, sockets.socket], reconnect_attempts=0):
        if (isinstance(address, int)):
            address = ('127.0.0.1', address)
        if isinstance(address, tuple):
            self.socket = sockets.create_connection(address)
            self.address = address
        else:
            if reconnect_attempts > 0:
                reconnect_attempts = 0
            self.socket = address
        self.buffer = bytearray()
        self.size = 0
        self.reconnect_attempts = reconnect_attempts

    def read(self, count) -> bytes:
        """
        block until "count" bytes are available and return them
        """
        while True:
            if count <= self.size:
                part = self.buffer[:count]
                self.buffer = self.buffer[count:]
                self.size -= count
                return part

            try:
                received = self.socket.recv(64 * 1024)
                if received == b'':
                    raise ConnectionError("received 0 bytes possibly socket disconnected")
            except sockets.error or ConnectionError as e:
                if self.reconnect_attempts > 0:
                    self.reconnect(cause=e)
                    continue
                else:
                    raise e

            self.buffer.extend(received)
            self.size += len(received)

    def sendall(self, bytes: bytes):
        while True:
            try:
                return self.socket.sendall(bytes)
            except sockets.error as e:
                if self.reconnect_attempts > 0:
                    self.reconnect(cause=e)
                    continue
                else:
                    raise e

    def reconnect(self, cause: BaseException):
        attempts = self.reconnect_attempts
        while True:
            try:
                self.socket = sockets.create_connection(self.address)
                break
            except sockets.error as e:
                attempts = attempts - 1
                if attempts == 0:
                    raise ConnectionError(f"attempted to reconnect {self.reconnect_attempts} but address did not respond, cause of reconnect: {str(cause)}") from e

    def read_int32(self):
        return int.from_bytes(self.read(8), byteorder='little')

    def send_int32(self, n: int):
        self.sendall(n.to_bytes(length=8, byteorder='little'))

    # read length then read bytes
    def read_utf8(self):
        len = self.read_int32()
        return self.read(len).decode('utf-8')

    # send length then send bytes
    def send_utf8(self, s: str):
        buf = s.encode('utf-8')
        self.send_int32(len(buf))
        self.sendall(buf)

    def close(self):
        self.socket.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        try:
            self.socket.close()
        except Exception as e:
            print("error closing socket", e)
        if exc_type is not None:
            return False  # exception happened
        return True
