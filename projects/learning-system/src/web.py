"""
学习智能体系统 - Web 前端

简单的 Web 界面
"""

from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# 简单的 HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>学习智能体系统</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        .card { border: 1px solid #ddd; padding: 20px; margin: 10px 0; border-radius: 5px; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 3px; cursor: pointer; }
        button:hover { background: #0056b3; }
        input, textarea { width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ddd; border-radius: 3px; }
        .result { background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>🤖 学习智能体系统</h1>
    
    <div class="card">
        <h2>创建 Worker</h2>
        <input type="text" id="workerRole" placeholder="角色 (architect/search/challenger/devops)">
        <input type="text" id="workerName" placeholder="名称">
        <button onclick="createWorker()">创建</button>
    </div>
    
    <div class="card">
        <h2>执行任务</h2>
        <input type="text" id="workerNameExec" placeholder="Worker 名称">
        <textarea id="taskContent" placeholder="任务内容" rows="3"></textarea>
        <button onclick="executeTask()">执行</button>
    </div>
    
    <div class="card">
        <h2>添加记忆</h2>
        <textarea id="memoryContent" placeholder="记忆内容" rows="3"></textarea>
        <input type="number" id="memoryImportance" placeholder="重要性 (1-10)" min="1" max="10">
        <button onclick="addMemory()">添加</button>
    </div>
    
    <div class="card">
        <h2>搜索结果</h2>
        <div id="result" class="result">等待操作...</div>
    </div>
    
    <script>
        async function createWorker() {
            const role = document.getElementById('workerRole').value;
            const name = document.getElementById('workerName').value;
            const res = await fetch('/api/worker/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({role, name})
            });
            const data = await res.json();
            document.getElementById('result').innerText = JSON.stringify(data, null, 2);
        }
        
        async function executeTask() {
            const name = document.getElementById('workerNameExec').value;
            const task = document.getElementById('taskContent').value;
            const res = await fetch(`/api/worker/${name}/execute`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({task})
            });
            const data = await res.json();
            document.getElementById('result').innerText = JSON.stringify(data, null, 2);
        }
        
        async function addMemory() {
            const content = document.getElementById('memoryContent').value;
            const importance = document.getElementById('memoryImportance').value;
            const res = await fetch('/api/memory/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content, importance: parseFloat(importance)})
            });
            const data = await res.json();
            document.getElementById('result').innerText = JSON.stringify(data, null, 2);
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    """首页"""
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/worker/create", methods=["POST"])
def create_worker_proxy():
    """创建 Worker 代理"""
    # TODO: 连接到后端 API
    return jsonify({"status": "success", "message": "Worker created"})


@app.route("/api/worker/<name>/execute", methods=["POST"])
def execute_task_proxy(name: str):
    """执行任务代理"""
    # TODO: 连接到后端 API
    return jsonify({"status": "success", "result": f"Task executed by {name}"})


@app.route("/api/memory/add", methods=["POST"])
def add_memory_proxy():
    """添加记忆代理"""
    # TODO: 连接到后端 API
    return jsonify({"status": "success", "message": "Memory added"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
