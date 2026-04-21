#!/usr/bin/env python3
"""软件度量可视化窗口工具。

功能：
- 选择 Java 项目目录
- 导入 UML/类图/用例图/流程图 或 设计 JSON
- 可选导入已有度量 JSON 报告
- 一键生成 JSON + HTML 可视化报告
"""

from __future__ import annotations

import json
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import List

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext


class MetricsGuiApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("软件度量可视化工具")
        self.root.geometry("980x740")

        self.repo_root = Path(__file__).resolve().parent.parent
        self.presentation_script = self.repo_root / "src" / "presentation_tool.py"
        self.python_exec = sys.executable

        self.diagram_files: List[Path] = []
        self.last_html: Path | None = None

        self.source_var = tk.StringVar()
        self.report_var = tk.StringVar()
        self.design_json_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(self.repo_root))
        self.persons_var = tk.StringVar(value="4")
        self.rate_var = tk.StringVar(value="120")

        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 6}

        top = tk.Frame(self.root)
        top.pack(fill=tk.X, **pad)

        tk.Label(top, text="Java 项目目录").grid(row=0, column=0, sticky="w")
        tk.Entry(top, textvariable=self.source_var, width=85).grid(row=0, column=1, sticky="we")
        tk.Button(top, text="浏览", command=self._pick_source).grid(row=0, column=2, sticky="e")

        tk.Label(top, text="已有度量 JSON（可选）").grid(row=1, column=0, sticky="w")
        tk.Entry(top, textvariable=self.report_var, width=85).grid(row=1, column=1, sticky="we")
        tk.Button(top, text="浏览", command=self._pick_report_json).grid(row=1, column=2, sticky="e")

        tk.Label(top, text="设计输入 JSON（可选）").grid(row=2, column=0, sticky="w")
        tk.Entry(top, textvariable=self.design_json_var, width=85).grid(row=2, column=1, sticky="we")
        tk.Button(top, text="浏览", command=self._pick_design_json).grid(row=2, column=2, sticky="e")

        tk.Label(top, text="输出目录").grid(row=3, column=0, sticky="w")
        tk.Entry(top, textvariable=self.output_var, width=85).grid(row=3, column=1, sticky="we")
        tk.Button(top, text="浏览", command=self._pick_output).grid(row=3, column=2, sticky="e")

        params = tk.Frame(self.root)
        params.pack(fill=tk.X, **pad)
        tk.Label(params, text="团队人数").pack(side=tk.LEFT)
        tk.Entry(params, textvariable=self.persons_var, width=8).pack(side=tk.LEFT, padx=8)
        tk.Label(params, text="小时成本").pack(side=tk.LEFT)
        tk.Entry(params, textvariable=self.rate_var, width=10).pack(side=tk.LEFT, padx=8)

        diagram_section = tk.LabelFrame(self.root, text="导入 UML / 类图 / 用例图 / 流程图文件（可选）")
        diagram_section.pack(fill=tk.BOTH, expand=False, **pad)

        action_bar = tk.Frame(diagram_section)
        action_bar.pack(fill=tk.X, padx=6, pady=5)
        tk.Button(action_bar, text="添加文件", command=self._add_diagrams).pack(side=tk.LEFT)
        tk.Button(action_bar, text="清空列表", command=self._clear_diagrams).pack(side=tk.LEFT, padx=8)

        self.diagram_list = tk.Listbox(diagram_section, height=7)
        self.diagram_list.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        controls = tk.Frame(self.root)
        controls.pack(fill=tk.X, **pad)
        tk.Button(controls, text="生成可视化报告", command=self._run_generation, bg="#0a9396", fg="white").pack(side=tk.LEFT)
        self.open_button = tk.Button(controls, text="打开 HTML 页面", command=self._open_html, state=tk.DISABLED)
        self.open_button.pack(side=tk.LEFT, padx=8)

        logs = tk.LabelFrame(self.root, text="运行日志")
        logs.pack(fill=tk.BOTH, expand=True, **pad)
        self.log_text = scrolledtext.ScrolledText(logs, height=16)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _pick_source(self) -> None:
        path = filedialog.askdirectory(title="选择 Java 项目目录")
        if path:
            self.source_var.set(path)

    def _pick_report_json(self) -> None:
        path = filedialog.askopenfilename(
            title="选择已有度量 JSON",
            filetypes=[("JSON", "*.json"), ("All Files", "*.*")],
        )
        if path:
            self.report_var.set(path)

    def _pick_design_json(self) -> None:
        path = filedialog.askopenfilename(
            title="选择设计输入 JSON",
            filetypes=[("JSON", "*.json"), ("All Files", "*.*")],
        )
        if path:
            self.design_json_var.set(path)

    def _pick_output(self) -> None:
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_var.set(path)

    def _add_diagrams(self) -> None:
        files = filedialog.askopenfilenames(
            title="选择 UML/类图等文件",
            filetypes=[
                ("图文件", "*.uml *.puml *.json *.xml *.txt *.png *.jpg *.jpeg"),
                ("所有文件", "*.*"),
            ],
        )
        if not files:
            return
        for file in files:
            p = Path(file)
            if p not in self.diagram_files:
                self.diagram_files.append(p)
                self.diagram_list.insert(tk.END, str(p))

    def _clear_diagrams(self) -> None:
        self.diagram_files.clear()
        self.diagram_list.delete(0, tk.END)

    def _log(self, message: str) -> None:
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def _build_design_json_from_files(self, output_dir: Path) -> Path | None:
        if self.design_json_var.get().strip():
            return Path(self.design_json_var.get().strip())
        if not self.diagram_files:
            return None

        design_payload = {"class_diagrams": [], "use_cases": [], "flow_charts": []}
        for f in self.diagram_files:
            lower_name = f.name.lower()
            stem = f.stem
            if "usecase" in lower_name or "use_case" in lower_name or "use-case" in lower_name:
                design_payload["use_cases"].append({"name": stem, "source": str(f)})
            elif "flow" in lower_name or "activity" in lower_name or "sequence" in lower_name:
                design_payload["flow_charts"].append({"name": stem, "source": str(f), "nodes": 0, "edges": 0})
            else:
                design_payload["class_diagrams"].append({"name": stem, "source": str(f), "attributes": [], "methods": []})

        generated = output_dir / "_generated_design_input.json"
        generated.write_text(json.dumps(design_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return generated

    def _run_generation(self) -> None:
        self.log_text.delete("1.0", tk.END)
        self.last_html = None
        self.open_button.config(state=tk.DISABLED)

        output_dir = Path(self.output_var.get().strip() or ".").resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_json = output_dir / "metrics_report_visual.json"
        output_html = output_dir / "metrics_dashboard.html"

        report_json = self.report_var.get().strip()
        source_dir = self.source_var.get().strip()

        cmd = [self.python_exec, str(self.presentation_script)]
        if report_json:
            cmd.extend(["--input-json", report_json])
            self._log("模式：使用已有度量 JSON")
        else:
            if not source_dir:
                messagebox.showerror("缺少输入", "请先选择 Java 项目目录或已有度量 JSON 文件。")
                return
            design_path = self._build_design_json_from_files(output_dir)
            cmd.extend(["--source", source_dir])
            if design_path:
                cmd.extend(["--design", str(design_path)])
            cmd.extend(["--persons", self.persons_var.get().strip() or "4"])
            cmd.extend(["--hourly-rate", self.rate_var.get().strip() or "120"])
            self._log("模式：直接分析 + 可视化")

        cmd.extend(["--json-output", str(output_json), "--html-output", str(output_html)])

        self._log("执行命令：")
        self._log(" ".join(cmd))

        proc = subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
        )
        if proc.stdout:
            self._log(proc.stdout.strip())
        if proc.stderr:
            self._log(proc.stderr.strip())

        if proc.returncode != 0:
            messagebox.showerror("生成失败", "请查看运行日志了解详情。")
            return

        self.last_html = output_html
        self.open_button.config(state=tk.NORMAL)
        self._log(f"完成。JSON：{output_json}")
        self._log(f"完成。HTML：{output_html}")
        messagebox.showinfo("成功", f"可视化页面已生成：\n{output_html}")

    def _open_html(self) -> None:
        if not self.last_html or not self.last_html.exists():
            messagebox.showwarning("未找到文件", "未找到 HTML 可视化页面。")
            return
        webbrowser.open(self.last_html.resolve().as_uri())


def main() -> None:
    root = tk.Tk()
    app = MetricsGuiApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
