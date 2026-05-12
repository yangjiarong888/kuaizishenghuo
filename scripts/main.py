"""
主程序入口 - 增强版
"""
import argparse
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commons.logger import setup_logger
from scripts.smoke_test import smoke_test
from testcases.test_login import run_login_tests, test_specific_login_method

logger = setup_logger(__name__)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="筷子生活App自动化测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python scripts/main.py --mode smoke           # 运行冒烟测试
  python scripts/main.py --mode login           # 运行完整登录测试
  python scripts/main.py --mode login --method wechat  # 测试微信登录
  python scripts/main.py --mode quick           # 快速启动测试
  python scripts/main.py --mode all             # 运行所有测试
        """
    )
    
    parser.add_argument("--mode", 
                       choices=["smoke", "login", "quick", "all", "method"], 
                       default="smoke",
                       help="测试模式")
    
    parser.add_argument("--method",
                       choices=["wechat", "google", "qq", "phone"],
                       help="指定登录方式测试")
    
    parser.add_argument("--device",
                       help="设备名称，如: P7T4XC99CYAEYL4H")
    
    parser.add_argument("--log-level",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       default="INFO",
                       help="日志级别")
    
    args = parser.parse_args()
    
    # 创建必要的目录
    os.makedirs("screenshots", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("筷子生活App自动化测试 - 优化版")
    logger.info("=" * 60)
    
    if args.mode == "smoke":
        logger.info("执行冒烟测试...")
        smoke_test()
        
    elif args.mode == "login":
        if args.method:
            logger.info(f"执行 {args.method} 登录测试...")
            test_specific_login_method(args.method)
        else:
            logger.info("执行完整登录测试...")
            run_login_tests()
            
    elif args.mode == "quick":
        from scripts.smoke_test import quick_start_app
        logger.info("快速启动测试...")
        quick_start_app()
        
    elif args.mode == "all":
        logger.info("执行所有测试...")
        smoke_test()
        run_login_tests()
        
    else:
        logger.error(f"不支持的测试模式: {args.mode}")
    
    logger.info("=" * 60)
    logger.info("测试完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()