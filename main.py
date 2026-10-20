#!/usr/bin/env python3
"""Tkinter desktop interface for the saved Wi-Fi password tool."""

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict, Optional

from wifi_passwords.backends import get_backend
from wifi_passwords.errors import WifiPasswordError
from wifi_passwords.models import SavedNetwork


class WifiPasswordApp:
    """A small GUI that retrieves only the credential selected by the user."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.backend = get_backend()
        self.networks: Dict[str, SavedNetwork] = {}
        self.results: "queue.Queue[tuple]" = queue.Queue()
        self.busy = False
        self.closed = False

        self.password = tk.StringVar()
        self.reveal_password = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="正在讀取已儲存的 Wi-Fi 網路…")

        self._build_window()
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.after(100, self._poll_results)
        self.refresh_networks()

    def _build_window(self) -> None:
        self.root.title("Saved Wi-Fi Passwords")
        self.root.geometry("760x460")
        self.root.minsize(620, 380)

        container = ttk.Frame(self.root, padding=16)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        heading = ttk.Label(
            container,
            text="已儲存的 Wi-Fi 網路",
            font=("TkDefaultFont", 16, "bold"),
        )
        heading.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        table_frame = ttk.Frame(container)
        table_frame.grid(row=1, column=0, sticky=tk.NSEW)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            table_frame,
            columns=("ssid", "profile", "interface"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("ssid", text="Wi-Fi 名稱")
        self.tree.heading("profile", text="設定檔")
        self.tree.heading("interface", text="網路介面")
        self.tree.column("ssid", width=260, minwidth=160)
        self.tree.column("profile", width=230, minwidth=120)
        self.tree.column("interface", width=180, minwidth=100)
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        self.tree.bind("<<TreeviewSelect>>", self._selection_changed)
        self.tree.bind("<Double-1>", lambda _event: self.retrieve_password())

        scrollbar = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        scrollbar.grid(row=0, column=1, sticky=tk.NS)
        self.tree.configure(yscrollcommand=scrollbar.set)

        password_frame = ttk.LabelFrame(container, text="密碼", padding=10)
        password_frame.grid(row=2, column=0, sticky=tk.EW, pady=(12, 0))
        password_frame.columnconfigure(0, weight=1)

        self.password_entry = ttk.Entry(
            password_frame,
            textvariable=self.password,
            show="•",
            state="readonly",
            font=("TkFixedFont", 11),
        )
        self.password_entry.grid(row=0, column=0, sticky=tk.EW, padx=(0, 8))

        self.reveal_button = ttk.Checkbutton(
            password_frame,
            text="顯示",
            variable=self.reveal_password,
            command=self._toggle_password,
        )
        self.reveal_button.grid(row=0, column=1, padx=(0, 8))

        self.copy_button = ttk.Button(
            password_frame,
            text="複製",
            command=self.copy_password,
            state=tk.DISABLED,
        )
        self.copy_button.grid(row=0, column=2)

        actions = ttk.Frame(container)
        actions.grid(row=3, column=0, sticky=tk.EW, pady=(12, 0))
        actions.columnconfigure(0, weight=1)

        ttk.Label(actions, textvariable=self.status).grid(row=0, column=0, sticky=tk.W)
        self.refresh_button = ttk.Button(
            actions, text="重新整理", command=self.refresh_networks
        )
        self.refresh_button.grid(row=0, column=1, padx=(8, 8))
        self.retrieve_button = ttk.Button(
            actions,
            text="取得選取的密碼",
            command=self.retrieve_password,
            state=tk.DISABLED,
        )
        self.retrieve_button.grid(row=0, column=2)

    def _start_task(
        self, action: Callable[[], object], on_success: Callable[[object], None]
    ) -> None:
        if self.busy:
            return
        self._set_busy(True)

        def worker() -> None:
            try:
                self.results.put((True, on_success, action()))
            except Exception as exc:  # The main thread presents OS/backend errors.
                self.results.put((False, None, exc))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_results(self) -> None:
        try:
            while True:
                succeeded, callback, value = self.results.get_nowait()
                self._set_busy(False)
                if succeeded:
                    callback(value)
                else:
                    self._show_error(value)
        except queue.Empty:
            pass
        if not self.closed:
            self.root.after(100, self._poll_results)

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.refresh_button.configure(state=tk.DISABLED if busy else tk.NORMAL)
        can_retrieve = not busy and bool(self.tree.selection())
        self.retrieve_button.configure(
            state=tk.NORMAL if can_retrieve else tk.DISABLED
        )

    def refresh_networks(self) -> None:
        self.status.set("正在讀取已儲存的 Wi-Fi 網路…")
        self._clear_password()
        self._start_task(
            lambda: self.backend.list_networks(include_passwords=False),
            self._networks_loaded,
        )

    def _networks_loaded(self, result: object) -> None:
        networks = list(result)
        self.tree.delete(*self.tree.get_children())
        self.networks.clear()
        for index, network in enumerate(networks):
            item_id = f"network-{index}"
            self.networks[item_id] = network
            self.tree.insert(
                "",
                tk.END,
                iid=item_id,
                values=(
                    network.ssid,
                    network.profile_id or "",
                    network.interface or "",
                ),
            )
        self.status.set(f"找到 {len(networks)} 個已儲存的 Wi-Fi 網路")

    def _selection_changed(self, _event=None) -> None:
        self._clear_password()
        self._set_busy(self.busy)

    def _selected_network(self) -> Optional[SavedNetwork]:
        selected = self.tree.selection()
        return self.networks.get(selected[0]) if selected else None

    def retrieve_password(self) -> None:
        network = self._selected_network()
        if network is None or self.busy:
            return
        self.status.set(f"正在讀取 {network.ssid} 的密碼…")
        self._clear_password()
        self._start_task(
            lambda: self.backend.get_network(network.ssid),
            self._password_loaded,
        )

    def _password_loaded(self, result: object) -> None:
        network = result
        if network.password is None:
            self._show_error(
                WifiPasswordError(network.error or "此網路沒有可讀取的已儲存密碼")
            )
            return
        self.password.set(network.password)
        self.copy_button.configure(state=tk.NORMAL)
        self.status.set(f"已讀取 {network.ssid} 的密碼")

    def _clear_password(self) -> None:
        self.password.set("")
        self.reveal_password.set(False)
        if hasattr(self, "password_entry"):
            self.password_entry.configure(show="•")
            self.copy_button.configure(state=tk.DISABLED)

    def _toggle_password(self) -> None:
        self.password_entry.configure(show="" if self.reveal_password.get() else "•")

    def copy_password(self) -> None:
        value = self.password.get()
        if not value:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.status.set("密碼已複製到剪貼簿")

    def _show_error(self, error: object) -> None:
        message = str(error)
        self.status.set("操作失敗")
        messagebox.showerror("無法讀取 Wi-Fi 密碼", message, parent=self.root)

    def _close(self) -> None:
        self.closed = True
        self.password.set("")
        self.root.destroy()


def main() -> int:
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"error: 無法啟動 Tkinter：{exc}")
        return 1

    try:
        WifiPasswordApp(root)
    except WifiPasswordError as exc:
        messagebox.showerror("無法啟動", str(exc), parent=root)
        root.destroy()
        return 1

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
