/ai-inventor/.claude/skills/.ability_client_venv/lib/python3.12/site-packages/fitz/__init__.py:17: FutureWarning: The `fitz` API is deprecated and will be removed in future. Use `import pymupdf` instead.
  warnings.warn(
URL: https://arxiv.org/pdf/2501.08603
Type: PDF
Pattern: def select_next_node (7 matches in 145724 chars)

--- Content ---

104043:... to visit.
Do not give additional explanations.
E.2. The Prompt of the Thought-Alignment Process
After obtaining the design idea and implementation by calling LLMs with the previous action prompts, MCTS-AHD will
conduct the second LLM call. In the second LLM call, we will input the design idea and implementation obtained from the
previous LLM call into the thought-alignment prompt as shown below for a more detailed and correlated heuristic function
description.
The thought-alignment Prompt
Solving Traveling Salesman Problem (TSP) with constructive heuristics. TSP requires finding the shortest path that
visits all given nodes and returns to the starting node.
Following is the Design Idea of a heuristic algorithm for the problem and the code with function name
’select next node’ for implementing the heuristic algorithm.
The select next node function takes as input the current node, the destination node, a set of unvisited nodes, and a
distance matrix, and returns the next node to visit.
Design Idea:
# The Design Idea
Code:
# The Python Code Implementation of A Function
The content of the Design Idea idea cannot fully represent what the algorithm has done informative. So, now you
should re-describe the algorithm using less than 3 sentences. Hint: You should reference the given Design Idea and
highlight the most critical design ideas of the code. You can analyse the code to describe which variables are given
higher priorities and which variables are given lower priorities, the parameters and the structure of the code.
24

Monte Carlo Tree Search for Comprehensive Exploration in LLM-Based Automatic Heuristic Design
E.3. Examples of LLM Outputs
This subsection provides two examples of LLM output in designing heuristics with MCTS-AHD. Every single LLM-based
heuristic generation includes two LLM calls. The first call generates the Python code of a heuristic function with action
prompts and the second call generates linguistic descriptions for heuristic functions with thought-alignment prompts.
Example of LLM output #1: Designing TSP heuristics within the step-by-step solving framework.
First Call Input:
The prompt for an MCTS-AHD action.
First Call Output:
{The new algorithm will utilize a hybrid approach that weighs the immediate distance (1.2) more heavily while still
considering the connection strength (0.6), ensuring that we select paths that are both cost-effective in the short term
and reasonable in the longer term by optimizing the total accumulated cost.}
def select_next_node(current_node, destination_node, unvisited_nodes,
distance_matrix):
if not unvisited_nodes:
return None
next_node = None
min_combined_cost = float(’inf’)
for candidate in unvisited_nodes:
immediate_distance = distance_matrix[current_node][candidate]
connection_strength = sum(distance_matrix[candidate][n] for n in unvisited_nodes if
n != candidate) / (max(len(unvisited_nodes) - 1, 1))
total_cost = immediate_distance
current_candidate = candidate
remaining_nodes = unvisited_nodes - {candidate}
while remaining_nodes:
best_next_node = min(remaining_nodes, key=lambda node: distance_matrix[
current_candidate][node])
total_cost += distance_matrix[current_candidate][best_next_node]
current_candidate = best_next_node
remaining_nodes.remove(best_next_node)
total_cost += distance_matrix[current_candidate][destination_node]
combined_cost = (1.2 * immediate_distance) + (0.6 / (connection_strength + 1)) +
total_cost
if combined_cost < min_combined_cost:
min_combined_cost = combined_cost
next_node = candidate
return next_node
Second Call Input:
The prompt of the thought-alignment process.
Second Call Output:
The algorithm utilizes a hybrid approach to solve the Traveling Salesman Problem by prioritizing immediate distance
(with a weight of 1.2) over connection strength (with a weight of 0.6) to select the next node to visit from a set of
unvisited nodes. It calculates a combined cost that considers the immediate distance to a candidate node, the average
connection strength to remaining unvisited nodes, and the total cost of visiting all remaining nodes before returning
to the destination. The algorithm systematically evaluates candidate nodes based on this combined cost, ensuring a
balance between short-term efficiency and overall path optimization.
25

Monte Carlo Tree Search for Comprehensive Exploration in LLM-Based Automatic Heuristic Design
Example of LLM output #2: Designing CAF for Cost-aware BO.
First Call Input:
The prompt for an MCTS-AHD action.
First Call Output:
{The new algorithm evaluates the potential improvement over the best observed value while incorporating a
compound risk factor based on both uncertainty and evaluation costs, adjusts the utility through a combination of
historical performance scaling, and normalizes the results across the test inputs to favor those with high expected
returns and low associated costs.}
import torch
def utility(train_x, train_y, best_x, best_y, test_x, mean_test_y, std_test_y,
cost_test_y, budget_used, budget_total):
# ...
--
131225:...te-box Setting: GPT-4o-mini
EoH
5.828
9.359
23.139
204.646
ReEvo
5.856
9.327
23.245
206.693
MCTS-AHD(Ours)
5.801
9.286
23.269
204.094
Black-box Setting: GPT-4o-mini
EoH
5.831
9.401
23.240
204.615
ReEvo
5.860
9.404
23.196
206.021
MCTS-AHD(Ours)
5.830
9.444
23.191
205.375
We can explain that MCTS-AHD’s better performance in application scenarios with complex heuristic space is highly
beneficial from its ability to explore complex function spaces and escape from local optima.
For its mediocre performance in black-box application scenarios, I believe this is mainly because compared to MCTS, which
only performs limited expansion on each heuristic, the population structure is computationally intensive and often involves
many rounds of LLM-based operations on a heuristic function in the population. So, the effectiveness of MCTS-AHD may
require LLMs more on its generation quality in limited number of MCTS expansions. In contrast, black-box application
scenarios make it difficult for LLMs to guarantee this condition, so these application scenarios will be tough for MCTS-AHD.
G. Examples of Evolution
To visually demonstrate the workflow of MCTS-AHD and its ability on exploration, we provide two examples of the
evolution of heuristics in two tasks, as shown in Figure 6.
The two examples of evolution clearly exhibit how MCTS-AHD conducts comprehensive explorations. For example, in
designing heuristics with a step-by-step construction framework for TSP, MCTS-AHD can expand potential child nodes from
nodes (e.g., MCTS node with ”Expansion: t=611”) that are not among the top 10 optimal ones (the performance range of the
top 10 optimal heuristics is the yellow shade), and ultimately reach the best heuristic. It reflects the superiority of employing
MCTS as an optimization framework instead of population-based EC. Population-based LLM-based AHD methods such as
EoH, ReEvo, and HSEvo lack consideration of worse-performing but potential heuristics. These algorithms will be obsessed
with processing top-performance heuristic functions. When the top 10 heuristics cannot obtain new heuristics surpassing the
top 10 performances with one LLM-based operation on heuristics, the evolution of heuristics will trap into local optima.
32

Monte Carlo Tree Search for Comprehensive Exploration in LLM-Based Automatic Heuristic Design
Performances g(·)
Evolution Steps
0
1000
0.1
0
�0
Exploration
Exploitation
Exploration Decay
Expansion: t = 122,        Action: e1,       g(·): -7.18502.
Code:
def select_next_node(current_node, destination_node, unvisited_nodes, distance_matrix):
    connectivity_scores = {node: sum(distance_matrix[node][other_node] for other_node in unvisited_nodes if node != 
other_node) for node in unvisited_nodes}
    
    def total_cost(node):
        travel_cost = distance_matrix[current_node][node]
        connectivity_penalty = (len(unvisited_nodes) - connectivity_scores[node]) / len(unvisited_nodes)
        return travel_cost + connectivity_penalty
    return min(unvisited_nodes, key=total_cost, default=None)
Description: ...
MCTS-Root
(Virtual)
Expansion , i.e., MCTS Links
MCTS nodes 
The performance range of the 
Top10 Heuristics
Expansion: t = 502,        Action: e2,       g(·): -6.36016.
Code:
def select_next_node(current_node, destination_node, unvisited_nodes, distance_matrix):
    scaling_factor, constant_penalty, bias_factor = 0.5, 2, 0.4
    average_distance = sum(distance_matrix[current_node][node] for node in unvisited_nodes) / len(unvisited_nodes) if unvisited_nodes 
else 0
    connectivity_scores = {node: sum(distance_matrix[node][other_node] for other_node in unvisited_nodes if node != other_node) for 
node in unvisited_nodes}
    def adjusted_cost(node):
        immediate_cost = distance_matrix[current_node][node]
        distance_to_destination = distance_matrix[node][destination_node]
        connectivity_penalty = scaling_factor * (len(unvisited_nodes) - connectivity_scores[node]) / len(unvisited_nodes)
        penalty = 0.5 * (immediate_cost + average_distance)
        return immediate_cost + penalty + constant_penalty + connectivity_penalty - (bias_factor * distance_to_destination)
    return min(unvisited_nodes, key=adjusted_cost, default=None)
Description: ...
Expansion: t = 528,        Action: m2,       g(·): -6.52703.
Code:
def select_next_node(current_node, destination_node, unvisited_nodes, distance_matrix):
    scaling_factor, constant_penalty, bias_factor = 0.7, 3, 0.5
    average_distance = sum(distance_matrix[current_node][node] ** 2 for node in unvisited_nodes) / len(unvisited_nodes) if unvisited_nodes else 0
    connectivity_scores = {node: sum(distance_matrix[node][other_node] ** 2 for other_node in unvisited_nodes if node != other_node) for node in unvisited_nodes}
    def adjusted_cost(node):
        immediate_cost = distance_matrix[current_node][node]
        distance_to_destination = distance_matrix[node][destination_node]
        connectivity_penalty = scaling_factor * (len(unvisited_nodes) - connectivity_scores[node]) / len(unvisited_nodes)
        penalty = 0.75 * (immediate_cost ** 2 + average_distance)
        return immediate_cost + penalty + constant_penalty + connectivity_penalty - (bias_factor * distance_to_destination ** 2)
    return min(unvisited_nodes, key=adjusted_cost, default=None)
Description: ...
Expansion: t = 611,        Action: m2,       g(·): -6.305.
Code:...
Description: ...
Expansion: t = 784,        
Action: m2,       g(·): -6.45066
Code:
def select_next_node(current_node, destination_node, unvisited_nodes, distance_matrix):
    scaling_factor, constant_penalty, bias_factor = 0.6, 0.5, 0.7
    average_distance = sum(distance_matrix[current_node][node] for node in unvisited_nodes) / 
len(unvisited_nodes) if unvisited_nodes else 0
    connectivity_scores = {node: sum(distance_matrix[node][other_node] for other_node in unvisited_nodes if 
node != other_node) for node in unvisited_nodes}
    def adjusted_cost(node):
        immediate_cost = distance_matrix[current_node][node]
        distance_to_destination = distance_matrix[node][destination_node]
        connectivity_penalty = scaling_factor * (len(unvisited_nodes) - connectivity_scores[node]) / 
len(unvisited_nodes)
        penalty = 0.3 * (immediate_cost + average_distance)
        return immediate_cost + penalty + constant_penalty + connectivity_penalty - (bias_factor * 
distance_to_destination)
    return min(unvisited_nodes, key=adjusted_cost, default=None)
Description: ...
Expansion: t = 985, 
Action: s1,       g(·): -6.27814.
Code:...
Description: ...
Expansion: t = 810, 
Action: m2,       g(·): -6.311.
Code:...
Description: ...
Expansion: t = 996,        Action: s1,       g(·): -6.26859.
Code:
def select_next_node(current_node, destination_node, unvisited_nodes, distance_matrix):
    scaling_factor, constant_penalty, bias_factor = 0.7, 0.4, 0.5
    average_distance = calculate_average_distance(unvisited_nodes, current_node, distance_matrix)
    connectivity_scores = calculate_connectivity_score(unvisited_nodes, distance_matrix)
    min_total_cost, next_node = float('inf'), None
    for node in unvisited_nodes:
        immediate_cost = distance_matrix[current_node][node]
        distance_to_destination = distance_matrix[node][destination_node]
        remaining_unvisited = unvisited_nodes - {node}
        mst_cost = minimum_spanning_tree(remaining_unvisited, distance_matrix) if remaining_unvisited else 0
        connectivity_penalty = scaling_factor * (len(unvisited_nodes) - connectivity_scores[node]) / len(unvisited_nodes)
        penalty = 0.4 * (immediate_cost + average_distance + mst_cost)
        adjusted_cost = immediate_cost + penalty + constant_penalty + connectivity_penalty - (bias_factor * distance_to_destination)
        if adjusted_cost < min_total_cost:
            min_total_cost, next_node = adjusted_cost, node
    return next_node
Description: ...
Evolution of  Step-by-step Constrction heuristics for TSP
(a) An Example of MCTS-AHD Evolution on Designing Step-by-step Construction Heuristics for TSP
Performances g(·)
Evolution Steps
0
1000
0.1
0
�0
Exploration
Exploitation
Exploration Decay
MCTS-Root
(Virtual)
Expansion , i.e., MCTS Links
MCTS nodes 
The performance range of the 
Top10 Heuristics
Expansion: t = 414,        Action: e1,       g(·): 40.17773.
Code:
def select_next_node(current_node, destination_node, unvisited_nodes, distance_matrix):
    scaling_factor, constant_penalty, bias_factor = 0.5, 2, 0.4
    average_distance = sum(distance_matrix[current_node][node] for node in unvisited_nodes) / len(unvisited_nodes) if unvisited_nodes else 0
    connectivity_scores = {node: sum(distance_matrix[node][other_node] for other_node in unvisited_nodes if node != other_node) for node in unvisited_nodes}
    def adjusted_cost(node):
        immediate_cost = distance_matrix[current_node][node]
        distance_to_destination = distance_matrix[node][destination_node]
        connectivity_penalty = scaling_factor * (len(unvisited_nodes) - connectivity_scores[node]) / len(unvisited_nodes)
        penalty = 0.5 * (immediate_cost + average_distance)
        return immediate_cost + penalty + constant_penalty + connectivity_penalty - (bias_factor * distance_to_destination)
    return min(unvisited_nodes, key=adjusted_cost, default=None)
Description: ...
Expansion: t = 694,  Action: s1,   g(·): 40.17621.
Code:
import numpy as np
def select_next_item(remaining_capacity, weights, values):
    n = len(weights)
    best_value, result = float('-inf'), -1
    weight_per_value = weights / values      # Calculate weight-to-value ratios and sort items
    items_sorted = sorted(range(n), key=lambda i: (weight_per_value[i], weights[i]))
    for index in items_sorted:
        if weights[index] <= remaining_capacity:
            total_value, total_weight = values[index], weights[index]
            for next_index in items_sorted:
                if next_index != index and total_weight + weights[next_index] <= remaining_capacity:
                    total_value += values[next_index]
                    total_weight += weights[next_index]
            total_value -= total_weight / (total_value + 1) if total_weight > 0 else 0
            if total_value > best_value:
                best_value, result = total_value, index
    return result
Description: ...
Expansion: t = 892,        Action: e2,       g(·): 40.17971.
Code:
import numpy as np
def select_next_item(remaining_capacity, weights, values):
    n = len(weights)
    best_value, result = float('-inf'), -1
    # Calculate penalty-adjusted scores
    penalty_scores = np.array(values) / (np.array(weights) + np.log(np.array(weights) + 1))
    penalty_scores *= remaining_capacity / np.maximum(weights, 1)
    # Sort items by penalty-adjusted scores
    items_sorted = sorted(range(n), key=lambda i: (-penalty_scor...
