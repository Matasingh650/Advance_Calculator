# # Simple Python Calculator

# def calculator():
#     print("=== Simple Calculator ===")
#     print("Operations: +  -  *  /")
#     print("Type 'exit' to quit")

#     while True:
#         try:
#             num1 = input("\nEnter first number: ")
#             if num1.lower() == "exit":
#                 print("Goodbye!")
#                 break
#             num1 = float(num1)

#             op = input("Enter operation (+, -, *, /): ").strip()
#             if op.lower() == "exit":
#                 print("Goodbye!")
#                 break

#             num2 = input("Enter second number: ")
#             if num2.lower() == "exit":
#                 print("Goodbye!")
#                 break
#             num2 = float(num2)

#             if op == "+":
#                 result = num1 + num2
#             elif op == "-":
#                 result = num1 - num2
#             elif op == "*":
#                 result = num1 * num2
#             elif op == "/":
#                 if num2 == 0:
#                     print("❌ Error: Division by zero is not allowed.")
#                     continue
#                 result = num1 / num2
#             else:
#                 print("❌ Invalid operation.")
#                 continue

#             print(f"✅ Result: {result}")
#         except ValueError:
#             print("❌ Please enter valid numbers.")

# if __name__ == "__main__":
#     calculator()


# advanced_calculator.py
# A full-featured scientific calculator with Tkinter + safe AST evaluation.

import tkinter as tk
from tkinter import ttk, messagebox
import math
import ast
import operator

# -------- Safe Evaluator (no eval) --------
class SafeEvaluator(ast.NodeVisitor):
    """
    Safely evaluate a mathematical expression AST with whitelisted nodes & functions.
    Supports constants pi/e, variable Ans, and a deg/rad switch for trig.
    """
    def __init__(self, variables=None, deg_mode=False):
        super().__init__()
        self.vars = variables or {}
        self.deg_mode = deg_mode

        # Operators
        self.bin_ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
        }
        self.unary_ops = {
            ast.UAdd: operator.pos,
            ast.USub: operator.neg,
        }

        # Math functions (wrapping trig for deg/rad)
        def _wrap_trig(f):
            return (lambda x: f(math.radians(x))) if self.deg_mode else f
        def _wrap_atrig(f):
            return (lambda x: math.degrees(f(x))) if self.deg_mode else f

        self.funcs = {
            "sin":  _wrap_trig(math.sin),
            "cos":  _wrap_trig(math.cos),
            "tan":  _wrap_trig(math.tan),
            "asin": _wrap_atrig(math.asin),
            "acos": _wrap_atrig(math.acos),
            "atan": _wrap_atrig(math.atan),
            "log":  lambda x, b=10: math.log(x, b),  # log base 10 by default
            "ln":   math.log,                        # natural log
            "sqrt": math.sqrt,
            "abs":  abs,
            "floor": math.floor,
            "ceil": math.ceil,
            "fact": math.factorial,
            "pow":  pow,
        }

        # Constants
        self.consts = {"pi": math.pi, "e": math.e}

    def visit(self, node):
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        elif isinstance(node, ast.Num):  # Python <3.8; kept for safety
            return node.n
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Only numeric constants allowed.")
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self.bin_ops:
                raise ValueError("Unsupported operator.")
            left = self.visit(node.left)
            right = self.visit(node.right)
            return self.bin_ops[op_type](left, right)
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self.unary_ops:
                raise ValueError("Unsupported unary operator.")
            operand = self.visit(node.operand)
            return self.unary_ops[op_type](operand)
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only simple function calls allowed.")
            name = node.func.id
            if name not in self.funcs:
                raise ValueError(f"Unknown function: {name}")
            fn = self.funcs[name]
            args = [self.visit(a) for a in node.args]
            # Keyword args support for log(x, b)
            kwargs = {kw.arg: self.visit(kw.value) for kw in node.keywords}
            return fn(*args, **kwargs)
        elif isinstance(node, ast.Name):
            if node.id in self.consts:
                return self.consts[node.id]
            if node.id in self.vars:
                return self.vars[node.id]
            raise ValueError(f"Unknown identifier: {node.id}")
        elif isinstance(node, ast.Paren) or isinstance(node, ast.Tuple):
            # Shouldn't normally hit; parentheses compile as BinOp nesting
            return [self.visit(elt) for elt in node.elts]
        else:
            raise ValueError("Unsupported syntax.")

    def eval(self, expr: str):
        # Minor pre-processing:
        expr = expr.replace("×", "*").replace("÷", "/").replace("^", "**")
        # Percent: replace trailing % tokens (e.g., "50%" -> "50/100")
        # also "200 + 10%" -> "200 + (10/100)"
        expr = expr.replace("%", "/100")

        # factorial via fact(), but also allow postfix "!" -> fact(x)
        # handle simple patterns: numbers or ) before !
        # Convert "5!" -> "fact(5)" and "(2+3)!" -> "fact((2+3))"
        def _replace_factorial(s):
            out = []
            i = 0
            while i < len(s):
                if s[i] == "!":
                    # shouldn't start with !
                    out.append("!")
                    i += 1
                    continue
                if s[i] == ")":
                    # find matching '('
                    depth = 1
                    j = len(out) - 1
                    while j >= 0:
                        if out[j] == ")":
                            depth += 1
                        elif out[j] == "(":
                            depth -= 1
                            if depth == 0:
                                break
                        j -= 1
                    # check next char(s) for !
                    k = i + 1
                    if k < len(s) and s[k] == "!":
                        # insert fact around the parenthesized expr
                        out.insert(j, "fact(")
                        out.append(")")
                        i = k + 1
                        continue
                # number literal followed by !
                if s[i].isdigit():
                    j = i
                    while j < len(s) and (s[j].isdigit() or s[j] == "."):
                        out.append(s[j]); j += 1
                    # If next is !, wrap the number with fact()
                    if j < len(s) and s[j] == "!":
                        # backtrack number
                        num_len = j - i
                        for _ in range(num_len):
                            out.pop()
                        out.append(f"fact({s[i:j]})")
                        i = j + 1
                        continue
                    i = j
                    continue
                out.append(s[i]); i += 1
            return "".join(out)

        expr = _replace_factorial(expr)

        try:
            node = ast.parse(expr, mode="eval")
        except SyntaxError:
            raise ValueError("Syntax error.")

        return self.visit(node)

# -------- GUI --------
class CalcApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Advanced Calculator")
        self.geometry("480x560")
        self.minsize(480, 560)

        # State
        self.deg_mode = tk.BooleanVar(value=True)     # Deg by default
        self.memory = 0.0
        self.ans = 0.0
        self.undo_stack = []
        self.redo_stack = []

        self._build_ui()
        self._bind_keys()

    # ---- UI ----
    def _build_ui(self):
        top = ttk.Frame(self, padding=(10, 10, 10, 0))
        top.pack(fill="x")

        self.entry = ttk.Entry(top, font=("Consolas", 18))
        self.entry.pack(fill="x")
        self.entry.focus()

        status_frame = ttk.Frame(self, padding=(10, 2))
        status_frame.pack(fill="x")
        self.mode_chk = ttk.Checkbutton(status_frame, text="Degrees", variable=self.deg_mode, command=self._on_mode_change)
        self.mode_chk.pack(side="left")
        self.ans_lbl = ttk.Label(status_frame, text="Ans = 0")
        self.ans_lbl.pack(side="right")

        mid = ttk.Frame(self, padding=(8, 6))
        mid.pack(fill="both", expand=True)

        # Left: buttons
        left = ttk.Frame(mid)
        left.pack(side="left", fill="both", expand=True)

        # Right: history
        right = ttk.Frame(mid)
        right.pack(side="right", fill="both")
        ttk.Label(right, text="History", font=("Segoe UI", 10, "bold")).pack()
        self.hist = tk.Listbox(right, width=22, height=24)
        self.hist.pack(fill="both", expand=True)
        self.hist.bind("<Double-1>", self._on_history_double)

        # Button grid
        btns = [
            ("MC","MR","M+","M-","C","⌫"),
            ("(",")","%", "Ans","pi","e"),
            ("sin","cos","tan","asin","acos","atan"),
            ("ln","log","sqrt","abs","floor","ceil"),
            ("7","8","9","/","^","//"),
            ("4","5","6","*","-","mod"),
            ("1","2","3","-","+/-","="),
            ("0",".",",", "+","!", "Enter"),
        ]
        # Map to commands
        grid = ttk.Frame(left)
        grid.pack(fill="both", expand=True)

        for r, row in enumerate(btns):
            for c, label in enumerate(row):
                b = ttk.Button(grid, text=label, command=lambda t=label: self._press(t))
                b.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
        for i in range(6):
            grid.columnconfigure(i, weight=1)
        for i in range(len(btns)):
            grid.rowconfigure(i, weight=1)

        # Bottom: equals / info
        self.info = ttk.Label(self, text="Use keyboard: Enter=equals, Esc=clear, Backspace=⌫, Ctrl+Z/Y undo/redo")
        self.info.pack(pady=(0,8))

        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")

    def _bind_keys(self):
        self.bind("<Return>", lambda e: self._press("="))
        self.bind("<KP_Enter>", lambda e: self._press("="))
        self.bind("<Escape>", lambda e: self._press("C"))
        self.bind("<BackSpace>", lambda e: self._press("⌫"))
        self.bind("<Control-z>", lambda e: self._undo())
        self.bind("<Control-y>", lambda e: self._redo())
        # Directly insert printable keys
        for ch in "0123456789.+-*/()^%":
            self.bind(ch, self._insert_key)
        self.bind("<Key>", self._on_any_key)

    # ---- Actions ----
    def _insert_key(self, e):
        self._snapshot()
        self.entry.insert("insert", e.char)

    def _on_any_key(self, e):
        # keep redo stack sane if user types
        if e.char and e.char.isprintable():
            self.redo_stack.clear()

    def _on_mode_change(self):
        self.info.config(text=f"Mode changed to {'Degrees' if self.deg_mode.get() else 'Radians'}.")

    def _snapshot(self):
        self.undo_stack.append(self.entry.get())

    def _undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.entry.get())
            prev = self.undo_stack.pop()
            self.entry.delete(0, "end")
            self.entry.insert(0, prev)

    def _redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.entry.get())
            nxt = self.redo_stack.pop()
            self.entry.delete(0, "end")
            self.entry.insert(0, nxt)

    def _on_history_double(self, _):
        sel = self.hist.curselection()
        if not sel: return
        text = self.hist.get(sel[0])
        # history line stored as "expr = result"
        if " = " in text:
            expr, result = text.split(" = ", 1)
            self.entry.delete(0, "end")
            self.entry.insert(0, result.strip())

    def _press(self, label):
        if label == "C":
            self._snapshot()
            self.entry.delete(0, "end")
            self.redo_stack.clear()
            return
        if label == "⌫":
            self._snapshot()
            s = self.entry.get()
            if s:
                self.entry.delete(len(s)-1, "end")
            return

        # Memory ops
        if label in ("MC","MR","M+","M-"):
            try:
                if label == "MC":
                    self.memory = 0.0
                    self.info.config(text="Memory cleared.")
                elif label == "MR":
                    self._snapshot()
                    self.entry.insert("insert", str(self.memory))
                elif label == "M+":
                    val = self._evaluate_silent()
                    self.memory += val
                    self.info.config(text=f"Memory += {val}")
                elif label == "M-":
                    val = self._evaluate_silent()
                    self.memory -= val
                    self.info.config(text=f"Memory -= {val}")
            except Exception as e:
                messagebox.showerror("Memory Error", str(e))
            return

        # Functions & tokens
        token_map = {
            "mod": "%", "Ans": "Ans", "pi": "pi", "e": "e",
            "sqrt": "sqrt(", "sin":"sin(", "cos":"cos(", "tan":"tan(",
            "asin":"asin(", "acos":"acos(", "atan":"atan(",
            "ln":"ln(", "log":"log(", "abs":"abs(", "floor":"floor(", "ceil":"ceil(",
            "!":"!", "^":"^", "//":"//", "+/-":"sign",
            "Enter":"=",  # alias
        }

        if label == "=":
            self._do_equals()
            return

        if label == "+/-":
            # Wrap current expression with -( ... )
            self._snapshot()
            s = self.entry.get().strip()
            if not s:
                self.entry.insert("insert", "-")
                return
            self.entry.delete(0, "end")
            self.entry.insert(0, f"-({s})")
            return

        self._snapshot()
        insert = token_map.get(label, label)
        # auto closing bracket helper for functions if user immediately presses ')'
        self.entry.insert("insert", insert)

    def _evaluate_silent(self):
        expr = self.entry.get().strip()
        if not expr:
            return 0.0
        # build variables
        variables = {"Ans": self.ans}
        ev = SafeEvaluator(variables=variables, deg_mode=self.deg_mode.get())
        val = ev.eval(expr)
        if isinstance(val, complex):
            raise ValueError("Complex results not supported.")
        return float(val)

    def _do_equals(self):
        expr = self.entry.get().strip()
        if not expr:
            return
        try:
            val = self._evaluate_silent()
            self.ans = val
            self.ans_lbl.config(text=f"Ans = {self._fmt(val)}")
            self._append_history(expr, val)
            self.entry.delete(0, "end")
            self.entry.insert(0, self._fmt(val))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _fmt(self, x):
        # Nicely format floats (avoid too many decimals)
        if abs(x) < 1e-9:
            x = 0.0
        s = f"{x:.12g}"
        return s

    def _append_history(self, expr, val):
        self.hist.insert(0, f"{expr} = {self._fmt(val)}")
        # keep list manageable
        if self.hist.size() > 200:
            self.hist.delete("end")

if __name__ == "__main__":
    app = CalcApp()
    app.mainloop()
