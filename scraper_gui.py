import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import queue
import os
from scraper import scrape, logger
from typing import Optional

class ScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Web Scraper Pro")
        self.root.geometry("900x700")
        
        # Set theme
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        self.colors = {
            'primary': '#2196F3',
            'secondary': '#64B5F6',
            'accent': '#FF9800',
            'background': '#F5F5F5',
            'text': '#212121',
            'success': '#4CAF50',
            'error': '#F44336',
            'warning': '#FFC107'
        }
        
        # Configure style
        style.configure('TFrame', background=self.colors['background'])
        style.configure('TLabel', background=self.colors['background'], foreground=self.colors['text'])
        style.configure('TButton', background=self.colors['primary'], foreground='white')
        style.configure('Accent.TButton', background=self.colors['accent'], foreground='white')
        style.configure('Success.TButton', background=self.colors['success'], foreground='white')
        style.configure('Error.TButton', background=self.colors['error'], foreground='white')
        
        # Queue for thread-safe communication
        self.queue = queue.Queue()
        
        # Create main container
        self.container = ttk.Frame(root, padding="20")
        self.container.pack(fill=tk.BOTH, expand=True)
        
        # Create header
        self.header_frame = ttk.Frame(self.container)
        self.header_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(self.header_frame, text="Web Scraper Pro", 
                 font=('Helvetica', 24, 'bold')).pack(side=tk.LEFT)
        
        # Create main content area
        self.content_frame = ttk.Frame(self.container)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create left panel
        self.left_panel = ttk.Frame(self.content_frame)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Create right panel
        self.right_panel = ttk.Frame(self.content_frame)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # URL Input
        self.url_frame = ttk.LabelFrame(self.left_panel, text="Target URL", padding="10")
        self.url_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.url_var = tk.StringVar(value="http://quotes.toscrape.com/")
        self.url_entry = ttk.Entry(self.url_frame, textvariable=self.url_var, width=40)
        self.url_entry.pack(fill=tk.X, pady=5)
        
        # Output File
        self.output_frame = ttk.LabelFrame(self.left_panel, text="Output Settings", padding="10")
        self.output_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.output_var = tk.StringVar(value="output.csv")
        self.output_entry = ttk.Entry(self.output_frame, textvariable=self.output_var, width=40)
        self.output_entry.pack(fill=tk.X, pady=5)
        
        self.browse_btn = ttk.Button(self.output_frame, text="Browse...", command=self.browse_file)
        self.browse_btn.pack(pady=5)
        
        # Scraping Settings
        self.settings_frame = ttk.LabelFrame(self.left_panel, text="Scraping Settings", padding="10")
        self.settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Max Pages
        ttk.Label(self.settings_frame, text="Max Pages:").pack(anchor=tk.W)
        self.max_pages_var = tk.StringVar(value="10")
        self.max_pages_entry = ttk.Spinbox(self.settings_frame, from_=1, to=100, 
                                         textvariable=self.max_pages_var, width=10)
        self.max_pages_entry.pack(fill=tk.X, pady=5)
        
        # Delay
        ttk.Label(self.settings_frame, text="Delay (seconds):").pack(anchor=tk.W)
        self.delay_var = tk.StringVar(value="1.0")
        self.delay_entry = ttk.Spinbox(self.settings_frame, from_=0.1, to=10, increment=0.1,
                                     textvariable=self.delay_var, width=10)
        self.delay_entry.pack(fill=tk.X, pady=5)
        
        # Mode (quotes or shop)
        ttk.Label(self.settings_frame, text="Mode:").pack(anchor=tk.W)
        self.mode_var = tk.StringVar(value="quotes")
        self.mode_combo = ttk.Combobox(self.settings_frame, textvariable=self.mode_var,
                                       values=["quotes", "shop"], state="readonly")
        self.mode_combo.pack(fill=tk.X, pady=5)
        ttk.Label(self.settings_frame, text="Max reviews per product (shop):").pack(anchor=tk.W)
        self.max_reviews_var = tk.StringVar(value="")
        self.max_reviews_entry = ttk.Spinbox(self.settings_frame, from_=0, to=10000, increment=1,
                                     textvariable=self.max_reviews_var, width=10)
        self.max_reviews_entry.pack(fill=tk.X, pady=5)
        
        # Control Buttons
        self.control_frame = ttk.Frame(self.left_panel)
        self.control_frame.pack(fill=tk.X, pady=10)
        
        self.start_btn = ttk.Button(self.control_frame, text="Start Scraping", 
                                  command=self.start_scraping, style='Success.TButton')
        self.start_btn.pack(fill=tk.X, pady=5)
        
        self.stop_btn = ttk.Button(self.control_frame, text="Stop", 
                                 command=self.stop_scraping, state=tk.DISABLED,
                                 style='Error.TButton')
        self.stop_btn.pack(fill=tk.X, pady=5)
        
        self.clear_btn = ttk.Button(self.control_frame, text="Clear Log", 
                                  command=self.clear_log, style='Accent.TButton')
        self.clear_btn.pack(fill=tk.X, pady=5)
        
        # Log Area
        self.log_frame = ttk.LabelFrame(self.right_panel, text="Scraping Log", padding="10")
        self.log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_area = scrolledtext.ScrolledText(self.log_frame, wrap=tk.WORD, 
                                                font=('Consolas', 10))
        self.log_area.pack(fill=tk.BOTH, expand=True)
        
        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self.right_panel, variable=self.progress_var, 
                                      maximum=100, mode='determinate')
        self.progress.pack(fill=tk.X, pady=10)
        
        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(self.right_panel, textvariable=self.status_var, 
                                  relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X)
        
        # Thread control
        self.stop_event = threading.Event()
        self.scraping_thread = None
        
        # Start the queue handler
        self.root.after(100, self.process_queue)
    
    def browse_file(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=self.output_var.get()
        )
        if filename:
            self.output_var.set(filename)
    
    def clear_log(self):
        self.log_area.delete(1.0, tk.END)
        self.status_var.set("Log cleared")
    
    def start_scraping(self):
        url = self.url_var.get().strip()
        output = self.output_var.get().strip()
        
        if not url:
            messagebox.showerror("Error", "Please enter a valid URL")
            return
        
        if not output:
            messagebox.showerror("Error", "Please specify an output file")
            return
        
        try:
            max_pages = int(self.max_pages_var.get())
            delay = float(self.delay_var.get())
            mr_raw = (self.max_reviews_var.get() or "").strip()
            max_reviews = int(mr_raw) if mr_raw != "" else None
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for Max Pages and Delay")
            return
        
        mode = (self.mode_var.get() or "quotes").strip()
        if mode not in ("quotes", "shop"):
            messagebox.showerror("Error", "Invalid mode. Choose 'quotes' or 'shop'.")
            return
        if max_reviews is not None and max_reviews <= 0:
            max_reviews = None
        
        # Clear previous logs
        self.log_area.delete(1.0, tk.END)
        self.status_var.set("Starting...")
        self.progress_var.set(0)
        
        # Disable controls
        self.toggle_controls(False)
        self.stop_event.clear()
        
        # Start scraping in a separate thread
        self.scraping_thread = threading.Thread(
            target=self.run_scraper,
            args=(url, output, delay, max_pages, mode, max_reviews),
            daemon=True
        )
        self.scraping_thread.start()
    
    def run_scraper(self, url: str, output: str, delay: float, max_pages: int, mode: str, max_reviews: Optional[int]):
        try:
            # Redirect logger to our queue
            import logging
            from functools import partial
            
            class QueueHandler(logging.Handler):
                def __init__(self, queue):
                    super().__init__()
                    self.queue = queue
                
                def emit(self, record):
                    self.queue.put(record.msg)
            
            # Configure logger
            logger = logging.getLogger("scrapper")
            logger.handlers = [QueueHandler(self.queue)]
            
            # Run the scraper
            self.queue.put(f"Starting scraping: {url} (mode={mode})")
            scrape(
                start_url=url,
                output=output,
                delay=delay,
                max_pages=max_pages,
                mode=mode,
                max_reviews_per_product=max_reviews
            )
            self.queue.put("Scraping completed successfully!")
            self.queue.put(("status", "Scraping completed!"))
            self.queue.put(("progress", 100))
            
        except Exception as e:
            self.queue.put(f"Error during scraping: {str(e)}")
            self.queue.put(("status", f"Error: {str(e)}"))
        finally:
            self.queue.put(("done", None))
    
    def stop_scraping(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to stop the current operation?"):
            self.stop_event.set()
            self.status_var.set("Stopping...")
    
    def toggle_controls(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.url_entry.config(state=state)
        self.output_entry.config(state=state)
        self.max_pages_entry.config(state=state)
        self.delay_entry.config(state=state)
        self.browse_btn.config(state=state)
        self.start_btn.config(state=state)
        self.stop_btn.config(state=tk.NORMAL if not enabled else tk.DISABLED)
    
    def process_queue(self):
        try:
            while True:
                try:
                    msg = self.queue.get_nowait()
                    if isinstance(msg, tuple):
                        if msg[0] == "status":
                            self.status_var.set(msg[1])
                        elif msg[0] == "progress":
                            self.progress_var.set(msg[1])
                        elif msg[0] == "done":
                            self.toggle_controls(True)
                    else:
                        self.log_area.insert(tk.END, msg + "\n")
                        self.log_area.see(tk.END)
                except queue.Empty:
                    break
        except Exception as e:
            self.log_area.insert(tk.END, f"Error processing queue: {str(e)}\n")
        
        self.root.after(100, self.process_queue)

def main():
    root = tk.Tk()
    app = ScraperApp(root)
    
    # Set window icon if available
    try:
        root.iconbitmap("scraper_icon.ico")  # Optional: add an icon file
    except:
        pass
    
    # Handle window close
    def on_closing():
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if hasattr(app, 'scraping_thread') and app.scraping_thread.is_alive():
                app.stop_scraping()
                app.root.after(100, root.destroy)
            else:
                root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
