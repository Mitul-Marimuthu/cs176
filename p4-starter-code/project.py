'''
Main file for configuring the network and running the simulator.
'''

import network_simulator


# Network 1
#
#    1
# E0 --- E1
# | \    |
# |  \   |
# |7  \3 | 1
# |    \ |
# |     \|
# E3 --- E2
#     2
#
network1 = [
	[(1, 1), (2, 3), (3, 7)], # E0
	[(0, 1), (2, 1)],         # E1
	[(0, 3), (1, 1), (3, 2)], # E2
	[(0, 7), (2, 2)],         # E3
]

# Network 2
#
#    1
# E0 --- E1
# | \    | \
# |  \   |  \
# |3  \4 | 4 |
# |    \ |   |
# |     \|   |
# E3     E2  / 1
#  \________/
#
network2 = [
	[(1, 1), (2, 4), (3, 3)], # E0
	[(0, 1), (2, 4), (3, 1)], # E1
	[(0, 4), (1, 4)],         # E2
	[(0, 3), (1, 1)],         # E3
]

# Network 3
#
#     1      2
# E0 --- E1 --- E2
# | \    |      |
# |  \5  |3     |1
# |   \  |      |
# |3   \-E3     E4
# |            /
# E5 ---------/
#          8
#
network3 = [
	[(1, 1), (3, 5), (5, 3)], # E0
	[(0, 1), (2, 2), (3, 3)], # E1
	[(1, 2), (4, 1)],         # E2
	[(0, 5), (1, 3)],         # E3
	[(2, 1), (5, 8)],         # E4
	[(0, 3), (4, 8)],         # E5
]

# Triangle (shortcut)
#
#        10
# E0 --------- E1
#  \           /
#   \1       2/
#    \       /
#      E2
#
# The direct E0-E1 link costs 10, but going via E2 costs only 3.
#
triangle = [
	[(1, 10), (2, 1)], # E0
	[(0, 10), (2, 2)], # E1
	[(0, 1),  (1, 2)], # E2
]


# Create a new simulation with `network1`, a random seed value of 499, and
# debugging level 3.
simulator = network_simulator.NetworkSimulator(network1, 499, 3)

# Actually run the simulator. This will return when the lowest cost routes are
# found.
simulator.run()

# Print the forwarding table for each entity.
simulator.display_forwarding_table(0)
simulator.display_forwarding_table(1)
simulator.display_forwarding_table(2)
simulator.display_forwarding_table(3)

# Print the route a packet would take from entity 0 to entity 3.
print(simulator.route_packet(0, 3))
