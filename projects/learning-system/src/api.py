"""
学习智能体系统 - API 接口

提供 RESTful API 供外部调用
"""

from flask import Flask, request, jsonify
from src.workers import create_worker
from src.core import MemoryManager, create_vector_db
from src.skills import SkillManager

app = Flask(__name__)

# 初始化全局组件
memory_manager = MemoryManager()
vector_db = create_vector_db("local")
skill_manager = SkillManager()
workers = {}


@app.route("/api/v1/worker/create", methods=["POST"])
def create_worker_api():
    """创建 Worker"""
    data = request.json
    role = data.get("role", "architect")
    name = data.get("name", f"{role}_worker")
    
    worker = create_worker(role)
    workers[name] = worker
    
    return jsonify({
        "status": "success",
        "worker": {"name": name, "role": role}
    })


@app.route("/api/v1/worker/<name>/execute", methods=["POST"])
def execute_task(name: str):
    """执行任务"""
    if name not in workers:
        return jsonify({"error": "Worker not found"}), 404
    
    data = request.json
    task = data.get("task", "")
    context = data.get("context", {})
    
    result = workers[name].execute(task, context)
    
    return jsonify({
        "status": "success",
        "result": result
    })


@app.route("/api/v1/memory/add", methods=["POST"])
def add_memory_api():
    """添加记忆"""
    data = request.json
    content = data.get("content", "")
    metadata = data.get("metadata", {})
    importance = data.get("importance", 1.0)
    
    memory_id = memory_manager.add_memory(content, metadata, importance)
    
    return jsonify({
        "status": "success",
        "memory_id": memory_id
    })


@app.route("/api/v1/memory/search", methods=["GET"])
def search_memory_api():
    """搜索记忆"""
    query = request.args.get("query", "")
    top_k = int(request.args.get("top_k", 5))
    
    results = memory_manager.retrieve(query, top_k)
    
    return jsonify({
        "status": "success",
        "memories": [
            {"id": m.id, "content": m.content, "importance": m.importance}
            for m in results
        ]
    })


@app.route("/api/v1/skill/list", methods=["GET"])
def list_skills_api():
    """列出技能"""
    category = request.args.get("category", None)
    skills = skill_manager.list_skills(category)
    
    return jsonify({
        "status": "success",
        "skills": skills
    })


@app.route("/api/v1/skill/execute", methods=["POST"])
def execute_skill_api():
    """执行技能"""
    data = request.json
    name = data.get("name", "")
    params = data.get("params", {})
    
    try:
        result = skill_manager.execute(name, **params)
        return jsonify({
            "status": "success",
            "result": result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/v1/vector/insert", methods=["POST"])
def insert_vector_api():
    """插入向量"""
    data = request.json
    vectors = data.get("vectors", [])
    metadata = data.get("metadata", [])
    
    ids = vector_db.insert(vectors, metadata)
    
    return jsonify({
        "status": "success",
        "ids": ids
    })


@app.route("/api/v1/vector/search", methods=["POST"])
def search_vector_api():
    """搜索向量"""
    data = request.json
    query_vector = data.get("query_vector", [])
    top_k = data.get("top_k", 5)
    
    results = vector_db.search(query_vector, top_k)
    
    return jsonify({
        "status": "success",
        "results": results
    })


@app.route("/api/v1/status", methods=["GET"])
def status_api():
    """系统状态"""
    return jsonify({
        "status": "running",
        "version": "0.1.0",
        "workers": list(workers.keys()),
        "memories": len(memory_manager.memories),
        "skills": skill_manager.list_skills()
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
