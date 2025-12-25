# src/gui.py
"""
艾宾浩斯AI单词本 - 智能测验系统
完整修复版：解决所有问题
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import datetime
import json
import os
import sys
import random

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

from .data_manager import WordDataManager, SM2Scheduler
from .sm2_algorithm import Word, AIEvaluator
class VocabularyTutorGUI:
    """AI单词辅导系统图形界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("艾宾浩斯AI单词本 - 智能测验系统")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f5f5f5")
        
        # 核心组件
        self.data_manager = WordDataManager()
        self.scheduler = SM2Scheduler()
        self.ai_evaluator = AIEvaluator()
        
        # 学习状态
        self.learning_mode = False
        self.current_learning_words = []
        self.current_index = 0
        self.current_mode = "meaning"
        self.correct_count = 0
        self.total_learned = 0
        
        # 学习流程控制
        self.allow_retry = False
        self.current_attempt = 0
        self.max_attempts = 2
        self.wrong_words_this_round = []
        self.is_review_phase = False
        
        # 学习数据
        self.today_new_words = []  # 今日新单词
        self.today_review_words = []  # 今日复习单词
        self.fixed_new_words = []  # 固定的新单词
        self.fixed_review_words = []  # 固定的复习单词
        
        # 显示控制
        self.show_list = True
        self.display_mode = "all"
        self.high_forget_words = []
        
        # 学习计划设置
        self.daily_new_words = 20
        self.daily_review_words = 50
        self.study_order = "顺序"
        
        # 初始化界面
        self.setup_ui()
        self.load_study_settings()
        self.refresh_word_categories()
        self.refresh_display()
        self.update_statistics()
    
    def setup_ui(self):
        """设置用户界面"""
        # 1. 顶部标题栏
        title_frame = ttk.Frame(self.root, padding="15")
        title_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(
            title_frame,
            text="艾宾浩斯AI单词本 - 智能测验系统",
            font=("微软雅黑", 20, "bold"),
            foreground="#2c3e50"
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            title_frame,
            text="基于AI自动评分的个性化英语单词记忆助手",
            font=("微软雅黑", 12),
            foreground="#7f8c8d"
        )
        subtitle_label.pack()
        
        # 2. 学习计划设置区域
        plan_frame = ttk.LabelFrame(self.root, text="📅 学习计划设置", padding="10")
        plan_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        # 每日新单词数
        ttk.Label(plan_frame, text="每日新单词数:", font=("微软雅黑", 10)).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.new_words_var = tk.IntVar(value=20)
        new_words_spin = ttk.Spinbox(plan_frame, from_=5, to=100, width=8, 
                                     textvariable=self.new_words_var)
        new_words_spin.grid(row=0, column=1, padx=5, pady=5)
        
        # 每日复习单词数
        ttk.Label(plan_frame, text="每日复习单词数:", font=("微软雅黑", 10)).grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.review_words_var = tk.IntVar(value=50)
        review_words_spin = ttk.Spinbox(plan_frame, from_=10, to=200, width=8,
                                       textvariable=self.review_words_var)
        review_words_spin.grid(row=0, column=3, padx=5, pady=5)
        
        # 学习顺序
        ttk.Label(plan_frame, text="学习顺序:", font=("微软雅黑", 10)).grid(row=0, column=4, sticky="w", padx=5, pady=5)
        self.order_var = tk.StringVar(value="顺序")
        order_combo = ttk.Combobox(plan_frame, textvariable=self.order_var, 
                                  values=["顺序", "随机", "按记忆强度", "按复习次数", "按遗忘风险"], 
                                  width=12, state="readonly")
        order_combo.grid(row=0, column=5, padx=5, pady=5)
        
        # 保存设置按钮
        ttk.Button(plan_frame, text="保存设置", 
                  command=self.save_study_settings, width=10).grid(row=0, column=6, padx=5, pady=5)
        
        # 3. 功能按钮栏
        self.button_frame = ttk.Frame(self.root, padding="10")
        self.button_frame.pack(fill=tk.X)
        
        # 功能按钮
        ttk.Button(self.button_frame, text="📥 导入Excel单词", 
                  command=self.import_excel, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="➕ 添加新单词", 
                  command=self.add_word_dialog, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="📚 开始今日学习", 
                  command=self.start_learning, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="📊 学习报告", 
                  command=self.show_progress_report, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="🔄 刷新列表", 
                  command=self.refresh_display, width=15).pack(side=tk.LEFT, padx=5)
        
        # 单词列表显示控制
        control_frame = ttk.Frame(self.button_frame)
        control_frame.pack(side=tk.LEFT, padx=20)
        
        # 显示/隐藏列表按钮
        self.show_list_btn = ttk.Button(
            control_frame,
            text="隐藏列表",
            command=self.toggle_word_list,
            width=10
        )
        self.show_list_btn.pack(side=tk.LEFT, padx=2)
        
        # 显示模式选择
        ttk.Label(control_frame, text="显示:", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(10, 2))
        self.display_mode_var = tk.StringVar(value="all")
        display_combo = ttk.Combobox(control_frame, textvariable=self.display_mode_var, 
                                    values=["所有单词", "今日新单词", "今日复习单词", "高遗忘风险"], 
                                    width=12, state="readonly")
        display_combo.pack(side=tk.LEFT, padx=2)
        display_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_display())
        
        # 4. 主内容区域
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # 左栏：单词列表
        self.list_frame = ttk.LabelFrame(self.main_frame, text="📖 单词列表", padding="10")
        self.list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 单词列表表格
        columns = ('单词', '释义', '状态', '复习情况')
        self.word_tree = ttk.Treeview(self.list_frame, columns=columns, show='headings', height=25)
        
        # 设置列宽
        self.word_tree.heading('单词', text='单词')
        self.word_tree.heading('释义', text='释义')
        self.word_tree.heading('状态', text='状态')
        self.word_tree.heading('复习情况', text='复习情况')
        
        self.word_tree.column('单词', width=120)
        self.word_tree.column('释义', width=150)
        self.word_tree.column('状态', width=80)
        self.word_tree.column('复习情况', width=200)
        
        # 滚动条
        tree_scroll = ttk.Scrollbar(self.list_frame, orient=tk.VERTICAL, command=self.word_tree.yview)
        self.word_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.word_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 右栏：学习面板
        right_frame = ttk.LabelFrame(self.main_frame, text="🎯 智能学习面板", padding="15")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 学习模式选择
        mode_frame = ttk.LabelFrame(right_frame, text="🎮 学习模式选择", padding="10")
        mode_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.mode_var = tk.StringVar(value="meaning")
        
        ttk.Radiobutton(mode_frame, text="释义模式 (看英文->输中文)", 
                       variable=self.mode_var, value="meaning").pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(mode_frame, text="拼写模式 (看中文->输英文)", 
                       variable=self.mode_var, value="spelling").pack(anchor=tk.W, padx=5, pady=2)
        
        # 当前单词显示
        self.current_word_label = ttk.Label(
            right_frame,
            text="点击'开始今日学习'按钮开始",
            font=("微软雅黑", 18, "bold"),
            foreground="#34495e"
        )
        self.current_word_label.pack(pady=20)
        
        # 答案输入区域
        self.answer_entry = ttk.Entry(
            right_frame,
            font=("微软雅黑", 14),
            width=30
        )
        self.answer_entry.pack(pady=10)
        self.answer_entry.bind("<Return>", lambda e: self.submit_answer())
        
        ttk.Button(
            right_frame,
            text="提交答案 (或按Enter键)",
            command=self.submit_answer,
            width=20
        ).pack(pady=5)
        
        # 反馈显示
        self.feedback_label = ttk.Label(
            right_frame,
            text="",
            font=("微软雅黑", 12),
            foreground="#2c3e50"
        )
        self.feedback_label.pack(pady=10)
        
        # 学习统计区
        stats_frame = ttk.LabelFrame(right_frame, text="📈 学习统计", padding="10")
        stats_frame.pack(fill=tk.X, pady=20)
        
        self.stats_text = tk.Text(
            stats_frame,
            height=8,
            font=("微软雅黑", 10),
            bg="#ecf0f1",
            relief=tk.FLAT
        )
        self.stats_text.pack(fill=tk.X)
        
        # 5. 底部状态栏
        self.status_bar = ttk.Frame(self.root, relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(
            self.status_bar,
            text="就绪 | 等待操作",
            font=("微软雅黑", 9)
        )
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # 绑定事件
        self.word_tree.bind("<Double-1>", self.on_word_double_click)
    
    def toggle_word_list(self):
        """切换单词列表显示/隐藏"""
        self.show_list = not self.show_list
        
        if self.show_list:
            self.show_list_btn.config(text="隐藏列表")
            self.list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        else:
            self.show_list_btn.config(text="显示列表")
            self.list_frame.pack_forget()
    
    def refresh_word_categories(self):
        """刷新单词分类数据"""
        self.today_new_words = self.data_manager.get_today_new_words()
        self.today_review_words = self.data_manager.get_today_review_words()
        self.high_forget_words = self.data_manager.get_high_forget_risk_words(0.6)
    
    def load_study_settings(self):
        """加载学习设置"""
        settings_file = "data/study_settings.json"
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                self.new_words_var.set(settings.get("每日新单词数", 20))
                self.review_words_var.set(settings.get("每日复习单词数", 50))
                self.order_var.set(settings.get("学习顺序", "顺序"))
            except Exception as e:
                print(f"加载设置失败: {e}")
    
    def save_study_settings(self):
        """保存学习设置"""
        settings = {
            "每日新单词数": self.new_words_var.get(),
            "每日复习单词数": self.review_words_var.get(),
            "学习顺序": self.order_var.get()
        }
        
        settings_file = "data/study_settings.json"
        os.makedirs(os.path.dirname(settings_file), exist_ok=True)
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        
        messagebox.showinfo("设置保存", "学习设置已保存！")
        self.update_status("学习设置已更新")
    
    def sort_words_by_order(self, words, order_mode):
        """按照指定的顺序对单词列表进行排序"""
        if order_mode == "顺序":
            return sorted(words, key=lambda w: w.text.lower())
        elif order_mode == "随机":
            random.shuffle(words)
            return words
        elif order_mode == "按记忆强度":
            return sorted(words, key=lambda w: w.ease_factor, reverse=True)
        elif order_mode == "按复习次数":
            return sorted(words, key=lambda w: w.repetitions, reverse=True)
        elif order_mode == "按遗忘风险":
            return sorted(words, key=lambda w: w.forget_risk, reverse=True)
        else:
            return words
    
    def refresh_display(self):
        """刷新单词列表显示"""
        # 清空现有项
        for item in self.word_tree.get_children():
            self.word_tree.delete(item)
        
        # 根据显示模式获取单词
        display_mode = self.display_mode_var.get()
        
        if display_mode == "所有单词":
            words = self.data_manager.load_words()
            display_text = "所有单词"
            
        elif display_mode == "今日新单词":
            # 如果今日新单词已固定，显示固定列表
            if hasattr(self, 'fixed_new_words') and self.fixed_new_words:
                words = self.fixed_new_words
                display_text = "今日新单词 (已固定)"
            else:
                # 否则显示当前的新单词
                self.refresh_word_categories()
                words = self.today_new_words
                display_text = "今日新单词"
            
        elif display_mode == "今日复习单词":
            # 如果今日复习单词已固定，显示固定列表
            if hasattr(self, 'fixed_review_words') and self.fixed_review_words:
                words = self.fixed_review_words
                display_text = "今日复习单词 (已固定)"
            else:
                # 否则显示当前的复习单词
                self.refresh_word_categories()
                words = self.today_review_words
                display_text = "今日复习单词"
            
        else:  # 高遗忘风险
            self.refresh_word_categories()
            words = self.high_forget_words
            display_text = "高遗忘风险单词"
        
        # 对单词进行排序
        order_mode = self.order_var.get()
        words = self.sort_words_by_order(words, order_mode)
        
        # 显示单词列表
        for word in words:
            # 确定状态
            if word.repetitions == 0:
                status = "新单词"
            elif word.repetitions >= 3 and word.ease_factor >= 2.5:
                status = "已掌握"
            else:
                status = "学习中"
            
            # 获取复习情况
            if word.repetitions == 0:
                review_info = "未学习"
            else:
                time_since = self.data_manager.format_time_since_last_review(word)
                if time_since == "未复习":
                    # 如果已经复习过但显示未复习，显示复习次数
                    review_info = f"复习{word.repetitions}次"
                else:
                    review_info = f"复习{word.repetitions}次 | 距上次: {time_since}"
            
            self.word_tree.insert('', tk.END, values=(
                word.text,
                word.meaning[:20] + "..." if len(word.meaning) > 20 else word.meaning,
                status,
                review_info
            ))
        
        self.update_status(f"已加载 {len(words)} 个单词 ({display_text})")
    
    def update_statistics(self):
        """更新学习统计信息 - 修复版"""
        try:
            stats = self.data_manager.get_learning_statistics()
            
            # 累计学习单词 = 已学习单词数（复习次数>0）
            learned_words = stats.get('reviewed_words', 0)
            
            # 计算今日已学习的单词
            today_learned = 0
            all_words = self.data_manager.load_words()
            for word in all_words:
                if word.repetitions > 0 and word.last_reviewed and word.last_reviewed == datetime.date.today():
                    today_learned += 1
            
            # 确保今日已学习单词不会超过总学习单词
            if today_learned > learned_words:
                today_learned = learned_words
            
            # 创建统计显示文本
            stats_display = f"""📊 学习统计概览
{'='*40}
📚 累计学习单词: {learned_words} 个
📅 今日已学习: {today_learned} 个
📅 今日待复习: {stats['due_today']} 个
⚠️  高遗忘风险: {stats['forget_risk_words']} 个

🎯 掌握情况:
  ✅ 已掌握: {stats['mastered']} 个
  📖 学习中: {stats['learning']} 个
  🆕 新单词: {stats['new']} 个

📈 平均记忆强度: {stats['avg_ease_factor']}
🔄 累计复习次数: {stats['total_reviews']} 次
{'='*40}
"""
            
            # 清空并更新统计文本
            self.stats_text.config(state=tk.NORMAL)
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, stats_display)
            self.stats_text.config(state=tk.DISABLED)
            
            # 更新状态栏
            self.update_status(f"统计已更新: 累计学习{learned_words}个单词, 今日已学{today_learned}个")
            
        except Exception as e:
            print(f"更新统计失败: {e}")
            # 即使出错，也尝试显示一些基本信息
            self.stats_text.config(state=tk.NORMAL)
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, "📊 学习统计\n暂时无法获取统计数据，请稍后再试。")
            self.stats_text.config(state=tk.DISABLED)
    
    def update_status(self, message):
        """更新状态栏"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.status_label.config(text=f"[{timestamp}] {message}")
        self.root.update_idletasks()
    
    def import_excel(self):
        """导入Excel文件"""
        file_path = filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=[
                ("Excel文件", "*.xlsx *.xls"),
                ("所有文件", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            self.update_status("正在导入Excel文件...")
            result = self.data_manager.import_from_excel(file_path)
            
            if result["success"]:
                messagebox.showinfo("导入成功", f"{result['message']}")
                self.refresh_word_categories()
                self.refresh_display()
                self.update_statistics()
                self.update_status(f"已导入 {result['new_count']} 个新单词")
            else:
                messagebox.showerror("导入失败", result["message"])
                
        except Exception as e:
            messagebox.showerror("导入失败", f"导入过程中出错:\n{str(e)}")
    
    def add_word_dialog(self):
        """添加新单词对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("添加新单词")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # 表单内容
        ttk.Label(dialog, text="英文单词:", font=("微软雅黑", 11)).pack(pady=(20, 5))
        word_entry = ttk.Entry(dialog, font=("微软雅黑", 11), width=30)
        word_entry.pack(pady=5)
        
        ttk.Label(dialog, text="中文释义:", font=("微软雅黑", 11)).pack(pady=(10, 5))
        meaning_entry = ttk.Entry(dialog, font=("微软雅黑", 11), width=30)
        meaning_entry.pack(pady=5)
        
        ttk.Label(dialog, text="例句 (可选):", font=("微软雅黑", 11)).pack(pady=(10, 5))
        example_entry = ttk.Entry(dialog, font=("微软雅黑", 11), width=30)
        example_entry.pack(pady=5)
        
        def save_word():
            word_text = word_entry.get().strip()
            meaning_text = meaning_entry.get().strip()
            example_text = example_entry.get().strip()
            
            if not word_text or not meaning_text:
                messagebox.showwarning("输入错误", "英文单词和中文释义不能为空！")
                return
            
            new_word = Word(text=word_text, meaning=meaning_text, example=example_text)
            self.data_manager.save_word(new_word)
            
            messagebox.showinfo("添加成功", f"单词 '{word_text}' 已添加到学习系统！")
            self.refresh_word_categories()
            self.refresh_display()
            self.update_statistics()
            dialog.destroy()
        
        # 按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="保存", command=save_word, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
        
        word_entry.focus()
    
    def start_learning(self):
        """开始今日学习"""
        # 获取用户设置
        daily_new = self.new_words_var.get()
        daily_review = self.review_words_var.get()
        order_mode = self.order_var.get()
        
        # 1. 确定今日新单词（固定不变）
        all_new_words = self.data_manager.get_today_new_words()
        new_words = self.sort_words_by_order(all_new_words, order_mode)
        
        if len(new_words) > daily_new:
            new_words = new_words[:daily_new]
        
        # 保存固定新单词列表
        self.fixed_new_words = new_words.copy()
        
        # 2. 确定今日复习单词（固定不变）
        high_risk_words = self.data_manager.get_high_forget_risk_words(0.6)
        today_review = self.data_manager.get_today_review_words()
        
        # 合并去重
        review_words_dict = {}
        for word in high_risk_words:
            if word.text not in review_words_dict:
                review_words_dict[word.text] = word
        
        for word in today_review:
            if word.text not in review_words_dict:
                review_words_dict[word.text] = word
        
        # 转换为列表并按遗忘风险排序
        all_review_words = list(review_words_dict.values())
        all_review_words = sorted(all_review_words, key=lambda w: w.forget_risk, reverse=True)
        
        # 限制数量
        if len(all_review_words) > daily_review:
            all_review_words = all_review_words[:daily_review]
        
        # 保存固定复习单词列表
        self.fixed_review_words = all_review_words.copy()
        
        # 3. 设置学习任务
        self.current_learning_words = all_review_words + new_words
        self.wrong_words_this_round = []
        
        if not self.current_learning_words:
            messagebox.showinfo("今日学习", "🎉 今天没有需要学习的单词。")
            return
        
        # 重置学习状态
        self.learning_mode = True
        self.current_index = 0
        self.correct_count = 0
        self.current_attempt = 0
        self.allow_retry = False
        self.is_review_phase = False
        
        # 显示学习计划
        plan_info = (f"📅 今日学习计划\n"
                    f"复习单词: {len(all_review_words)}个\n"
                    f"新学单词: {len(new_words)}个\n"
                    f"总计: {len(self.current_learning_words)}个单词")
        
        self.update_status(plan_info)
        messagebox.showinfo("学习开始", plan_info)
        
        # 开始学习
        self.show_current_word()
    
    def show_current_word(self):
        """显示当前正在学习的单词"""
        if self.current_index >= len(self.current_learning_words):
            # 检查是否有错误的单词需要重新学习
            if self.wrong_words_this_round:
                messagebox.showinfo("重新学习", f"有{len(self.wrong_words_this_round)}个单词需要重新学习")
                self.current_learning_words = self.wrong_words_this_round.copy()
                self.current_index = 0
                self.wrong_words_this_round = []
                self.update_status(f"重新学习 {len(self.current_learning_words)} 个错误单词")
                self.show_current_word()
                return
            
            # 学习完成
            self.learning_mode = False
            self.current_word_label.config(text="🎉 今日学习完成！")
            self.feedback_label.config(text="")
            self.answer_entry.delete(0, tk.END)
            self.answer_entry.config(state=tk.DISABLED)
            
            # 计算准确率
            total_words = len(self.current_learning_words)
            if total_words > 0:
                accuracy = (self.correct_count / total_words) * 100
            else:
                accuracy = 0
            
            # 确保准确率合理
            if accuracy > 100:
                accuracy = 100
            
            # 最后更新一次统计
            self.update_statistics()
            self.refresh_display()
            
            messagebox.showinfo(
                "学习完成", 
                f"🎉 今日学习完成！\n"
                f"总学习单词: {total_words} 个\n"
                f"正确单词: {self.correct_count} 个\n"
                f"准确率: {accuracy:.1f}%\n"
                f"已自动更新学习进度"
            )
            
            self.update_status("今日学习完成")
            return
        
        # 检查是否进入复习阶段
        if (self.current_index == 0 and 
            len(self.fixed_review_words) > 0 and
            self.current_learning_words[0] in self.fixed_review_words):
            
            response = messagebox.askyesno(
                "进入复习阶段", 
                f"现在开始复习{len(self.fixed_review_words)}个单词。\n"
                f"建议使用拼写模式测试单词记忆，是否切换到拼写模式？"
            )
            if response:
                self.mode_var.set("spelling")
                self.update_status("已切换到拼写模式")
        
        # 显示当前单词
        current_word = self.current_learning_words[self.current_index]
        mode = self.mode_var.get()
        
        if mode == "meaning":
            self.current_word_label.config(text=f"🔤 请输入 '{current_word.text}' 的中文释义：")
        else:
            self.current_word_label.config(text=f"📖 请输入 '{current_word.meaning}' 的英文单词：")
        
        # 清空输入框
        self.answer_entry.delete(0, tk.END)
        self.answer_entry.config(state=tk.NORMAL)
        self.feedback_label.config(text="")
        
        # 重置重试状态
        self.current_attempt = 0
        self.allow_retry = False
        
        # 聚焦到输入框
        self.answer_entry.focus()
        
        # 更新状态栏
        progress = f"{self.current_index + 1}/{len(self.current_learning_words)}"
        word_type = "复习" if current_word in self.fixed_review_words else "新学"
        self.update_status(f"正在{word_type}单词 ({progress})")
    
    def submit_answer(self):
        """提交用户输入的答案 - 修复清空输入和错误处理逻辑"""
        if not self.learning_mode or self.current_index >= len(self.current_learning_words):
            return
        
        user_input = self.answer_entry.get().strip()
        if not user_input:
            messagebox.showwarning("输入为空", "请输入答案！")
            return
        
        current_word = self.current_learning_words[self.current_index]
        mode = self.mode_var.get()
        
        # 评估答案
        if mode == "meaning":
            quality = self.ai_evaluator.evaluate_meaning(user_input, current_word.meaning, current_word.text)
        else:
            quality = self.ai_evaluator.evaluate_spelling(user_input, current_word.text, current_word.meaning)
        
        # 增加尝试次数
        self.current_attempt += 1
        
        # 清空输入框 - 无论对错都清空
        self.answer_entry.delete(0, tk.END)
        
        # 处理答案
        if quality >= 4:
            # 答案正确
            feedback = f"✅ 正确！ (AI评分: {quality}/5)"
            feedback_color = "#27ae60"
            self.correct_count += 1
            
            # 更新记忆状态
            updated_word = self.scheduler.update_review_schedule(current_word, quality)
            self.data_manager.save_word(updated_word)
            
            # 实时更新统计和显示
            self.update_statistics()
            self.refresh_display()
            
            # 延迟后显示下一个单词
            self.answer_entry.config(state=tk.DISABLED)
            self.feedback_label.config(text=feedback, foreground=feedback_color)
            self.root.after(1500, self.next_word)
            
        elif self.current_attempt < self.max_attempts and not self.allow_retry:
            # 第一次错误，允许重试
            feedback = f"⚠️ 接近，请再试一次 (AI评分: {quality}/5)"
            feedback_color = "#f39c12"
            self.allow_retry = True
            
            # 显示反馈，但不切换到下一个单词
            self.feedback_label.config(text=feedback, foreground=feedback_color)
            
            # 重新激活输入框，让用户重新输入
            self.answer_entry.config(state=tk.NORMAL)
            self.answer_entry.focus()
            
        else:
            # 第二次错误或质量太低
            if quality >= 2:
                feedback = f"❌ 错误，已尝试2次 (AI评分: {quality}/5)"
            else:
                feedback = f"❌ 错误 (AI评分: {quality}/5)"
            feedback_color = "#e74c3c"
            
            # 添加到错误单词列表
            if current_word not in self.wrong_words_this_round:
                self.wrong_words_this_round.append(current_word)
            
            # 更新记忆状态（即使错误也要记录，但质量较低）
            updated_word = self.scheduler.update_review_schedule(current_word, max(0, quality-1))
            self.data_manager.save_word(updated_word)
            
            # 实时更新统计和显示
            self.update_statistics()
            self.refresh_display()
            
            # 延迟后显示下一个单词
            self.answer_entry.config(state=tk.DISABLED)
            self.feedback_label.config(text=feedback, foreground=feedback_color)
            self.root.after(1500, self.next_word)
    
    def next_word(self):
        """切换到下一个单词"""
        self.current_index += 1
        self.show_current_word()
    
    def show_progress_report(self):
        """显示学习进度报告"""
        report_window = tk.Toplevel(self.root)
        report_window.title("学习进度报告")
        report_window.geometry("900x700")
        report_window.transient(self.root)
        
        # 获取数据
        words = self.data_manager.load_words()
        stats = self.data_manager.get_learning_statistics()
        
        if not words:
            ttk.Label(report_window, text="暂无学习数据", font=("微软雅黑", 14)).pack(pady=50)
            return
        
        # 创建Matplotlib图表
        fig = Figure(figsize=(10, 8), dpi=100)
        
        # 创建4个子图
        ax1 = fig.add_subplot(2, 2, 1)
        ax2 = fig.add_subplot(2, 2, 2)
        ax3 = fig.add_subplot(2, 2, 3)
        ax4 = fig.add_subplot(2, 2, 4)
        
        fig.suptitle(f"学习报告 - {datetime.date.today()}", fontsize=16, fontweight='bold')
        
        # 1. 掌握情况饼图
        if stats['total_words'] > 0:
            labels = ['已掌握', '学习中', '新单词']
            sizes = [stats['mastered'], stats['learning'], stats['new']]
            colors = ['#4CAF50', '#FFC107', '#2196F3']
            
            # 过滤掉大小为0的部分
            filtered_data = [(label, size, color) for label, size, color in zip(labels, sizes, colors) if size > 0]
            
            if filtered_data:
                filtered_labels, filtered_sizes, filtered_colors = zip(*filtered_data)
                ax1.pie(filtered_sizes, labels=filtered_labels, colors=filtered_colors, 
                       autopct='%1.1f%%', startangle=90)
        else:
            ax1.text(0.5, 0.5, '暂无学习数据', ha='center', va='center', fontsize=12)
        
        ax1.set_title('单词掌握情况分布')
        
        # 2. 记忆强度分布
        ease_factors = [w.ease_factor for w in words if w.repetitions > 0]
        if ease_factors:
            ax2.hist(ease_factors, bins=10, color='skyblue', edgecolor='black', alpha=0.7)
            ax2.set_xlabel('记忆强度 (易度因子)')
            ax2.set_ylabel('单词数量')
            ax2.set_title('记忆强度分布')
            ax2.axvline(x=2.5, color='red', linestyle='--', label='默认强度 (2.5)')
            ax2.legend()
        else:
            ax2.text(0.5, 0.5, '暂无记忆强度数据', ha='center', va='center', fontsize=12)
            ax2.set_title('记忆强度分布')
        
        # 3. 复习次数分布
        if words:
            repetitions_counts = [w.repetitions for w in words]
            max_rep = max(repetitions_counts) if repetitions_counts else 5
            ax3.hist(repetitions_counts, bins=range(0, min(max_rep, 20)+2), 
                    color='lightgreen', edgecolor='black', alpha=0.7)
            ax3.set_xlabel('复习次数')
            ax3.set_ylabel('单词数量')
            ax3.set_title('复习次数分布')
        
        # 4. 文本统计信息
        learned_words = stats.get('reviewed_words', 0)
        
        # 计算今日已学习的单词
        today_learned = 0
        for word in words:
            if word.repetitions > 0 and word.last_reviewed and word.last_reviewed == datetime.date.today():
                today_learned += 1
        
        stats_text = f"""
学习统计摘要
{'='*40}
📊 累计学习单词: {learned_words} 个
📅 今日已学习: {today_learned} 个
📅 今日待复习: {stats['due_today']} 个
⚠️  高遗忘风险: {stats['forget_risk_words']} 个

掌握情况:
  ✅ 已掌握: {stats['mastered']} 个
  📖 学习中: {stats['learning']} 个
  🆕 新单词: {stats['new']} 个

📈 平均记忆强度: {stats['avg_ease_factor']}
🔄 累计复习次数: {stats['total_reviews']} 次
{'='*40}
📅 报告生成时间: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        ax4.axis('off')
        ax4.text(0, 0.95, stats_text, fontsize=10, fontfamily='Microsoft YaHei',
                verticalalignment='top', linespacing=1.8)
        
        fig.tight_layout()
        
        # 嵌入到Tkinter窗口
        canvas = FigureCanvasTkAgg(fig, master=report_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 添加导出按钮
        button_frame = ttk.Frame(report_window)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        def export_report():
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG图片", "*.png"), ("所有文件", "*.*")],
                initialfile=f"学习报告_{datetime.date.today()}.png"
            )
            if file_path:
                try:
                    fig.savefig(file_path, dpi=300, bbox_inches='tight')
                    messagebox.showinfo("导出成功", f"报告已保存到:\n{file_path}")
                except Exception as e:
                    messagebox.showerror("导出失败", f"保存失败:\n{str(e)}")
        
        ttk.Button(button_frame, text="📤 导出报告", command=export_report).pack(side=tk.LEFT)
    
    def on_word_double_click(self, event):
        """双击单词显示详细信息"""
        selection = self.word_tree.selection()
        if selection:
            item = self.word_tree.item(selection[0])
            values = item['values']
            word_text = values[0]
            
            words = self.data_manager.load_words()
            for word in words:
                if word.text == word_text:
                    time_since = self.data_manager.format_time_since_last_review(word)
                    details = f"""
单词详细信息
{'='*30}
英文: {word.text}
中文: {word.meaning}
例句: {word.example if word.example else '无'}

学习状态:
  复习次数: {word.repetitions} 次
  当前间隔: {word.interval} 天
  记忆强度: {word.ease_factor:.2f}
  下次复习: {word.next_review}
  距上次复习: {time_since}
  遗忘风险: {word.forget_risk:.1%}
  创建时间: {word.created_at}
"""
                    messagebox.showinfo(f"单词详情 - {word.text}", details)
                    break


def main():
    """主函数"""
    root = tk.Tk()
    app = VocabularyTutorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()