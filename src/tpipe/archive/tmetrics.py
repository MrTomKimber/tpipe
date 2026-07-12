
# =================================================================
# Node Scoring Metrics
# =================================================================
from typing import Optional, Literal, Callable, Iterator
import networkx as nx
from functools import reduce



def contains_children(G, node):
    for child in G.successors(node):
        edge_dict = G.get_edge_data(node, child, default={})
        if any(data.get("kind") == "contains" for data in edge_dict.values()):
            yield child

def iter_typed_children(G, node, edge_type="contains", edge_attr="kind"):
    for _, child, key, data in G.out_edges(node, keys=True, data=True):
        if data.get(edge_attr) == edge_type:
            yield child, key, data


def typed_children(G, node, edge_type="contains", edge_attr="kind"):
    seen = set()
    for child, key, data in iter_typed_children(G, node, edge_type=edge_type, edge_attr=edge_attr):
        if child not in seen:
            seen.add(child)
            yield child

def typed_parents(G, child, edge_type="contains", edge_attr="kind"):
    seen = set()
    for parent, _, key, data in G.in_edges(child, keys=True, data=True):
        if data.get(edge_attr) == edge_type and parent not in seen:
            seen.add(parent)
            yield parent
            
def calculate_node_text_length(G, node):
    text = G.nodes[node]["data"].text
    G.nodes[node]["data"].node_metrics["text_length"]=len(text) if text is not None else 0

def calculate_node_word_count(G, node):
    # Crude count of words based on length of simple text.split()
    text = G.nodes[node]["data"].text
    G.nodes[node]["data"].node_metrics["text_word_count"]=len(text.split()) if text is not None else 0

def discount_factor(score, factor):
    return score * factor

def aggregate_measure(node, 
                      child_scores, 
                      G, 
                      metric_name, 
                      reduce_fn, 
                      discount_fn:Callable,
                      initial=None
                      ):

    own = G.nodes[node]["data"].node_metrics.get(metric_name, 0)
    values = [own] + [discount_fn(s) for s in child_scores]

    if initial is not None:
        return reduce(reduce_fn, values, initial)

    return reduce(reduce_fn, values)

def roll_up_metric(
    G,
    root,
    metric_getter,
    reduce_fn,
    out_key,
    edge_type="contains",
    edge_attr="kind",
):
    scores = {}

    for node in nx.dfs_postorder_nodes(G, source=root):
        child_scores = [
            scores[child]
            for child in typed_children(G, node, edge_type=edge_type, edge_attr=edge_attr)
        ]
        own_value = metric_getter(G, node)
        total = reduce_fn(own_value, child_scores)
        scores[node] = total
        G.nodes[node]["data"].subtree_metrics[out_key] = total

    return scores

def calculate_node_sibling_metrics(
    G,
    node,
    value_getter,
    sibling_metric_fn,
    edge_type="contains",
    edge_attr="kind",
):
    parents = list(typed_parents(G, node, edge_type=edge_type, edge_attr=edge_attr))
    if not parents:
        return {}

    if len(parents) > 1:
        raise ValueError(f"Node {node!r} has multiple {edge_type!r} parents")

    parent = parents[0]
    siblings = [s for s in typed_children(G, parent, edge_type=edge_type, edge_attr=edge_attr) if s != node]

    node_score = value_getter(G, node)
    sibling_scores = [value_getter(G, sibling) for sibling in siblings]

    metrics = sibling_metric_fn(node_score, sibling_scores, node=node, parent=parent, G=G)
    G.nodes[node]["data"].node_metrics.update(metrics)
    return metrics