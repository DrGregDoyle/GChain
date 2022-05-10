'''
Functions for networking

In order to transmit data over a network, the receiving node needs to know:
    -What kind of data it is (data type)
    -The length of the data
    -That it received the data correctly

A message will have the following format:

#====================================================================#
#|  field       |   bit size    |   hex chars   |   byte size       |#
#====================================================================#
#   data type   |   8           |   2           |   1               |#
#   data length |   16          |   4           |   2               |#
#   data        |   var         |   var         |   var             |#
#   checksum    |   256         |   64          |   32              |#
#====================================================================#

However, for confirmation, we don't need to send any data. Hence the confirmation message will have the following format:
#====================================================================#
#|  field       |   bit size    |   hex chars   |   byte size       |#
#====================================================================#
# confirm string|   8           |   2           |   1               |#
#====================================================================#


SERVER EVENTS
#================================================#
#|      Data Type       |       Hex value       |       Int value       |#
#================================================#
#|  Ping/IsAlive        |       00              |#
#|  Node Connect        |       01              |#
#|  Network Connect     |       02              |#
#|  Disconnect          |       03              |#
#|  Transaction         |       04              |#
#|  Transaction Request |       05              |#
#|  New Block           |       06              |#
#|  Indexed Block       |       07              |#
#|  Status              |       08              |#
#|  Hash Match          |       09              |#
#|  Hash Index          |       0A              |#          10
#|  Confirm             |       0B              |#          11
#|  Checksum Error      |       0C              |#          12
#|  Node List           |       0D              |#          13
#================================================#

CLIENT EVENTS
#================================================#
#|      Data Type       |       Hex value       |       Int value       |#
#================================================#
#|      Confirm         |       01              |#
#|      Retry           |       02              |#
#|      Fail            |       03              |#
#================================================#


'''

'''
IMPORTS
'''
import socket
from requests import get
from hashlib import sha256

'''
NETWORK
'''
DATA_LENGTH_BITS = 16
DATA_TYPE_BITS = 8
CHECKSUM_BITS = 256
CLIENT_MESSAGE_BITS = 8


def receive_event_data(client: socket):
    '''
    The Node server will be receiving various requests from Node clients.
    The datatype indicates how the Node will interpret the data sent.
    The data length is necessary for the socket to accept the data.
    Finally the checksum is for the Node serve to verify the data.
    The messages sent by the client are byte-encoded, so we decode every message to its original string value.
    '''
    datatype = client.recv(DATA_TYPE_BITS // 4).decode()
    data_length = int(client.recv(DATA_LENGTH_BITS // 4).decode(), 16)
    data = client.recv(data_length).decode()
    checksum = client.recv(CHECKSUM_BITS // 4).decode()
    return datatype, data, checksum


def receive_client_message(client: socket):
    '''
    The Node client will receive a 1-byte message from the server and proceed based on the message
    '''
    return client.recv(CLIENT_MESSAGE_BITS // 4).decode()


def send_to_server(client: socket, datatype: int, data: str):
    '''
    We will send 4 messages to the server: datatype, data_length, data and checksum.
    These message will be 'byte-encoded' in order to be sent through the socket.
    The datatype will be given as an integer and sent as a 1-byte hex string.
    '''
    datatype = format(datatype, f'0{DATA_TYPE_BITS // 4}x')
    data_length = format(len(data), f'0{DATA_LENGTH_BITS // 4}x')
    checksum = format(int(sha256(data.encode()).hexdigest(), 16), f'0{CHECKSUM_BITS // 4}x')

    client.send(datatype.encode())
    client.send(data_length.encode())
    client.send(data.encode())
    client.send(checksum.encode())


def send_to_client(client: socket, message_type: int):
    '''
    The server sends a return message to the client whenever it receives data. The message_type will be given as an
    integer and encoded as a 1-byte hex string.
    '''
    message = format(message_type, f'0{CLIENT_MESSAGE_BITS // 4}x')
    client.send(message.encode())


def close_socket(socket_toclose):
    socket_toclose.shutdown(socket.SHUT_RDWR)
    socket_toclose.close()


def create_socket():
    new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    new_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    return new_socket


def get_local_ip():
    '''
    Returns local ip address
    '''
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def get_ip():
    ip = get('https://api.ipify.org').content.decode()
    return ip
