import pandas as pd
import networkx as nx
import json

def detect_mode(data):
    """
    自动检测数据模式
    
    Args:
        data: 数据对象，可以是字典（JSON解析后）或DataFrame（CSV读取后）
    
    Returns:
        str: 检测到的模式，'timestamp' 或 'snapshot'
    """
    if isinstance(data, dict):
        # JSON数据
        if 'snapshots' in data:
            return 'snapshot'
        elif 'edges' in data:
            # 检查edges中是否有timestamp
            edges = data.get('edges', [])
            if edges and isinstance(edges, list):
                first_edge = edges[0]
                if 'timestamp' in first_edge:
                    return 'timestamp'
        # 默认返回snapshot
        return 'snapshot'
    elif isinstance(data, pd.DataFrame):
        # CSV数据
        columns = [col.lower() for col in data.columns]
        if 'timestamp' in columns or 'time' in columns:
            return 'timestamp'
        else:
            return 'snapshot'
    else:
        raise ValueError("Unsupported data type")

def load_from_csv(file_path, mode):
    """
    从CSV文件加载时序图数据
    
    Args:
        file_path (str): CSV文件路径
        mode (str): 数据模式，'timestamp' 或 'snapshot'
    
    Returns:
        dict: 加载的数据
    """
    df = pd.read_csv(file_path)
    
    if mode == 'timestamp':
        # 时间戳模式：每行代表一条边，包含source, target, timestamp
        data = {
            'mode': 'timestamp',
            'edges': []
        }
        for _, row in df.iterrows():
            edge = {
                'source': row['source'],
                'target': row['target'],
                'timestamp': row['timestamp']
            }
            data['edges'].append(edge)
    elif mode == 'snapshot':
        # 快照模式：每行代表一个快照，包含timestamp, nodes, edges
        data = {
            'mode': 'snapshot',
            'snapshots': []
        }
        for _, row in df.iterrows():
            snapshot = {
                'timestamp': row['timestamp'],
                'nodes': json.loads(row['nodes']),
                'edges': json.loads(row['edges'])
            }
            data['snapshots'].append(snapshot)
    else:
        raise ValueError("Mode must be 'timestamp' or 'snapshot'")
    
    return data

def load_from_json(file_path):
    """
    从JSON文件加载时序图数据
    
    Args:
        file_path (str): JSON文件路径
    
    Returns:
        dict: 加载的数据
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    return data

def build_timestamp_graph(data):
    """
    将时间戳模式的数据转换为NetworkX图对象
    
    Args:
        data (dict): 时间戳模式的数据
    
    Returns:
        nx.MultiDiGraph: NetworkX图对象
    """
    G = nx.MultiDiGraph()
    
    for edge in data['edges']:
        source = edge['source']
        target = edge['target']
        timestamp = edge['timestamp']
        
        # 添加节点
        G.add_node(source)
        G.add_node(target)
        
        # 添加边，附带时间戳属性
        G.add_edge(source, target, timestamp=timestamp)
    
    return G

def build_snapshot_graphs(data):
    """
    将快照模式的数据转换为NetworkX图对象列表
    
    Args:
        data (dict): 快照模式的数据
    
    Returns:
        list: NetworkX图对象列表
    """
    graphs = []
    
    for snapshot in data['snapshots']:
        G = nx.DiGraph()
        timestamp = snapshot['timestamp']
        
        # 添加节点
        for node in snapshot['nodes']:
            G.add_node(node)
        
        # 添加边，附带时间戳属性
        for edge in snapshot['edges']:
            source = edge['source']
            target = edge['target']
            G.add_edge(source, target, timestamp=timestamp)
        
        graphs.append(G)
    
    return graphs

def graph_to_dict(nx_graph):
    """
    将NetworkX图对象转换为D3前端所需的格式
    
    Args:
        nx_graph (nx.DiGraph or nx.MultiDiGraph): NetworkX图对象
    
    Returns:
        dict: 包含nodes和links的字典
    """
    nodes = []
    links = []
    
    # 计算节点度数并添加到节点属性
    for node in nx_graph.nodes():
        degree = nx_graph.degree(node)
        nodes.append({
            'id': node,
            'degree': degree
        })
    
    # 添加边，包含source, target和timestamp
    if nx_graph.is_multigraph():
        # 多重图遍历方式
        for source, target, key, attrs in nx_graph.edges(data=True, keys=True):
            links.append({
                'source': source,
                'target': target,
                'timestamp': attrs.get('timestamp', 0)
            })
    else:
        # 普通图遍历方式
        for source, target, attrs in nx_graph.edges(data=True):
            links.append({
                'source': source,
                'target': target,
                'timestamp': attrs.get('timestamp', 0)
            })
    
    return {
        'nodes': nodes,
        'links': links
    }

if __name__ == '__main__':
    # 生成临时的Mock数据（CSV）
    import os
    
    # 生成时间戳模式的CSV数据
    timestamp_csv = 'source,target,timestamp\nA,B,1\nB,C,2\nC,A,3\nA,C,4\nB,A,5'
    
    # 生成快照模式的CSV数据
    snapshot_csv = 'timestamp,nodes,edges\n1,"[""A"",""B"",""C""]","[{""source"":""A"",""target"":""B""},{""source"":""B"",""target"":""C""}]"\n2,"[""A"",""B"",""C"",""D""]","[{""source"":""A"",""target"":""B""},{""source"":""B"",""target"":""C""},{""source"":""C"",""target"":""D""}]"'
    
    # 生成时间戳模式的JSON数据
    timestamp_json = {
        "mode": "timestamp",
        "edges": [
            {"source": "X", "target": "Y", "timestamp": 1},
            {"source": "Y", "target": "Z", "timestamp": 2},
            {"source": "Z", "target": "X", "timestamp": 3}
        ]
    }
    
    # 生成快照模式的JSON数据
    snapshot_json = {
        "mode": "snapshot",
        "snapshots": [
            {
                "timestamp": 1,
                "nodes": ["P", "Q", "R"],
                "edges": [
                    {"source": "P", "target": "Q"},
                    {"source": "Q", "target": "R"}
                ]
            },
            {
                "timestamp": 2,
                "nodes": ["P", "Q", "R", "S"],
                "edges": [
                    {"source": "P", "target": "Q"},
                    {"source": "Q", "target": "R"},
                    {"source": "R", "target": "S"}
                ]
            }
        ]
    }
    
    # 写入临时文件
    with open('timestamp_data.csv', 'w') as f:
        f.write(timestamp_csv)
    
    with open('snapshot_data.csv', 'w') as f:
        f.write(snapshot_csv)
    
    with open('timestamp_data.json', 'w') as f:
        json.dump(timestamp_json, f)
    
    with open('snapshot_data.json', 'w') as f:
        json.dump(snapshot_json, f)
    
    print("=== 测试CSV数据加载与图构建 ===")
    # 测试时间戳模式CSV
    timestamp_data = load_from_csv('timestamp_data.csv', 'timestamp')
    timestamp_graph = build_timestamp_graph(timestamp_data)
    timestamp_dict = graph_to_dict(timestamp_graph)
    print("时间戳模式CSV结果:")
    print(json.dumps(timestamp_dict, indent=2))
    
    # 测试快照模式CSV
    snapshot_data = load_from_csv('snapshot_data.csv', 'snapshot')
    snapshot_graphs = build_snapshot_graphs(snapshot_data)
    print("\n快照模式CSV结果:")
    for i, graph in enumerate(snapshot_graphs):
        snapshot_dict = graph_to_dict(graph)
        print(f"快照 {i+1}:")
        print(json.dumps(snapshot_dict, indent=2))
    
    print("\n=== 测试JSON数据加载与图构建 ===")
    # 测试时间戳模式JSON
    timestamp_data_json = load_from_json('timestamp_data.json', 'timestamp')
    timestamp_graph_json = build_timestamp_graph(timestamp_data_json)
    timestamp_dict_json = graph_to_dict(timestamp_graph_json)
    print("时间戳模式JSON结果:")
    print(json.dumps(timestamp_dict_json, indent=2))
    
    # 测试快照模式JSON
    snapshot_data_json = load_from_json('snapshot_data.json', 'snapshot')
    snapshot_graphs_json = build_snapshot_graphs(snapshot_data_json)
    print("\n快照模式JSON结果:")
    for i, graph in enumerate(snapshot_graphs_json):
        snapshot_dict_json = graph_to_dict(graph)
        print(f"快照 {i+1}:")
        print(json.dumps(snapshot_dict_json, indent=2))
    
    # 清理临时文件
    for file in ['timestamp_data.csv', 'snapshot_data.csv', 'timestamp_data.json', 'snapshot_data.json']:
        if os.path.exists(file):
            os.remove(file)
