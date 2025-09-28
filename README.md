💡 DMX Light Controller (Tkinter + Python Serial)
โปรแกรมควบคุมไฟพาร์ DMX 512 ผ่านคอมพิวเตอร์ โดยใช้พอร์ต Serial (เช่น USB to DMX Adapter) และอินเทอร์เฟซผู้ใช้แบบกราฟิก (GUI) ที่สร้างด้วย Tkinter

🛠️ ความต้องการ (Requirements)
โปรแกรมนี้ต้องการไลบรารี Python สำหรับการสื่อสารผ่านพอร์ตซีเรียล และการสร้าง GUI:

Python 3.x

pyserial: สำหรับจัดการการเชื่อมต่อ DMX (Baud Rate 250000)

Tkinter: (มักจะมาพร้อมกับ Python อยู่แล้ว) สำหรับ GUI

การติดตั้งไลบรารี
ใช้ pip เพื่อติดตั้ง pyserial:

pip install pyserial

🚀 วิธีการใช้งาน (How to Use)
เชื่อมต่อ DMX Interface: เสียบ DMX Interface (เช่น USB-to-DMX Adapter) เข้ากับคอมพิวเตอร์

รันโปรแกรม:

python dmx_controller_gui.py

เลือกพอร์ต: เมื่อโปรแกรมเริ่มต้น จะมีหน้าต่าง "DMX Port Selection" ขึ้นมา

เลือกพอร์ต COM ที่เชื่อมต่อกับ DMX Interface ของคุณ

กดปุ่ม "Connect Selected Port"

ควบคุมไฟ:

ใช้ปุ่มโหมดต่าง ๆ (Color Chase, Party Mode, Strobe ฯลฯ) เพื่อเปลี่ยนเอฟเฟกต์

ใช้แถบ 🔆 Brightness เพื่อปรับความสว่างโดยรวมของทุกโหมด

ใช้ส่วน 🎨 Manual Color Control เพื่อกำหนดค่าสี RGB ด้วยตนเอง

การตั้งค่าไฟ (Configuration)
คุณสามารถปรับการตั้งค่า DMX ได้ที่เมนู "ตั้งค่า" (Settings) ที่ด้านบนของโปรแกรม:

ตั้งค่าจำนวนไฟพาร์: กำหนดจำนวนไฟพาร์ทั้งหมดที่ใช้งาน (โปรแกรมจะกำหนด Address อัตโนมัติ: Light 1 @ Ch 1, Light 2 @ Ch 9, Light 3 @ Ch 17, ฯลฯ)

ตั้งค่ารหัส Channel Group (A/B): เนื่องจากไฟพาร์บางรุ่นใช้ Channel สีที่ต่างกัน:

Group A (มาตรฐาน): Red = Ch 2, Green = Ch 3, Blue = Ch 4

Group B (ไฟบางรุ่น): Red = Ch 5, Green = Ch 6, Blue = Ch 7, White = Ch 8
คุณสามารถเลือก Group A หรือ B ให้กับไฟแต่ละดวงได้

⚙️ โครงสร้างและการทำงานของโปรแกรม
โปรแกรมนี้แบ่งการทำงานออกเป็น 3 ส่วนหลัก:

1. DMXController (การสื่อสาร)
ทำหน้าที่ เชื่อมต่อและส่งข้อมูล DMX ผ่านพอร์ต Serial

ใช้ pyserial ในการตั้งค่า Baud Rate เป็น 250000 (DMX Standard) และกำหนด Stop Bits เป็น 2

มี Array ขนาด 513 ไบต์ (dmx_data) สำหรับเก็บค่า Channel DMX ทั้งจักรวาล (Channel 0 คือ Start Code, Channel 1-512 คือ Dimmer/Color)

เมธอด send_data() จะรับผิดชอบในการส่งแพ็กเก็ต DMX ที่สมบูรณ์ รวมถึงการสร้างสัญญาณ Break และ Mark-After-Break (MAB) ก่อนส่งข้อมูล 512 Channels

2. LightEffect (การสร้างเอฟเฟกต์)
รับผิดชอบในการ คำนวณค่าสี และเอฟเฟกต์ตามโหมดที่เลือก

ใช้ Configuration ของไฟแต่ละดวง (Start Address และ Channel Group A/B) เพื่อกำหนดค่าที่ถูกต้อง

มีเมธอดต่าง ๆ เช่น color_chase(), rainbow_fade(), fire_effect() โดยอาศัยฟังก์ชันทางคณิตศาสตร์ (เช่น math.sin) และการแปลงสี (HSV to RGB) เพื่อสร้างแอนิเมชันที่ราบรื่น

3. DMXControllerGUI (ส่วนติดต่อผู้ใช้)
สร้างอินเทอร์เฟซด้วย Tkinter/ttk

จัดการการเลือก DMX Port และการตั้งค่าจำนวน/ประเภทของไฟ

รัน Animation Loop ใน Thread แยก (threading.Thread) เพื่อให้ GUI ไม่ค้างในขณะที่โปรแกรมกำลังคำนวณเอฟเฟกต์และส่งข้อมูล DMX อย่างต่อเนื่อง (ประมาณ 40 ครั้งต่อวินาที)

เมื่อผู้ใช้เลือกโหมด, GUI จะเปลี่ยนค่า self.current_mode และเธรด Animation Loop จะเรียกใช้เมธอด Effect ที่เกี่ยวข้อง
