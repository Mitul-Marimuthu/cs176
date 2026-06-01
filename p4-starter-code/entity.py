import packet as packet_module

INF = 999
_BIG = float('inf')


class Entity:
    def __init__(self, entity_index, number_entities):
        self.index = entity_index
        self.n = number_entities
        self.dist = [_BIG] * number_entities
        self.dist[entity_index] = 0
        self.next_hop = [None] * number_entities
        self.next_hop[entity_index] = entity_index
        self.neighbors = {}
        self.neighbor_dvs = {}

    def _dv_costs(self):
        return [c if c < _BIG else INF for c in self.dist]

    def initialize_costs(self, neighbor_costs):
        for neighbor, cost in neighbor_costs:
            self.neighbors[neighbor] = cost
            if cost < self.dist[neighbor]:
                self.dist[neighbor] = cost
                self.next_hop[neighbor] = neighbor

        costs = self._dv_costs()
        return [packet_module.Packet(nb, costs) for nb in self.neighbors]

    def update(self, pkt):
        src = pkt.get_source()
        raw = pkt.get_costs()
        self.neighbor_dvs[src] = [c if c < INF else _BIG for c in raw]

        changed = False
        for d in range(self.n):
            if d == self.index:
                continue
            best_cost = _BIG
            best_hop = None
            for v, link_cost in self.neighbors.items():
                if v in self.neighbor_dvs:
                    via = link_cost + self.neighbor_dvs[v][d]
                    if via < best_cost:
                        best_cost = via
                        best_hop = v
            if best_cost < self.dist[d]:
                self.dist[d] = best_cost
                self.next_hop[d] = best_hop
                changed = True

        if not changed:
            return []

        costs = self._dv_costs()
        return [packet_module.Packet(nb, costs) for nb in self.neighbors]

    def get_all_costs(self):
        result = []
        for i in range(self.n):
            cost = self.dist[i] if self.dist[i] < _BIG else INF
            hop  = self.next_hop[i] if self.next_hop[i] is not None else i
            result.append((hop, cost))
        return result

    def forward_next_hop(self, destination):
        return self.next_hop[destination]
