# src/sm2_algorithm.py
"""
SM2间隔重复算法模块
"""
import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import random


@dataclass
class Word:
    """单词数据类，记录一个单词的所有记忆状态"""
    text: str                     # 英文单词
    meaning: str                  # 中文释义
    example: str = ""            # 例句（可选）
    repetitions: int = 0          # 复习次数
    interval: int = 1            # 当前复习间隔（天）
    ease_factor: float = 2.5     # 易度因子，默认值2.5
    next_review: datetime.date = field(
        default_factory=lambda: datetime.date.today() + datetime.timedelta(days=1)
    )
    last_reviewed: Optional[datetime.date] = None  # 上次复习时间
    created_at: datetime.date = field(default_factory=datetime.date.today)  # 创建时间
    forget_risk: float = 0.0  # 遗忘风险系数 (0.0-1.0)
    
    def calculate_forget_risk(self) -> float:
        """计算遗忘风险系数"""
        if not self.last_reviewed or self.repetitions == 0:
            return 1.0  # 新单词遗忘风险最高
        
        # 基于艾宾浩斯遗忘曲线计算
        days_since_last_review = (datetime.date.today() - self.last_reviewed).days
        
        if self.repetitions <= 1:
            # 第1次复习后
            if days_since_last_review <= 1:
                return 0.1
            elif days_since_last_review <= 7:
                return 0.3
            else:
                return 0.7
        elif self.repetitions <= 3:
            # 2-3次复习后
            if days_since_last_review <= 7:
                return 0.1
            elif days_since_last_review <= 30:
                return 0.3
            else:
                return 0.5
        else:
            # 4次以上复习后
            if days_since_last_review <= self.interval * 0.5:
                return 0.1
            elif days_since_last_review <= self.interval:
                return 0.3
            elif days_since_last_review <= self.interval * 2:
                return 0.6
            else:
                return 0.9


class SM2Scheduler:
    """SM2间隔重复调度器"""
    
    def __init__(self):
        self.quality_to_ease_change = {
            0: -0.8,  # 完全忘记
            1: -0.5,  # 很难回忆
            2: -0.2,  # 有点困难
            3: 0.0,   # 正确但费劲
            4: 0.1,   # 正确
            5: 0.2,   # 完美回忆
        }
    
    def update_review_schedule(self, word: Word, quality: int) -> Word:
        """
        根据复习质量更新单词的复习计划
        quality: 0-5，表示回忆质量
        """
        # 记录上次复习时间
        word.last_reviewed = datetime.date.today()
        word.repetitions += 1
        
        # 更新易度因子
        word.ease_factor += self.quality_to_ease_change.get(quality, 0.0)
        word.ease_factor = max(1.3, min(2.5, word.ease_factor))  # 保持在合理范围内
        
        # 根据复习次数和质量计算下次复习间隔
        if quality < 3:
            # 回答不正确，重置间隔
            word.interval = 1
            word.repetitions = 0
        else:
            if word.repetitions == 1:
                word.interval = 1
            elif word.repetitions == 2:
                word.interval = 3
            else:
                word.interval = int(word.interval * word.ease_factor)
        
        # 安排下次复习时间
        word.next_review = datetime.date.today() + datetime.timedelta(days=word.interval)
        
        # 重新计算遗忘风险
        word.forget_risk = word.calculate_forget_risk()
        
        return word
    
    def get_forgetting_curve_words(self, words: List[Word], threshold: float = 0.7) -> List[Word]:
        """
        获取遗忘风险高的单词
        threshold: 遗忘风险阈值，默认0.7
        """
        high_risk_words = []
        for word in words:
            if word.repetitions > 0:  # 只考虑已学习过的单词
                word.forget_risk = word.calculate_forget_risk()
                if word.forget_risk >= threshold and word.next_review > datetime.date.today():
                    high_risk_words.append(word)
        
        # 按遗忘风险排序
        high_risk_words.sort(key=lambda w: w.forget_risk, reverse=True)
        return high_risk_words


class AIEvaluator:
    """AI自动评分器"""
    
    def evaluate_meaning(self, user_input: str, correct_meaning: str, word_text: str) -> int:
        """
        评估中文释义准确性
        返回评分 0-5
        """
        # 简单实现：基于字符串相似度
        user_input = user_input.strip().lower()
        correct_meaning = correct_meaning.strip().lower()
        
        if not user_input:
            return 0
        
        # 完全匹配
        if user_input == correct_meaning:
            return 5
        
        # 包含关系
        if user_input in correct_meaning or correct_meaning in user_input:
            return 4
        
        # 长度相似
        len_diff = abs(len(user_input) - len(correct_meaning))
        if len_diff <= 2:
            return 3
        
        # 部分匹配
        common_chars = set(user_input) & set(correct_meaning)
        if len(common_chars) >= 2:
            return 2
        
        return 1
    
    def evaluate_spelling(self, user_input: str, correct_spelling: str, word_meaning: str) -> int:
        """
        评估英文拼写准确性
        返回评分 0-5
        """
        user_input = user_input.strip().lower()
        correct_spelling = correct_spelling.strip().lower()
        
        if not user_input:
            return 0
        
        # 完全匹配
        if user_input == correct_spelling:
            return 5
        
        # 小写/大小写问题
        if user_input.lower() == correct_spelling.lower():
            return 4
        
        # 常见的拼写错误容错
        if len(user_input) == len(correct_spelling):
            # 计算编辑距离
            diff_count = sum(1 for a, b in zip(user_input, correct_spelling) if a != b)
            if diff_count == 1:
                return 3
            elif diff_count == 2:
                return 2
        
        return 1


def test_sm2_algorithm():
    """SM2算法测试"""
    print("=" * 60)
    print("SM2算法模块测试")
    print("=" * 60)
    
    scheduler = SM2Scheduler()
    evaluator = AIEvaluator()
    
    # 创建一个测试单词
    test_word = Word("test", "测试", "This is a test.")
    print(f"创建单词: {test_word.text} -> {test_word.meaning}")
    print(f"初始状态: 复习次数={test_word.repetitions}, 间隔={test_word.interval}天")
    
    # 模拟几次复习
    for i, quality in enumerate([5, 4, 3, 5], 1):
        test_word = scheduler.update_review_schedule(test_word, quality)
        print(f"\n第{i}次复习 (质量={quality}):")
        print(f"  复习次数: {test_word.repetitions}")
        print(f"  间隔: {test_word.interval}天")
        print(f"  下次复习: {test_word.next_review}")
        print(f"  遗忘风险: {test_word.forget_risk:.2f}")
    
    # 测试AI评分
    print("\n" + "=" * 60)
    print("AI评分测试:")
    
    meaning_score = evaluator.evaluate_meaning("测试", "测试", "test")
    print(f"释义评分: '测试' -> {meaning_score}/5")
    
    spelling_score = evaluator.evaluate_spelling("test", "test", "测试")
    print(f"拼写评分: 'test' -> {spelling_score}/5")
    
    print("\n" + "=" * 60)
    print("SM2算法模块测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_sm2_algorithm()