import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import Calendar, DateEntry
import sqlite3
from datetime import datetime
import threading
import time

# -------------------- Main Application Class --------------------

class ScheduleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("College Schedule Reminder Pro")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # Modern color scheme with improved contrast
        self.colors = {
            'background': '#F8F9FA',
            'primary': '#2A6F97',
            'secondary': '#468FAF',
            'accent': '#FF7F51',
            'text': '#212529',
            'highlight': '#FFD166',
            'header': '#014F86'
        }
        
        # Configure custom styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Base styles
        self.style.configure('.', background=self.colors['background'], 
                             font=('Helvetica', 12))
        self.style.configure('TFrame', background=self.colors['background'])
        self.style.configure('TLabel', background=self.colors['background'], 
                             foreground=self.colors['text'])
        self.style.configure('Header.TLabel', 
                             font=('Helvetica', 16, 'bold'),
                             foreground=self.colors['header'],
                             padding=10)
        self.style.configure('Event.Treeview', 
                             rowheight=30,
                             font=('Helvetica', 11))
        self.style.map('TButton',
                       background=[('active', self.colors['secondary']),
                                   ('!active', self.colors['primary'])],
                       foreground=[('active', 'white'),
                                   ('!active', 'white')])
        # Accent button style
        self.style.configure('Accent.TButton',
                             background=self.colors['accent'],
                             foreground='white',
                             font=('Helvetica', 12, 'bold'))
        
        # Initialize database and UI
        self.init_database()
        self.create_main_interface()
        self.start_notification_thread()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def init_database(self):
        self.conn = sqlite3.connect('college_schedule.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY,
                date TEXT NOT NULL,
                course TEXT NOT NULL,
                time TEXT NOT NULL,
                location TEXT NOT NULL,
                notes TEXT,
                category TEXT,
                recurrence_type TEXT,
                recurrence_end TEXT,
                recurrence_days TEXT,
                reminder_time INTEGER
            )
        ''')
        self.conn.commit()

    def create_main_interface(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Configure grid layout: left for Calendar, right for Event List.
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(0, weight=1)
        
        # Calendar Section with improved styling
        cal_frame = ttk.Frame(main_frame)
        cal_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        
        # Month/Year Header with proper color
        self.month_year_label = ttk.Label(
            cal_frame, 
            style='Header.TLabel',
            anchor="center"
        )
        self.month_year_label.pack(fill=tk.X)
        
        # Enhanced Calendar Widget with slightly reduced day font size
        self.cal = Calendar(
            cal_frame,
            selectmode='day',
            date_pattern='y-mm-dd',
            background=self.colors['background'],
            bordercolor=self.colors['primary'],
            headersbackground=self.colors['primary'],
            headersforeground='white',
            normalbackground=self.colors['background'],
            weekendbackground='#E9ECEF',
            weekendforeground=self.colors['text'],
            othermonthbackground='#F1F3F5',
            othermonthwebackground='#F1F3F5',
            font=('Helvetica', 11),
            headersfont=('Helvetica', 12, 'bold')
        )
        self.cal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.cal.bind("<<CalendarSelected>>", self.on_calendar_change)
        self.update_month_year_label()

        # Event List Section with modern styling
        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=0, column=1, sticky='nsew', padx=10, pady=10)
        
        # Event List Header
        ttk.Label(list_frame, text="Today's Schedule", style='Header.TLabel').pack(fill=tk.X)
        
        # Enhanced Treeview with centered text
        self.event_tree = ttk.Treeview(
            list_frame,
            columns=("Time", "Course", "Location"),
            show="headings",
            style='Event.Treeview',
            selectmode='browse'
        )
        for col in ["Time", "Course", "Location"]:
            self.event_tree.heading(col, text=col, anchor=tk.CENTER)
            self.event_tree.column(col, anchor=tk.CENTER, width=120)
        self.event_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.event_tree.yview)
        self.event_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Action Button with improved styling
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="Manage Events", command=self.open_event_manager,
                   style='Accent.TButton').pack(padx=10, ipadx=20, ipady=8)
        
        self.update_event_list()

    def update_month_year_label(self):
        date_str = self.cal.get_date()  # Expected format: YYYY-MM-DD
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            month_year_text = date_obj.strftime("%B %Y")
            self.month_year_label.config(text=month_year_text,
                                         foreground=self.colors['header'])
        except Exception:
            self.month_year_label.config(text="")

    def on_calendar_change(self, event):
        self.update_month_year_label()
        self.update_event_list()

    def update_event_list(self, event=None):
        # Clear the event tree
        for item in self.event_tree.get_children():
            self.event_tree.delete(item)
            
        selected_date_str = self.cal.get_date()  # Format: YYYY-MM-DD
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d')
        
        # Retrieve all events from the database
        self.cursor.execute("SELECT * FROM schedule")
        rows = self.cursor.fetchall()
        for ev in rows:
            # ev indices:
            # 0=id, 1=date, 2=course, 3=time, 4=location, 5=notes, 6=category,
            # 7=recurrence_type, 8=recurrence_end, 9=recurrence_days, 10=reminder_time
            event_date = datetime.strptime(ev[1], '%Y-%m-%d')
            rec_type = ev[7]
            show_event = False
            if rec_type is None or rec_type.strip() == "" or rec_type == "None":
                if event_date.date() == selected_date.date():
                    show_event = True
            else:
                # Only show repeating events if the original event date is not later than the selected date.
                if event_date.date() <= selected_date.date():
                    if ev[8]:
                        try:
                            rec_end = datetime.strptime(ev[8], '%Y-%m-%d')
                            if selected_date.date() > rec_end.date():
                                show_event = False
                            else:
                                show_event = True
                        except Exception:
                            show_event = True
                    else:
                        show_event = True
                    if rec_type == "Daily":
                        show_event = True
                    elif rec_type == "Weekly":
                        if event_date.weekday() == selected_date.weekday():
                            show_event = True
                    elif rec_type == "Weekly (Specific Days)":
                        days = [d.strip() for d in ev[9].split(',')] if ev[9] else []
                        if selected_date.strftime('%A') in days:
                            show_event = True
                    elif rec_type == "Monthly":
                        if event_date.day == selected_date.day:
                            show_event = True
                    elif rec_type == "Yearly":
                        if event_date.month == selected_date.month and event_date.day == selected_date.day:
                            show_event = True
            if show_event:
                self.event_tree.insert("", "end", iid=ev[0], values=(ev[3], ev[2], ev[4]))

    def start_notification_thread(self):
        def check_reminders():
            # Use a separate connection for thread safety.
            conn_thread = sqlite3.connect('college_schedule.db')
            cursor_thread = conn_thread.cursor()
            while self.running:
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                cursor_thread.execute('''SELECT * FROM schedule 
                    WHERE datetime(date || ' ' || time) BETWEEN datetime(?) AND datetime(?, '+30 minutes')
                    AND reminder_time IS NOT NULL
                ''', (now, now))
                for ev in cursor_thread.fetchall():
                    self.root.after(0, lambda ev=ev: messagebox.showinfo(
                        "Reminder", f"Upcoming: {ev[2]} at {ev[3]}\nLocation: {ev[4]}\nNotes: {ev[5]}"
                    ))
                    cursor_thread.execute("UPDATE schedule SET reminder_time = NULL WHERE id=?", (ev[0],))
                    conn_thread.commit()
                time.sleep(60)
            conn_thread.close()
        
        self.running = True
        thread = threading.Thread(target=check_reminders, daemon=True)
        thread.start()

    def open_event_manager(self):
        EventManagerWindow(self)

    def on_closing(self):
        self.running = False
        self.conn.close()
        self.root.destroy()


# -------------------- Event Management Window --------------------

class EventManagerWindow:
    def __init__(self, parent_app):
        self.parent_app = parent_app
        self.conn = parent_app.conn
        self.cursor = self.conn.cursor()
        
        self.win = tk.Toplevel(parent_app.root)
        self.win.title("Event Manager")
        self.win.geometry("800x600")
        self.win.grab_set()  # Make the window modal
        
        # Modern styling for the modal window
        self.style = ttk.Style()
        self.style.configure('Modal.TFrame', background='#FFFFFF')
        self.style.configure('Modal.TLabel', background='#FFFFFF', 
                             foreground=parent_app.colors['text'])
        
        self.create_modern_interface()

    def create_modern_interface(self):
        main_frame = ttk.Frame(self.win, style='Modal.TFrame', padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header Section
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        ttk.Label(header_frame, text="Event Manager", style='Header.TLabel').pack(side=tk.LEFT)
        
        # Search Bar (optional)
        search_frame = ttk.Frame(header_frame)
        search_frame.pack(side=tk.RIGHT)
        ttk.Entry(search_frame, width=25).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Search", style='TButton').pack(side=tk.LEFT)
        
        # Form Section with modern inputs
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.X, pady=10)
        
        labels = [
            "Date (YYYY-MM-DD):", "Course:", "Time (HH:MM):", "Location:",
            "Notes:", "Category:", "Reminder (min):", "Recurrence:"
        ]
        self.vars = {}
        for i, text in enumerate(labels):
            self.create_modern_input(form_frame, text, i)
        
        # Recurrence End field (placed below Recurrence)
        rec_end_frame = ttk.Frame(main_frame)
        rec_end_frame.pack(fill=tk.X, pady=5)
        ttk.Label(rec_end_frame, text="Recurrence End (YYYY-MM-DD):", width=25, anchor=tk.W).pack(side=tk.LEFT)
        self.rec_end_var = tk.StringVar()
        DateEntry(rec_end_frame, textvariable=self.rec_end_var, date_pattern='y-mm-dd').pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Recurrence Specific Days (for "Weekly (Specific Days)")
        self.weekly_frame = ttk.Frame(main_frame)
        self.weekly_frame.pack(fill=tk.X, pady=10)
        self.weekly_days_vars = {}
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in days:
            var = tk.BooleanVar()
            self.weekly_days_vars[day] = var
            chk = ttk.Checkbutton(self.weekly_frame, text=day[:3], variable=var)
            chk.pack(side=tk.LEFT, padx=2)
        self.weekly_frame.pack_forget()  # Hide by default
        
        # Action Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=20)
        actions = [
            ("Add Event", self.add_event),
            ("Update Event", self.update_event),
            ("Delete Event", self.delete_event),
            ("Close", self.win.destroy)
        ]
        for text, cmd in actions:
            ttk.Button(btn_frame, text=text, command=cmd, style='TButton').pack(side=tk.LEFT, padx=5, ipadx=10)
        
        # Listbox to show events on the given date
        ttk.Label(main_frame, text="Events on this date:", style='Modal.TLabel').pack(fill=tk.X, pady=5)
        self.event_listbox = tk.Listbox(main_frame, height=5)
        self.event_listbox.pack(fill=tk.BOTH, expand=True)
        self.event_listbox.bind("<<ListboxSelect>>", self.load_selected_event)
        
        self.update_listbox()

    def create_modern_input(self, parent, label_text, row):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        ttk.Label(frame, text=label_text, width=25, anchor=tk.W).pack(side=tk.LEFT)
        var = tk.StringVar()
        self.vars[label_text] = var
        if label_text == "Date (YYYY-MM-DD):":
            DateEntry(frame, textvariable=var, date_pattern='y-mm-dd').pack(side=tk.LEFT, fill=tk.X, expand=True)
        elif label_text == "Time (HH:MM):":
            ttk.Entry(frame, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        else:
            ttk.Entry(frame, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        # For the Recurrence field, bind to show/hide weekly selector
        if label_text == "Recurrence:":
            cb = ttk.Combobox(frame, textvariable=var, values=["None", "Daily", "Weekly", "Weekly (Specific Days)", "Monthly", "Yearly"], state="readonly")
            cb.current(0)
            cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
            cb.bind("<<ComboboxSelected>>", self.toggle_weekly_selector)

    def toggle_weekly_selector(self, event):
        rec = self.vars["Recurrence:"].get()
        if rec == "Weekly (Specific Days)":
            self.weekly_frame.pack(fill=tk.X, pady=10)
        else:
            self.weekly_frame.pack_forget()
    
    def update_listbox(self):
        self.event_listbox.delete(0, tk.END)
        date_val = self.vars["Date (YYYY-MM-DD):"].get().strip()
        self.cursor.execute("SELECT id, time, course FROM schedule WHERE date = ?", (date_val,))
        self.events = self.cursor.fetchall()
        for ev in self.events:
            display = f"{ev[1]} - {ev[2]}"
            self.event_listbox.insert(tk.END, display)
    
    def load_selected_event(self, event):
        if not self.event_listbox.curselection():
            return
        index = self.event_listbox.curselection()[0]
        ev = self.events[index]
        self.selected_event_id = ev[0]
        self.cursor.execute("SELECT * FROM schedule WHERE id = ?", (self.selected_event_id,))
        event_data = self.cursor.fetchone()
        if event_data:
            # event_data indices: 0=id, 1=date, 2=course, 3=time, 4=location, 5=notes, 6=category,
            # 7=recurrence_type, 8=recurrence_end, 9=recurrence_days, 10=reminder_time
            self.vars["Date (YYYY-MM-DD):"].set(event_data[1])
            self.vars["Course:"].set(event_data[2])
            self.vars["Time (HH:MM):"].set(event_data[3])
            self.vars["Location:"].set(event_data[4])
            self.vars["Notes:"].set(event_data[5])
            self.vars["Category:"].set(event_data[6])
            self.vars["Reminder (min):"].set(str(event_data[10]) if event_data[10] is not None else "")
            self.vars["Recurrence:"].set(event_data[7] if event_data[7] else "None")
            self.rec_end_var.set(event_data[8])
            if event_data[7] == "Weekly (Specific Days)" and event_data[9]:
                days_str = event_data[9]
                for day, var in self.weekly_days_vars.items():
                    var.set(day in [d.strip() for d in days_str.split(',')])
            else:
                for var in self.weekly_days_vars.values():
                    var.set(False)
    
    def validate_fields(self):
        date_val = self.vars["Date (YYYY-MM-DD):"].get().strip()
        course = self.vars["Course:"].get().strip()
        time_str = self.vars["Time (HH:MM):"].get().strip()
        location = self.vars["Location:"].get().strip()
        if not date_val or not course or not time_str or not location:
            messagebox.showerror("Error", "Date, Course, Time, and Location are required.")
            return False
        try:
            datetime.strptime(date_val, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Date must be in YYYY-MM-DD format.")
            return False
        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            messagebox.showerror("Error", "Time must be in HH:MM format (24-hour).")
            return False
        return True
    
    def add_event(self):
        if not self.validate_fields():
            return
        date_val = self.vars["Date (YYYY-MM-DD):"].get().strip()
        course = self.vars["Course:"].get().strip()
        time_str = self.vars["Time (HH:MM):"].get().strip()
        location = self.vars["Location:"].get().strip()
        notes = self.vars["Notes:"].get().strip()
        category = self.vars["Category:"].get().strip()
        reminder = self.vars["Reminder (min):"].get().strip() or 0
        rec_type = self.vars["Recurrence:"].get().strip()
        rec_end = self.rec_end_var.get().strip()
        rec_days = ""
        if rec_type == "Weekly (Specific Days)":
            rec_days = ",".join([day for day, var in self.weekly_days_vars.items() if var.get()])
        data = (date_val, course, time_str, location, notes, category, rec_type, rec_end, rec_days, reminder)
        try:
            self.cursor.execute('''
                INSERT INTO schedule (date, course, time, location, notes, category, recurrence_type, recurrence_end, recurrence_days, reminder_time)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            ''', data)
            self.conn.commit()
            messagebox.showinfo("Success", "Event added successfully.")
            self.update_listbox()
            self.parent_app.update_event_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def update_event(self):
        if not hasattr(self, "selected_event_id"):
            messagebox.showwarning("Warning", "Select an event from the list first.")
            return
        if not self.validate_fields():
            return
        date_val = self.vars["Date (YYYY-MM-DD):"].get().strip()
        course = self.vars["Course:"].get().strip()
        time_str = self.vars["Time (HH:MM):"].get().strip()
        location = self.vars["Location:"].get().strip()
        notes = self.vars["Notes:"].get().strip()
        category = self.vars["Category:"].get().strip()
        reminder = self.vars["Reminder (min):"].get().strip() or 0
        rec_type = self.vars["Recurrence:"].get().strip()
        rec_end = self.rec_end_var.get().strip()
        rec_days = ""
        if rec_type == "Weekly (Specific Days)":
            rec_days = ",".join([day for day, var in self.weekly_days_vars.items() if var.get()])
        data = (date_val, course, time_str, location, notes, category, rec_type, rec_end, rec_days, reminder, self.selected_event_id)
        try:
            self.cursor.execute('''
                UPDATE schedule SET date=?, course=?, time=?, location=?, notes=?, category=?, recurrence_type=?, recurrence_end=?, recurrence_days=?, reminder_time=?
                WHERE id=?
            ''', data)
            self.conn.commit()
            messagebox.showinfo("Success", "Event updated successfully.")
            self.update_listbox()
            self.parent_app.update_event_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def delete_event(self):
        if not hasattr(self, "selected_event_id"):
            messagebox.showwarning("Warning", "Select an event from the list first.")
            return
        if messagebox.askyesno("Confirm", "Delete this event?"):
            try:
                self.cursor.execute("DELETE FROM schedule WHERE id = ?", (self.selected_event_id,))
                self.conn.commit()
                messagebox.showinfo("Success", "Event deleted.")
                self.update_listbox()
                self.parent_app.update_event_list()
            except Exception as e:
                messagebox.showerror("Error", str(e))

# -------------------- Main Program --------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = ScheduleApp(root)
    root.mainloop()
