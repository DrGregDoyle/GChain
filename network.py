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
#|  Address             |       0A              |#          10
#|  Confirm             |       0B              |#          11
#|  Checksum Error      |       0C              |#          12
#================================================#





'''

'''
IMPORTS
'''
import socket
from hashlib import sha256

'''
NETWORK
'''
DATA_LENGTH_BITS = 16
DATA_TYPE_BITS = 8
CHECKSUM_BITS = 256


def package_and_send_data(client: socket, datatype: int, data: str):
    '''
    Client will be used to send the data/
    Datatype will be a hex string indicating what type of data it is.
    The data will be a string, which we hash to create the checksum.
    '''
    datatype = format(datatype, f'0{DATA_TYPE_BITS // 4}x')
    data_length = format(len(data), f'0{DATA_LENGTH_BITS // 4}x')
    checksum = format(int(sha256(data.encode()).hexdigest(), 16), f'0{CHECKSUM_BITS // 4}x')

    client.send(datatype.encode())
    client.send(data_length.encode())
    client.send(data.encode())
    client.send(checksum.encode())


def receive_data(client: socket):
    datatype = client.recv(DATA_TYPE_BITS // 4).decode()
    print(f'datatype: {datatype}')
    data_length = int(client.recv(DATA_LENGTH_BITS // 4).decode(), 16)
    print(f'data length: {data_length}')
    data = client.recv(data_length).decode()
    print(f'data: {data}')
    checksum = client.recv(CHECKSUM_BITS // 4).decode()
    print(f'checksum: {checksum}')

    return datatype, data, checksum


def close_socket(socket_toclose):
    socket_toclose.shutdown(socket.SHUT_RDWR)
    socket_toclose.close()


def create_socket():
    new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    new_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    return new_socket
