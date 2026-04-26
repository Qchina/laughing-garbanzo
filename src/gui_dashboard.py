#!/usr/bin/env python3
"""High-interaction, premium-feel desktop UI for software metrics."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from typing import List

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


TXT = {
    "app_title": "软件度量工作台 Pro",
    "hero_title": "软件度量自动化分析",
    "hero_subtitle": "交互增强版：实时日志、阶段进度、输入校验、可取消任务、快捷查看结果",
    "card_inputs": "步骤 1：输入配置",
    "card_files": "步骤 2：图文件输入（可选）",
    "card_logs": "步骤 3：执行与日志",
    "label_source": "Java 项目目录",
    "label_report": "已有度量 JSON（可选）",
    "label_design": "设计输入 JSON（可选）",
    "label_output": "输出目录",
    "label_team": "团队人数",
    "label_rate": "小时成本",
    "btn_browse": "浏览",
    "btn_add": "添加文件",
    "btn_clear": "清空列表",
    "btn_generate": "开始生成",
    "btn_open_html": "打开 HTML",
    "btn_open_output": "打开输出目录",
    "btn_cancel": "取消任务",
    "btn_toggle_log": "折叠日志",
    "btn_copy_cmd": "复制命令",
    "status_ready": "就绪：请补全输入后开始",
    "status_running": "运行中：正在执行分析...",
    "status_success": "成功：报告已生成",
    "status_failed": "失败：执行过程中出现错误",
    "status_cancelled": "已取消：任务中止",
    "status_missing": "输入不完整：请检查必填项",
    "stage_prepare": "阶段 1/4：校验输入参数",
    "stage_run": "阶段 2/4：执行分析任务",
    "stage_parse": "阶段 3/4：整理报告产物",
    "stage_done": "阶段 4/4：完成",
    "progress_idle": "待执行",
    "progress_running": "执行中",
    "progress_done": "已完成",
    "mode_json": "模式：使用已有度量 JSON",
    "mode_direct": "模式：直接分析 + 可视化",
    "run_cmd": "执行命令：",
    "done_json": "输出 JSON：{path}",
    "done_html": "输出 HTML：{path}",
    "err_missing_title": "缺少输入",
    "err_missing_msg": "请先选择 Java 项目目录，或提供已有度量 JSON 文件。",
    "err_failed_title": "生成失败",
    "err_failed_msg": "请查看实时日志，定位错误原因。",
    "ok_title": "生成成功",
    "ok_msg": "报告已生成，是否立即打开 HTML？",
    "cancel_title": "取消任务",
    "cancel_msg": "已请求取消，正在停止任务...",
    "warn_html_title": "未找到 HTML",
    "warn_html_msg": "尚未生成 HTML 报告，请先执行生成。",
    "dlg_source": "选择 Java 项目目录",
    "dlg_report": "选择已有度量 JSON",
    "dlg_design": "选择设计输入 JSON",
    "dlg_output": "选择输出目录",
    "dlg_diagrams": "选择 UML/类图等文件",
    "card_history": "最近任务（最多 5 条）",
    "history_col_time": "时间",
    "history_col_mode": "模式",
    "history_col_status": "结果",
    "btn_apply_history": "填充配置",
    "btn_rerun_history": "重新运行",
    "btn_open_history": "打开结果",
    "history_empty": "暂无历史任务",
    "history_loaded": "已加载历史配置，可直接执行。",
    "history_none_title": "未选择记录",
    "history_none_msg": "请先在历史列表中选择一条任务记录。",
    "history_open_warn": "该记录没有可打开的结果文件。",
    "status_open_html": "已打开 HTML 报告",
    "status_open_output": "已打开输出目录",
    "status_copy_cmd": "已复制命令到剪贴板",
}


class MetricsGuiApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(TXT["app_title"])
        self.root.geometry("1240x880")
        self.root.minsize(1100, 780)

        self.repo_root = Path(__file__).resolve().parent.parent
        self.presentation_script = self.repo_root / "src" / "presentation_tool.py"
        self.python_exec = sys.executable
        self.history_file = self.repo_root / ".gui_history.json"

        self.diagram_files: List[Path] = []
        self.history_records: List[dict[str, object]] = []
        self.last_html: Path | None = None
        self.last_output_dir: Path = self.repo_root
        self.last_cmd = ""
        self.active_output_json: Path | None = None
        self.active_output_html: Path | None = None
        self.active_output_dir: Path = self.repo_root
        self.active_mode_label = "未开始"
        self.active_cancel_requested = False
        self.run_finalized = False
        self.logs_collapsed = False

        self.source_var = tk.StringVar()
        self.report_var = tk.StringVar()
        self.design_json_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(self.repo_root))
        self.persons_var = tk.StringVar(value="4")
        self.rate_var = tk.StringVar(value="120")
        self.status_var = tk.StringVar(value=TXT["status_ready"])
        self.phase_var = tk.StringVar(value=TXT["progress_idle"])
        self.progress_var = tk.DoubleVar(value=0.0)

        self.is_running = False
        self.process: subprocess.Popen[str] | None = None
        self.worker_thread: threading.Thread | None = None
        self.queue: Queue[tuple[str, object]] = Queue()

        self._setup_style()
        self._build_ui()
        self._load_history()
        self._bind_live_validation()

    def _setup_style(self) -> None:
        self.root.configure(bg="#edf2fb")
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Card.TLabelframe", background="#ffffff", borderwidth=1, relief="solid")
        style.configure("Card.TLabelframe.Label", background="#ffffff", foreground="#1d3557", font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("Field.TLabel", background="#ffffff", foreground="#2f4b66", font=("Microsoft YaHei UI", 9))
        style.configure("Hint.TLabel", background="#ffffff", foreground="#6b7c93", font=("Microsoft YaHei UI", 8))
        style.configure("Primary.TButton", padding=(15, 8), font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("Secondary.TButton", padding=(11, 7), font=("Microsoft YaHei UI", 9))
        style.configure("Ghost.TButton", padding=(11, 7), font=("Microsoft YaHei UI", 9))
        style.map("Primary.TButton", background=[("active", "#1849b8"), ("!active", "#2563eb")], foreground=[("!disabled", "#ffffff")])
        style.map("Secondary.TButton", background=[("active", "#dbeafe"), ("!active", "#eaf2ff")], foreground=[("!disabled", "#1f3b63")])
        style.map("Ghost.TButton", background=[("active", "#fef3c7"), ("!active", "#fff7dc")], foreground=[("!disabled", "#7c5d09")])

    def _build_ui(self) -> None:
        outer = tk.Frame(self.root, bg="#edf2fb")
        outer.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)
        self._build_header(outer)
        self._build_kpis(outer)

        body = tk.Frame(outer, bg="#edf2fb")
        body.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        left = tk.Frame(body, bg="#edf2fb")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right = tk.Frame(body, bg="#edf2fb", width=420)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(12, 0))
        right.pack_propagate(False)
        right_top = tk.Frame(right, bg="#edf2fb")
        right_top.pack(fill=tk.BOTH, expand=True)
        right_bottom = tk.Frame(right, bg="#edf2fb", height=230)
        right_bottom.pack(fill=tk.X, pady=(10, 0))
        right_bottom.pack_propagate(False)

        self._build_input_card(left)
        self._build_files_card(left)
        self._build_actions(left)
        self._build_log_card(right_top)
        self._build_history_card(right_bottom)
        self._build_status_bar(outer)

    def _build_header(self, parent: tk.Widget) -> None:
        header = tk.Frame(parent, bg="#174ea6", height=104)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text=TXT["hero_title"], bg="#174ea6", fg="#ffffff", font=("Microsoft YaHei UI", 18, "bold")).pack(anchor="w", padx=16, pady=(14, 0))
        tk.Label(header, text=TXT["hero_subtitle"], bg="#174ea6", fg="#dbeafe", font=("Microsoft YaHei UI", 10)).pack(anchor="w", padx=16, pady=(4, 0))

    def _build_kpis(self, parent: tk.Widget) -> None:
        strip = tk.Frame(parent, bg="#edf2fb")
        strip.pack(fill=tk.X, pady=(10, 0))
        self.ind_mode = self._kpi(strip, "运行模式", "未开始")
        self.ind_stage = self._kpi(strip, "当前阶段", TXT["progress_idle"])
        self.ind_input = self._kpi(strip, "输入状态", "待检查")
        self.ind_task = self._kpi(strip, "任务状态", "空闲")

    def _kpi(self, parent: tk.Widget, title: str, value: str) -> tk.Label:
        card = tk.Frame(parent, bg="#ffffff", bd=1, relief="solid")
        padx = 0 if not parent.winfo_children() else 8
        card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(padx, 0))
        tk.Label(card, text=title, bg="#ffffff", fg="#60748a", font=("Microsoft YaHei UI", 8)).pack(anchor="w", padx=10, pady=(6, 0))
        label = tk.Label(card, text=value, bg="#ffffff", fg="#1d3557", font=("Microsoft YaHei UI", 10, "bold"))
        label.pack(anchor="w", padx=10, pady=(2, 7))
        return label

    def _build_input_card(self, parent: tk.Widget) -> None:
        card = ttk.LabelFrame(parent, text=TXT["card_inputs"], style="Card.TLabelframe")
        card.pack(fill=tk.X, pady=(0, 10))
        card.columnconfigure(1, weight=1)
        self._add_path(card, 0, TXT["label_source"], self.source_var, self._pick_source)
        self._add_path(card, 1, TXT["label_report"], self.report_var, self._pick_report_json)
        self._add_path(card, 2, TXT["label_design"], self.design_json_var, self._pick_design_json)
        self._add_path(card, 3, TXT["label_output"], self.output_var, self._pick_output)

        row = tk.Frame(card, bg="#ffffff")
        row.grid(row=4, column=0, columnspan=3, sticky="ew", padx=10, pady=(4, 8))
        ttk.Label(row, text=TXT["label_team"], style="Field.TLabel").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.persons_var, width=8).pack(side=tk.LEFT, padx=(8, 18))
        ttk.Label(row, text=TXT["label_rate"], style="Field.TLabel").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.rate_var, width=10).pack(side=tk.LEFT, padx=(8, 0))

        self.hint = ttk.Label(card, text="提示：项目目录与已有 JSON 二选一即可开始。", style="Hint.TLabel")
        self.hint.grid(row=5, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 8))

    def _add_path(self, card: ttk.LabelFrame, row: int, label: str, var: tk.StringVar, handler) -> None:
        ttk.Label(card, text=label, style="Field.TLabel").grid(row=row, column=0, sticky="w", padx=(10, 8), pady=8)
        ttk.Entry(card, textvariable=var).grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=8)
        ttk.Button(card, text=TXT["btn_browse"], style="Secondary.TButton", command=handler).grid(row=row, column=2, sticky="e", padx=(0, 10), pady=8)

    def _build_files_card(self, parent: tk.Widget) -> None:
        card = ttk.LabelFrame(parent, text=TXT["card_files"], style="Card.TLabelframe")
        card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        bar = tk.Frame(card, bg="#ffffff")
        bar.pack(fill=tk.X, padx=10, pady=(8, 6))
        ttk.Button(bar, text=TXT["btn_add"], style="Secondary.TButton", command=self._add_files).pack(side=tk.LEFT)
        ttk.Button(bar, text=TXT["btn_clear"], style="Ghost.TButton", command=self._clear_files).pack(side=tk.LEFT, padx=(8, 0))

        frame = tk.Frame(card, bg="#ffffff")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.file_list = tk.Listbox(
            frame,
            bg="#f7fbff",
            fg="#234",
            selectbackground="#cfe3ff",
            selectforeground="#1d3557",
            borderwidth=1,
            relief="solid",
            font=("Consolas", 9),
        )
        self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.file_list.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_list.configure(yscrollcommand=sb.set)

    def _build_actions(self, parent: tk.Widget) -> None:
        row = tk.Frame(parent, bg="#edf2fb")
        row.pack(fill=tk.X)
        self.btn_generate = ttk.Button(row, text=TXT["btn_generate"], style="Primary.TButton", command=self._run_generation)
        self.btn_generate.pack(side=tk.LEFT)
        self.btn_cancel = ttk.Button(row, text=TXT["btn_cancel"], style="Ghost.TButton", command=self._cancel_generation, state=tk.DISABLED)
        self.btn_cancel.pack(side=tk.LEFT, padx=(8, 0))
        self.btn_open_html = ttk.Button(row, text=TXT["btn_open_html"], style="Secondary.TButton", command=self._open_html, state=tk.DISABLED)
        self.btn_open_html.pack(side=tk.LEFT, padx=(8, 0))
        self.btn_open_out = ttk.Button(row, text=TXT["btn_open_output"], style="Secondary.TButton", command=self._open_output, state=tk.DISABLED)
        self.btn_open_out.pack(side=tk.LEFT, padx=(8, 0))
        self.btn_copy_cmd = ttk.Button(row, text=TXT["btn_copy_cmd"], style="Secondary.TButton", command=self._copy_last_cmd)
        self.btn_copy_cmd.pack(side=tk.LEFT, padx=(8, 0))

        p = tk.Frame(parent, bg="#edf2fb")
        p.pack(fill=tk.X, pady=(8, 0))
        self.progress = ttk.Progressbar(p, orient="horizontal", mode="determinate", maximum=100, variable=self.progress_var)
        self.progress.pack(fill=tk.X)

    def _build_log_card(self, parent: tk.Widget) -> None:
        self.log_card = ttk.LabelFrame(parent, text=TXT["card_logs"], style="Card.TLabelframe")
        self.log_card.pack(fill=tk.BOTH, expand=True)

        toolbar = tk.Frame(self.log_card, bg="#ffffff")
        toolbar.pack(fill=tk.X, padx=8, pady=(8, 0))
        self.btn_toggle_log = ttk.Button(toolbar, text=TXT["btn_toggle_log"], style="Secondary.TButton", command=self._toggle_logs)
        self.btn_toggle_log.pack(side=tk.LEFT)

        self.log_text = ScrolledText(
            self.log_card,
            font=("Consolas", 9),
            bg="#f8fbff",
            fg="#1f3550",
            insertbackground="#1f3550",
            borderwidth=0,
            padx=10,
            pady=8,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.log_text.tag_configure("ERROR", foreground="#b91c1c")
        self.log_text.tag_configure("WARN", foreground="#9a6700")
        self.log_text.tag_configure("INFO", foreground="#1d4ed8")

    def _build_status_bar(self, parent: tk.Widget) -> None:
        bar = tk.Frame(parent, bg="#dbeafe", height=36)
        bar.pack(fill=tk.X, pady=(10, 0))
        bar.pack_propagate(False)
        tk.Label(bar, textvariable=self.status_var, bg="#dbeafe", fg="#1e3a5f", font=("Microsoft YaHei UI", 9), anchor="w", padx=10).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(bar, textvariable=self.phase_var, bg="#dbeafe", fg="#1e40af", font=("Microsoft YaHei UI", 9, "bold"), anchor="e", padx=10).pack(side=tk.RIGHT)

    def _build_history_card(self, parent: tk.Widget) -> None:
        card = ttk.LabelFrame(parent, text=TXT["card_history"], style="Card.TLabelframe")
        card.pack(fill=tk.BOTH, expand=True)

        table_frame = tk.Frame(card, bg="#ffffff")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 6))
        self.history_table = ttk.Treeview(
            table_frame,
            columns=("time", "mode", "status"),
            show="headings",
            height=5,
        )
        self.history_table.heading("time", text=TXT["history_col_time"])
        self.history_table.heading("mode", text=TXT["history_col_mode"])
        self.history_table.heading("status", text=TXT["history_col_status"])
        self.history_table.column("time", width=132, anchor="w")
        self.history_table.column("mode", width=150, anchor="w")
        self.history_table.column("status", width=80, anchor="center")
        self.history_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.history_table.bind("<Double-1>", lambda _e: self._apply_history_selection())
        sb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.history_table.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_table.configure(yscrollcommand=sb.set)

        actions = tk.Frame(card, bg="#ffffff")
        actions.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(actions, text=TXT["btn_apply_history"], style="Secondary.TButton", command=self._apply_history_selection).pack(side=tk.LEFT)
        ttk.Button(actions, text=TXT["btn_rerun_history"], style="Secondary.TButton", command=self._rerun_history_selection).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(actions, text=TXT["btn_open_history"], style="Ghost.TButton", command=self._open_history_selection).pack(side=tk.LEFT, padx=(8, 0))

    def _bind_live_validation(self) -> None:
        for var in (self.source_var, self.report_var, self.output_var, self.design_json_var):
            var.trace_add("write", lambda *_: self._validate_inputs())
        self._validate_inputs()

    def _validate_inputs(self) -> None:
        source_ok = bool(self.source_var.get().strip())
        report_ok = bool(self.report_var.get().strip())
        output_ok = bool(self.output_var.get().strip())
        valid = output_ok and (source_ok or report_ok)
        if valid:
            self.ind_input.config(text="可执行", fg="#15803d")
            self.hint.config(text="输入校验通过：可直接开始生成。")
        else:
            self.ind_input.config(text="待补全", fg="#b45309")
            self.hint.config(text="请补全：输出目录 +（项目目录 或 JSON）")
        if not self.is_running:
            self.btn_generate.config(state=(tk.NORMAL if valid else tk.DISABLED))

    def _log(self, msg: str) -> None:
        upper = msg.upper()
        tag = None
        if "ERROR" in upper or "FAILED" in upper:
            tag = "ERROR"
        elif "WARN" in upper:
            tag = "WARN"
        elif "阶段" in msg or "模式：" in msg or "执行命令" in msg:
            tag = "INFO"
        self.log_text.insert(tk.END, msg + "\n", tag)
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def _pick_source(self) -> None:
        path = filedialog.askdirectory(title=TXT["dlg_source"])
        if path:
            self.source_var.set(path)

    def _pick_report_json(self) -> None:
        path = filedialog.askopenfilename(title=TXT["dlg_report"], filetypes=[("JSON", "*.json"), ("All Files", "*.*")])
        if path:
            self.report_var.set(path)

    def _pick_design_json(self) -> None:
        path = filedialog.askopenfilename(title=TXT["dlg_design"], filetypes=[("JSON", "*.json"), ("All Files", "*.*")])
        if path:
            self.design_json_var.set(path)

    def _pick_output(self) -> None:
        path = filedialog.askdirectory(title=TXT["dlg_output"])
        if path:
            self.output_var.set(path)

    def _add_files(self) -> None:
        files = filedialog.askopenfilenames(
            title=TXT["dlg_diagrams"],
            filetypes=[("图文件", "*.uml *.puml *.json *.xml *.txt *.png *.jpg *.jpeg"), ("所有文件", "*.*")],
        )
        if not files:
            return
        for file in files:
            p = Path(file)
            if p not in self.diagram_files:
                self.diagram_files.append(p)
                self.file_list.insert(tk.END, str(p))
        self.status_var.set(f"已导入文件 {len(self.diagram_files)} 个")

    def _clear_files(self) -> None:
        self.diagram_files.clear()
        self.file_list.delete(0, tk.END)
        self.status_var.set("已清空图文件列表")

    def _load_history(self) -> None:
        if not self.history_file.exists():
            self.history_records = []
            self._refresh_history_table()
            return
        try:
            data = json.loads(self.history_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self.history_records = [item for item in data if isinstance(item, dict)][:5]
            else:
                self.history_records = []
        except Exception:
            self.history_records = []
        self._refresh_history_table()

    def _save_history(self) -> None:
        self.history_file.write_text(
            json.dumps(self.history_records[:5], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _refresh_history_table(self) -> None:
        for item in self.history_table.get_children():
            self.history_table.delete(item)
        if not self.history_records:
            self.history_table.insert("", tk.END, values=(TXT["history_empty"], "-", "-"))
            return
        for index, record in enumerate(self.history_records):
            self.history_table.insert(
                "",
                tk.END,
                iid=str(index),
                values=(
                    str(record.get("timestamp", "-")),
                    str(record.get("mode", "-")),
                    str(record.get("status_text", "-")),
                ),
            )

    def _selected_history(self) -> dict[str, object] | None:
        selected = self.history_table.selection()
        if not selected:
            messagebox.showwarning(TXT["history_none_title"], TXT["history_none_msg"])
            return None
        row_id = selected[0]
        if not row_id.isdigit():
            messagebox.showwarning(TXT["history_none_title"], TXT["history_none_msg"])
            return None
        index = int(row_id)
        if index < 0 or index >= len(self.history_records):
            messagebox.showwarning(TXT["history_none_title"], TXT["history_none_msg"])
            return None
        return self.history_records[index]

    def _apply_history_selection(self) -> None:
        record = self._selected_history()
        if not record:
            return
        self.source_var.set(str(record.get("source", "")))
        self.report_var.set(str(record.get("report_json", "")))
        self.design_json_var.set(str(record.get("design_json", "")))
        self.output_var.set(str(record.get("output_dir", self.repo_root)))
        self.persons_var.set(str(record.get("persons", "4")))
        self.rate_var.set(str(record.get("hourly_rate", "120")))

        files = record.get("diagram_files", [])
        self.diagram_files.clear()
        self.file_list.delete(0, tk.END)
        if isinstance(files, list):
            for raw in files:
                p = Path(str(raw))
                self.diagram_files.append(p)
                self.file_list.insert(tk.END, str(p))
        self.status_var.set(TXT["history_loaded"])

    def _rerun_history_selection(self) -> None:
        self._apply_history_selection()
        if self.is_running:
            return
        self._run_generation()

    def _open_history_selection(self) -> None:
        record = self._selected_history()
        if not record:
            return
        html_path = Path(str(record.get("output_html", "")))
        output_dir = Path(str(record.get("output_dir", "")))
        if html_path.exists():
            webbrowser.open(html_path.resolve().as_uri())
            self.status_var.set(TXT["status_open_html"])
            return
        if output_dir.exists():
            webbrowser.open(output_dir.resolve().as_uri())
            self.status_var.set(TXT["status_open_output"])
            return
        messagebox.showwarning(TXT["warn_html_title"], TXT["history_open_warn"])

    def _push_history(self, status: str) -> None:
        status_text = {"success": "成功", "failed": "失败", "cancelled": "取消"}.get(status, "未知")
        record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "mode": self.active_mode_label,
            "status": status,
            "status_text": status_text,
            "source": self.source_var.get().strip(),
            "report_json": self.report_var.get().strip(),
            "design_json": self.design_json_var.get().strip(),
            "output_dir": str(self.active_output_dir),
            "output_json": str(self.active_output_json) if self.active_output_json else "",
            "output_html": str(self.active_output_html) if self.active_output_html else "",
            "persons": self.persons_var.get().strip() or "4",
            "hourly_rate": self.rate_var.get().strip() or "120",
            "diagram_files": [str(item) for item in self.diagram_files],
            "command": self.last_cmd,
        }
        self.history_records.insert(0, record)
        self.history_records = self.history_records[:5]
        self._save_history()
        self._refresh_history_table()

    def _finalize_run(self, status: str, done_payload: tuple[str, str, str] | None = None) -> None:
        if self.run_finalized:
            return
        self.run_finalized = True
        if status == "success" and done_payload:
            output_json, output_html, output_dir = done_payload
            self.last_html = Path(output_html)
            self.last_output_dir = Path(output_dir)
            self.btn_open_html.config(state=tk.NORMAL)
            self.btn_open_out.config(state=tk.NORMAL)
            self._log(TXT["done_json"].format(path=output_json))
            self._log(TXT["done_html"].format(path=output_html))
            self.status_var.set(TXT["status_success"])
            self.phase_var.set(TXT["progress_done"])
            self.progress_var.set(100)
            self._set_running(False)
            self._push_history("success")
            if messagebox.askyesno(TXT["ok_title"], TXT["ok_msg"]):
                self._open_html()
            return
        if status == "failed":
            self.status_var.set(TXT["status_failed"])
            self.phase_var.set(TXT["progress_idle"])
            self._set_running(False)
            self._push_history("failed")
            messagebox.showerror(TXT["err_failed_title"], TXT["err_failed_msg"])
            return
        self.status_var.set(TXT["status_cancelled"])
        self.phase_var.set(TXT["progress_idle"])
        self.progress_var.set(0)
        self._set_running(False)
        self._push_history("cancelled")

    def _build_design_json_from_files(self, output_dir: Path) -> Path | None:
        if self.design_json_var.get().strip():
            return Path(self.design_json_var.get().strip())
        if not self.diagram_files:
            return None
        payload = {"class_diagrams": [], "use_cases": [], "flow_charts": []}
        for f in self.diagram_files:
            lower = f.name.lower()
            stem = f.stem
            if "usecase" in lower or "use_case" in lower or "use-case" in lower:
                payload["use_cases"].append({"name": stem, "source": str(f)})
            elif "flow" in lower or "activity" in lower or "sequence" in lower:
                payload["flow_charts"].append({"name": stem, "source": str(f), "nodes": 0, "edges": 0})
            else:
                payload["class_diagrams"].append({"name": stem, "source": str(f), "attributes": [], "methods": []})
        out = output_dir / "_generated_design_input.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return out

    def _set_running(self, running: bool) -> None:
        self.is_running = running
        self.btn_cancel.config(state=(tk.NORMAL if running else tk.DISABLED))
        self.ind_task.config(text=("运行中" if running else "空闲"), fg=("#1d4ed8" if running else "#1d3557"))
        self._validate_inputs()

    def _enqueue(self, kind: str, payload: object) -> None:
        self.queue.put((kind, payload))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "log":
                    self._log(str(payload))
                elif kind == "status":
                    self.status_var.set(str(payload))
                elif kind == "phase":
                    self.phase_var.set(str(payload))
                    self.ind_stage.config(text=str(payload), fg="#1d4ed8")
                elif kind == "progress":
                    self.progress_var.set(float(payload))
                elif kind == "done_ok":
                    self._finalize_run("success", payload)  # type: ignore[arg-type]
                elif kind == "done_fail":
                    self._finalize_run("failed")
                elif kind == "done_cancel":
                    self._finalize_run("cancelled")
        except Empty:
            pass
        finally:
            if self.is_running:
                self.root.after(120, self._poll_queue)

    def _run_generation(self) -> None:
        if self.is_running:
            return
        report_json = self.report_var.get().strip()
        source_dir = self.source_var.get().strip()
        output_dir = Path(self.output_var.get().strip() or ".").resolve()
        if not report_json and not source_dir:
            self.status_var.set(TXT["status_missing"])
            messagebox.showerror(TXT["err_missing_title"], TXT["err_missing_msg"])
            return
        output_dir.mkdir(parents=True, exist_ok=True)
        output_json = output_dir / "metrics_report_visual.json"
        output_html = output_dir / "metrics_dashboard.html"

        self.log_text.delete("1.0", tk.END)
        self.last_html = None
        self.btn_open_html.config(state=tk.DISABLED)
        self.btn_open_out.config(state=tk.DISABLED)
        self._set_running(True)
        self.status_var.set(TXT["status_running"])
        self.phase_var.set(TXT["progress_running"])
        self.progress_var.set(6)
        self.active_cancel_requested = False
        self.run_finalized = False
        self.active_output_json = output_json
        self.active_output_html = output_html
        self.active_output_dir = output_dir
        self.active_mode_label = "JSON 模式" if report_json else "直连分析"

        cmd = [self.python_exec, str(self.presentation_script)]
        self._enqueue("phase", TXT["stage_prepare"])
        self._enqueue("progress", 14)

        if report_json:
            cmd.extend(["--input-json", report_json])
            self.ind_mode.config(text="JSON 模式", fg="#1d4ed8")
            self._enqueue("log", TXT["mode_json"])
        else:
            design_path = self._build_design_json_from_files(output_dir)
            cmd.extend(["--source", source_dir])
            if design_path:
                cmd.extend(["--design", str(design_path)])
            cmd.extend(["--persons", self.persons_var.get().strip() or "4"])
            cmd.extend(["--hourly-rate", self.rate_var.get().strip() or "120"])
            self.ind_mode.config(text="直连分析", fg="#1d4ed8")
            self._enqueue("log", TXT["mode_direct"])

        cmd.extend(["--json-output", str(output_json), "--html-output", str(output_html)])
        self.last_cmd = " ".join(cmd)
        self._enqueue("log", TXT["run_cmd"])
        self._enqueue("log", self.last_cmd)

        def worker() -> None:
            self._enqueue("phase", TXT["stage_run"])
            self._enqueue("progress", 35)
            try:
                self.process = subprocess.Popen(
                    cmd,
                    cwd=str(self.repo_root),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                if self.process.stdout:
                    for line in self.process.stdout:
                        self._enqueue("log", line.rstrip())
                rc = self.process.wait()
                self.process = None
                if rc != 0:
                    if self.active_cancel_requested:
                        self._enqueue("done_cancel", None)
                    elif self.is_running:
                        self._enqueue("done_fail", None)
                    else:
                        self._enqueue("done_cancel", None)
                    return
                self._enqueue("phase", TXT["stage_parse"])
                self._enqueue("progress", 82)
                self._enqueue("phase", TXT["stage_done"])
                self._enqueue("progress", 96)
                self._enqueue("done_ok", (str(output_json), str(output_html), str(output_dir)))
            except Exception as exc:
                self._enqueue("log", f"ERROR: {exc}")
                self._enqueue("done_fail", None)

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()
        self.root.after(100, self._poll_queue)

    def _cancel_generation(self) -> None:
        if not self.is_running:
            return
        messagebox.showinfo(TXT["cancel_title"], TXT["cancel_msg"])
        self.active_cancel_requested = True
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except Exception:
                pass
        self._enqueue("done_cancel", None)

    def _open_html(self) -> None:
        if not self.last_html or not self.last_html.exists():
            messagebox.showwarning(TXT["warn_html_title"], TXT["warn_html_msg"])
            return
        webbrowser.open(self.last_html.resolve().as_uri())
        self.status_var.set(TXT["status_open_html"])

    def _open_output(self) -> None:
        webbrowser.open(self.last_output_dir.resolve().as_uri())
        self.status_var.set(TXT["status_open_output"])

    def _copy_last_cmd(self) -> None:
        if not self.last_cmd:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.last_cmd)
        self.status_var.set(TXT["status_copy_cmd"])

    def _toggle_logs(self) -> None:
        if self.logs_collapsed:
            self.log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
            self.btn_toggle_log.config(text=TXT["btn_toggle_log"])
            self.logs_collapsed = False
        else:
            self.log_text.pack_forget()
            self.btn_toggle_log.config(text="展开日志")
            self.logs_collapsed = True


def main() -> None:
    root = tk.Tk()
    MetricsGuiApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
