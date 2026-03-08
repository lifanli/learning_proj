"""
运行测试

测试 Worker 实际运行程序
"""

from src.tester import create_tester

def main():
    """运行测试"""
    tester = create_tester()
    
    print("🧪 学习智能体系统 - 测试开始")
    print("=" * 50)
    
    # 运行完整测试
    result = tester.full_test()
    print(result)
    
    # 输出测试报告
    report = tester.get_test_report()
    print("\n📊 测试报告摘要:")
    print(f"  总测试数：{report['total']}")
    print(f"  通过：{report['success']}")
    print(f"  失败：{report['failed']}")
    
    return report['failed'] == 0

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
