# Temporal Graph

基于 Vue、Flask 和 NetworkX 的时序图可视化项目。前端用于上传和展示时序图数据，后端负责数据解析、图构建、图指标计算及最短路径查询。

## 项目结构

```text
temporal graph/
├── backend/                 # Flask 后端与数据处理逻辑
│   ├── app.py               # API 服务入口
│   ├── data_loader.py       # 数据加载、建图和指标计算
│   ├── requirements.txt     # 运行依赖
│   ├── requirements-dev.txt # 开发与测试依赖
│   └── tests/               # 小组自行编写的测试代码
├── frontend/                # Vue + Vite 前端
│   ├── src/
│   └── package.json
├── timestamp_data.json      # 时序图示例数据
└── snapshot_data.json       # 快照图示例数据
```

## 前置条件

- Python 3.10 或更高版本
- Node.js LTS（包含 npm）
- 建议使用 Windows PowerShell

可使用以下命令确认环境：

```powershell
python --version
node -v
npm -v
```

如果 PowerShell 提示无法执行 `npm.ps1`，可使用 `npm.cmd` 代替下文中的 `npm`，或为当前用户设置执行策略：

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

## 启动后端

在项目根目录打开 PowerShell，执行：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

后端启动成功后会监听：<http://127.0.0.1:5000>

> 请在 `backend` 目录中启动 `app.py`。后端会按当前工作目录读取本地数据文件。

## 启动前端

另开一个 PowerShell 窗口，在项目根目录执行：

```powershell
cd frontend
npm install
npm run dev
```

浏览器访问 Vite 在终端中显示的地址，通常为 <http://localhost:5173>。

## 数据格式

上传功能支持 `.csv` 和 `.json` 文件。系统处理两类时序图数据：

- **时间戳模式**：每条边包含 `source`、`target` 和 `timestamp`。
- **快照模式**：数据由多个时间点的快照组成，每个快照包含节点集合和边集合。

项目根目录中的 `timestamp_data.json` 和 `snapshot_data.json` 可用于了解输入结构。

## 运行测试

测试代码在 `backend/tests/`。虚拟环境在仓库根目录 `.venv`（若还没有，在仓库根目录执行 `python -m venv .venv`）。

在 `backend` 目录安装开发依赖后，一键跑全部用例（模块一 + 模块二）：

```powershell
cd backend
..\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
..\.venv\Scripts\python.exe -m pytest -q
```

只跑模块二（AI 生成后经人工核对的脚本 `tests/test_m2_pjj.py`）：

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_m2_pjj.py -v
```

当前合计 52 条，应全部通过。若本机虚拟环境建在 `backend/.venv`，把上面的 `..\.venv` 改成 `.\.venv` 即可。

## 常见问题

### 上传时显示“服务器处理文件失败”

先查看浏览器开发者工具的 Network 响应内容，以及后端终端中的状态码。若响应中包含 `No module named 'scipy'`，请在 `backend` 目录运行：

```powershell
.\.venv\Scripts\python.exe -m pip install scipy
```

安装完成后重新启动后端服务。

### 前端无法获取数据

确认 Flask 后端仍在运行于 `http://127.0.0.1:5000`，然后刷新前端页面。
