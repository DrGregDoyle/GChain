'''
NODE testing
'''

'''
IMPORTS
'''
from node import Node
from block import decode_raw_block

'''
TESTS
'''


def test_consensus_algorithm():
    '''
    We verify that the consensus algorithm sorts hashes with the same frequency by timestamp
    '''
    n1 = Node()
    n2 = Node()

    # Mine N1 Block
    n1.start_miner()
    while n1.height == 0:
        pass
    n1.stop_miner()

    # Mine N2 Block
    n2.start_miner()
    while n2.height == 0:
        pass
    n2.stop_miner()

    # Get block ids
    id1 = decode_raw_block(n1.last_block).id
    id2 = decode_raw_block(n2.last_block).id

    # Connect to network
    # n2.connect_to_network(n1.local_node, use_local=True)
    n1.connect_to_node(n2.local_node)
    n2.connect_to_node(n1.local_node)
    n2.match_to_consensus_chain()
    n2.get_missing_blocks()

    # Verify block ids
    assert decode_raw_block(n1.last_block).id == id1
    assert decode_raw_block(n2.last_block).id == id1

    n1.stop_event_listener()
    n2.stop_event_listener()
