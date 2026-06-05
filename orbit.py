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
        banned_top = set()
        banned_bottom = set()
        
        for _ in range(max_options):
            temp_top = dict(self.top_inv)
            temp_bottom = dict(self.bottom_inv)
            temp_spacers = dict(self.spacer_inv)
            
            arbor_setup = []
            failed = False
            used_top_rubbers = []
            used_bottom_rubbers = []
            
            for target in slit_targets:
                top_combo = self._find_single_combo(target, temp_top, temp_spacers, banned_top)
                if not top_combo: failed = True; break
                for item in top_combo:
                    if item >= 9.0: 
                        temp_top[item] -= 1
                        used_top_rubbers.append(item)
                    else: temp_spacers[item] -= 1
                    
                bottom_combo = self._find_single_combo(target, temp_bottom, temp_spacers, banned_bottom)
                if not bottom_combo: failed = True; break
                for item in bottom_combo:
                    if item >= 9.0: 
                        temp_bottom[item] -= 1
                        used_bottom_rubbers.append(item)
                    else: temp_spacers[item] -= 1
                    
                arbor_setup.append({
                    'top': dict(Counter(top_combo)),
                    'bottom': dict(Counter(bottom_combo))
                })
                
            if not failed:
                solutions.append(arbor_setup)
                t_rubbers = [x for x in used_top_rubbers if x >= 9.0]
                b_rubbers = [x for x in used_bottom_rubbers if x >= 9.0]
                if t_rubbers: banned_top.add(max(t_rubbers))
                if b_rubbers: banned_bottom.add(max(b_rubbers))
                if not t_rubbers and not b_rubbers: break
            else:
                break
        return solutions

# --- STREAMLIT UI ---
st.set_page_config(page_title="Orbit Factory ERP", layout="wide", page_icon="⚙️")

# إدراج الشعار
try:
    st.image("orbit.jpg", width=250)
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

with st.sidebar.expander("⚙️ السبسرات (Spacers)", expanded=False):
    for s in METAL_SPACERS_LIST: active_spacers[s] = st.number_input(f"سبسر {s} mm", min_value=0, value=100, step=1, key=f"sp_{s}")

with st.sidebar.expander("🟡 ربر أصفر - علوي (ذكر)", expanded=True):
    ref_dict_yellow = GERMAN_YELLOW if origin_key == "ألماني" else CHINESE_YELLOW
    for s, qty in ref_dict_yellow.items(): active_top[s] = st.number_input(f"أصفر {s} mm", min_value=0, value=qty, step=1, key=f"top_{s}")

with st.sidebar.expander("🟢 ربر أخضر - سفلي (أنثى)", expanded=True):
    ref_dict_green = GERMAN_GREEN if origin_key == "ألماني" else CHINESE_GREEN
    for s, qty in ref_dict_green.items(): active_bottom[s] = st.number_input(f"أخضر {s} mm", min_value=0, value=qty, step=1, key=f"bot_{s}")

calc = OrbitSlittingCalculator(top_inv=active_top, bottom_inv=active_bottom, spacer_inv=active_spacers)

# Create 4 Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🔪 هندسة الشرحات (Slits)", 
    "⚙️ إعدادات الرأس (Head B)", 
    "📐 حسابات الكويل (Coil Data)", 
    "📦 تخطيط الدفعات (Batches)"
])

# -----------------------------------------
# TAB 1: MAIN SLIT CALCULATOR
# -----------------------------------------
with tab1:
    st.header("هندسة وتخطيط الشرحات (علوي وسفلي)")
    
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
        st.error(f"⚠️ خطأ: المجموع ({total_slits_width:.2f} mm) يتجاوز عرض الكويل ({coil_width:.2f} mm)!")
    else:
        st.success(f"✅ العرض سليم. الفواقد (Scrap Trim): {coil_width - total_slits_width:.2f} mm")
        
        if st.button("ابحث عن تشكيلات للعمودين", type="primary"):
            spacer_targets = [w - calc.knife_width for w in slit_widths]
            if any(t < 0 for t in spacer_targets):
                st.error("أحد الشرحات أصغر من عرض السكينة!")
            else:
                options = calc.get_multiple_arbor_options(spacer_targets, max_options=5)
                if options:
                    st.info("✅ الكمية مناسبة! تم إيجاد خيارات تتطابق مع المخزون.")
                    
                    for i, arbor_setup in enumerate(options):
                        # العنوان بخلفية صفراء بارزة للفصل بين الخيارات
                        st.markdown(f"""
                        <div style="background-color: #ffeb3b; padding: 12px; border-radius: 8px; margin-top: 30px; margin-bottom: 15px; border: 2px solid #fbc02d;">
                            <h3 style="margin: 0; color: #000; text-align: center;">🛠️ الخيار الهندسي رقم {i + 1}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # --- 1. BILL OF MATERIALS (BOM) HIDDEN IN EXPANDER ---
                        total_top = Counter()
                        total_bottom = Counter()
                        for setup in arbor_setup:
                            total_top.update(setup['top'])
                            total_bottom.update(setup['bottom'])
                            
                        with st.expander("📦 اضغط لمعرفة فاتورة المواد الإجمالية (BOM) لجميع الشرحات", expanded=False):
                            bom_c1, bom_c2 = st.columns(2)
                            with bom_c1:
                                st.info("**إجمالي القطع للعمود العلوي (🟡 ذكر):**")
                                st.write(f"- 🔪 سكينة مقاس 8.0 mm: **{num_slits} حبة**")
                                for size, count in sorted(total_top.items(), reverse=True):
                                    t_type = "ربر أصفر" if size >= 9.0 else "سبسر"
                                    st.write(f"- {t_type} مقاس {size} mm: **{count} حبة**")
                            with bom_c2:
                                st.success("**إجمالي القطع للعمود السفلي (🟢 أنثى):**")
                                st.write(f"- 🔪 سكينة مقاس 8.0 mm: **{num_slits} حبة**")
                                for size, count in sorted(total_bottom.items(), reverse=True):
                                    t_type = "ربر أخضر" if size >= 9.0 else "سبسر"
                                    st.write(f"- {t_type} مقاس {size} mm: **{count} حبة**")
                                
                        # --- 2. DETAILED SLIT BREAKDOWN VISIBLE ---
                        st.markdown("### 🔍 تفاصيل التركيب لكل شرحة:")
                        for slit_idx, setup in enumerate(arbor_setup):
                            st.markdown(f"#### 🔹 الشرحة {slit_idx + 1} (الهدف: {slit_widths[slit_idx]:.2f} mm)")
                            c1, c2 = st.columns(2)
                            
                            with c1:
                                st.markdown("🟡 **العمود العلوي (ذكر)**")
                                st.markdown(f"- 🔪 سكينة: 8.0 mm (x1)")
                                for size, count in sorted(setup['top'].items(), reverse=True):
                                    t_type = "ربر أصفر" if size >= 9.0 else "سبسر"
                                    st.markdown(f"- {t_type}: {size} mm (x{count})")
                                    
                            with c2:
                                st.markdown("🟢 **العمود السفلي (أنثى)**")
                                st.markdown(f"- 🔪 سكينة: 8.0 mm (x1)")
                                for size, count in sorted(setup['bottom'].items(), reverse=True):
                                    t_type = "ربر أخضر" if size >= 9.0 else "سبسر"
                                    st.markdown(f"- {t_type}: {size} mm (x{count})")
                            st.markdown("---")
                else:
                    st.error("❌ الكمية غير مناسبة! المخزون لا يكفي لتركيب العمودين لهذه الشرحات.")

# -----------------------------------------
# TAB 2: HEAD B OFFSET
# -----------------------------------------
with tab2:
    st.header("إعدادات الرأس (Head B Offset)")
    thickness = st.number_input("سماكة الصاج (mm):", min_value=0.20, max_value=1.60, value=0.50, step=0.01)
    if st.button("احسب أبعاد الرأس", type="primary"):
        top_target, bottom_target = calc.get_offset_targets(thickness)
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
# TAB 3: COIL DATA (Weight, Length, Outer Diameter)
# -----------------------------------------
with tab3:
    st.header("حسابات الكويل (الأوزان، الأطوال، والقطر الخارجي)")
    
    calc_mode = st.radio("طريقة الحساب:", ["حساب الطول من الوزن", "حساب الطول والوزن من القطر الخارجي (OD)"], horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        material = st.selectbox("المادة:", ["ألمنيوم (2.74)", "حديد (7.85)"])
        density = 2.74 if "ألمنيوم" in material else 7.85
        width_m = st.number_input("عرض الكويل (mm):", value=1230.0) / 1000.0
        thickness_coil = st.number_input("سماكة الصاج (mm):", min_value=0.01, value=0.27)
    
    with col2:
        line_speed = st.number_input("السرعة (m/min):", value=75.0)
        if calc_mode == "حساب الطول من الوزن":
            coil_weight = st.number_input("الوزن الإجمالي (kg):", value=4758.0)
        else:
            outer_diameter = st.number_input("القطر الخارجي OD (mm):", value=983.0)
            inner_diameter = st.number_input("القطر الداخلي ID (mm):", value=508.0)
            # إضافة معامل الرص لمعايرة الفراغات بين طبقات الصاج
            packing_factor = st.number_input("معامل الرص (Packing Factor %):", min_value=50.0, max_value=100.0, value=88.5, step=0.5, help="الصاج الملفوف يحتوي على فراغات هواء دقيقة تقلل من الوزن الفعلي مقارنة بالكتلة الصلبة.") / 100.0
            
    if st.button("احسب بيانات الكويل", type="primary"):
        weight_per_meter = thickness_coil * width_m * density
        
        if weight_per_meter > 0:
            if calc_mode == "حساب الطول من الوزن":
                coil_length = coil_weight / weight_per_meter
            else:
                # المعادلة الهندسية: الطول = المساحة الجانبية / السماكة
                # Area = (pi / 4) * (OD^2 - ID^2) * Packing Factor
                area_mm2 = (math.pi / 4.0) * ((outer_diameter**2) - (inner_diameter**2)) * packing_factor
                coil_length = area_mm2 / (thickness_coil * 1000.0)
                coil_weight = coil_length * weight_per_meter
                
            processing_time = coil_length / line_speed
            
            st.divider()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("الوزن لكل متر", f"{weight_per_meter:.3f} kg/m")
            c2.metric("طول الكويل المتوقع", f"{coil_length:,.1f} متر")
            c3.metric("الوزن الإجمالي", f"{coil_weight:,.1f} kg")
            c4.metric("وقت التشغيل", f"{processing_time:.1f} دقيقة")
            
            st.info(f"💡 انسخ الطول ({coil_length:,.1f} متر) لاستخدامه في تخطيط الدفعات في التبويب التالي.")

# -----------------------------------------
# TAB 4: BATCH PLANNING
# -----------------------------------------
with tab4:
    st.header("تخطيط دفعات الإنتاج للكويل")
    st.markdown("قسم الكويل الرئيسي إلى دفعات تصنيعية وحدد طول كل دفعة.")
    
    main_length = st.number_input("الطول الإجمالي للكويل (متر):", min_value=1.0, value=5000.0, step=10.0)
    num_batches = st.number_input("عدد الدفعات (Batches):", min_value=1, max_value=20, value=2, step=1)
    
    st.divider()
    st.subheader("أطوال الدفعات (متر)")
    
    batch_lengths = []
    b_cols = st.columns(min(num_batches, 4))
    
    for i in range(int(num_batches)):
        with b_cols[i % len(b_cols)]:
            b_len = st.number_input(f"طول الدفعة {i+1} (متر):", min_value=0.0, value=float(main_length/num_batches), step=10.0, key=f"batch_{i}")
            batch_lengths.append(b_len)
            
    total_batches = sum(batch_lengths)
    remaining = main_length - total_batches
    
    st.markdown("### ملخص الإنتاج")
    
    if total_batches > main_length:
        st.error(f"⚠️ خطأ: مجموع أطوال الدفعات ({total_batches:,.1f} م) يتجاوز الطول الكلي للكويل ({main_length:,.1f} م)!")
        st.progress(1.0)
    else:
        percentage = total_batches / main_length
        st.progress(percentage)
        
        col_res1, col_res2 = st.columns(2)
        col_res1.metric("مجموع أطوال الدفعات الحالية", f"{total_batches:,.1f} متر")
        col_res2.metric("الطول المتبقي من الكويل", f"{remaining:,.1f} متر")
        
        if remaining == 0:
            st.success("✅ تم توزيع الكويل بالكامل بدقة على الدفعات.")
        else:
            st.info("ℹ️ يوجد طول متبقي في الكويل يمكن توزيعه على الدفعات أو تخزينه كباقي (Remnant).")
