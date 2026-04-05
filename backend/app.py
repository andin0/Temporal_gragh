from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import networkx as nx
from werkzeug.utils import secure_filename
from data_loader import load_from_csv, load_from_json, build_timestamp_graph, build_snapshot_graphs, graph_to_dict

app = Flask(__name__)
CORS(app)  # 配置 CORS 允许前端跨域请求

# 初始化数据
timestamp_data = None
snapshot_data = None
# 全局图对象
global_G = None

def load_mock_data():
    """加载本地的 mock 文件"""
    global timestamp_data, snapshot_data, global_G
    
    # 检查文件是否存在，如果不存在则创建
    if not os.path.exists('timestamp_data.json'):
        # 创建时间戳模式的 mock 数据
        timestamp_json = {
            "mode": "timestamp",
            "edges": [
                {"source": "X", "target": "Y", "timestamp": 1},
                {"source": "Y", "target": "Z", "timestamp": 2},
                {"source": "Z", "target": "X", "timestamp": 3},
                {"source": "X", "target": "Z", "timestamp": 4},
                {"source": "Y", "target": "X", "timestamp": 5}
            ]
        }
        import json
        with open('timestamp_data.json', 'w') as f:
            json.dump(timestamp_json, f)
    
    if not os.path.exists('snapshot_data.json'):
        # 创建快照模式的 mock 数据
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
        import json
        with open('snapshot_data.json', 'w') as f:
            json.dump(snapshot_json, f)
    
    # 加载数据
    timestamp_data = load_from_json('timestamp_data.json', 'timestamp')
    snapshot_data = load_from_json('snapshot_data.json', 'snapshot')
    
    # 构建并存储图对象
    global_G = build_timestamp_graph(timestamp_data)

# 加载 mock 数据
load_mock_data()

@app.route('/api/graph/timestamp', methods=['GET'])
def get_timestamp_graph():
    """获取时间戳图数据"""
    try:
        # 构建图
        graph = build_timestamp_graph(timestamp_data)
        # 序列化
        graph_dict = graph_to_dict(graph)
        # 返回 JSON 格式
        return jsonify(graph_dict)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/graph/snapshot', methods=['GET'])
def get_snapshot_graphs():
    """获取快照图数据"""
    try:
        # 构建多个图
        graphs = build_snapshot_graphs(snapshot_data)
        # 序列化每个快照
        result = []
        for i, graph in enumerate(graphs):
            graph_dict = graph_to_dict(graph)
            # 获取对应的 timestamp
            timestamp = snapshot_data['snapshots'][i]['timestamp']
            result.append({
                'snapshot_id': i + 1,
                'timestamp': timestamp,
                'nodes': graph_dict['nodes'],
                'links': graph_dict['links']
            })
        # 返回 JSON 数组
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传文件并解析为图表数据"""

    global global_G
    try:
        # 检查是否有文件和模式参数
        if 'file' not in request.files or 'mode' not in request.form:
            return jsonify({'error': '缺少文件或模式参数'}), 400
        
        file = request.files['file']
        mode = request.form['mode']
        
        if mode not in ['timestamp', 'snapshot']:
            return jsonify({'error': '模式必须是 timestamp 或 snapshot'}), 400
        
        # 保存临时文件
        temp_filename = 'temp_upload' + os.path.splitext(file.filename)[1]
        file.save(temp_filename)
        
        # 根据文件类型加载数据
        if file.filename.endswith('.csv'):
            data = load_from_csv(temp_filename, mode)
        elif file.filename.endswith('.json'):
            data = load_from_json(temp_filename, mode)
        else:
            os.remove(temp_filename)
            return jsonify({'error': '只支持 CSV 和 JSON 文件'}), 400
        
        # 构建图并序列化
        if mode == 'timestamp':
            graph = build_timestamp_graph(data)
            result = graph_to_dict(graph)
            # 更新全局图对象 (删掉这里的 global global_G)
            global_G = graph
        else:  # snapshot
            graphs = build_snapshot_graphs(data)
            result = []
            for i, graph in enumerate(graphs):
                graph_dict = graph_to_dict(graph)
                # 获取对应的 timestamp
                timestamp = data['snapshots'][i]['timestamp']
                result.append({
                    # ...
                })
            # 使用第一个快照更新全局图对象 (删掉这里的 global global_G)
            global_G = graphs[0]
        
        # 清理临时文件
        os.remove(temp_filename)
        
        return jsonify(result)
    except Exception as e:
        # 清理临时文件
        if 'temp_filename' in locals() and os.path.exists(temp_filename):
            os.remove(temp_filename)
        return jsonify({'error': str(e)}), 500

@app.route('/api/shortest-path', methods=['POST'])
def shortest_path():
    """计算最短路径"""
    try:
        data = request.json
        source = data.get('source')
        target = data.get('target')
        current_links = data.get('links') # 接收前端当前正在展示的连线

        if not source or not target or current_links is None:
            return jsonify({'error': '缺少必要参数'}), 400

        # 根据前端实际渲染的连线，动态临时构建严格有向图
        strict_g = nx.DiGraph()
        for link in current_links:
            src = link['source']
            tgt = link['target']
            src_id = src['id'] if isinstance(src, dict) else src
            tgt_id = tgt['id'] if isinstance(tgt, dict) else tgt
            strict_g.add_edge(src_id, tgt_id)

        if source not in strict_g or target not in strict_g:
            return jsonify({"error": "当前视图中不存在该节点"}), 404

        path = nx.shortest_path(strict_g, source=source, target=target)
        return jsonify({"path": path})
    except nx.NetworkXNoPath:
        return jsonify({"error": "两节点之间不存在有向路径"}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
