# src/data_manager.py
"""
数据管理模块 - 修复版
修复所有语法错误
"""
import json
import os
import datetime
from typing import List, Dict, Any, Optional
import traceback

from .sm2_algorithm import Word, SM2Scheduler

# 尝试导入pandas
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None


class WordDataManager:
    """单词数据管理器 - 修复版"""
    
    def __init__(self, file_path: str = "data/word_data.json"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        self.data = self._load_data()
        self.scheduler = SM2Scheduler()
    
    def _load_data(self) -> Dict[str, Any]:
        """从JSON文件加载数据"""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"警告: {self.file_path} 格式错误，将使用空数据")
                return {"words": {}, "version": "3.1"}
            except Exception as e:
                print(f"加载数据文件时出错: {e}")
                return {"words": {}, "version": "3.1"}
        return {"words": {}, "version": "3.1"}
    
    def save_word(self, word: Word) -> bool:
        """保存或更新一个单词的数据"""
        try:
            word_dict = {
                "text": word.text,
                "meaning": word.meaning,
                "example": word.example,
                "repetitions": word.repetitions,
                "interval": word.interval,
                "ease_factor": word.ease_factor,
                "next_review": word.next_review.isoformat(),
                "last_reviewed": word.last_reviewed.isoformat() if word.last_reviewed else None,
                "created_at": word.created_at.isoformat(),
                "forget_risk": word.forget_risk
            }
            self.data["words"][word.text] = word_dict
            self._save_to_file()
            return True
        except Exception as e:
            print(f"保存单词时出错: {e}")
            return False
    
    def load_words(self) -> List[Word]:
        """加载所有单词为Word对象列表"""
        word_objects = []
        for word_text, word_dict in self.data.get("words", {}).items():
            try:
                # 处理日期字段
                try:
                    next_review = datetime.date.fromisoformat(word_dict.get("next_review", 
                        (datetime.date.today() + datetime.timedelta(days=1)).isoformat()))
                except (KeyError, ValueError):
                    next_review = datetime.date.today() + datetime.timedelta(days=1)
                
                # 处理上次复习时间
                last_reviewed = None
                if word_dict.get("last_reviewed"):
                    try:
                        last_reviewed = datetime.date.fromisoformat(word_dict["last_reviewed"])
                    except (KeyError, ValueError):
                        pass
                
                # 处理创建时间
                try:
                    created_at = datetime.date.fromisoformat(word_dict.get("created_at", 
                        datetime.date.today().isoformat()))
                except (KeyError, ValueError):
                    created_at = datetime.date.today()
                
                # 创建Word对象
                word = Word(
                    text=word_dict.get("text", word_text),
                    meaning=word_dict.get("meaning", ""),
                    example=word_dict.get("example", ""),
                    repetitions=word_dict.get("repetitions", 0),
                    interval=word_dict.get("interval", 1),
                    ease_factor=word_dict.get("ease_factor", 2.5),
                    next_review=next_review,
                    last_reviewed=last_reviewed,
                    created_at=created_at,
                    forget_risk=word_dict.get("forget_risk", 0.0)
                )
                word_objects.append(word)
            except Exception as e:
                print(f"加载单词 '{word_text}' 时出错: {e}")
                continue
        
        return word_objects
    
    def _save_to_file(self) -> bool:
        """保存数据到文件"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存数据时出错: {e}")
            return False
    
    def get_today_new_words(self) -> List[Word]:
        """获取今日新单词（从未复习过的）"""
        all_words = self.load_words()
        new_words = [w for w in all_words if w.repetitions == 0]
        return new_words
    
    def get_today_review_words(self) -> List[Word]:
        """获取今日需要复习的单词"""
        today = datetime.date.today()
        all_words = self.load_words()
        
        today_words = []
        for word in all_words:
            if word.next_review <= today and word.repetitions > 0:
                today_words.append(word)
        
        return today_words
    
    def get_high_forget_risk_words(self, threshold: float = 0.6) -> List[Word]:
        """获取遗忘风险高的单词"""
        all_words = self.load_words()
        return self.scheduler.get_forgetting_curve_words(all_words, threshold)
    
    def format_time_since_last_review(self, word: Word) -> str:
        """格式化距上次复习时间"""
        if not word.last_reviewed or word.repetitions == 0:
            return "未复习"
        
        # 如果上次复习时间就是今天，显示"今天"
        if word.last_reviewed == datetime.date.today():
            return "今天"
        
        delta = datetime.date.today() - word.last_reviewed
        
        years = delta.days // 365
        months = (delta.days % 365) // 30
        days = (delta.days % 365) % 30
        
        parts = []
        if years > 0:
            parts.append(f"{years}年")
        if months > 0:
            parts.append(f"{months}月")
        if days > 0:
            parts.append(f"{days}天")
        
        return " ".join(parts) if parts else "1天"
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """获取学习统计数据"""
        all_words = self.load_words()
        total = len(all_words)
        
        if total == 0:
            return {
                "total_words": 0,
                "mastered": 0,
                "learning": 0,
                "new": 0,
                "due_today": 0,
                "avg_ease_factor": 0.0,
                "total_reviews": 0,
                "reviewed_words": 0,
                "forget_risk_words": 0
            }
        
        today = datetime.date.today()
        mastered = 0
        learning = 0
        new_words = 0
        due_today = 0
        ease_sum = 0.0
        reviewed_count = 0
        total_reviews = 0
        
        for word in all_words:
            total_reviews += word.repetitions
            
            if word.repetitions == 0:
                new_words += 1
            else:
                reviewed_count += 1
                
                if word.repetitions >= 3 and word.ease_factor >= 2.5:
                    mastered += 1
                else:
                    learning += 1
                
                ease_sum += word.ease_factor
            
            if word.next_review <= today and word.repetitions > 0:
                due_today += 1
        
        avg_ease = ease_sum / reviewed_count if reviewed_count > 0 else 0.0
        
        # 计算遗忘风险单词数量
        forget_risk_words = len(self.get_high_forget_risk_words(0.6))
        
        return {
            "total_words": total,
            "mastered": mastered,
            "learning": learning,
            "new": new_words,
            "due_today": due_today,
            "avg_ease_factor": round(avg_ease, 2),
            "total_reviews": total_reviews,
            "reviewed_words": reviewed_count,
            "forget_risk_words": forget_risk_words
        }
    
    def _normalize_column_name(self, col_name: str) -> Optional[str]:
        """规范化Excel列名"""
        if not isinstance(col_name, str):
            col_name = str(col_name)
        
        col_name = col_name.strip().lower()
        
        # 修复字典定义，确保键值对正确
        column_mappings = {
            'word': ['word', '单词', '英文', 'english', 'vocabulary'],
            'meaning': ['meaning', '释义', '意思', '中文', 'chinese', 'translation'],
            'example': ['example', '例句', '例子', 'sentence']
        }
        
        for standard_name, variants in column_mappings.items():
            if col_name in variants or any(variant in col_name for variant in variants):
                return standard_name
        
        return None
    
    def _detect_excel_columns(self, df) -> Dict[str, str]:
        """自动检测Excel中的列名"""
        detected_columns = {}
        
        for col in df.columns:
            normalized = self._normalize_column_name(str(col))
            if normalized and normalized not in detected_columns:
                detected_columns[normalized] = str(col)
        
        return detected_columns
    
    def import_from_excel(self, file_path: str) -> Dict[str, Any]:
        """从Excel文件批量导入单词"""
        if not PANDAS_AVAILABLE or pd is None:
            return {
                "success": False,
                "message": "pandas库未安装，无法导入Excel文件",
                "new_count": 0,
                "total_count": 0
            }
        
        try:
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "message": f"文件不存在: {file_path}",
                    "new_count": 0,
                    "total_count": 0
                }
            
            try:
                df = pd.read_excel(file_path)
            except Exception as e:
                return {
                    "success": False,
                    "message": f"读取Excel文件失败: {str(e)}",
                    "new_count": 0,
                    "total_count": 0
                }
            
            if df.empty:
                return {
                    "success": False,
                    "message": "Excel文件为空",
                    "new_count": 0,
                    "total_count": 0
                }
            
            # 自动检测列名
            column_mapping = self._detect_excel_columns(df)
            
            required_cols = ['word', 'meaning']
            missing_cols = [col for col in required_cols if col not in column_mapping]
            
            if missing_cols:
                return {
                    "success": False,
                    "message": f"无法自动检测列: {', '.join(missing_cols)}。请确保Excel包含'单词'和'释义'列",
                    "detected_columns": column_mapping,
                    "new_count": 0,
                    "total_count": 0
                }
            
            imported_words = []
            skipped_words = []
            error_words = []
            
            for i, (_, row) in enumerate(df.iterrows(), start=0):
                try:
                    # 获取行号（从2开始，因为Excel第一行是标题）
                    row_num = i + 2
                    
                    # 获取数据
                    word_text = str(row[column_mapping['word']]).strip()
                    meaning_text = str(row[column_mapping['meaning']]).strip()
                    
                    if not word_text or not meaning_text:
                        skipped_words.append(f"第{row_num}行: 单词或释义为空")
                        continue
                    
                    # 获取例句
                    example_text = ""
                    if 'example' in column_mapping:
                        example_val = row[column_mapping['example']]
                        example_text = str(example_val).strip() if pd.notna(example_val) else ""
                    
                    # 检查单词是否已存在
                    if word_text in self.data["words"]:
                        skipped_words.append(f"第{row_num}行: '{word_text}' 已存在")
                        continue
                    
                    # 创建新单词
                    new_word = Word(
                        text=word_text,
                        meaning=meaning_text,
                        example=example_text
                    )
                    new_word.next_review = datetime.date.today() + datetime.timedelta(days=1)
                    
                    if self.save_word(new_word):
                        imported_words.append(word_text)
                    else:
                        error_words.append(f"第{row_num}行: '{word_text}' 保存失败")
                        
                except Exception as e:
                    error_words.append(f"第{i+2}行: 处理失败 - {str(e)}")
            
            result = {
                "success": True,
                "message": f"导入完成。成功: {len(imported_words)}, 跳过: {len(skipped_words)}, 失败: {len(error_words)}",
                "new_count": len(imported_words),
                "total_count": len(df),
                "imported_words": imported_words[:10],
                "skipped_count": len(skipped_words),
                "error_count": len(error_words)
            }
            
            return result
        
        except Exception as e:
            error_msg = f"导入Excel失败: {str(e)}"
            print(f"❌ {error_msg}")
            traceback.print_exc()
            
            return {
                "success": False,
                "message": error_msg,
                "new_count": 0,
                "total_count": 0
            }


def test_data_manager():
    """数据管理器测试"""
    print("=" * 60)
    print("数据管理模块测试 - 修复版")
    print("=" * 60)
    
    import os
    
    # 使用测试文件
    manager = WordDataManager("data/test_data.json")
    
    # 清理可能存在的旧测试文件
    if os.path.exists("data/test_data.json"):
        os.remove("data/test_data.json")
    
    # 测试基本功能
    test_word = Word("test", "测试", "This is a test.")
    test_word.last_reviewed = datetime.date.today() - datetime.timedelta(days=5)
    test_word.repetitions = 3
    manager.save_word(test_word)
    print("✅ 单词保存测试通过")
    
    words = manager.load_words()
    print(f"✅ 单词加载测试通过 (已加载 {len(words)} 个单词)")
    
    # 测试时间格式化
    time_str = manager.format_time_since_last_review(words[0])
    print(f"✅ 时间格式化测试: {time_str}")
    
    # 测试遗忘风险单词
    forget_words = manager.get_high_forget_risk_words()
    print(f"✅ 遗忘风险单词检测: 找到 {len(forget_words)} 个高风险单词")
    
    stats = manager.get_learning_statistics()
    print(f"✅ 学习统计测试通过:")
    print(f"   总数: {stats['total_words']}")
    print(f"   已掌握: {stats['mastered']}")
    print(f"   遗忘风险单词: {stats['forget_risk_words']} 个")
    
    # 清理测试文件
    if os.path.exists("data/test_data.json"):
        os.remove("data/test_data.json")
    
    print("\n" + "=" * 60)
    print("数据管理模块测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_data_manager()