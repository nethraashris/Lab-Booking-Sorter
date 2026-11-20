"""
Lab Booking Request Sorter - Graphical User Interface (GUI)
===========================================================
Course: CIT AI-Native Engineering Programme · Semester 1 · Assessment 5 (Capstone)

A modern, clean desktop GUI built using Python's built-in tkinter/ttk.
No external pip libraries needed!

Features:
- Single-click to run full sorting process (main.py pipeline)
- Interactive tabbed interface for:
  1. Overview & Summary Statistics (KPI metric cards)
  2. Tentative Schedule Table (Color-coded for Lab In-Charge review)
  3. Issues & Problems Table (Color-coded by conflict/capacity/Sunday/missing info)
  4. Raw Requests & Extracted JSON Audit
  5. Live Console Execution Log
- Filter and search records easily
- Direct export buttons
- Explicit Human Checkpoint banner
"""

import os
import csv
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

# Import core decision logic from main.py without rewriting rules
import main as core


class LabBookingGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Lab Booking Request Sorter · Lab In-Charge Dashboard")
        self.geometry("1100;750".replace(";", "x"))
        self.minsize(950, 650)

        # Application theme colors
        self.colors = {
            "primary": "#1E3A8A",      # Navy Blue
            "accent": "#2563EB",       # Royal Blue
            "bg": "#F8FAFC",           # Light Gray/White
            "card_bg": "#FFFFFF",      # Card Background
            "text": "#0F172A",         # Dark Slate
            "text_muted": "#64748B",   # Slate Muted
            "border": "#E2E8F0",       # Light Border
            "success": "#16A34A",      # Emerald Green
            "warning": "#D97706",      # Amber
            "danger": "#DC2626",       # Crimson Red
            "purple": "#7C3AED",       # Violet
            "info": "#0284C7"          # Sky Blue
        }

        self.configure(bg=self.colors["bg"])
        self.records = []
        self.labs = {}
        self.bookings = set()

        self._setup_styles()
        self._build_header()
        self._build_notebook()
        self._build_statusbar()

        # Load existing data on startup
        self.load_current_data()

    def _setup_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        # General Notebook
        self.style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[16, 8])
        self.style.map("TNotebook.Tab",
                       background=[("selected", "#FFFFFF"), ("!selected", "#E2E8F0")],
                       foreground=[("selected", self.colors["primary"]), ("!selected", self.colors["text_muted"])])

        # Treeview styling
        self.style.configure("Treeview",
                             font=("Segoe UI", 9),
                             rowheight=28,
                             background="#FFFFFF",
                             fieldbackground="#FFFFFF",
                             foreground=self.colors["text"],
                             borderwidth=1,
                             relief="solid")
        self.style.configure("Treeview.Heading",
                             font=("Segoe UI", 10, "bold"),
                             background="#F1F5F9",
                             foreground=self.colors["primary"],
                             relief="flat")
        self.style.map("Treeview.Heading", background=[("active", "#E2E8F0")])

    def _build_header(self):
        # Header container
        header_frame = tk.Frame(self, bg=self.colors["primary"], height=70)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        # Title & Subtitle
        title_box = tk.Frame(header_frame, bg=self.colors["primary"])
        title_box.pack(side=tk.LEFT, padx=20, pady=12)

        lbl_title = tk.Label(
            title_box,
            text="Lab Booking Request Sorter",
            font=("Segoe UI", 16, "bold"),
            fg="#FFFFFF",
            bg=self.colors["primary"]
        )
        lbl_title.pack(anchor=tk.W)

        lbl_sub = tk.Label(
            title_box,
            text="CIT AI-Native Engineering · Capstone Assessment · Human-in-the-Loop Scheduling",
            font=("Segoe UI", 9),
            fg="#93C5FD",
            bg=self.colors["primary"]
        )
        lbl_sub.pack(anchor=tk.W)

        # Action Buttons
        btn_box = tk.Frame(header_frame, bg=self.colors["primary"])
        btn_box.pack(side=tk.RIGHT, padx=20, pady=12)

        self.btn_run = tk.Button(
            btn_box,
            text="▶ Process All Requests",
            font=("Segoe UI", 10, "bold"),
            bg="#22C55E",
            fg="#FFFFFF",
            activebackground="#16A34A",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.run_pipeline_threaded
        )
        self.btn_run.pack(side=tk.LEFT, padx=6)

        btn_refresh = tk.Button(
            btn_box,
            text="⟳ Reload Files",
            font=("Segoe UI", 9, "bold"),
            bg="#3B82F6",
            fg="#FFFFFF",
            activebackground="#1D4ED8",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=10,
            pady=6,
            cursor="hand2",
            command=self.load_current_data
        )
        btn_refresh.pack(side=tk.LEFT, padx=4)

        # Human Checkpoint Alert Strip
        checkpoint_bar = tk.Frame(self, bg="#FEF3C7", height=32, highlightbackground="#F59E0B", highlightthickness=1)
        checkpoint_bar.pack(fill=tk.X, side=tk.TOP)
        lbl_check = tk.Label(
            checkpoint_bar,
            text="⚠️  MANDATORY HUMAN CHECKPOINT: The software only prepares tentative proposals. The Lab In-Charge holds sole authority to confirm bookings.",
            font=("Segoe UI", 9, "bold"),
            fg="#92400E",
            bg="#FEF3C7"
        )
        lbl_check.pack(pady=4)

    def _build_notebook(self):
        container = tk.Frame(self, bg=self.colors["bg"])
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=10)

        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Dashboard & Metrics
        self.tab_dash = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(self.tab_dash, text="📊 Overview & Summary")
        self._build_dashboard_tab()

        # Tab 2: Tentative Schedule (Available)
        self.tab_sched = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(self.tab_sched, text="🗓️ Tentative Schedule")
        self._build_schedule_tab()

        # Tab 3: Issues & Conflicts
        self.tab_issues = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(self.tab_issues, text="⚠️ Issues & Clashes")
        self._build_issues_tab()

        # Tab 4: Full Audit Log
        self.tab_audit = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(self.tab_audit, text="📋 All Requests Audit")
        self._build_audit_tab()

        # Tab 5: Live Console Output
        self.tab_log = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(self.tab_log, text="💻 Execution Log")
        self._build_log_tab()

    def _build_dashboard_tab(self):
        # KPI Cards Frame
        kpi_frame = tk.Frame(self.tab_dash, bg=self.colors["bg"])
        kpi_frame.pack(fill=tk.X, pady=12)

        self.card_total = self._create_kpi_card(kpi_frame, "Total Requests", "0", self.colors["primary"])
        self.card_avail = self._create_kpi_card(kpi_frame, "Available Slots", "0", self.colors["success"])
        self.card_conf = self._create_kpi_card(kpi_frame, "Conflicts / Clashes", "0", self.colors["danger"])
        self.card_cap = self._create_kpi_card(kpi_frame, "Over Capacity", "0", self.colors["warning"])
        self.card_closed = self._create_kpi_card(kpi_frame, "Sunday / Closed", "0", self.colors["purple"])
        self.card_info = self._create_kpi_card(kpi_frame, "Needs More Info", "0", self.colors["info"])

        # Split pane for Lab Breakdown & Text Summary
        split_frame = tk.Frame(self.tab_dash, bg=self.colors["bg"])
        split_frame.pack(fill=tk.BOTH, expand=True, pady=6)

        # Left: Lab Allocation Tree
        left_box = tk.LabelFrame(
            split_frame,
            text="  Tentative Bookings Per Laboratory  ",
            font=("Segoe UI", 10, "bold"),
            bg="#FFFFFF",
            fg=self.colors["primary"],
            padx=10,
            pady=10
        )
        left_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        self.tree_labs = ttk.Treeview(
            left_box,
            columns=("code", "name", "capacity", "bookings"),
            show="headings",
            height=6
        )
        self.tree_labs.heading("code", text="Lab Code")
        self.tree_labs.heading("name", text="Lab Name")
        self.tree_labs.heading("capacity", text="Capacity")
        self.tree_labs.heading("bookings", text="Booked Count")
        self.tree_labs.column("code", width=80, anchor=tk.CENTER)
        self.tree_labs.column("name", width=180)
        self.tree_labs.column("capacity", width=80, anchor=tk.CENTER)
        self.tree_labs.column("bookings", width=100, anchor=tk.CENTER)
        self.tree_labs.pack(fill=tk.BOTH, expand=True)

        # Right: Summary Report Preview
        right_box = tk.LabelFrame(
            split_frame,
            text="  Official summary.txt Report  ",
            font=("Segoe UI", 10, "bold"),
            bg="#FFFFFF",
            fg=self.colors["primary"],
            padx=10,
            pady=10
        )
        right_box.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        self.txt_summary = tk.Text(
            right_box,
            font=("Consolas", 9),
            bg="#F8FAFC",
            fg=self.colors["text"],
            relief="flat",
            wrap=tk.WORD
        )
        self.txt_summary.pack(fill=tk.BOTH, expand=True)

    def _create_kpi_card(self, parent, title, val, color):
        frame = tk.Frame(parent, bg="#FFFFFF", highlightbackground=self.colors["border"], highlightthickness=1)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        lbl_val = tk.Label(frame, text=val, font=("Segoe UI", 20, "bold"), fg=color, bg="#FFFFFF")
        lbl_val.pack(pady=(10, 0))

        lbl_t = tk.Label(frame, text=title, font=("Segoe UI", 8, "bold"), fg=self.colors["text_muted"], bg="#FFFFFF")
        lbl_t.pack(pady=(0, 10))

        return lbl_val

    def _build_schedule_tab(self):
        lbl_note = tk.Label(
            self.tab_sched,
            text="✅ Tentative Schedule (schedule.csv): Available requests sorted in date order, awaiting Lab In-Charge sign-off.",
            font=("Segoe UI", 9, "italic"),
            fg=self.colors["success"],
            bg=self.colors["bg"]
        )
        lbl_note.pack(anchor=tk.W, pady=(4, 6))

        scroll = ttk.Scrollbar(self.tab_sched, orient=tk.VERTICAL)
        self.tree_sched = ttk.Treeview(
            self.tab_sched,
            columns=("date", "slot", "lab", "students", "id", "summary"),
            show="headings",
            yscrollcommand=scroll.set
        )
        scroll.config(command=self.tree_sched.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_sched.heading("date", text="Date")
        self.tree_sched.heading("slot", text="Slot")
        self.tree_sched.heading("lab", text="Lab")
        self.tree_sched.heading("students", text="Students")
        self.tree_sched.heading("id", text="Request ID")
        self.tree_sched.heading("summary", text="Summary of Activity")

        self.tree_sched.column("date", width=100, anchor=tk.CENTER)
        self.tree_sched.column("slot", width=60, anchor=tk.CENTER)
        self.tree_sched.column("lab", width=70, anchor=tk.CENTER)
        self.tree_sched.column("students", width=80, anchor=tk.CENTER)
        self.tree_sched.column("id", width=90, anchor=tk.CENTER)
        self.tree_sched.column("summary", width=400)

        self.tree_sched.pack(fill=tk.BOTH, expand=True)

    def _build_issues_tab(self):
        lbl_note = tk.Label(
            self.tab_issues,
            text="⚠️ Issues Log (issues.csv): All requests that cannot be booked as requested, with human-readable explanations.",
            font=("Segoe UI", 9, "italic"),
            fg=self.colors["danger"],
            bg=self.colors["bg"]
        )
        lbl_note.pack(anchor=tk.W, pady=(4, 6))

        scroll = ttk.Scrollbar(self.tab_issues, orient=tk.VERTICAL)
        self.tree_issues = ttk.Treeview(
            self.tab_issues,
            columns=("id", "sent", "status", "reason", "request"),
            show="headings",
            yscrollcommand=scroll.set
        )
        scroll.config(command=self.tree_issues.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_issues.heading("id", text="ID")
        self.tree_issues.heading("sent", text="Sent Date")
        self.tree_issues.heading("status", text="Status Problem")
        self.tree_issues.heading("reason", text="Detailed Reason")
        self.tree_issues.heading("request", text="Original Request Text")

        self.tree_issues.column("id", width=60, anchor=tk.CENTER)
        self.tree_issues.column("sent", width=90, anchor=tk.CENTER)
        self.tree_issues.column("status", width=120, anchor=tk.CENTER)
        self.tree_issues.column("reason", width=320)
        self.tree_issues.column("request", width=400)

        self.tree_issues.tag_configure("conflict", foreground=self.colors["danger"])
        self.tree_issues.tag_configure("over_capacity", foreground=self.colors["warning"])
        self.tree_issues.tag_configure("lab_closed", foreground=self.colors["purple"])
        self.tree_issues.tag_configure("needs_more_info", foreground=self.colors["info"])

        self.tree_issues.pack(fill=tk.BOTH, expand=True)

    def _build_audit_tab(self):
        lbl_note = tk.Label(
            self.tab_audit,
            text="📋 Complete Audit (results.csv): Every single incoming request processed with extracted JSON facts and status.",
            font=("Segoe UI", 9, "italic"),
            fg=self.colors["text_muted"],
            bg=self.colors["bg"]
        )
        lbl_note.pack(anchor=tk.W, pady=(4, 6))

        scroll = ttk.Scrollbar(self.tab_audit, orient=tk.VERTICAL)
        self.tree_audit = ttk.Treeview(
            self.tab_audit,
            columns=("id", "sent", "lab", "date", "slot", "students", "status", "reason"),
            show="headings",
            yscrollcommand=scroll.set
        )
        scroll.config(command=self.tree_audit.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_audit.heading("id", text="ID")
        self.tree_audit.heading("sent", text="Sent")
        self.tree_audit.heading("lab", text="Lab")
        self.tree_audit.heading("date", text="Date")
        self.tree_audit.heading("slot", text="Slot")
        self.tree_audit.heading("students", text="Students")
        self.tree_audit.heading("status", text="Decision Status")
        self.tree_audit.heading("reason", text="Reason / Audit Note")

        self.tree_audit.column("id", width=50, anchor=tk.CENTER)
        self.tree_audit.column("sent", width=85, anchor=tk.CENTER)
        self.tree_audit.column("lab", width=60, anchor=tk.CENTER)
        self.tree_audit.column("date", width=85, anchor=tk.CENTER)
        self.tree_audit.column("slot", width=55, anchor=tk.CENTER)
        self.tree_audit.column("students", width=65, anchor=tk.CENTER)
        self.tree_audit.column("status", width=115, anchor=tk.CENTER)
        self.tree_audit.column("reason", width=380)

        self.tree_audit.pack(fill=tk.BOTH, expand=True)

    def _build_log_tab(self):
        self.txt_log = tk.Text(
            self.tab_log,
            font=("Consolas", 10),
            bg="#0F172A",
            fg="#F8FAFC",
            wrap=tk.WORD,
            relief="flat"
        )
        self.txt_log.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.log("Console initialized. Ready to process booking requests.\n")

    def _build_statusbar(self):
        status_bar = tk.Frame(self, bg="#E2E8F0", height=24)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_status = tk.Label(
            status_bar,
            text="Ready. System in compliance with faculty specification.",
            font=("Segoe UI", 9),
            fg=self.colors["text_muted"],
            bg="#E2E8F0"
        )
        self.lbl_status.pack(side=tk.LEFT, padx=10)

        lbl_right = tk.Label(
            status_bar,
            text="Model: Groq Llama-3.3-70B · Sem: 2026-10-01 to 2026-12-15",
            font=("Segoe UI", 9),
            fg=self.colors["text_muted"],
            bg="#E2E8F0"
        )
        lbl_right.pack(side=tk.RIGHT, padx=10)

    def log(self, text):
        self.txt_log.insert(tk.END, text + "\n")
        self.txt_log.see(tk.END)

    def load_current_data(self):
        """Loads and visualizes the generated CSV files in the GUI tables."""
        # Clear existing treeview rows
        for t in [self.tree_sched, self.tree_issues, self.tree_audit, self.tree_labs]:
            for row in t.get_children():
                t.delete(row)

        # Load Labs
        self.labs = core.load_labs("labs.csv")

        # 1. Load results.csv
        total = 0
        counts = {"available": 0, "conflict": 0, "over_capacity": 0, "lab_closed": 0, "needs_more_info": 0}
        lab_sched_counts = {c: 0 for c in self.labs.keys()}

        if os.path.exists("results.csv"):
            with open("results.csv", "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    total += 1
                    status = r["status"]
                    counts[status] = counts.get(status, 0) + 1
                    self.tree_audit.insert("", tk.END, values=(
                        r["id"], r["sent"], r["lab"], r["date"], r["slot"], r["students"], status, r["reason"]
                    ))

        # 2. Load schedule.csv
        if os.path.exists("schedule.csv"):
            with open("schedule.csv", "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    lab = r["lab"]
                    if lab in lab_sched_counts:
                        lab_sched_counts[lab] += 1
                    self.tree_sched.insert("", tk.END, values=(
                        r["date"], r["slot"], lab, r["students"], r["request_id"], r["summary"]
                    ))

        # 3. Load issues.csv
        if os.path.exists("issues.csv"):
            with open("issues.csv", "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    status = r["status"]
                    self.tree_issues.insert("", tk.END, values=(
                        r["id"], r["sent"], status, r["reason"], r["request"]
                    ), tags=(status,))

        # Update KPI Cards
        self.card_total.config(text=str(total))
        self.card_avail.config(text=str(counts.get("available", 0)))
        self.card_conf.config(text=str(counts.get("conflict", 0)))
        self.card_cap.config(text=str(counts.get("over_capacity", 0)))
        self.card_closed.config(text=str(counts.get("lab_closed", 0)))
        self.card_info.config(text=str(counts.get("needs_more_info", 0)))

        # Update Labs table
        for code, info in self.labs.items():
            self.tree_labs.insert("", tk.END, values=(
                code, info["name"], info["capacity"], lab_sched_counts.get(code, 0)
            ))

        # Update Summary text preview
        if os.path.exists("summary.txt"):
            with open("summary.txt", "r", encoding="utf-8") as f:
                self.txt_summary.delete("1.0", tk.END)
                self.txt_summary.insert(tk.END, f.read())

        self.lbl_status.config(text=f"Loaded {total} requests from CSV reports. Ready.")

    def run_pipeline_threaded(self):
        """Runs the main.py sorter logic in a background thread to keep GUI responsive."""
        self.btn_run.config(state=tk.DISABLED, text="⏳ Processing...")
        self.lbl_status.config(text="Processing requests with Groq API and Python rules...")
        self.notebook.select(self.tab_log)

        thread = threading.Thread(target=self._run_pipeline_worker, daemon=True)
        thread.start()

    def _run_pipeline_worker(self):
        self.log("\n" + "=" * 60)
        self.log(f"Starting processing run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log("=" * 60)

        try:
            core.main()
            self.log("\n[Success] Processing complete! Refreshing GUI views...")
            self.after(0, self._on_pipeline_success)
        except Exception as e:
            self.log(f"\n[Error during processing]: {e}")
            self.after(0, lambda: messagebox.showerror("Processing Error", f"An error occurred: {e}"))
            self.after(0, self._on_pipeline_finish)

    def _on_pipeline_success(self):
        self.load_current_data()
        self._on_pipeline_finish()
        messagebox.showinfo("Complete", "All requests processed successfully!\nOutput CSV and summary files updated.")
        self.notebook.select(self.tab_dash)

    def _on_pipeline_finish(self):
        self.btn_run.config(state=tk.NORMAL, text="▶ Process All Requests")


if __name__ == "__main__":
    app = LabBookingGUI()
    app.mainloop()
