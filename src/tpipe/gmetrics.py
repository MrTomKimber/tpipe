
from typing import Optional, Literal, Callable, Iterator
import networkx as nx
from functools import partial

# Measures
# ==================================================
def measure_text_length(G, node):
    text = G.nodes[node]["data"].text or ""
    return len(text)

def measure_word_count(G, node):
    # Crude count of words based on length of simple text.split()
    text = G.nodes[node]["data"].text or ""
    return len(text.split())

def get_node_metric_fn(name, default=0):
    def getter(G, node):
        return G.nodes[node]["data"].node_metrics.get(name, default)
    return getter
# Writers
# ==================================================
def write_metric(G, node, value, name):
    G.nodes[node]["data"].node_metrics[name]=value

# Selectors
# ==================================================
def select_children(G, node, edge_type="contains", edge_attr="kind"):
    children = set([ child 
                for _, child, key, data in G.out_edges(node, keys=True, data=True)
                if data.get(edge_attr) == edge_type])
    return children

def select_parent(G, node, edge_type="contains", edge_attr="kind"):
    parents = set([ parent
                for _, parent, key, data in G.in_edges(node, keys=True, data=True)
                if data.get(edge_attr) == edge_type])
    return parents

def select_siblings(G, node, edge_type="contains", edge_attr="kind"):
    parent = select_parent(G, node, edge_type, edge_attr)
    siblings = set([s for s in select_children(G, parent, edge_type, edge_attr) if s != node])
    return siblings

# Adjustors
# ==================================================

def adjust_default(value, source_node, target_node, G):
    return value

def adjust_discount(value, source_node, target_node, G, factor=0.9):
    # source_node, target_node, G part of function sig
    # to enable other discount functions to be context aware
    # in this example, it's just applying a simple factor
    # to the value supplied
    return factor * value

# Reducers
# ==================================================

def reduce_sum(values):
    return sum(values)

def reduce_count(values):
    return len(values)

def reduce_mean(values):
    return sum(values)/len(values)


# Application
# ==================================================
# Atomic Application
def apply_metric(
    G,
    node,
    base_fn,
    write_fn,
    measure_fn=None,
    selector_fn=None,
    adjust_fn=None,
    reduce_fn=None,
):
    value = base_fn(G, node)
    if selector_fn is None:
        write_fn(G, node, value)
        return value

    related_nodes = list(selector_fn(G, node))
    values = [measure_fn(G, other) for other in related_nodes]

    if adjust_fn is not None:
        values = [
            adjust_fn(value, source_node=other, target_node=node, G=G)
            for other, value in zip(related_nodes, values)
        ]

    if reduce_fn is None:
        raise ValueError("reduce_fn is required for relational aggregation")

    result = reduce_fn([value] + values)
    write_fn(G, node, result)
    return result

# Bottom-Up Application
def bottom_up_apply(G, root, apply_fn, edge_type="contains", edge_attr="kind"):
    for node in nx.dfs_postorder_nodes(G, source=root):
        apply_fn(G, node)


# ========================================================
#  
#
# ========================================================

#apply_text_length_fn = partial(gmetrics.apply_metric,
#                               base_fn=gmetrics.measure_text_length, 
#                               write_fn=partial(gmetrics.write_metric, name="text_length"))
#
#apply_word_count_fn = partial(gmetrics.apply_metric, 
#                              base_fn=gmetrics.measure_word_count, 
#                              write_fn=partial(gmetrics.write_metric, name="word_count"))

#aggregate_text_length_fn = partial(gmetrics.apply_metric,
#                                base_fn=gmetrics.get_node_metric_fn("text_length"), 
#                               measure_fn=gmetrics.get_node_metric_fn("aggregate_text_length"), 
#                               write_fn=partial(gmetrics.write_metric, name="aggregate_text_length"), 
#                               selector_fn=gmetrics.select_children, 
#                               adjust_fn=gmetrics.adjust_default, 
#                               reduce_fn=gmetrics.reduce_sum)

#sibling_mean_text_length_fn = partial(gmetrics.apply_metric,
#                                base_fn=gmetrics.get_node_metric_fn("aggregate_text_length"), 
#                               measure_fn=gmetrics.get_node_metric_fn("aggregate_text_length"), 
#                               write_fn=partial(gmetrics.write_metric, name="mean_sibling_text_length"), 
#                               selector_fn=gmetrics.select_siblings, 
#                               adjust_fn=gmetrics.adjust_default, 
#                               reduce_fn=gmetrics.reduce_mean)




#gmetrics.bottom_up_apply(gn, root_node_id, apply_text_length_fn)
#gmetrics.bottom_up_apply(gn, root_node_id, apply_word_count_fn)
#gmetrics.bottom_up_apply(gn, root_node_id, aggregate_text_length_fn)
#gmetrics.bottom_up_apply(gn, root_node_id, sibling_mean_text_length_fn)
