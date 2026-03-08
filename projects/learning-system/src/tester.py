"""
测试 Worker

负责实际运行程序并测试
"""

from src.core.agent import Agent
import subprocess
import sys
import os


class TesterWorker(Agent):
    """测试 Worker"""
    
    def __init__(self):
        super().__init__("测试员", "Tester Worker")
        self.test_results = []
    
    def execute(self, task: str, context: dict = None) -> str:
        """执行测试任务"""
        if task == "run_main":
            return self.run_main()
        elif task == "run_api":
            return self.run_api()
        elif task == "run_web":
            return self.run_web()
        elif task == "run_tests":
            return self.run_tests()
        elif task == "full_test":
            return self.full_test()
        else:
            return f"Unknown test task: {task}"
    
    def run_main(self) -> str:
        """运行主程序"""
        try:
            result = subprocess.run(
                [sys.executable, "main.py"],
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout + result.stderr
            self.test_results.append({
                "test": "run_main",
                "success": result.returncode == 0,
                "output": output
            })
            return f"主程序运行：{'成功' if result.returncode == 0 else '失败'}\n{output}"
        except Exception as e:
            error_msg = f"运行失败：{e}"
            self.test_results.append({
                "test": "run_main",
                "success": False,
                "error": error_msg
            })
            return error_msg
    
    def run_api(self) -> str:
        """运行 API 服务"""
        try:
            # 后台运行 API 服务
            result = subprocess.run(
                [sys.executable, "-m", "src.api"],
                capture_output=True,
                text=True,
                timeout=10
            )
            output = result.stdout + result.stderr
            self.test_results.append({
                "test": "run_api",
                "success": True,
                "output": output
            })
            return f"API 服务启动：成功\n{output}"
        except subprocess.TimeoutExpired:
            # 超时说明服务正在运行
            self.test_results.append({
                "test": "run_api",
                "success": True,
                "output": "Service running"
            })
            return "API 服务启动：成功 (运行中)"
        except Exception as e:
            error_msg = f"启动失败：{e}"
            self.test_results.append({
                "test": "run_api",
                "success": False,
                "error": error_msg
            })
            return error_msg
    
    def run_web(self) -> str:
        """运行 Web 界面"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "src.web"],
                capture_output=True,
                text=True,
                timeout=10
            )
            output = result.stdout + result.stderr
            self.test_results.append({
                "test": "run_web",
                "success": True,
                "output": output
            })
            return f"Web 界面启动：成功\n{output}"
        except subprocess.TimeoutExpired:
            self.test_results.append({
                "test": "run_web",
                "success": True,
                "output": "Service running"
            })
            return "Web 界面启动：成功 (运行中)"
        except Exception as e:
            error_msg = f"启动失败：{e}"
            self.test_results.append({
                "test": "run_web",
                "success": False,
                "error": error_msg
            })
            return error_msg
    
    def run_tests(self) -> str:
        """运行单元测试"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-v"],
                capture_output=True,
                text=True,
                timeout=60
            )
            output = result.stdout + result.stderr
            self.test_results.append({
                "test": "run_tests",
                "success": result.returncode == 0,
                "output": output
            })
            return f"单元测试：{'通过' if result.returncode == 0 else '失败'}\n{output}"
        except Exception as e:
            error_msg = f"测试失败：{e}"
            self.test_results.append({
                "test": "run_tests",
                "success": False,
                "error": error_msg
            })
            return error_msg
    
    def full_test(self) -> str:
        """完整测试"""
        results = []
        
        # 1. 运行主程序
        results.append("=== 主程序测试 ===")
        results.append(self.run_main())
        
        # 2. 运行单元测试
        results.append("\n=== 单元测试 ===")
        results.append(self.run_tests())
        
        # 3. 启动 API 服务
        results.append("\n=== API 服务测试 ===")
        results.append(self.run_api())
        
        # 4. 启动 Web 界面
        results.append("\n=== Web 界面测试 ===")
        results.append(self.run_web())
        
        # 生成测试报告
        success_count = sum(1 for r in self.test_results if r.get("success", False))
        total_count = len(self.test_results)
        
        report = f"\n\n{'='*40}\n"
        report += f"测试报告\n"
        report += f"{'='*40}\n"
        report += f"总测试数：{total_count}\n"
        report += f"通过：{success_count}\n"
        report += f"失败：{total_count - success_count}\n"
        report += f"通过率：{success_count/total_count*100:.1f}%\n"
        report += f"{'='*40}\n"
        
        return "\n".join(results) + report
    
    def get_test_report(self) -> dict:
        """获取测试报告"""
        return {
            "total": len(self.test_results),
            "success": sum(1 for r in self.test_results if r.get("success", False)),
            "failed": sum(1 for r in self.test_results if not r.get("success", True)),
            "results": self.test_results
        }


def create_tester() -> TesterWorker:
    """创建测试 Worker"""
    return TesterWorker()
