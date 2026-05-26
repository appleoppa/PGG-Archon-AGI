#!/usr/bin/env python3
"""
run_init.py - 盘古初始化入口

执行完整的初始化流程
启动七大模块
"""

import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[Pangu-Init] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """主初始化流程"""
    print("=" * 50)
    print("  盘古 Pangu 初始化启动")
    print("=" * 50)
    print()
    
    try:
        # 1. LLM钩子初始化
        logger.info("1/6 - 初始化LLM钩子...")
        from engine.llm_hook import LLMInitHook
        LLMInitHook().first_time_init()
        print("   ✅ LLM钩子就绪")
        
        # 2. 记忆恢复
        logger.info("2/6 - 恢复记忆上下文...")
        from memory.memory_hook import LLMMemoryHook
        LLMMemoryHook().auto_restore_all()
        print("   ✅ 记忆恢复完成")
        
        # 3. 技能自检
        logger.info("3/6 - 检查技能库...")
        from self_evolve.auto_skill_fetch import AutoSkillFetch
        AutoSkillFetch().auto_fill_missing_skills()
        print("   ✅ 技能检查完成")
        
        # 4. 代码规范
        logger.info("4/6 - 构建代码规范基线...")
        from code_standard.standard_hook import LLMStandardHook
        LLMStandardHook().first_build_self_standard()
        print("   ✅ 代码规范就绪")
        
        # 5. 情感系统
        logger.info("5/6 - 初始化情感系统...")
        from emotion.emotion_hook import EmotionHook
        EmotionHook().init_emotion_system()
        print("   ✅ 情感系统就绪")
        
        # 6. 自动智能体
        logger.info("6/6 - 启动自动智能体...")
        from auto_agent.agent_hook import AutoAgentHook
        result = AutoAgentHook().run_auto_agent()
        print(f"   ✅ 自动智能体运行: {result.get('status', 'unknown')}")
        
        print()
        print("=" * 50)
        print("  🎯 盘古七大模块全部就绪")
        print("=" * 50)
        print()
        print("系统状态:")
        print(f"  - ΔG总值: {result.get('inspect', {}).get('delta_g_total', 'N/A')}")
        print(f"  - 系统状态: {result.get('inspect', {}).get('system_state', 'N/A')}")
        print(f"  - 需要自愈: {'是' if result.get('inspect', {}).get('need_heal') else '否'}")
        print()
        
        return True
        
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        print()
        print(f"❌ 初始化失败: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
