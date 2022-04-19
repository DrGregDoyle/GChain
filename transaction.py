'''
The transaction class


Bits    | Bytes     | Hex chars     | Field
-------------------------------------------
32      | 4         | 8             | Version
64      | 8         | 16            | Input count
var     | var       | var           | All inputs
64      | 8         | 16            | Output count
var     | var       | var           | All outputs


#TODO: Get variable length integer working for input/output count


'''


class Transaction:

    def __init__(self, version: int, input_count: int, inputs: list, output_count: int, outputs: list):
        '''
        We create the transaction
        '''

        self.version = version
        self.input_count = input_count
        self.inputs = inputs
        self.output_count = output_count
        self.outputs = outputs
