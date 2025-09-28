import serial
import serial.tools.list_ports
import time
import os
import threading
import random
import math
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# ============== 💡 DMX Configuration Constants ==================
DMX_BAUD_RATE = 250000 # Standard DMX baud rate (250kbps)
CHANNELS_PER_LIGHT = 8 # Each light reserves 8 channels

# Channel maps definition based on the light type within the 8-channel block
CHANNEL_MAPS = {
    # Type A: Common small par light (Red on Ch 2)
    'A': {'dimmer': 1, 'red': 2, 'green': 3, 'blue': 4, 'white': 5, 'strobe': 6, 'mode': 7, 'speed': 8},
    # Type B: Based on the user's original CH_MAP (Red on Ch 5)
    'B': {'dimmer': 1, 'red': 5, 'green': 6, 'blue': 7, 'white': 8, 'strobe': 2, 'mode': 3, 'speed': 4}
}
# =======================================================


class DMXController:
    """Manages the DMX serial connection and data."""
    
    def __init__(self, port, baud_rate):
        self.port = port
        self.baud_rate = baud_rate
        self.ser = None
        self.dmx_data = bytearray([0] * 513) # DMX512 universe
        self.connected = False
        
        if not self.port:
            print("❌ DMX Port not selected.")
            return

        try:
            # Initialize serial connection
            self.ser = serial.Serial(self.port, self.baud_rate, bytesize=8, stopbits=2, timeout=0.1)
            self.connected = True
            print(f"✅ Connected to DMX port: {self.port}")
        except serial.SerialException as e:
            print(f"❌ Error connecting to DMX port {self.port}: {e}")
            self.connected = False

    def set_channel(self, channel, value):
        """Sets a specific DMX channel with a value (0-255)."""
        if 1 <= channel <= 512:
            self.dmx_data[channel] = int(max(0, min(255, value)))
            
    def send_data(self):
        """Sends the DMX data packet."""
        if self.connected and self.ser and self.ser.is_open:
            try:
                # DMX packet must start with a break, MAB, and start code (0x00)
                self.ser.sendBreak(duration=0.0001) # Break (100us min)
                time.sleep(0.000016) # Mark-After-Break (16us min)
                self.ser.write(self.dmx_data)
            except Exception as e:
                # Handle cases where the port disconnects mid-send
                print(f"Error sending DMX data: {e}. Disconnecting.")
                self.connected = False
                self.ser.close()


class LightEffect:
    """Handles different lighting effects using dynamic light configurations."""
    
    def __init__(self, dmx_controller, light_configs):
        self.dmx = dmx_controller
        self.light_configs = light_configs # Reference to the list of light configurations
        self.brightness = 128
        self.time_counter = 0

    def get_channel_map(self, light_type):
        """Returns the channel map (A or B) for a given light type."""
        return CHANNEL_MAPS.get(light_type, CHANNEL_MAPS['B'])

    def set_rgbw(self, light_index, r, g, b, w=0, dimmer_value=None):
        """Helper to set RGBW and Dimmer for a specific light index."""
        config = self.light_configs[light_index]
        start_channel = config['address']
        ch_map = self.get_channel_map(config['type'])
        
        dimmer = dimmer_value if dimmer_value is not None else self.brightness

        self.dmx.set_channel(start_channel + ch_map['dimmer'] - 1, dimmer)
        self.dmx.set_channel(start_channel + ch_map['red'] - 1, r)
        self.dmx.set_channel(start_channel + ch_map['green'] - 1, g)
        self.dmx.set_channel(start_channel + ch_map['blue'] - 1, b)
        self.dmx.set_channel(start_channel + ch_map['white'] - 1, w)

    # --- Core Helpers ---
    def hsv_to_rgb(self, h, s, v):
        """Convert HSV color to RGB values (0-255)."""
        h = h % 360
        s = max(0, min(1, s))
        v = max(0, min(1, v))
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c
        
        if 0 <= h < 60: r, g, b = c, x, 0
        elif 60 <= h < 120: r, g, b = x, c, 0
        elif 120 <= h < 180: r, g, b = 0, c, x
        elif 180 <= h < 240: r, g, b = 0, x, c
        elif 240 <= h < 300: r, g, b = x, 0, c
        else: r, g, b = c, 0, x
        
        return int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)

    # --- Lighting Modes (Refactored to use dynamic configuration) ---

    def white_light(self):
        """Mode 1: Pure white light."""
        for i in range(len(self.light_configs)):
            self.set_rgbw(i, 0, 0, 0, w=self.brightness)
    
    def color_chase(self):
        """Mode 2: Slow color chase with different colors per light."""
        for i in range(len(self.light_configs)):
            # Each light has a different phase offset
            phase = (self.time_counter + i * (360 // len(self.light_configs))) % 360
            r, g, b = self.hsv_to_rgb(phase, 1.0, self.brightness / 255.0)
            self.set_rgbw(i, r, g, b, w=0)
            
        self.time_counter += 2 
    
    def strobe_effect(self):
        """Mode 3: Fast strobe effect (White)."""
        strobe_on = (int(self.time_counter / 2) % 2) == 0
        intensity = 255 if strobe_on else 0
        
        for i in range(len(self.light_configs)):
            self.set_rgbw(i, 0, 0, 0, w=intensity, dimmer_value=intensity)
            
        self.time_counter += 1
    
    def dance_mode(self):
        """Mode 4: Rhythmic dance-like effect."""
        for i in range(len(self.light_configs)):
            light_beat = math.sin((self.time_counter + i * 30) * 0.25) * 0.5 + 0.5
            light_intensity = int(light_beat * self.brightness)
            
            # Alternate between warm and cool colors
            if i % 2 == 0:
                r, g, b = light_intensity, int(light_intensity * 0.7), 0
            else:
                r, g, b = 0, int(light_intensity * 0.7), light_intensity
            
            self.set_rgbw(i, r, g, b, w=0)
            
        self.time_counter += 3
    
    def rainbow_fade(self):
        """Mode 5: Smooth rainbow fade across all lights."""
        base_hue = (self.time_counter * 2) % 360
        
        for i in range(len(self.light_configs)):
            hue = (base_hue + i * (360 // len(self.light_configs))) % 360
            r, g, b = self.hsv_to_rgb(hue, 0.8, self.brightness / 255.0)
            self.set_rgbw(i, r, g, b, w=0)
            
        self.time_counter += 1
    
    def fire_effect(self):
        """Mode 6: Flickering fire effect (Red/Orange)."""
        for i in range(len(self.light_configs)):
            flicker = random.uniform(0.6, 1.0)
            base_intensity = int(self.brightness * flicker)
            
            red = base_intensity
            green = int(base_intensity * random.uniform(0.3, 0.7))
            blue = int(base_intensity * random.uniform(0.0, 0.2))
            
            self.set_rgbw(i, red, green, blue, w=0)
    
    def ocean_wave(self):
        """Mode 7: Ocean wave effect with blue and teal colors."""
        for i in range(len(self.light_configs)):
            wave = math.sin((self.time_counter + i * 40) * 0.1) * 0.5 + 0.5
            intensity = int(wave * self.brightness)
            
            red = 0
            green = int(intensity * 0.6)
            blue = intensity
            
            self.set_rgbw(i, red, green, blue, w=0)
            
        self.time_counter += 2
    
    def party_mode(self):
        """Mode 8: Fast random color changes."""
        if self.time_counter % 5 == 0:
            for i in range(len(self.light_configs)):
                r = random.randint(0, self.brightness)
                g = random.randint(0, self.brightness)
                b = random.randint(0, self.brightness)
                self.set_rgbw(i, r, g, b, w=0)
            
        self.time_counter += 1
    
    def lightning_effect(self):
        """Mode 9: Lightning effect with random bright flashes."""
        ambient = int(self.brightness * 0.1)
        
        if random.random() < 0.05: # 5% chance of lightning per frame
            for i in range(len(self.light_configs)):
                self.set_rgbw(i, 255, 255, 255, w=255, dimmer_value=255)
        else:
            for i in range(len(self.light_configs)):
                self.set_rgbw(i, 0, 0, ambient, w=0, dimmer_value=ambient)
    
    def turn_off_all(self):
        """Mode 0: Turn off all lights."""
        for i in range(len(self.light_configs)):
            self.set_rgbw(i, 0, 0, 0, w=0, dimmer_value=0)


class DMXControllerGUI:
    """GUI interface for DMX light controller."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🎨 DMX Light Controller")
        self.root.geometry("500x750")
        self.root.configure(bg='#1e1e1e') # Set root background

        # Set up a ttk style for better looking buttons (Dark theme)
        self.setup_styles()
        
        # --- State Variables ---
        self.selected_port = None
        self.num_lights = tk.IntVar(value=3)
        self.light_configs = [] # Stores: [{'type': 'A', 'address': 1}, ...]
        
        # --- Initialization ---
        self.selected_port = self._select_dmx_port_dialog()
        # If the user closed the port selection dialog without selecting a port, close the app.
        if not self.selected_port:
             self.root.destroy()
             return

        self._update_light_configs(self.num_lights.get())

        self.dmx = DMXController(self.selected_port, DMX_BAUD_RATE)
        self.effect = LightEffect(self.dmx, self.light_configs)
        
        self.current_mode = '0'
        self.is_running = False
        self.animation_thread = None
        
        self.create_widgets()
        self.start_animation()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_styles(self):
        """Setup ttk styles for a dark theme."""
        style = ttk.Style()
        
        # Configure a general dark theme style
        style.theme_use("clam") # Clam theme is usually good for customization
        
        # TButton style for the Connect button
        style.configure("TButton", 
                        background="#4e4e4e", 
                        foreground="#ffffff", 
                        font=("Arial", 10, "bold"),
                        relief="flat",
                        padding=5)
        style.map("TButton", 
                  background=[('active', '#5e5e5e')])
        
        # TFrame and TLabelframe
        style.configure("TFrame", background="#1e1e1e")
        style.configure("TLabelFrame", 
                        background="#1e1e1e", 
                        foreground="#ffffff") # Foreground for the label text
        style.configure("TLabel", 
                        background="#1e1e1e", 
                        foreground="#ffffff")
        style.configure("TRadiobutton", 
                        background="#1e1e1e", 
                        foreground="#ffffff")


    # --- Configuration Management ---

    def _get_start_address(self, index):
        """Calculate the starting DMX address for a light index."""
        return (index * CHANNELS_PER_LIGHT) + 1

    def _update_light_configs(self, new_count):
        """Update list of light configurations based on new count."""
        current_count = len(self.light_configs)
        
        if new_count > current_count:
            for i in range(current_count, new_count):
                self.light_configs.append({
                    'type': 'B', # Default new lights to Type B (like original code)
                    'address': self._get_start_address(i)
                })
        elif new_count < current_count:
            self.light_configs = self.light_configs[:new_count]
            
        # Ensure all addresses are updated (in case CHANNELS_PER_LIGHT changes, though fixed here)
        for i in range(new_count):
            self.light_configs[i]['address'] = self._get_start_address(i)

        self.num_lights.set(new_count)
    
    def _set_light_count(self):
        """Menu: Set the total number of par lights."""
        new_count = simpledialog.askinteger("ตั้งค่าจำนวนไฟพาร์", 
                                            "ระบุจำนวนไฟพาร์ทั้งหมด (8 Channels ต่อดวง):",
                                            initialvalue=self.num_lights.get(),
                                            minvalue=1,
                                            parent=self.root)
        if new_count is not None and new_count != self.num_lights.get():
            self._update_light_configs(new_count) 
            self._update_status_label() # Update display
            self.turn_off_all() # Reset lights
            
    def _set_light_type_dialog(self):
        """Menu: Set the channel group (A/B) for each light."""
        dialog = tk.Toplevel(self.root)
        dialog.title("ตั้งค่ารหัส Channel Group (A/B)")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Use ttk widgets for styling consistency with the Toplevel theme
        ttk.Label(dialog, text="กำหนดรหัสไฟ (A/B) เพื่อระบุตำแหน่ง Channel สี:", font=("Arial", 10, "bold")).pack(pady=10)
        
        type_vars = {}
        for i in range(self.num_lights.get()):
            config = self.light_configs[i]
            light_num = i + 1
            type_vars[i] = tk.StringVar(value=config['type'])
            
            frame = ttk.Frame(dialog)
            frame.pack(fill="x", padx=10, pady=2)
            
            ttk.Label(frame, text=f"LIGHT {light_num} (Ch {config['address']}):").pack(side="left")
            ttk.Radiobutton(frame, text="Group A (Red=Ch2)", variable=type_vars[i], value='A').pack(side="left", padx=10)
            ttk.Radiobutton(frame, text="Group B (Red=Ch5)", variable=type_vars[i], value='B').pack(side="left")

        def apply_changes():
            for i in range(self.num_lights.get()):
                new_type = type_vars[i].get()
                self.light_configs[i]['type'] = new_type
            dialog.destroy()
            self.turn_off_all() # Reset colors based on new channel map

        # Use tk.Button here if custom color is desired, otherwise ttk.Button
        ttk.Button(dialog, text="บันทึก", command=apply_changes).pack(pady=10)
        self.root.wait_window(dialog)


    # --- Port Selection Dialog ---

    def _select_dmx_port_dialog(self):
        """Displays a dialog for manual COM port selection."""
        ports = serial.tools.list_ports.comports()
        available_ports = [(p.device, f"{p.device} - {p.description}") for p in ports]
        
        if not available_ports:
            messagebox.showerror("Error", "ไม่พบพอร์ต COM ใดๆ โปรดตรวจสอบการเชื่อมต่อ DMX Interface")
            return None

        # Dialog setup
        dialog = tk.Toplevel(self.root)
        dialog.title("🔎 DMX Port Selection")
        dialog.grab_set()
        
        # Use ttk.Label (ttk widgets do not use bg/fg parameters directly)
        ttk.Label(dialog, text="DMX Port Selection", font=('Arial', 14, 'bold')).pack(pady=10)
        ttk.Label(dialog, text="โปรดเลือกพอร์ต COM สำหรับ DMX Interface:").pack(pady=5, padx=10)

        # Listbox for ports (tk.Listbox uses standard tk colors)
        list_frame = ttk.Frame(dialog)
        list_frame.pack(padx=10, fill="both", expand=True)

        listbox = tk.Listbox(list_frame, height=5, selectmode=tk.SINGLE, font=("Arial", 10),
                             bg='#2e2e2e', fg='#ffffff', selectbackground='#5e5e5e')
        listbox.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.configure(yscrollcommand=scrollbar.set)

        for _, port_info in available_ports:
            listbox.insert(tk.END, port_info)
        
        selected_port_device = tk.StringVar()

        def select_port():
            """Function linked to the 'Connect' button."""
            try:
                selected_index = listbox.curselection()[0]
                port_device, _ = available_ports[selected_index]
                selected_port_device.set(port_device)
                dialog.destroy()
            except IndexError:
                messagebox.showwarning("Warning", "กรุณาเลือกพอร์ตก่อนกดเชื่อมต่อ")

        # Use ttk.Button which supports the style defined in setup_styles
        ttk.Button(dialog, 
                   text="Connect Selected Port", 
                   command=select_port).pack(pady=10, padx=10)

        # Wait for dialog closure
        self.root.wait_window(dialog)
        
        return selected_port_device.get()

    # --- GUI Layout ---

    def _update_status_label(self):
        """Updates the connection and configuration status label."""
        port_text = self.dmx.port if self.dmx.port else "NONE"
        
        status_color = '#00ff00' if self.dmx.connected else '#ff0000'
        status_text = f"✅ Connected: {port_text}" if self.dmx.connected else f"❌ Disconnected: {port_text}"
        
        config_text = f" | ไฟ: {self.num_lights.get()} ดวง | Ch/ดวง: {CHANNELS_PER_LIGHT}"

        # status_label is a tk.Label, so fg can be used
        self.status_label.config(text=status_text + config_text, fg=status_color)
        
    def create_widgets(self):
        """Create all GUI widgets."""
        
        # Title (tk.Label)
        title_label = tk.Label(self.root, text="🎨 DMX Light Controller", 
                                font=("Arial", 20, "bold"), 
                                bg='#1e1e1e', fg='#ffffff')
        title_label.pack(pady=10)
        
        # Configuration Menu
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ตั้งค่า", menu=settings_menu)
        settings_menu.add_command(label="1. ตั้งค่าจำนวนไฟพาร์", command=self._set_light_count)
        settings_menu.add_command(label="2. ตั้งค่ารหัส Channel Group (A/B)", command=self._set_light_type_dialog)
        settings_menu.add_command(label="3. เปลี่ยน DMX Port", command=self._reconnect_dmx)


        # Connection status (tk.Label)
        self.status_label = tk.Label(self.root, font=("Arial", 10), bg='#1e1e1e')
        self.status_label.pack(pady=5)
        self._update_status_label()
        
        # Current mode display (tk.Label)
        self.mode_label = tk.Label(self.root, text="Current Mode: All Off",
                                    font=("Arial", 14, "bold"),
                                    bg='#1e1e1e', fg='#ffff00')
        self.mode_label.pack(pady=10)
        
        # Brightness control (tk.Frame)
        brightness_frame = tk.Frame(self.root, bg='#1e1e1e')
        brightness_frame.pack(pady=10)
        
        # tk.Label
        tk.Label(brightness_frame, text="🔆 Brightness:", 
                font=("Arial", 12), bg='#1e1e1e', fg='#ffffff').pack(side=tk.LEFT)
        
        # tk.Scale (uses standard tk colors)
        self.brightness_var = tk.IntVar(value=self.effect.brightness)
        self.brightness_scale = tk.Scale(brightness_frame, from_=0, to=255, 
                                        orient=tk.HORIZONTAL, length=200,
                                        variable=self.brightness_var,
                                        command=self.on_brightness_change,
                                        bg='#2e2e2e', fg='#ffffff', troughcolor='#444444',
                                        activebackground='#3e3e3e', highlightbackground='#1e1e1e')
        self.brightness_scale.pack(side=tk.LEFT, padx=10)
        
        # tk.Label
        self.brightness_label = tk.Label(brightness_frame, text=f"{self.effect.brightness}",
                                        font=("Arial", 12), bg='#1e1e1e', fg='#ffffff')
        self.brightness_label.pack(side=tk.LEFT)
        
        # Mode buttons (tk.Frame)
        modes_frame = tk.Frame(self.root, bg='#1e1e1e')
        modes_frame.pack(pady=10, padx=20)
        
        button_configs = [
            ("0", "🔴 All Off", "#ff4444", self.turn_off_all),
            ("1", "💡 White Light", "#ffffff", lambda: self.set_mode('1', 'White Light')),
            ("2", "🌈 Color Chase", "#ff6600", lambda: self.set_mode('2', 'Color Chase')),
            ("3", "⚡ Strobe", "#ffff00", lambda: self.set_mode('3', 'Strobe Effect')),
            ("4", "🕺 Dance Mode", "#ff00ff", lambda: self.set_mode('4', 'Dance Mode')),
            ("5", "🌈 Rainbow Fade", "#00ffff", lambda: self.set_mode('5', 'Rainbow Fade')),
            ("6", "🔥 Fire Effect", "#ff4400", lambda: self.set_mode('6', 'Fire Effect')),
            ("7", "🌊 Ocean Wave", "#0066ff", lambda: self.set_mode('7', 'Ocean Wave')),
            ("8", "🎉 Party Mode", "#ff0088", lambda: self.set_mode('8', 'Party Mode')),
            ("9", "⛈️ Lightning", "#8888ff", lambda: self.set_mode('9', 'Lightning Effect')),
        ]
        
        for i, (key, text, color, command) in enumerate(button_configs):
            row = i // 2
            col = i % 2
            
            # Use tk.Button to allow custom colors (bg/fg)
            btn = tk.Button(modes_frame, text=text, 
                            font=("Arial", 11, "bold"),
                            bg='#2e2e2e', fg=color, # Custom colors allowed on tk.Button
                            activebackground='#3e3e3e',
                            activeforeground=color,
                            width=18, height=2,
                            command=command, relief='raised', bd=2)
            btn.grid(row=row, column=col, padx=5, pady=5)
        
        # Manual color control (tk.LabelFrame)
        manual_frame = tk.LabelFrame(self.root, text="🎨 Manual Color Control", 
                                        font=("Arial", 12, "bold"),
                                        bg='#1e1e1e', fg='#ffffff', bd=3, relief=tk.GROOVE)
        manual_frame.pack(pady=20, padx=20, fill=tk.X)
        
        colors = [('Red', '#ff0000'), ('Green', '#00ff00'), ('Blue', '#0000ff')]
        self.color_vars = {}
        
        for color_name, color_code in colors:
            # tk.Frame
            frame = tk.Frame(manual_frame, bg='#1e1e1e')
            frame.pack(pady=5, fill=tk.X)
            
            # tk.Label
            tk.Label(frame, text=f"{color_name}:", width=6,
                     font=("Arial", 10), bg='#1e1e1e', fg=color_code).pack(side=tk.LEFT)
            
            var = tk.IntVar(value=0)
            self.color_vars[color_name.lower()] = var
            
            # tk.Scale
            tk.Scale(frame, from_=0, to=255, orient=tk.HORIZONTAL, 
                     length=250, variable=var,
                     bg='#2e2e2e', fg='#ffffff', troughcolor='#444444',
                     activebackground='#3e3e3e', highlightbackground='#1e1e1e').pack(side=tk.LEFT, padx=10)
        
        # tk.Button
        manual_btn = tk.Button(manual_frame, text="Apply Manual Colors to ALL Lights",
                                command=self.apply_manual_colors,
                                font=("Arial", 10, "bold"),
                                bg='#4e4e4e', fg='#ffffff',
                                activebackground='#5e5e5e')
        manual_btn.pack(pady=10)
    
    def on_brightness_change(self, value):
        """Handle brightness slider change."""
        self.effect.brightness = int(value)
        self.brightness_label.config(text=str(self.effect.brightness))
        
    def apply_manual_colors(self):
        """Apply manual RGB colors to all lights."""
        self.current_mode = 'manual'
        self.mode_label.config(text="Current Mode: Manual Colors")
        
        r = self.color_vars['red'].get()
        g = self.color_vars['green'].get()
        b = self.color_vars['blue'].get()
        
        # Manual mode requires setting channels directly using the configuration
        for i in range(len(self.light_configs)):
            self.effect.set_rgbw(i, r, g, b, w=0)
    
    def set_mode(self, mode, name):
        """Set lighting mode."""
        self.current_mode = mode
        self.effect.time_counter = 0 # Reset animation counter
        self.mode_label.config(text=f"Current Mode: {name}")
    
    def turn_off_all(self):
        """Turn off all lights."""
        self.current_mode = '0'
        self.mode_label.config(text="Current Mode: All Off")
        self.effect.turn_off_all()

    def _reconnect_dmx(self):
        """Close current connection, select new port, and reinitialize DMX."""
        # 1. Stop animation and close connection
        self.is_running = False
        if self.dmx.ser and self.dmx.ser.is_open:
            self.dmx.ser.close()
        
        # 2. Select new port
        new_port = self._select_dmx_port_dialog()
        
        # 3. Reinitialize DMX object
        if new_port:
            self.dmx = DMXController(new_port, DMX_BAUD_RATE)
            self.effect = LightEffect(self.dmx, self.light_configs)
            self._update_status_label()
            self.start_animation() # Restart thread
        else:
            self.dmx.connected = False
            self.dmx.port = "NONE"
            self._update_status_label()
            self.start_animation() # Restart thread (will run but won't send data)

    # --- Threading/Animation Loop ---
    
    def start_animation(self):
        """Start the animation thread if not running."""
        if not self.is_running:
            self.is_running = True
            self.animation_thread = threading.Thread(target=self.animation_loop, daemon=True)
            self.animation_thread.start()
    
    def animation_loop(self):
        """Main animation loop running in separate thread."""
        while self.is_running:
            try:
                # Only execute effect if not in manual mode (which is static)
                if self.current_mode != 'manual':
                    if self.current_mode == '0': self.effect.turn_off_all()
                    elif self.current_mode == '1': self.effect.white_light()
                    elif self.current_mode == '2': self.effect.color_chase()
                    elif self.current_mode == '3': self.effect.strobe_effect()
                    elif self.current_mode == '4': self.effect.dance_mode()
                    elif self.current_mode == '5': self.effect.rainbow_fade()
                    elif self.current_mode == '6': self.effect.fire_effect()
                    elif self.current_mode == '7': self.effect.ocean_wave()
                    elif self.current_mode == '8': self.effect.party_mode()
                    elif self.current_mode == '9': self.effect.lightning_effect()
                    
                # Send DMX data (DMXController handles connection check)
                self.dmx.send_data()
                time.sleep(0.025) # ~40 FPS
                
            except Exception as e:
                # Critical error in the loop thread
                print(f"Animation loop error: {e}")
                time.sleep(1.0)
    
    def on_closing(self):
        """Handle window closing."""
        self.is_running = False
        
        # Turn off all lights and send final data
        self.effect.turn_off_all()
        self.dmx.send_data()
        
        # Close serial connection
        if self.dmx.ser and self.dmx.ser.is_open:
            self.dmx.ser.close()
        
        # Wait for thread to finish gracefully
        if self.animation_thread and self.animation_thread.is_alive():
            self.animation_thread.join(timeout=1.0)
        
        self.root.destroy()

def main():
    """Main function to start the GUI."""
    try:
        root = tk.Tk()
        # Custom TTK style setup is required before GUI initialization
        # (The setup_styles method is called inside DMXControllerGUI's __init__)
        app = DMXControllerGUI(root)
        root.mainloop()
        
    except Exception as e:
        # This catch block is useful for errors that happen *before* the mainloop starts,
        # like the port selection issue, or now, the styling issue.
        messagebox.showerror("Error", f"Failed to start DMX Controller: {str(e)}")

if __name__ == '__main__':
    main()
