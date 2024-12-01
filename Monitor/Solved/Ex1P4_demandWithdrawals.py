#! /usr/bin/python3

import time
import random
import sys
from multiprocessing import Process, Lock, Condition, Value, Array



### Monitor start

class Buffer:
    def __init__(self, nb_cases):
        self.nb_cases = nb_cases
        self.storage_val = Array('i', [-1] * nb_cases)  # Shared buffer for values
        self.storage_type = Array('i', [-1] * nb_cases)  # Shared buffer for types
        self.ptr_prod = Value('i', 0)  # Shared producer pointer
        self.ptr_cons = Value('i', 0)  # Shared consumer pointer
        self.count = Value('i', 0)  # Count of items in the buffer

        # Synchronization tools
        self.lock = Lock()
        self.not_full = Condition(self.lock)  # Condition for full buffer
        self.not_empty = Condition(self.lock)  # Condition for empty buffer
        self.type_not_available = Condition(self.lock)  # Condition for requested type

    def produce(self, msg_val, msg_type, msg_source):
        with self.lock:  # Acquire lock for mutual exclusion
            while self.count.value == self.nb_cases:  # Wait if the buffer is full
                self.not_full.wait()

            position = self.ptr_prod.value
            print(f"Producer {msg_source} produced {msg_val} (type {msg_type}) in position {position}")
            self.storage_val[position] = msg_val
            self.storage_type[position] = msg_type
            self.ptr_prod.value = (position + 1) % self.nb_cases
            self.count.value += 1

            self.not_empty.notify_all()  # Notify all consumers that the buffer is no longer empty
            self.type_not_available.notify_all()  # Notify consumers waiting for specific types

    def consume(self, id_cons, requested_type):
        with self.lock:  # Acquire lock for mutual exclusion
            while True:
                while self.count.value == 0:  # Wait if the buffer is empty
                    self.not_empty.wait()

                initial_ptr_cons = self.ptr_cons.value  # Save the starting pointer position
                while True:
                    position = self.ptr_cons.value
                    if self.storage_type[position] == requested_type:
                        # Found the requested type
                        msg_val = self.storage_val[position]
                        msg_type = self.storage_type[position]
                        print(f"Consumer {id_cons} consumed {msg_val} (type {msg_type}) from position {position}")
                        self.storage_val[position] = -1
                        self.storage_type[position] = -1
                        self.ptr_cons.value = (position + 1) % self.nb_cases
                        self.count.value -= 1

                        self.not_full.notify_all()  # Notify waiting producers
                        return msg_val

                    # Skip if the type doesn't match
                    self.ptr_cons.value = (position + 1) % self.nb_cases

                    # If the consumer cycles back to the starting position, no matching type exists
                    if self.ptr_cons.value == initial_ptr_cons:
                        self.type_not_available.wait()
                        break

#### Monitor end

def producer(msg_val, msg_type, msg_source, nb_times, buffer):
    for _ in range(nb_times):
        time.sleep(random.random())  # Simulate production time
        buffer.produce(msg_val, msg_type, msg_source)  # Produce the message
        msg_val += 1  # Increment message value for the next production




def consumer(id_cons, nb_times, requested_type, buffer):
    for _ in range(nb_times):
        time.sleep(random.random())  # Simulate consumption time
        buffer.consume(id_cons, requested_type)  # Consume a message of the requested type



if __name__ == '__main__':
    if len(sys.argv) != 6:
        print("Usage: %s <Nb Prod <= 20> <Nb Conso <= 20> <Nb Cases <= 20> <Nb Times Prod> <Nb Times Cons>" % sys.argv[0])
        sys.exit(1)

    nb_prod = int(sys.argv[1])
    nb_cons = int(sys.argv[2])
    nb_cases = int(sys.argv[3])
    nb_times_prod = int(sys.argv[4])
    nb_times_cons = int(sys.argv[5])

    buffer = Buffer(nb_cases)
    
    producers, consumers = [], []

    for id_prod in range(nb_prod):
        msg_val_start, msg_type, msg_source = id_prod * nb_times_prod, id_prod % 2, id_prod
        prod = Process(target=producer, args=(msg_val_start, msg_type, msg_source, nb_times_prod, buffer))
        prod.start()
        producers.append(prod)

    for id_cons in range(nb_cons):
        requested_type = id_cons % 2  # Alternate requested types between 0 and 1
        cons = Process(target=consumer, args=(id_cons, nb_times_cons, requested_type, buffer))
        cons.start()
        consumers.append(cons)

    for prod in producers:
        prod.join()

    for cons in consumers:
        cons.join()
