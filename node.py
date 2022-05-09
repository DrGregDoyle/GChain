'''
The Node class

'''

'''
IMPORTS
'''
import socket
import threading

from block import Block, decode_raw_block
from blockchain import Blockchain
from helpers import utc_to_seconds, list_to_node, verify_checksum
from miner import Miner
from network import get_ip, get_local_ip, close_socket, create_socket, send_to_client, send_to_server, \
    receive_event_data, receive_client_message
from transaction import Transaction, decode_raw_transaction
from utxo import UTXO_OUTPUT, UTXO_INPUT
from wallet import Wallet
import json
from hashlib import sha256

'''
CLASS
'''


class Node:
    '''
    We have two notions of node: there is the Node class, and there is the node socket, which is an ip address and
    port. We will refer to the Node class object explicitly using the uppercase N and the node socket using the
    lowercase n.

    NOTE: All ip addresses must be given in SINGLE QUOTES as a string

    NOTE: The node_list will be a list of all connected Nodes. And the server node of each Node is what's saved in
    the node_list.

    '''
    '''
    MESSAGE TYPES
    '''
    DATATYPES = [
        "PING",
        "NODE CONNECT",
        "NETWORK CONNECT",
        "DISCONNECT",
        "TRANSACTION",
        "TRANSACTION REQUEST",
        "NEW BLOCK",
        "INDEXED BLOCK",
        "STATUS",
        "HASH MATCH",
        "ADDRESS",
        "CONFIRM",
        "CHECKSUM ERROR",
        "NODE LIST"
    ]

    '''
    NETWORKING CONSTANTS
    '''
    DEFAULT_PORT = 41000
    DEFAULT_FORMAT = 'utf-8'
    LISTENER_TIMEOUT = 10
    MESSAGE_RETRIES = 5

    def __init__(self, wallet=None):
        '''

        '''
        # Instantiate the Blockchain
        self.blockchain = Blockchain()

        # Create Miner
        self.miner = Miner()

        # Create local wallet if none used during instantiation
        if wallet is None:
            self.wallet = Wallet()
        else:
            self.wallet = wallet

        # Create Mining and Listening flags
        self.is_mining = False
        self.is_listening = False

        # Create transaction lists
        self.incoming_transactions = []
        self.validated_transactions = []
        self.orphaned_transactions = []

        # Create Mining stats dict
        self.mining_stats = {}

        # Setup server
        self.listening_address = '0.0.0.0'
        self.server_address = get_ip()
        self.local_address = get_local_ip()

        # Setup node list
        self.node_list = []

        # Start Event Listener
        self.start_event_listener()

    '''
    PROPERTIES
    '''

    @property
    def last_block(self):
        return self.blockchain.last_block

    @property
    def utxos(self):
        return self.blockchain.utxos

    @property
    def curve(self):
        return self.blockchain.curve

    @property
    def height(self):
        return self.blockchain.height

    '''
    MINER
    '''

    def start_miner(self):
        if not self.is_mining:
            # Get hash rate before beginning
            # Logging
            print('Calculating hashrate')
            self.mining_stats.update({'hashrate': self.miner.get_hashrate()})

            # Start mining Block in new thread
            self.is_mining = True
            self.mining_thread = threading.Thread(target=self.mine_block)
            self.mining_thread.start()
        else:
            # Logging
            print('Miner already running')

    def stop_miner(self):
        if self.is_mining:
            self.miner.stop_mining()
            while self.mining_thread.is_alive():
                pass
            self.is_mining = False
        else:
            # Logging
            print('Miner already stopped')

    def mine_block(self):
        interrupted = False
        while not interrupted:
            # Create Mining Transaction
            mining_amount = self.get_mining_amount()
            mining_output = UTXO_OUTPUT(mining_amount, self.wallet.address)
            current_height = self.blockchain.height
            mining_transaction = Transaction(inputs=[], outputs=[mining_output.raw_utxo], min_height=current_height + 1)
            self.validated_transactions.insert(0, mining_transaction.raw_tx)

            # Create candidate block
            if self.last_block == []:
                new_block = Block('', self.get_mining_target(), 0, self.validated_transactions)
            else:
                last_block = decode_raw_block(self.last_block)
                new_block = Block(last_block.id, self.get_mining_target(), 0, self.validated_transactions)

            # Mine block
            start_time = utc_to_seconds()
            mined_raw_block = self.miner.mine_block(new_block.raw_block)

            # Add block or interrupt miner
            if mined_raw_block != '':
                end_time = utc_to_seconds()
                mining_time = end_time - start_time
                mined_block = decode_raw_block(mined_raw_block)
                added = self.add_block(mined_block.raw_block)
                if added:
                    self.validated_transactions = []
                    self.mining_stats.update({"mining_time": mining_time})
            else:
                # Remove mining transaction
                self.validated_transactions.pop(0)
                interrupted = True
        # Stop mining if the thread is interrupted
        self.is_mining = False

    def get_mining_amount(self):
        '''
        The mining reward will be the difference between the sum of all input amounts and the sum of all output
        amounts, plus the reward variable. We also verify that the total_input_amount >= total_output_amount and that
        the referenced output utxos for each input utxo exists.
        '''

        total_input_amount = 0
        total_output_amount = 0
        reward = self.get_mining_reward()

        for t in self.validated_transactions:
            # Recover tx
            temp_tx = decode_raw_transaction(t)

            # Add total input amount for tx
            for i in temp_tx.inputs:
                tx_id = i.tx_id
                tx_index = int(i.tx_index, 16)
                input_index = self.utxos.index[(self.utxos['tx_id'] == tx_id) & (self.utxos['tx_index'] == tx_index)]
                assert not input_index.empty
                total_input_amount += int(self.utxos.loc[input_index]['amount'].values[0], 16)

            # Add total output amount for tx
            for t in temp_tx.outputs:
                total_output_amount += int(t.amount, 16)

        assert total_input_amount >= total_output_amount
        return reward + (total_input_amount - total_output_amount)

    def get_mining_reward(self):
        return self.blockchain.determine_reward()

    def get_mining_target(self):
        '''
        Algorithm for determining mining target goes here
        '''
        return self.blockchain.determine_target()

    '''
    ADD BLOCK
    '''

    def add_block(self, raw_block: str):
        '''

        '''
        added = self.blockchain.add_block(raw_block)
        if added:
            self.check_for_parents()
        return added

    '''
    TRANSACTIONS
    '''

    def add_transaction(self, raw_tx: str) -> bool:
        '''
        When a Node receives a new transaction (tx), one of three things may happen: either the tx gets validated,
        in which case it's added to the validated transactions pool; or the tx has an invalid signature and locking
        script, in which case the tx is rejected; or the tx contains inputs which reference outputs which don't exist
        in the db, in which case this tx gets put in the orphaned transactions pool.

        We recover a Transaction object from the raw_tx string. We then iterate over all inputs. For each input,
        we first check that the referenced utxo output is stored in the blockchain. If the reference output does not
        exist, the Transaction gets flagged as orphaned. For the inputs whose reference utxo exists, we validate the
        input signature with the output locking script (compressed public key). If the signature fails validation,
        we reject the tx, otherwise we continue. As well, as we are validating each input tx, we are adding the value
        of the amount of the corresponding output utxo.

        Finally, if the transaction is not flagged as orphaned, we verify that the total input amount available in
        the output utxos stored in the blockchain is greater than or equal to the total output amount of the
        Transaction outputs. If the total input amount is smaller than the total output amount, we reject the tx.

        With the final check complete, either the tx is added to the validated tx pool or the orphaned tx pool,
        depending on the orphan flag.
        '''

        # Recover the transaction object
        new_tx = decode_raw_transaction(raw_tx)

        # Return false if already validated or orphaned
        if new_tx in self.validated_transactions or new_tx in self.orphaned_transactions:
            return False

        # Set orphaned transaction Flag
        all_inputs = True

        # Validate inputs
        total_input_amount = 0
        for i in new_tx.inputs:  # Looping over utxo_input objects

            # Get the row index for the output utxo
            tx_id = i.tx_id
            tx_index = int(i.tx_index, 16)
            input_index = self.utxos.index[(self.utxos['tx_id'] == tx_id) & (self.utxos['tx_index'] == tx_index)]

            # If the row doesn't exist, mark for orphan
            if input_index.empty:
                all_inputs = False

            # If the row exists, validate the input with the output and add the amount
            else:
                # Increase total_input_amount
                amount = int(self.utxos.loc[input_index]['amount'].values[0], 16)
                total_input_amount += amount

                # Validate the signature
                address = self.utxos.loc[input_index]['address'].values[0]
                if not self.blockchain.validate_signature(i.signature, address, tx_id):
                    return False

        # If not flagged for orphaned
        if all_inputs:
            # Get the total output amount
            total_output_amount = 0
            for t in new_tx.outputs:
                total_output_amount += int(t.amount, 16)

            # Verify the total output amount
            if total_output_amount > total_input_amount:
                return False

            # Add tx to validated tx pool
            self.validated_transactions.append(raw_tx)

            # Send tx to network
            self.send_transaction_to_network(raw_tx)

        # Flagged for orphaned. Add to orphan pool
        else:
            self.orphaned_transactions.append(raw_tx)

        return True

    def check_for_parents(self):
        '''
        For every orphaned transaction, we see if its parents have arrived yet. If not, they will either be placed
        back in the orphaned tx pool, or invalidated.
        '''
        orphan_copies = self.orphaned_transactions.copy()
        self.orphaned_transactions = []
        for r in orphan_copies:
            self.add_transaction(r)

    '''
    SERVER
    '''

    def create_nodes(self):
        '''
        The server will listen on address 0.0.0.0 - this allows it to listen to requests from multiple ip addresses (
        i.e., both internal and external.) To receive messages from external machines, the machine running the Node
        must port-forward the ports 41000--42000 to their internal IP address.
        '''
        port_found = False
        temp_port = self.DEFAULT_PORT
        while not port_found:
            try:
                temp_socket = create_socket()
                temp_socket.bind((socket.gethostname(), temp_port))
                port_found = True
            except OSError:
                # Logging
                print(f'Port {temp_port} unavailable.')
                temp_port += 1
        self.port = temp_port
        self.listening_node = (self.listening_address, self.port)
        self.server_node = (self.server_address, self.port)
        self.local_node = (self.local_address, self.port)

    '''
    EVENT LISTENER
    '''

    def start_event_listener(self):
        if not self.is_listening:
            self.is_listening = True
            self.listening_thread = threading.Thread(target=self.event_listener)
            self.listening_thread.start()

    def stop_event_listener(self):
        if self.is_listening:
            # Stop all mining
            if self.is_mining:
                self.stop_miner()

            # Disconnnect from network
            self.__disconnect_from_network()

            # Set listening to False
            self.is_listening = False

            # Logging
            print(f'Shutting down listener within {self.LISTENER_TIMEOUT} seconds.', end='\r\n')

            # Wait for thread to Die
            while self.listening_thread.is_alive():
                pass

            # Clear port
            self.port = None

        # Logging
        print('Event listener turned off.')

    def event_listener(self):
        '''
        '''

        # Create nodes
        self.create_nodes()

        # Logging
        print(f'Listening node: {self.listening_node}')
        print(f'Server node: {self.server_node}')
        print(f'Local node: {self.local_node}')

        # Add server node to node_list
        self.node_list.append(self.server_node)

        # Listen on that port
        listening_socket = create_socket()
        listening_socket.settimeout(self.LISTENER_TIMEOUT)
        listening_socket.bind(self.listening_node)
        listening_socket.listen()

        # Create new thread for events
        while self.is_listening:
            try:
                event, addr = listening_socket.accept()
                event_thread = threading.Thread(target=self.handle_event, args=(event, addr,))
                event_thread.start()
            except socket.timeout:
                pass
        close_socket(listening_socket)

    def handle_event(self, event, addr):
        '''

        '''
        # Receive event data
        type, data, checksum = receive_event_data(event)

        # Verify checksum
        if not verify_checksum(data, checksum):
            send_to_client(event, 2)

        # TESTING#
        print(f'Type: {type}')
        print(f'Data: {data}')
        print(f'Checksum: {checksum}')
        #########

        if type == '01':
            self.node_connect_event(event, data)
        elif type == '02':
            self.network_connect_event(event, data)
        elif type == '03':
            self.disconnect_from_network_event(event, data)
        elif type == '04':
            self.new_transaction_event(event, data)
        elif type == '05':
            self.get_transaction_event(event, data)

    '''
    SERVER EVENTS
    '''

    def node_connect_event(self, client: socket, node: str):
        '''
        The node will be a json string of a list with the host and port. We can retrieve the list with json.loads -
        and then the tuple with the list_to_node function.
        '''
        new_node = list_to_node(json.loads(node))
        if new_node not in self.node_list:
            # Logging
            print(f'Node connection established with {new_node}')
            self.node_list.append(new_node)
        send_to_client(client, 1)

    def network_connect_event(self, client: socket, node: str):
        '''
        The Node will confirm the network request and send the node list.
        It will then run the node_connect_event to add the new node received
        '''
        send_to_client(client, 1)
        send_to_server(client, 2, json.dumps(self.node_list))
        self.node_connect_event(client, node)

    def disconnect_from_network_event(self, client: socket, node: str):
        '''
        We remove the node from the node_list.
        '''
        new_node = list_to_node(json.loads(node))
        if new_node in self.node_list:
            self.node_list.remove(new_node)
        # CONSENSUS DICT
        send_to_client(client, 1)

    def new_transaction_event(self, client: socket, raw_tx: str):
        '''

        '''

        if raw_tx not in self.validated_transactions:
            # Logging
            print('Received new transaction')
            self.add_transaction(raw_tx)
        send_to_client(client, 1)

    def get_transaction_event(self, client: socket, node: str):
        '''

        '''
        new_node = list_to_node(json.loads(node))
        send_to_client(client, 1)
        for t in self.validated_transactions:
            self.send_transaction_to_node(new_node, t)

    '''
    CLIENT EVENTS
    '''

    def connect_to_node(self, node: tuple) -> bool:
        '''
        We attempt to connect to the node (socket) given. Will retry if we get such a message up to MESSAGE_RETRIES
        times.
        '''
        if node not in [self.listening_node, self.server_node, self.local_node]:
            connected = False
            retry_count = 0
            while not connected and retry_count < self.MESSAGE_RETRIES:
                try:
                    node_socket = create_socket()
                    node_socket.connect(node)
                    send_to_server(node_socket, 1, json.dumps(self.server_node))
                    confirm_message = receive_client_message(node_socket)
                    if confirm_message == '01':
                        connected = True
                        if node not in self.node_list:
                            self.node_list.append(node)
                    elif confirm_message == '02':
                        retry_count += 1
                    close_socket(node_socket)

                    # TESTING
                    print(f'Confirm message: {confirm_message}')

                except ConnectionRefusedError:
                    # Logging
                    print(f'Unable to connect to node {node}')
                    retry_count += 1

                except TimeoutError:
                    # Logging
                    print(f'Timeout error connecting to {node}')
                    retry_count += 1
            return connected

        else:
            # Logging
            print(f'Cannot connect to own address: {node}')
            return False

    def connect_to_network(self, node: tuple):
        '''
        We send a network request to a node - which means we will receive a node_list.
        For all the new nodes in the node_list, we will run connect_to_node
        '''
        # Track new nodes
        new_nodes = []

        # If the node isn't ours and we're listening
        if node not in [self.listening_node, self.local_node, self.server_node] and self.is_listening:
            node_list_received = False
            retry_count = 0
            while not node_list_received and retry_count < self.MESSAGE_RETRIES:
                try:
                    network_socket = create_socket()
                    network_socket.connect(node)
                    send_to_server(network_socket, 2, json.dumps(self.server_node))
                    message = receive_client_message(network_socket)

                    # If confirm message, get the node list
                    if message == '01':
                        # Get node list
                        type, data, checksum = receive_event_data(network_socket)

                        # Get confirm message that server added node
                        node_added = receive_client_message(network_socket)

                        # If all data valid, proceed
                        if verify_checksum(data, checksum) and type == '02' and node_added == '01':
                            # Node list will be a list of "nodes as list"
                            node_list = json.loads(data)

                            # Add all the new nodes to node_list
                            for L in node_list:
                                new_node = list_to_node(L)
                                if new_node not in self.node_list:
                                    self.node_list.append(new_node)
                                    new_nodes.append(new_node)
                            node_list_received = True
                            # Logging
                            print(f'Successfully received node list from {node}')

                        # If checksum fails, retry
                        else:
                            retry_count += 1
                    else:
                        retry_count += 1
                    close_socket(network_socket)

                except ConnectionRefusedError:
                    # Logging
                    print(f'Unable to connect to node {node}')
                    retry_count += 1
        elif node in [self.listening_node, self.local_node, self.server_node]:
            # Logging
            print(f'Cannot connect to own node: {node}')
        elif not self.is_listening:
            # Logging
            print('Event listener not running')

        # Now connect to all new_nodes
        for n in new_nodes:
            self.connect_to_node(n)

        # Send existing transactions
        for tx in self.validated_transactions:
            self.send_transaction_to_network(tx)

        # Get transactions from node
        self.get_transactions_from_node(node)

        # ACHIEVE CONSENSUS

    def __disconnect_from_network(self):
        '''
        Send disconnect message to all nodes in node_list.
        Set to private as we only want this called when we stop event listener
        '''
        # Remove our own port first
        self.node_list.remove(self.server_node)

        # Get iterable list
        node_list = self.node_list.copy()

        # Iterate over all nodes in node_list
        for node in node_list:
            # Allow for retries
            disconnected = False
            retries = 0
            while not disconnected and retries < self.MESSAGE_RETRIES:
                try:
                    client = create_socket()
                    client.connect(node)
                    send_to_server(client, 3, json.dumps(self.server_node))
                    message = receive_client_message(client)
                    if message == '01':
                        # Logging
                        print(f'Disconnect message sent successfully to {node}')
                        self.node_list.remove(node)
                        disconnected = True
                    else:
                        retries += 1
                    close_socket(client)
                except ConnectionRefusedError:
                    # Logging
                    print(f'Unable to send disconnect message to {node}')
                    retries += 1

        # Logging
        print(f'After disconnecting the node_list is {self.node_list}')

    def send_transaction_to_node(self, node: tuple, raw_tx: str):
        '''
        We send a raw_tx to the node
        '''
        if node not in [self.listening_node, self.server_node, self.local_node]:
            connected = False
            retries = 0
            while not connected and retries < self.MESSAGE_RETRIES:
                try:
                    client = create_socket()
                    client.connect(node)
                    send_to_server(client, 4, raw_tx)
                    message = receive_client_message(client)
                    if message == '01':
                        # Logging
                        print(f'Successfully sent transaction to {node}')
                        connected = True
                    else:
                        retries += 1
                except ConnectionRefusedError:
                    # Logging
                    print(f'Error connecting to {node} for transaction')
                    retries += 1

            if not connected:
                # Logging
                print(f'Failed to send transaction {decode_raw_transaction(raw_tx).id}')
        else:
            # Logging
            print('Cannot send transaction to own node.')

    def send_transaction_to_network(self, raw_tx: str):
        for node in self.node_list:
            if node != self.server_node:
                self.send_transaction_to_node(node, raw_tx)

    def get_transactions_from_node(self, node: tuple):
        '''
        We request the validated transactions from a node
        '''
        if node not in [self.listening_node, self.server_node, self.local_node]:
            connected = False
            retries = 0
            while not connected and retries < self.MESSAGE_RETRIES:
                try:
                    client = create_socket()
                    client.connect(node)
                    send_to_server(client, 5, json.dumps(self.server_node))
                    message = receive_client_message(client)
                    if message == '01':
                        # Logging
                        print(f'Successfully requested transaction from {node}')
                        connected = True
                    else:
                        retries += 1
                except ConnectionRefusedError:
                    # Logging
                    print(f'Error connecting to {node} for transaction requests')
                    retries += 1

            if not connected:
                # Logging
                print(f'Failed to request transactions from {node}')
        else:
            # Logging
            print('Cannot send transaction to own node.')

    # TESTING
    def generate_function(self):
        '''
        We generate a function and add it to the validated_transactions node
        '''
        utxo_list = self.utxos.iloc[0].values
        tx_id = utxo_list[0]
        tx_index = utxo_list[1]
        amount = int(utxo_list[2], 16)
        address = utxo_list[3]

        # Genesis signature
        sig = '4203bbb4f439d5f7cd3507e8f780d1ad51ea29a3bd092e88814cacedf6877072eb284023c31f713e6a80e9ff2540e8bbe55d851b6056e42bfe2d45f44091f1a98419713f37131ff32388ffdeb085cb86b76f857d9ddeb1f3f1fb758a69c997de1d12e32'
        utxo_input = UTXO_INPUT(tx_id, tx_index, sig)
        output1 = UTXO_OUTPUT(amount // 2, self.wallet.address)
        output2 = UTXO_OUTPUT(amount // 2, address)
        new_tx = Transaction(inputs=[utxo_input.raw_utxo], outputs=[output1.raw_utxo, output2.raw_utxo])
        self.add_transaction(new_tx.raw_tx)
