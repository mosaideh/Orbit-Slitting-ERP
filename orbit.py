import streamlit as st
import math
from collections import Counter

# --- INVENTORY CONSTANTS ---
GERMAN_GREEN = {92.0: 20, 80.0: 9, 40.0: 6, 38.0: 6, 27.0: 8, 23.0: 8, 20.0: 16, 19.0: 2, 12.0: 18, 10.0: 15}
GERMAN_YELLOW = {92.0: 15, 80.0: 9, 40.0: 10, 38.0: 9, 27.0: 10, 23.0: 0, 20.0: 29, 19.0: 3, 12.0: 7, 10.0: 11, 9.6: 6}
CHINESE_GREEN = {92.0: 10, 80.0: 11, 38.0: 11, 23.0: 11, 20.0: 12}
CHINESE_YELLOW = {92.0: 10, 80.0: 11, 40.0: 1, 38.0: 13, 23.0: 10, 20.0: 11}
METAL_SPACERS_LIST = [5.0, 3.9, 3.5, 3.2, 3.0, 2.7, 2.5, 2.0, 1.86, 1.68, 1.32, 1.16, 1.14, 1.12, 1.1, 1.08, 1.06, 1.04, 1.02, 1.01, 1.0, 0.5]

# --- THE CORE LOGIC ---
class OrbitSlittingCalculator:
    def __init__(self, top_inv, bottom_inv, spacer_inv):
        self.top_inv = top_inv       
        self.bottom_inv = bottom_inv 
        self.spacer_inv = spacer_inv
        self.knife_width = 8.0

    def get_offset_targets(self, thickness):
        top_offset = 22.0
        if 0.20 <= thickness <= 0.45: return top_offset, 30.10
        elif 0.45 < thickness <= 0.75: return top_offset, 30.12
        elif 0.75 < thickness <= 1.05: return top_offset, 30.14
        elif 1.05 < thickness <= 1.35: return top_offset, 30.16
        elif 1.35 <= thickness <= 1.60: return top_offset, 30.18
        else: return None, None

    def _find_single_combo(self, target_width, rubber_inv, spacer_inv, banned_sizes=set()):
        target_int = int(round(target_width * 100))
        inv_int = {}
        for size, qty in rubber_inv.items():
            if qty > 0 and size not in banned_sizes: inv_int[int(round(size * 100))] = qty
        for size, qty in spacer_inv.items():
            if qty > 0: inv_int[int(round(size * 100))] = qty
                
        sizes_int = sorted(inv_int.keys(), reverse=True)
        dp = {0: []}
        
        for current_width in range(1, target_int + 1):
            best_combo = None
            for size in sizes_int:
                if current_width - size in dp:
                    prev_combo = dp[current_width - size]
                    if prev_combo.count(size) < inv_int[size]:
                        combo = prev_combo + [size]
                        if best_combo is None or len(combo) < len(best_combo): best_combo = combo
            if best_combo is not None: dp[current_width] = best_combo
            
        if target_int in dp: return [x / 100.0 for x in dp[target_int]]
        return None

    def get_multiple_arbor_options(self, slit_targets, max_options=5):
        solutions = []
        banned_rubbers = set()
        
        for _ in range(max_options):
            temp_bottleneck = {}
            for size in set(self.top_inv.keys()) | set(self.bottom_inv.keys()):
                temp_bottleneck[size] = min(self.top_inv.get(size, 0), self.bottom_inv.get(size, 0))
                
            temp_spacers = dict(self.spacer_inv)
            arbor_setup = []
            failed = False
            used_rubbers_in_option = []
            
            for target in slit_targets:
                combo = self._find_single_combo(target, temp_bottleneck, temp_spacers, banned_rubbers)
                if not combo: failed = True; break
                
                rubbers = sorted([x for x in combo if x >= 9.0], reverse=True)
                spacers = sorted([x for x in combo if x < 9.0], reverse=True)
                
                for r in rubbers:
                    temp_bottleneck[r] -= 1
                    used_rubbers_in_option.append(r)
                for s in spacers:
                    temp_spacers[s] -= 1
                    
                if len(rubbers) == 1:
                    top_y, top_g = rubbers, []
                    bot_g, bot_y = rubbers, []
                elif len(rubbers) > 1:
                    top_y = rubbers[:-1] 
                    top_g = [rubbers[-1]] 
                    bot_g = rubbers[:-1] 
                    bot_y = [rubbers[-1]] 
                else:
                    top_y, top_g, bot_g, bot_y = [], [], [], []
                
                arbor_setup.append({
                    'rubbers_used': rubbers,
                    'top': {'yellow': top_y, 'green': top_g, 'spacers': spacers},
                    'bottom': {'green': bot_g, 'yellow': bot_y, 'spacers': spacers}
                })
                
            if not failed:
                solutions.append(arbor_setup)
                if used_rubbers_in_option: banned_rubbers.add(max(used_rubbers_in_option))
                else: break
            else:
                break
        return solutions

# --- SMART ALLOY ENGINE ---
def analyze_alloy(alloy_code, thickness, width):
    alloy_str = str(alloy_code).strip()
    if alloy_str.startswith('1') or alloy_str.startswith('8'):
        cls, sigma = "سبيكة طرية (Soft)", 0.55
    elif alloy_str.startswith('3') or alloy_str.startswith('4'):
        cls, sigma = "سبيكة نصف قاسية (Medium)", 1.0
    elif alloy_str.startswith('5') or alloy_str.startswith('6') or alloy_str.startswith('7'):
        cls, sigma = "سبيكة قاسية (Hard)", 1.8
    else:
        cls, sigma = "غير مصنف (افتراضي: متوسط)", 1.0
        
    recoiler_tension = (thickness * width) * sigma
    back_tension = recoiler_tension * 0.5 
    
    if thickness < 0.35:
        taper_pct, taper_reason = 40, "سماكة رقيقة: تحتاج تخفيض عالي (40%) لمنع انهيار الكويل."
    elif 0.35 <= thickness < 0.8:
        taper_pct, taper_reason = 30, "سماكة متوسطة: تخفيض قياسي (30%) لمنع انبعاج الحواف."
    else:
        taper_pct, taper_reason = 15, "سماكة عالية: تتحمل الضغط، تخفيض بسيط (15%) فقط."
        
    end_tension = recoiler_tension * (1 - (taper_pct / 100))
    return cls, recoiler_tension, back_tension, taper_pct, end_tension, taper_reason

# --- STREAMLIT UI ---
st.set_page_config(page_title="Orbit Factory ERP", layout="wide", page_icon="⚙️")

st.markdown("""
    <style>
    [data-testid="stImage"] { background-color: #0b0f19; padding: 15px; border-radius: 12px; border: 1px solid #333; width: fit-content; margin-bottom: 20px;}
    .metric-card { background-color: #f8f9fa; border-left: 5px solid #0056b3; padding: 15px; border-radius: 5px; margin-bottom: 10px; color: #000;}
    /* تعديل بسيط لمحاذاة الشيك بوكس مع العداد */
    .stCheckbox { margin-top: 6px; } 
    </style>
""", unsafe_allow_html=True)

try:
    st.image("logo1.png", width=250)
except:
    pass

st.title("🏭 نظام أوربيت لإدارة التشريح والإنتاج")
st.markdown("---")

# -----------------------------------------
# SIDEBAR: SETUP & LIVE INVENTORY
# -----------------------------------------
st.sidebar.header("⚙️ المخزون المتاح حالياً")
rubber_origin = st.sidebar.radio("اختر نوع الربر بناءً على السماكة:", ["ألماني (أقل من 0.7 mm)", "صيني (أعلى من 0.7 mm)"])
origin_key = "ألماني" if "ألماني" in rubber_origin else "صيني"
st.sidebar.divider()

active_top, active_bottom, active_spacers = {}, {}, {}

# دالة مساعدة لإنشاء صف (Checkbox + NumberInput)
def create_inventory_row(label, default_qty, key_prefix):
    col1, col2 = st.columns([3, 2])
    with col1:
        is_active = st.checkbox(label, value=True, key=f"chk_{key_prefix}")
    with col2:
        qty = st.number_input("الكمية", min_value=0, value=default_qty, step=1, key=f"num_{key_prefix}", label_visibility="collapsed")
    return qty if is_active else 0

with st.sidebar.expander("⚙️ السبسرات (Spacers)", expanded=False):
    for s in METAL_SPACERS_LIST: 
        active_spacers[s] = create_inventory_row(f"سبسر {s} mm", 100, f"sp_{s}")

with st.sidebar.expander("🟡 ربر أصفر - علوي (ذكر)", expanded=True):
    ref_dict_yellow = GERMAN_YELLOW if origin_key == "ألماني" else CHINESE_YELLOW
    for s, qty in ref_dict_yellow.items(): 
        active_top[s] = create_inventory_row(f"أصفر {s} mm", qty, f"top_{s}")

with st.sidebar.expander("🟢 ربر أخضر - سفلي (أنثى)", expanded=True):
    ref_dict_green = GERMAN_GREEN if origin_key == "ألماني" else CHINESE_GREEN
    for s, qty in ref_dict_green.items(): 
        active_bottom[s] = create_inventory_row(f"أخضر {s} mm", qty, f"bot_{s}")

calc = OrbitSlittingCalculator(top_inv=active_top, bottom_inv=active_bottom, spacer_inv=active_spacers)

# Create 5 Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔪 هندسة الشرحات (Slits)", "⚙️ إعدادات الرأس (Head B)", "📐 حسابات الكويل (Coil Data)", "📦 تخطيط الدفعات (Batches)", "🎛️ هندسة الشد (Tension)"])

# -----------------------------------------
# TAB 1: MAIN SLIT CALCULATOR
# -----------------------------------------
with tab1:
    st.header("هندسة وتخطيط الشرحات (العلوي والسفلي المتطابق)")
    
    colA, colB = st.columns(2)
    with colA: coil_width = st.number_input("عرض الكويل الإجمالي (mm):", min_value=1.0, value=1000.0, step=1.0)
    with colB: num_slits = st.number_input("عدد الشرحات المطلوبة:", min_value=1, max_value=20, value=3, step=1)
        
    st.divider()
    st.subheader("أبعاد الشرحات")
    
    slit_widths = []
    cols = st.columns(min(num_slits, 4))
    for i in range(int(num_slits)):
        with cols[i % len(cols)]:
            w = st.number_input(f"عرض الشرحة {i+1} (mm):", min_value=0.1, value=float(coil_width/num_slits), step=0.1, key=f"slit_{i}")
            slit_widths.append(w)
            
    total_slits_width = sum(slit_widths)
    if total_slits_width > coil_width:
        st.error("⚠️ خطأ: المجموع يتجاوز عرض الكويل!")
    else:
        st.success(f"✅ العرض سليم. الفواقد (Scrap Trim): {coil_width - total_slits_width:.2f} mm")
        
        if st.button("ابحث عن تشكيلات للعمودين", type="primary"):
            spacer_targets = [w - calc.knife_width for w in slit_widths]
            if any(t < 0 for t in spacer_targets):
                st.error("أحد الشرحات أصغر من عرض السكينة!")
            else:
                options = calc.get_multiple_arbor_options(spacer_targets, max_options=5)
                if options:
                    st.info("✅ الكمية مناسبة! تم تجميع الخيارات بشكل متطابق هندسياً.")
                    for i, arbor_setup in enumerate(options):
                        st.markdown(f"""<div style="background-color: #ffeb3b; padding: 12px; border-radius: 8px; margin-top: 30px; margin-bottom: 15px; border: 2px solid #fbc02d;">
                            <h3 style="margin: 0; color: #000; text-align: center;">🛠️ الخيار الهندسي رقم {i + 1}</h3></div>""", unsafe_allow_html=True)
                        
                        total_rubbers = Counter()
                        for setup in arbor_setup: total_rubbers.update(setup['rubbers_used'])
                            
                        with st.expander("📦 اضغط لمعرفة فاتورة المواد الإجمالية (BOM)", expanded=False):
                            bom_c1, bom_c2 = st.columns(2)
                            with bom_c1:
                                st.info("**العمود العلوي (🟡 ذكر)**")
                                st.write(f"- 🔪 سكينة: **{num_slits} حبة**")
                                for size, count in sorted(total_rubbers.items(), reverse=True):
                                    st.write(f"- ربر أصفر مقاس {size} mm: **{count} حبة**")
                            with bom_c2:
                                st.success("**العمود السفلي (🟢 أنثى)**")
                                st.write(f"- 🔪 سكينة: **{num_slits} حبة**")
                                for size, count in sorted(total_rubbers.items(), reverse=True):
                                    st.write(f"- ربر أخضر مقاس {size} mm: **{count} حبة**")
                                
                        st.markdown("### 🔍 تفاصيل التركيب المتطابق لكل شرحة:")
                        for slit_idx, setup in enumerate(arbor_setup):
                            st.markdown(f"#### 🔹 الشرحة {slit_idx + 1} ({slit_widths[slit_idx]:.2f} mm)")
                            c1, c2 = st.columns(2)
                            
                            with c1:
                                st.markdown("🟡 **العمود العلوي (ذكر)**")
                                st.markdown("- 🔪 سكينة: 8.0 mm (x1)")
                                if setup['top']['yellow']:
                                    for s, q in sorted(Counter(setup['top']['yellow']).items(), reverse=True): st.markdown(f"- 🟡 ربر أصفر: {s} mm (x{q})")
                                if setup['top']['green']:
                                    for s, q in sorted(Counter(setup['top']['green']).items(), reverse=True): st.markdown(f"- 🟢 ربر أخضر: {s} mm (x{q})")
                                if setup['top']['spacers']:
                                    for s, q in sorted(Counter(setup['top']['spacers']).items(), reverse=True): st.markdown(f"- ⚙️ سبسر: {s} mm (x{q})")
                                    
                            with c2:
                                st.markdown("🟢 **العمود السفلي (أنثى)**")
                                st.markdown("- 🔪 سكينة: 8.0 mm (x1)")
                                if setup['bottom']['green']:
                                    for s, q in sorted(Counter(setup['bottom']['green']).items(), reverse=True): st.markdown(f"- 🟢 ربر أخضر: {s} mm (x{q})")
                                if setup['bottom']['yellow']:
                                    for s, q in sorted(Counter(setup['bottom']['yellow']).items(), reverse=True): st.markdown(f"- 🟡 ربر أصفر: {s} mm (x{q})")
                                if setup['bottom']['spacers']:
                                    for s, q in sorted(Counter(setup['bottom']['spacers']).items(), reverse=True): st.markdown(f"- ⚙️ سبسر: {s} mm (x{q})")
                            st.markdown("---")
                else:
                    st.error("❌ المخزون المزدوج (الأصفر والأخضر معاً لنفس المقاس) لا يكفي لتركيب العمودين.")

# -----------------------------------------
# TAB 2: HEAD B OFFSET
# -----------------------------------------
with tab2:
    st.header("إعدادات الرأس (Head B Offset)")
    thickness_b = st.number_input("سماكة الصاج (mm):", min_value=0.20, max_value=1.60, value=0.50, step=0.01)
    if st.button("احسب أبعاد الرأس", type="primary"):
        top_target, bottom_target = calc.get_offset_targets(thickness_b)
        if top_target:
            col1, col2 = st.columns(2)
            col1.metric("الجانب العلوي (أصفر)", f"{top_target} mm")
            col2.metric("الجانب السفلي (أخضر)", f"{bottom_target} mm")
            
            top_opt = calc._find_single_combo(top_target, calc.top_inv, calc.spacer_inv)
            if top_opt: st.info(f"**الترتيب العلوي:** " + " + ".join([f"{s}mm(x{c})" for s, c in sorted(Counter(top_opt).items(), reverse=True)]))
            else: st.warning("المخزون لا يغطي القياس العلوي.")
                
            bot_opt = calc._find_single_combo(bottom_target, calc.bottom_inv, calc.spacer_inv)
            if bot_opt: st.success(f"**الترتيب السفلي:** " + " + ".join([f"{s}mm(x{c})" for s, c in sorted(Counter(bot_opt).items(), reverse=True)]))
            else: st.warning("المخزون لا يغطي القياس السفلي.")

# -----------------------------------------
# TAB 3: COIL DATA
# -----------------------------------------
with tab3:
    st.header("حسابات الكويل (الأوزان، الأطوال، والقطر الخارجي)")
    calc_mode = st.radio("طريقة الحساب:", ["حساب الطول من الوزن", "حساب الوزن من الطول", "حساب الطول والوزن من القطر الخارجي (OD)"], horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        material = st.selectbox("المادة:", ["ألمنيوم (2.74)", "حديد (7.85)"])
        density = 2.74 if "ألمنيوم" in material else 7.85
        width_m = st.number_input("عرض الكويل (mm):", value=1230.0) / 1000.0
        thickness_coil = st.number_input("السماكة (mm):", min_value=0.01, value=0.27)
    with col2:
        line_speed = st.number_input("السرعة (m/min):", value=75.0)
        
        if calc_mode == "حساب الطول من الوزن":
            coil_weight = st.number_input("الوزن الإجمالي للكويل (kg):", value=4758.0)
        elif calc_mode == "حساب الوزن من الطول":
            coil_length_input = st.number_input("الطول الإجمالي للكويل (متر):", value=2060.0)
        else:
            outer_diameter = st.number_input("القطر الخارجي OD (mm):", value=1433.0)
            inner_diameter = st.number_input("القطر الداخلي ID (mm):", value=508.0)
            packing_factor = st.number_input("معامل الرص (Packing Factor %):", value=88.5) / 100.0
            
    if st.button("احسب بيانات الكويل", type="primary"):
        weight_per_meter = thickness_coil * width_m * density
        if weight_per_meter > 0:
            
            if calc_mode == "حساب الطول من الوزن":
                coil_length = coil_weight / weight_per_meter
            elif calc_mode == "حساب الوزن من الطول":
                coil_length = coil_length_input
                coil_weight = coil_length * weight_per_meter
            else:
                area_mm2 = (math.pi / 4.0) * ((outer_diameter**2) - (inner_diameter**2)) * packing_factor
                coil_length = area_mm2 / (thickness_coil * 1000.0)
                coil_weight = coil_length * weight_per_meter
                
            st.divider()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("الوزن لكل متر", f"{weight_per_meter:.3f} kg/m")
            c2.metric("الطول الإجمالي", f"{coil_length:,.1f} متر")
            c3.metric("الوزن الإجمالي", f"{coil_weight:,.1f} kg")
            c4.metric("وقت التشغيل", f"{coil_length / line_speed:.1f} دقيقة")

# -----------------------------------------
# TAB 4: BATCH PLANNING
# -----------------------------------------
with tab4:
    st.header("تخطيط دفعات الإنتاج للكويل")
    col_b1, col_b2 = st.columns(2)
    with col_b1: main_length = st.number_input("الطول الإجمالي للكويل (متر):", min_value=1.0, value=5000.0)
    with col_b2: num_batches = st.number_input("عدد الدفعات المطلوبة (Batches):", min_value=1, value=2)
    
    st.divider()
    if num_batches > 0:
        batch_length = main_length / num_batches
        st.metric(label="طول الدفعة الواحدة", value=f"{batch_length:,.1f} متر")
        b_cols = st.columns(min(num_batches, 6))
        for i in range(int(num_batches)):
            with b_cols[i % len(b_cols)]: st.info(f"**الدفعة {i+1}**\n\n{batch_length:,.1f} م")

# -----------------------------------------
# TAB 5: TENSION CALIBRATION
# -----------------------------------------
with tab5:
    st.header("🎛️ هندسة ومعايرة الشد (Tension Calibration)")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        sel_alloy = st.selectbox("نوع السبيكة (Alloy):", ["3105", "1050", "1100", "3003", "5005", "5052", "8011", "أخرى..."])
        alloy_input = st.text_input("إدخال يدوي:", value="3105") if sel_alloy == "أخرى..." else sel_alloy
    with col_t2: tension_thickness = st.number_input("سماكة الصاج (mm) لحساب الشد:", min_value=0.01, value=0.27)
    with col_t3: tension_width = st.number_input("إجمالي عرض الشرحات (mm):", min_value=1.0, value=1230.0)
        
    if st.button("⚙️ تحليل وحساب الشد", type="primary"):
        cls, rec_t, back_t, t_pct, end_t, t_reason = analyze_alloy(alloy_input, tension_thickness, tension_width)
        st.markdown(f"### 📊 تصنيف المادة: **{cls}**")
        st.markdown(f"""
        <div class="metric-card"><h4 style="margin:0; color:#0056b3;">1. قوة لف الريكويلر (Recoiler)</h4><h2 style="margin:0;">{rec_t:,.0f} Kg</h2></div>
        <div class="metric-card" style="border-left-color: #28a745;"><h4 style="margin:0; color:#28a745;">2. الشد العكسي (Back Tension)</h4><h2 style="margin:0;">{back_t:,.0f} Kg</h2></div>
        """, unsafe_allow_html=True)
        st.info(f"💡 **تحليل النظام للشد المتناقص:** {t_reason}")
        col_bar1, col_bar2 = st.columns([1, 3])
        with col_bar1: st.metric(label="نسبة الانخفاض (Taper)", value=f"% {t_pct}")
        with col_bar2:
            st.markdown(f"**سينخفض من `{rec_t:,.0f} Kg` إلى `{end_t:,.0f} Kg`**")
            st.progress(1.0 - (t_pct / 100.0))
