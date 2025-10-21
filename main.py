# -*- coding: utf-8 -*-
import os, time, threading, socket
from flask import Flask, request, redirect, url_for, render_template_string
import tkinter as tk
from PIL import Image, ImageTk
import qrcode

# -----------------------------
# مسارات وأساسيات
# -----------------------------
BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_local_ip():
    """يحاول الحصول على IP المحلي الحقيقي لشبكتك (ليس 127.0.0.1)."""
    ip = "127.0.0.1"
    try:
        import socket as _s
        s = _s.socket(_s.AF_INET, _s.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            pass
    return ip

def control_url():
    return f"http://{get_local_ip()}:5000"

# -----------------------------
# الحالة المشتركة
# -----------------------------
state_lock = threading.Lock()
state = {
    # اسم الشركة (هيدر متحرك)
    "company_name": "A.M Market",
    "company_color": "white",
    "company_bg": "#0d47a1",
    "company_font": "Arial",
    "company_size": 26,

    # البيانات
    "buyer": "علي مهدي",
    "product": "حاسوب محمول",
    "price": "750000",

    # ضبط عام
    "font": "Arial",
    "size": 22,
    "bg": "white",

    # الأشكال والألوان لكل حقل
    "shape_product": "rounded",  # rectangle/oval/rounded/diamond
    "shape_price": "diamond",
    "shape_buyer": "oval",

    "fill_product": "#e3f2fd",
    "outline_product": "#1565c0",
    "text_product": "#0d47a1",

    "fill_price": "#fff3e0",
    "outline_price": "#e65100",
    "text_price": "#b71c1c",

    "fill_buyer": "#e8f5e9",
    "outline_buyer": "#2e7d32",
    "text_buyer": "#1b5e20",

    # صورة المنتج
    "product_image_path": None,

    # مؤقّت (بدون تبييض)
    "end_at": None,

    # QR Code
    "show_qr": True,
    "qr_size": 160,  # بكسل

    # قفل التحديث
    "dirty": True,
}

# -----------------------------
# لوحة التحكم (Flask)
# -----------------------------
app = Flask(__name__)

CONTROL_HTML = """
<!doctype html>
<meta charset="utf-8">
<title>لوحة التحكم - شاشة العرض</title>
<style>
  body{font-family:system-ui,Segoe UI,Arial;background:#f6f7fb;margin:0}
  .wrap{max-width:940px;margin:24px auto;background:#fff;padding:18px 20px;border-radius:14px;box-shadow:0 10px 24px rgba(0,0,0,.06)}
  h1{margin:0 0 8px}
  fieldset{border:1px solid #e9e9e9;border-radius:12px;margin:12px 0;padding:12px}
  legend{padding:0 8px}
  label{display:block;margin:8px 0 4px}
  input[type=text],input[type=number],select{width:100%;padding:10px;border:1px solid #ddd;border-radius:10px}
  .row{display:flex;gap:12px;flex-wrap:wrap}
  .row > div{flex:1;min-width:220px}
  .btn{display:inline-block;padding:10px 14px;border-radius:10px;border:0;background:#0d47a1;color:#fff;cursor:pointer}
  .muted{color:#666;font-size:.9em}
  .bar{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
  .pill{background:#eef3ff;padding:6px 10px;border-radius:999px;display:inline-block}
</style>

<div class="wrap">
  <h1>لوحة التحكم (من الموبايل)</h1>
  <p class="muted">رابط التحكم: <span class="pill">{{ ctrl_url }}</span></p>

  <form action="/apply" method="post">
    <fieldset>
      <legend>اسم الشركة داخل الشاشة</legend>
      <div class="row">
        <div><label>الاسم</label><input name="company_name" type="text" value="{{s.company_name}}"></div>
        <div><label>الخط</label><input name="company_font" type="text" value="{{s.company_font}}"></div>
        <div><label>الحجم</label><input name="company_size" type="number" value="{{s.company_size}}"></div>
      </div>
      <div class="row">
        <div><label>لون النص</label><input name="company_color" type="text" value="{{s.company_color}}"></div>
        <div><label>لون الخلفية</label><input name="company_bg" type="text" value="{{s.company_bg}}"></div>
      </div>
    </fieldset>

    <fieldset>
      <legend>البيانات</legend>
      <div class="row">
        <div><label>اسم المنتج</label><input name="product" type="text" value="{{s.product}}"></div>
        <div><label>السعر</label><input name="price" type="text" value="{{s.price}}"></div>
        <div><label>اسم المشتري</label><input name="buyer" type="text" value="{{s.buyer}}"></div>
      </div>
    </fieldset>

    <fieldset>
      <legend>التنسيق العام</legend>
      <div class="row">
        <div><label>الخط</label><input name="font" type="text" value="{{s.font}}"></div>
        <div><label>الحجم</label><input name="size" type="number" value="{{s.size}}"></div>
        <div><label>خلفية الشاشة</label><input name="bg" type="text" value="{{s.bg}}"></div>
      </div>
    </fieldset>

    <fieldset>
      <legend>الأشكال والألوان</legend>
      <div class="row">
        <div>
          <label>شكل المنتج</label>
          <select name="shape_product">
            <option value="rectangle" {% if s.shape_product=='rectangle' %}selected{% endif %}>مستطيل</option>
            <option value="oval" {% if s.shape_product=='oval' %}selected{% endif %}>دائرة/بيضاوي</option>
            <option value="rounded" {% if s.shape_product=='rounded' %}selected{% endif %}>مستطيل بحواف دائرية</option>
            <option value="diamond" {% if s.shape_product=='diamond' %}selected{% endif %}>مُعين</option>
          </select>
          <label>تعبئة/حدود/نص</label>
          <div class="row">
            <div><input name="fill_product" type="text" value="{{s.fill_product}}"></div>
            <div><input name="outline_product" type="text" value="{{s.outline_product}}"></div>
            <div><input name="text_product" type="text" value="{{s.text_product}}"></div>
          </div>
        </div>

        <div>
          <label>شكل السعر</label>
          <select name="shape_price">
            <option value="rectangle" {% if s.shape_price=='rectangle' %}selected{% endif %}>مستطيل</option>
            <option value="oval" {% if s.shape_price=='oval' %}selected{% endif %}>دائرة/بيضاوي</option>
            <option value="rounded" {% if s.shape_price=='rounded' %}selected{% endif %}>مستطيل بحواف دائرية</option>
            <option value="diamond" {% if s.shape_price=='diamond' %}selected{% endif %}>مُعين</option>
          </select>
          <label>تعبئة/حدود/نص</label>
          <div class="row">
            <div><input name="fill_price" type="text" value="{{s.fill_price}}"></div>
            <div><input name="outline_price" type="text" value="{{s.outline_price}}"></div>
            <div><input name="text_price" type="text" value="{{s.text_price}}"></div>
          </div>
        </div>

        <div>
          <label>شكل اسم المشتري</label>
          <select name="shape_buyer">
            <option value="rectangle" {% if s.shape_buyer=='rectangle' %}selected{% endif %}>مستطيل</option>
            <option value="oval" {% if s.shape_buyer=='oval' %}selected{% endif %}>دائرة/بيضاوي</option>
            <option value="rounded" {% if s.shape_buyer=='rounded' %}selected{% endif %}>مستطيل بحواف دائرية</option>
            <option value="diamond" {% if s.shape_buyer=='diamond' %}selected{% endif %}>مُعين</option>
          </select>
          <label>تعبئة/حدود/نص</label>
          <div class="row">
            <div><input name="fill_buyer" type="text" value="{{s.fill_buyer}}"></div>
            <div><input name="outline_buyer" type="text" value="{{s.outline_buyer}}"></div>
            <div><input name="text_buyer" type="text" value="{{s.text_buyer}}"></div>
          </div>
        </div>
      </div>
    </fieldset>

    <fieldset>
      <legend>QR Code</legend>
      <div class="row">
        <div style="display:flex;align-items:center;gap:8px">
          <input type="checkbox" name="show_qr" value="1" {% if s.show_qr %}checked{% endif %}> إظهار QR على شاشة العرض
        </div>
        <div>
          <label>حجم QR (بكسل)</label>
          <input name="qr_size" type="number" value="{{s.qr_size}}">
          <div class="muted">هذا QR يفتح {{ ctrl_url }}</div>
        </div>
      </div>
    </fieldset>

    <div class="bar" style="margin-top:12px">
      <button class="btn" type="submit">حفظ/تطبيق</button>

      <form action="/start" method="post" class="bar">
        <label>مدة العرض (ثوانٍ)</label>
        <input name="seconds" type="number" value="10" style="width:120px">
        <button class="btn" type="submit">بدء العرض</button>
      </form>
    </div>
  </form>

  <hr>

  <form action="/upload" method="post" enctype="multipart/form-data">
    <label>رفع صورة المنتج (PNG/JPG)</label>
    <input type="file" name="file" accept="image/*">
    <button class="btn" type="submit">رفع</button>
    {% if s.product_image_path %}
      <div class="muted">الصورة الحالية: {{s.product_image_path}}</div>
    {% endif %}
  </form>
</div>
"""

@app.route("/")
def home():
    with state_lock:
        s = dict(state)
    return render_template_string(CONTROL_HTML, s=s, ctrl_url=control_url())

@app.route("/apply", methods=["POST"])
def apply():
    with state_lock:
        keys = [
            "company_name","company_color","company_bg","company_font",
            "product","price","buyer","font","bg",
            "shape_product","shape_price","shape_buyer",
            "fill_product","outline_product","text_product",
            "fill_price","outline_price","text_price",
            "fill_buyer","outline_buyer","text_buyer",
        ]
        for k in keys:
            val = request.form.get(k, "")
            if val != "":
                state[k] = val

        # حجم الخطوط
        if request.form.get("company_size"):
            try: state["company_size"] = int(request.form["company_size"])
            except: pass
        if request.form.get("size"):
            try: state["size"] = int(request.form["size"])
            except: pass

        # QR
        state["show_qr"] = request.form.get("show_qr") == "1"
        if request.form.get("qr_size"):
            try: state["qr_size"] = max(80, min(480, int(request.form["qr_size"])))
            except: pass

        state["dirty"] = True
    return redirect(url_for("home"))

@app.route("/start", methods=["POST"])
def start():
    sec = int(request.form.get("seconds","10") or "10")
    with state_lock:
        state["end_at"] = time.time() + max(1, sec)
        state["dirty"] = True
    return redirect(url_for("home"))

@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f:
        return redirect(url_for("home"))
    name = os.path.basename(f.filename or "product.png")
    path = os.path.join(UPLOAD_DIR, name)
    f.save(path)
    with state_lock:
        state["product_image_path"] = path
        state["dirty"] = True
    return redirect(url_for("home"))

# -----------------------------
# أدوات الرسم (Tkinter)
# -----------------------------
def draw_rounded_rect(c, x1, y1, x2, y2, r=20, **kw):
    r = min(r, (x2-x1)//2, (y2-y1)//2)
    c.create_rectangle(x1+r, y1, x2-r, y2, **kw)
    c.create_rectangle(x1, y1+r, x2, y2-r, **kw)
    c.create_arc(x1, y1, x1+2*r, y1+2*r, start=90, extent=90, style="pieslice", **kw)
    c.create_arc(x2-2*r, y1, x2, y1+2*r, start=0, extent=90, style="pieslice", **kw)
    c.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90, style="pieslice", **kw)
    c.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90, style="pieslice", **kw)

def draw_shape(c, shape, bbox, fill, outline, width=2):
    x1,y1,x2,y2 = bbox
    if shape == "rectangle":
        c.create_rectangle(x1,y1,x2,y2, fill=fill, outline=outline, width=width)
    elif shape == "oval":
        c.create_oval(x1,y1,x2,y2, fill=fill, outline=outline, width=width)
    elif shape == "rounded":
        draw_rounded_rect(c,x1,y1,x2,y2,r=22, fill=fill, outline=outline, width=width)
    elif shape == "diamond":
        cx=(x1+x2)//2; cy=(y1+y2)//2
        pts=[cx,y1, x2,cy, cx,y2, x1,cy]
        c.create_polygon(pts, fill=fill, outline=outline, width=width)

# -----------------------------
# تطبيق العرض (Tkinter)
# -----------------------------
class DisplayApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("شاشة العرض")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="white")
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        # هيدر الشركة
        self.banner = tk.Canvas(self.root, height=70, highlightthickness=0, bg="white")
        self.banner.pack(fill="x", side="top")
        self.banner_text_id = None
        self.banner_dx = 2

        # منطقة الحقول
        self.fields = tk.Canvas(self.root, height=320, highlightthickness=0, bg="white")
        self.fields.pack(fill="x", padx=40, pady=10)

        # منطقة الصورة
        self.image_area = tk.Frame(self.root, height=360, bg="white")
        self.image_area.pack(fill="both", expand=True, padx=40, pady=(0,20))
        self.image_area.pack_propagate(False)
        self.image_label = tk.Label(self.image_area, bg="white")
        self.image_label.pack(fill="both", expand=True)
        self.image_label.bind("<Configure>", lambda e: self.render())

        # QR أسفل يمين الشاشة (بدّلناه من أعلى يمين)
        self.qr_label = tk.Label(self.root, bg="white")
        self.qr_label.place(relx=1.0, rely=1.0, anchor="se", x=-16, y=-16)  # <<< أسفل يمين

        self.product_photo = None
        self.qr_photo = None

        # حلقات
        self.root.after(100, self.loop)
        self.root.after(60, self.animate_banner)

    def loop(self):
        with state_lock:
            # عند انتهاء الوقت: ما نبيّض الشاشة، فقط نوقف المؤقّت ونطنّ جرس خفيف
            if state["end_at"] and time.time() >= state["end_at"]:
                state["end_at"] = None
                state["dirty"] = True
                try:
                    self.root.bell()
                except Exception:
                    pass
            dirty = state["dirty"]

        if dirty:
            self.render()
            with state_lock:
                state["dirty"] = False
        self.root.after(120, self.loop)

    def animate_banner(self):
        if self.banner_text_id is not None:
            self.banner.move(self.banner_text_id, -self.banner_dx, 0)
            x1,y1,x2,y2 = self.banner.bbox(self.banner_text_id)
            W = self.banner.winfo_width()
            if x2 < 0:
                self.banner.move(self.banner_text_id, W - x1, 0)
        self.root.after(30, self.animate_banner)

    def _make_qr_image(self, url, size):
        qr = qrcode.QRCode(
            version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10, border=2
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        img = img.resize((size, size))
        return img

    def render(self):
        with state_lock:
            s = dict(state)

        # خلفيات
        self.root.config(bg=s["bg"])
        self.banner.config(bg=s["company_bg"])
        self.fields.config(bg=s["bg"])
        self.image_area.config(bg=s["bg"])
        self.image_label.config(bg=s["bg"])

        # (1) شريط الشركة
        self.banner.delete("all")
        name = s["company_name"] or "اسم الشركة"
        font = (s["company_font"] or "Arial", int(s["company_size"] or 26), "bold")
        color = s["company_color"] or "white"
        x_start = self.banner.winfo_width() or 800
        y = 35
        self.banner_text_id = self.banner.create_text(x_start, y, text=name, font=font, fill=color, anchor="w")

        # (1.1) QR أسفل يمين
        if s["show_qr"]:
            try:
                img = self._make_qr_image(control_url(), int(s["qr_size"]))
                self.qr_photo = ImageTk.PhotoImage(img)
                self.qr_label.config(image=self.qr_photo)
                self.qr_label.lift()  # فوق العناصر
            except Exception:
                self.qr_label.config(image="")
                self.qr_photo = None
        else:
            self.qr_label.config(image="")
            self.qr_photo = None

        # (2) الحقول بأشكالها
        self.fields.delete("all")
        W = self.fields.winfo_width() or 1200
        H = self.fields.winfo_height() or 320
        pad = 18
        row_h = (H - pad*4) // 3
        left = pad
        right = W - pad

        font_tuple = (s["font"] or "Arial", int(s["size"] or 22), "bold")

        # المنتج
        bbox1 = (left, pad, right, pad+row_h)
        draw_shape(self.fields, s["shape_product"], bbox1, s["fill_product"], s["outline_product"])
        self.fields.create_text((left+right)//2, pad+row_h//2, text=f"اسم المنتج: {s['product']}",
                                font=font_tuple, fill=s["text_product"], anchor="c")

        # السعر
        bbox2 = (left, pad*2+row_h, right, pad*2+row_h*2)
        draw_shape(self.fields, s["shape_price"], bbox2, s["fill_price"], s["outline_price"])
        self.fields.create_text((left+right)//2, pad*2+row_h+row_h//2, text=f"السعر: {s['price']} دينار",
                                font=font_tuple, fill=s["text_price"], anchor="c")

        # المشتري
        bbox3 = (left, pad*3+row_h*2, right, pad*3+row_h*3)
        draw_shape(self.fields, s["shape_buyer"], bbox3, s["fill_buyer"], s["outline_buyer"])
        self.fields.create_text((left+right)//2, pad*3+row_h*2+row_h//2, text=f"اسم المشتري: {s['buyer']}",
                                font=font_tuple, fill=s["text_buyer"], anchor="c")

        # (3) صورة المنتج
        self.product_photo = None
        if s["product_image_path"] and os.path.exists(s["product_image_path"]):
            try:
                img = Image.open(s["product_image_path"]).convert("RGBA")
                w = max(self.image_label.winfo_width(), 10)
                h = max(self.image_label.winfo_height(), 10)
                img.thumbnail((w, h))
                self.product_photo = ImageTk.PhotoImage(img)
                self.image_label.config(image=self.product_photo)
            except:
                self.image_label.config(image="")

# -----------------------------
# تشغيل Flask + Tkinter
# -----------------------------
def run_flask():
    # host=0.0.0.0 حتى يشتغل من الموبايل على نفس الشبكة
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    DisplayApp().root.mainloop()

if __name__ == "__main__":
    main()
