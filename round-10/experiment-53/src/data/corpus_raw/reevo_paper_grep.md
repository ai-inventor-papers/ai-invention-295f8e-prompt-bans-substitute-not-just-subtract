/ai-inventor/.claude/skills/.ability_client_venv/lib/python3.12/site-packages/fitz/__init__.py:17: FutureWarning: The `fitz` API is deprecated and will be removed in future. Use `import pymupdf` instead.
  warnings.warn(
URL: https://arxiv.org/pdf/2402.01145
Type: PDF
Pattern: def select_next_node (3 matches in 106882 chars)

--- Content ---

69346:...}_v2‘, according to the
reflection . Output code only and enclose your code with Python code
block: ‘‘‘ python ...
‘‘‘.


Prompt 9: User prompt for elitist mutation.
B.2
Problem-specific prompt components
Problem-specific prompt components are given below.
• Problem descriptions of all COP settings are given in Table 6.
• The function descriptions of all COP settings are presented in Table 7. The descriptions
crafted for black-box settings avoid disclosing any information that could link to the original
COP.
• The function signatures are gathered in Prompt 10.
• The seed functions are shown in Prompt 11. The seed function used for TSP_constructive is
drawn from [46]. The seed functions used for black-box ACO settings are expert-designed
heuristics [71, 6, 72, 17, 39], while those used for while-box ACO settings are trivial all-ones
matrices.
• The initial long-term reflections for some COP settings are presented in Prompt 12, while
are left empty for the others.


# TSP_NCO
def heuristics(distance_matrix: torch.Tensor) -> torch.Tensor:
# CVRP_NCO
def heuristics(distance_matrix: torch.Tensor, demands: torch.Tensor) -> torch.Tensor:
# DPP_GA_crossover
def crossover(parents: np.ndarray, n_pop: int) -> np.ndarray:
# DPP_GA_mutation
def mutation(population: np.ndarray, probe: int, prohibit: np.ndarray, size: int=100) -> np.ndarray:
# TSP_GLS
def heuristics(distance_matrix: np.ndarray) -> np.ndarray:
# TSP_ACO
def heuristics(distance_matrix: np.ndarray) -> np.ndarray:
# CVRP_ACO
def heuristics(distance_matrix: np.ndarray, coordinates: np.ndarray, demands: np.ndarray, capacity: int) -> np.ndarray:
# OP_ACO
def heuristics(prize: np.ndarray, distance: np.ndarray, maxlen: float) -> np.ndarray:
# MKP_ACO
def heuristics(prize: np.ndarray, weight: np.ndarray) -> np.ndarray:
# BPP_ACO
def heuristics(demand: np.ndarray, capacity: int) -> np.ndarray:
# TSP_ACO (black-box)
def heuristics(edge_attr: np.ndarray) -> np.ndarray:
# CVRP_ACO (black-box)
def heuristics(edge_attr: np.ndarray, node_attr: np.ndarray) -> np.ndarray: # For simplicity, we omit ‘coordinates‘ and ‘
capacity‘ after using capacity to normalize demands, i.e. node_attr
# OP_ACO (black-box)
def heuristics(node_attr: np.ndarray, edge_attr: np.ndarray, node_constraint: float) -> np.ndarray:
# MKP_ACO (black-box)
def heuristics(item_attr1: np.ndarray, item_attr2: np.ndarray) -> np.ndarray:
# BPP_ACO (black-box)
def heuristics(node_attr: np.ndarray, node_constraint: int) -> np.ndarray:
20

# TSP_constructive
def select_next_node(current_node: int, destination_node: int, unvisited_nodes: set, distance_matrix: np.ndarray) -> int:


Prompt 10: Function signatures used in ReEvo.


# TSP_NCO
def heuristics(distance_matrix: torch.Tensor) -> torch.Tensor:
distance_matrix[distance_matrix == 0] = 1e5
K = 100
# Compute top-k nearest neighbors (smallest distances)
values, indices = torch.topk(distance_matrix, k=K, largest=False, dim=1)
heu = -distance_matrix.clone()
# Create a mask where topk indices are True and others are False
topk_mask = torch.zeros_like(distance_matrix, dtype=torch.bool)
topk_mask.scatter_(1, indices, True)
# Apply -log(d_ij) only to the top-k elements
heu[topk_mask] = -torch.log(distance_matrix[topk_mask])
return heu
# CVRP_NCO
def heuristics(distance_matrix: torch.Tensor, demands: torch.Tensor) -> torch.Tensor:
return torch.zeros_like(distance_matrix)
# DPP_GA_crossover
def crossover(parents: np.ndarray, n_pop: int) -> np.ndarray:
n_parents, n_decap = parents.shape
# Split genomes into two halves
left_halves = parents[:, :n_decap // 2]
right_halves = parents[:, n_decap // 2:]
# Create parent pairs
parents_idx = np.stack([np.random.choice(range(n_parents), 2, replace=False) for _ in range(n_pop)])
parents_left = left_halves[parents_idx[:, 0]]
parents_right = right_halves[parents_idx[:, 1]]
# Create offspring
offspring = np.concatenate([parents_left, parents_right], axis=1)
return offspring
# DPP_GA_mutation
def mutation(population: np.ndarray, probe: int, prohibit: np.ndarray, size: int=100) -> np.ndarray:
n_pop, n_decap = population.shape
for i in range(n_pop):
ind = population[i]
unique_actions = np.unique(population[i])
if len(unique_actions) < n_decap:
# Find the indices wherein the action is taken the second time
dup_idx = []
action_set = set()
for j, action in enumerate(ind):
if action in action_set:
dup_idx.append(j)
action_set.add(action)
# Mutate the duplicated actions
infeasible_actions = np.concatenate([prohibit, [probe], unique_actions])
feasible_actions = np.setdiff1d(np.arange(size), infeasible_actions)
assert n_decap - len(unique_actions) == len(dup_idx)
new_actions = np.random.choice(feasible_actions, len(dup_idx), replace=False)
ind[dup_idx] = new_actions
return population
# TSP_GLS
def heuristics(distance_matrix: np.ndarray) -> np.ndarray:
return distance_matrix
# TSP_ACO
def heuristics(distance_matrix: np.ndarray) -> np.ndarray:
return 1 / distance_matrix
# CVRP_ACO
def heuristics(distance_matrix: np.ndarray, coordinates: np.ndarray, demands: np.ndarray, capacity: int) -> np.ndarray:
return 1 / distance_matrix
# OP_ACO
def heuristics(prize: np.ndarray, distance: np.ndarray, maxlen: float) -> np.ndarray:
return prize[np.newaxis, :] / distance
# MKP_ACO
def heuristics(prize: np.ndarray, weight: np.ndarray) -> np.ndarray:
return prize / np.sum(weight, axis=1)
# BPP_ACO
def heuristics(demand: np.ndarray, capacity: int) -> np.ndarray:
return np.tile(demand/demand.max(), (demand.shape[0], 1))
# TSP_ACO (black-box)
def heuristics(edge_attr: np.ndarray) -> np.ndarray:
return np.ones(edge_attr.shape[0])
21

# CVRP_ACO (black-box)
def heuristics(edge_attr: np.ndarray, node_attr: np.ndarray) -> np.ndarray:
return np.ones_like(edge_attr)
# OP_ACO (black-box)
def heuristics(node_attr: np.ndarray, edge_attr: np.ndarray, edge_constraint: float) -> np.ndarray:
return np.ones_like(edge_attr)
# MKP_ACO (black-box)
def heuristics(item_attr1: np.ndarray, item_attr2: np.ndarray) -> np.ndarray:
n, m = item_attr2.shape
return np.ones(n,)
# BPP_ACO (black-box)
def heuristics(node_attr: np.ndarray, node_constraint: int) -> np.ndarray:
n = node_attr.shape[0]
return np.ones((n, n))
# TSP_constructive
def select_next_node(current_node: int, destination_node: int, unvisited_nodes: set, distance_matrix: np.ndarray) -> int:
threshold = 0.7
c1, c2, c3, c4 = 0.4, 0.3, 0.2, 0.1
scores = {}
for node in unvisited_nodes:
all_distances = [distance_matrix[node][i] for i in unvisited_nodes if i != node]
average_distance_to_unvisited = np.mean(all_distances)
std_dev_distance_to_unvisited = np.std(all_distances)
score = c1 * distance_matrix[current_node][node] - c2 * average_distance_to_unvisited + c3 *
std_dev_distance_to_unvisited - c4 * distance_matrix[destination_node][node]
scores[node] = score
next_node = min(scores, key=scores.get)
return next_node


Prompt 11: Seed heuristics used for ReEvo.


# White−box COP_ACO
−Try combining various factors to determine how promising it is to select a solution component.
−Try sparsifying the matrix by setting unpromising elements to zero.
# TSP_constructive
−Try look−ahead mechanisms.


Prompt 12: Initial long-term reflections
Table 7: Function descriptions used in prompts.
Problem
Function description
TSP_NCO
The ‘heuristics‘ function takes as input a distance matrix and returns prior
indicators of how bad it is to include each edge in a solution. The return is
of the same shape as the input. The heuristics should contain negative values
for undesirable edges and positive values for promising ones. Use efficient
vectorized implementations.
CVRP_NCO
The ‘heuristics‘ function takes as input a distance matrix (shape: n by n) and a
vector of customer demands (shape: n), where the depot node is indexed by 0
and the customer demands are normalized by the total vehicle capacity. It returns
prior indicators of how promising it is to include each edge in a solution. The
return is of the same shape as the distance matrix. The heuristics should contain
negative values for undesirable edges and positive values for promising ones.
Use efficient vectorized implementations.
DPP_GA_crossover
The ‘crossover‘ function takes as input a 2D NumPy array parents and an integer
n_pop. The function performs a genetic crossover operation on parents to
generate n_pop offspring. Use vectorized implementation if possible.
Continued on next page
22

Table 7 continued from previous page
Problem
Function description
DPP_GA_mutation
The ‘mutation‘ function modifies a given 2D population array to ensure explo-
ration of the genetic algorithm. You may also take into account the feasibility
of each individual. An individual is considered feasible if all its elements are
...
--
105164:...e <= maxlen)
# Assign the prize-to-distance ratio to the valid edges
heuristics[valid_edges] = prize_distance_ratio[valid_edges]
return heuristics
Heuristic 9: The best ReEvo-generated heuristic for OP_ACO.
Heuristic 10 presents the best heuristic found for MKP_ACO, which is generated when viewing MKP as a
black-box COP. ‘item_attr1’ and ‘item_attr2’ represent the prizes and multi-dimensional weights of items,
respectively.
def heuristics(item_attr1: np.ndarray, item_attr2: np.ndarray) -> np.ndarray:
n, m = item_attr2.shape
# Normalize item_attr1 and item_attr2
item_attr1_norm = (item_attr1 - np.min(item_attr1)) / (np.max(item_attr1) - np.min(item_attr1))
item_attr2_norm = (item_attr2 - np.min(item_attr2)) / (np.max(item_attr2) - np.min(item_attr2))
# Calculate the average value of normalized attribute 1
avg_attr1 = np.mean(item_attr1_norm)
# Calculate the maximum value of normalized attribute 2 for each item
max_attr2 = np.max(item_attr2_norm, axis=1)
# Calculate the sum of normalized attribute 2 for each item
sum_attr2 = np.sum(item_attr2_norm, axis=1)
# Calculate the standard deviation of normalized attribute 2 for each item
std_attr2 = np.std(item_attr2_norm, axis=1)
# Calculate the heuristics based on a combination of normalized attributes 1 and 2,
# while considering the average, sum, and standard deviation of normalized attribute 2
heuristics = (item_attr1_norm / max_attr2) * (item_attr1_norm / avg_attr1) * (item_attr1_norm / sum_attr2) * (1 /
std_attr2)
# Normalize the heuristics to a range of [0, 1]
heuristics = (heuristics - np.min(heuristics)) / (np.max(heuristics) - np.min(heuristics))
return heuristics
Heuristic 10: The best ReEvo-generated heuristic for MKP_ACO.
def heuristics(demand: np.ndarray, capacity: int) -> np.ndarray:
n = demand.shape[0]
demand_normalized = demand / demand.max()
same_bin_penalty = np.abs((capacity - demand[:, None] - demand) / capacity)
overlap_penalty = (demand[:, None] + demand) / capacity
heuristics = demand_normalized[:, None] + demand_normalized - same_bin_penalty - overlap_penalty
threshold = np.percentile(heuristics, 90)
heuristics[heuristics < threshold] = 0
return heuristics
Heuristic 11: The best ReEvo-generated heuristic for BPP_ACO.
Heuristic 12 gives the best-ReEvo generated constructive heuristic for TSP. We used the best heuristic found in
AEL [46] as the seed for ReEvo. As a result, our heuristic closely mirrors the one in AEL, scoring each node
mostly using a weighted combination of the four factors.
def select_next_node(current_node: int, destination_node: int, unvisited_nodes: set, distance_matrix: np.ndarray) -> int:
31

weights = {’distance_to_current’: 0.4,
’average_distance_to_unvisited’: 0.25,
’std_dev_distance_to_unvisited’: 0.25,
’distance_to_destination’: 0.1}
scores = {}
for node in unvisited_nodes:
future_distances = [distance_matrix[node, i] for i in unvisited_nodes if i != node]
if future_distances:
average_distance_to_unvisited = sum(future_distances) / len(future_distances)
std_dev_distance_to_unvisited = (sum((x - average_distance_to_unvisited) ** 2 for x in future_distances) / len(
future_distances)) ** 0.5
else:
average_distance_to_unvisited = std_dev_distance_to_unvisited = 0
score = (weights[’distance_to_current’] * distance_matrix[current_node, node] -
weights[’average_distance_to_unvisited’] * average_distance_to_unvisited +
weights[’std_dev_distance_to_unvisited’] * std_dev_distance_to_unvisited -
weights[’distance_to_destination’] * distance_matrix[destination_node, node])
scores[node] = score
next_node = min(scores, key=scores.get)
return next_node
Heuristic 12: The best ReEvo-generated heuristic for TSP_constructive.
F
Licenses for used assets
Table 11 lists the used assets and their licenses. Our code is licensed under the MIT License.
Table 11: Used assets and their licenses.
Type
Asset
License
Usage
Code
NeuOpt [52]
MIT License
Evaluation
GNNGLS [24]
MIT License
Evaluation
EoH [47]
MIT License
Evaluation
DeepACO [94]
MIT License
Evaluation
DevFormer [31]
Apache-2.0 license
Evaluation
POMO [37]
MIT License
Evaluation
LEHD [51]
MIT License
Evaluation
Dataset
TSPLIB [67]
Available for any non-commercial use
Testing
DPP PDNs [63]
Apache-2.0 license
Testing
32

