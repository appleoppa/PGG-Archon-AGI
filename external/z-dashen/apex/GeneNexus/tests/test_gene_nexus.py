"""GeneNexus 测试"""
import sys
sys.path.insert(0, '..')

from gene_nexus import GeneReader, StrategyExtractor, SkillGenerator, ApexV103SkillEvolver


def test_import():
    """测试导入"""
    assert GeneReader is not None
    assert StrategyExtractor is not None
    assert SkillGenerator is not None
    assert ApexV103SkillEvolver is not None
    print("✅ 导入测试通过")


def test_apex_v103():
    """测试APEX V10.3演化器"""
    evolver = ApexV103SkillEvolver()
    result = evolver.evolve_skill_with_apex(
        {"signal_strength": 0.8},
        current_quality=0.7
    )
    assert "evolved_quality" in result
    assert result["evolved_quality"] > 0
    print(f"✅ APEX V10.3测试通过: evolved_quality={result['evolved_quality']:.4f}")


if __name__ == "__main__":
    test_import()
    test_apex_v103()
    print("\n🎉 所有测试通过！")
