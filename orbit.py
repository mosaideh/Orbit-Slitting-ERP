import streamlit as st
import math
from collections import Counter

# --- STREAMLIT CONFIG & TRANSLATION ENGINE ---
st.set_page_config(page_title="Orbit Factory ERP", layout="wide", page_icon="⚙️")

# جعل الإنجليزية هي اللغة الافتراضية
lang = st.sidebar.radio("🌐 Interface / واجهة المستخدم", ["English", "العربية"])

def tr(ar_text, en_text):
    return en_text if lang == "English" else ar_text

# --- INVENTORY CONSTANTS ---
GERMAN_GREEN = {92.0: 20, 80.0: 9, 40.0: 6, 38.0: 6, 27.0: 8, 23.0: 8, 20.0: 16, 19.0: 2, 12.0: 18, 10.0: 15}
GERMAN_YELLOW = {92.0: 15, 80.0: 9, 40.0: 10, 38.0: 9, 27.0: 10, 23.0: 0, 20.0: 29, 19.0: 3, 12.0: 7, 10.0: 11, 9.6: 6}
CHINESE_GREEN = {92.0: 10, 80.0: 11, 38.0: 11, 23.0: 11, 20.0: 12}
CHINESE_YELLOW = {92.0: 10, 80.0: 11, 40.0: 1, 38.0: 13, 23.0: 10, 20.0: 11}
METAL_SPACERS_LIST = [5.0, 3.9, 3.5, 3.2, 3.0, 2.7, 2.5, 2.0, 1.86, 1.68, 1.32, 1.16, 1.14, 1.12, 1.1, 1.08, 1.06, 1.04, 1.02, 1.01, 1.0, 0.5]

# --- THE CORE LOGIC (V9: PENALTY-BASED HYBRID ENGINE) ---
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

    def _find_single_combo_legacy(self, target_width, rubber_inv, spacer_inv):
        target_int = int(round(target_width * 100))
        sizes = sorted([int(round(s*100)) for s,q in list(rubber_inv.items()) + list(spacer_inv.items()) if q>0], reverse=True)
        inv = {int(round(s*100)): q for s,q in list(rubber_inv.items()) + list(spacer_inv.items()) if q>0}
        dp = {0: []}
        for w in range(1, target_int + 1):
            best = None
            for sz in sizes:
                if w - sz in dp:
                    prev = dp[w-sz]
                    if prev.count(sz) < inv.get(sz, 0):
                        cand = prev + [sz]
                        if best is None or len(cand) < len(best): best = cand
            if best is not None: dp[w] = best
        if target_int in dp:
            return sorted([x/100.0 for x in dp[target_int]], reverse=True)
        return None

    def _get_color_needs(self, top_c_int, bot_c_int):
        y_n = Counter()
        g_n = Counter()
        if len(top_c_int) == 1: 
            y_n[top_c_int[0]] += 1
        elif len(top_c_int) > 1:
            for x in top_c_int[:-1]: y_n[x] += 1
            g_n[top_c_int[-1]] += 1
            
        if len(bot_c_int) == 1: 
            g_n[bot_c_int[0]] += 1
        elif len(bot_c_int) > 1:
            for x in bot_c_int[:-1]: g_n[x] += 1
            y_n[bot_c_int[-1]] += 1
        return y_n, g_n

    def get_multiple_arbor_options(self, slit_targets, max_options=5):
        s_int = {int(round(k*100)): v for k, v in self.spacer_inv.items() if v > 0}
        s_sizes = sorted(s_int.keys(), reverse=True)
        
        y_inv_int = {int(round(k*100)): v for k, v in self.top_inv.items() if v > 0}
        g_inv_int = {int(round(k*100)): v for k, v in self.bottom_inv.items() if v > 0}
        
        r_sizes_set = set(y_inv_int.keys()) | set(g_inv_int.keys())
        r_sizes = sorted(list(r_sizes_set), reverse=True)
        
        all_slit_combos = []
        for t_width in slit_targets:
            target_int = int(round(t_width * 100))
            dp_sp = {0: []}
            for w in range(1, target_int + 1):
                best = None
                for sp in s_sizes:
                    if w - sp in dp_sp:
                        prev = dp_sp[w - sp]
                        if prev.count(sp) < s_int.get(sp, 0):
                            cand = prev + [sp]
                            if best is None or len(cand) < len(best): best = cand
                if best is not None: dp_sp[w] = best
                    
            def find_r(target, max_len=7):
                res = []
                def dfs(rem, path, idx):
                    if rem == 0:
                        res.append(path)
                        return
                    if idx >= len(r_sizes) or len(path) > max_len: return
                    size = r_sizes[idx]
                    max_q = min(12, rem // size) 
                    for q in range(max_q, -1, -1):
                        dfs(rem - q * size, path + [size]*q, idx + 1)
                dfs(target, [], 0)
                return res

            options_for_this_slit = []
            for sp_w, sp_combo in dp_sp.items():
                r_w = target_int - sp_w
                if r_w < 0: continue
                
                r_combos = find_r(r_w)
                for top_c in r_combos:
                    for bot_c in r_combos:
                        if top_c.count(9200) == bot_c.count(9200):
                            y_needs, g_needs = self._get_color_needs(top_c, bot_c)
                            possible = True
                            for s, q in y_needs.items():
                                if y_inv_int.get(s, 0) < q: possible = False; break
                            if possible:
                                for s, q in g_needs.items():
                                    if g_inv_int.get(s, 0) < q: possible = False; break
                            
                            if possible:
                                is_sym = (top_c == bot_c)
                                # النظام هنا يعاقب التطابق اللامتماثل بـ 50 نقطة لمنع اختياره كخيار أساسي
                                penalty = 0 if is_sym else 50
                                cost = len(top_c) + len(bot_c) + len(sp_combo) + penalty
                                
                                options_for_this_slit.append({
                                    'top_r': [x/100.0 for x in top_c],
                                    'bot_r': [x/100.0 for x in bot_c],
                                    'sp': [x/100.0 for x in sp_combo],
                                    'y_needs': y_needs,
                                    'g_needs': g_needs,
                                    'is_sym': is_sym,
                                    'cost': cost
                                })
            
            # ترتيب خيارات الشرحة الواحدة بحيث تطفو الخيارات المتطابقة (صفر عقوبة) للأعلى
            options_for_this_slit.sort(key=lambda x: x['cost'])
            all_slit_combos.append(options_for_this_slit)

        valid_arbors = []
        def build_arbor(slit_idx, rem_y, rem_g, rem_s, current_arbor):
            if len(valid_arbors) >= 200: return
            if slit_idx == len(slit_targets):
                valid_arbors.append(current_arbor)
                return
                
            for opt in all_slit_combos[slit_idx]:
                y_needs, g_needs = opt['y_needs'], opt['g_needs']
                sp_c = Counter([int(round(x*100)) for x in opt['sp']])
                
                possible = True
                for s, q in y_needs.items():
                    if rem_y.get(s, 0) < q: possible = False; break
                if not possible: continue
                for s, q in g_needs.items():
                    if rem_g.get(s, 0) < q: possible = False; break
                if not possible: continue
                for s, q in sp_c.items():
                    if rem_s.get(s, 0) < q: possible = False; break
                if not possible: continue
                
                next_y = dict(rem_y)
                for s, q in y_needs.items(): next_y[s] -= q
                next_g = dict(rem_g)
                for s, q in g_needs.items(): next_g[s] -= q
                next_s = dict(rem_s)
                for s, q in sp_c.items(): next_s[s] -= q
                
                build_arbor(slit_idx + 1, next_y, next_g, next_s, current_arbor + [opt])
                
        build_arbor(0, y_inv_int, g_inv_int, s_int, [])
        
        if not valid_arbors: return []
            
        # فرز الأعمدة حسب التكلفة الإجمالية لضمان صدارة الأعمدة المتطابقة 100%
        valid_arbors.sort(key=lambda arb: sum(c['cost'] for c in arb))
        
        selected_options = []
        seen_signatures = set()
        
        for arbor in valid_arbors:
            if len(selected_options) >= max_options: break
                
            rubbers_flat = []
            has_asym = False
            for combo in arbor:
                rubbers_flat.extend(combo['top_r'])
                rubbers_flat.extend(combo['bot_r'])
                if not combo['is_sym']: has_asym = True
            
            c = Counter(rubbers_flat)
            # دمج وجود اللاتماثل في البصمة ليعتبره النظام تنوعاً مستقلاً
            sig = (c.get(92.0, 0), c.get(80.0, 0), c.get(40.0, 0), c.get(38.0, 0), has_asym)
            
            if sig not in seen_signatures:
                seen_signatures.add(sig)
                
                formatted_arbor = []
                for combo in arbor:
                    t_r = sorted(combo['top_r'], reverse=True)
                    b_r = sorted(combo['bot_r'], reverse=True)
                    s_used = sorted(combo['sp'], reverse=True)
                    
                    if len(t_r) == 1:
                        top_y, top_g = t_r, []
                    elif len(t_r) > 1:
                        top_y, top_g = t_r[:-1], [t_r[-1]]
                    else:
                        top_y, top_g = [], []
                        
                    if len(b_r) == 1:
                        bot_g, bot_y = b_r, []
                    elif len(b_r) > 1:
                        bot_g, bot_y = b_r[:-1], [b_r[-1]]
                    else:
                        bot_g, bot_y = [], []
                        
                    formatted_arbor.append({
                        'top': {'yellow': top_y, 'green': top_g, 'spacers': s_used},
                        'bottom': {'green': bot_g, 'yellow': bot_y, 'spacers': s_used},
                        'is_sym': combo['is_sym']
                    })
                selected_options.append(formatted_arbor)
                
        return selected_options

# --- SMART ALLOY ENGINE ---
def analyze_alloy(alloy_code, thickness, width):
    alloy_str = str(alloy_code).strip()
    if alloy_str.startswith('1') or alloy_str.startswith('8'):
        cls = tr("سبيكة طرية (Soft)", "Soft Alloy (1xxx/8xxx)")
        sigma = 0.55
    elif alloy_str.startswith('3') or alloy_str.startswith('4'):
        cls = tr("سبيكة نصف قاسية (Medium)", "Medium Hard Alloy (3xxx/4xxx)")
        sigma = 1.0
    elif alloy_str.startswith('5') or alloy_str.startswith('6') or alloy_str.startswith('7'):
        cls = tr("سبيكة قاسية (Hard)", "Hard Alloy (5xxx/6xxx)")
        sigma = 1.8
    else:
        cls = tr("غير مصنف (افتراضي: متوسط)", "Unclassified (Default: Medium)")
        sigma = 1.0
        
    recoiler_tension = (thickness * width) * sigma
    back_tension = recoiler_tension * 0.5 
    
    if thickness < 0.35:
        taper_pct = 40
        taper_reason = tr("سماكة رقيقة: تحتاج تخفيض عالي (40%) لمنع انهيار الكويل.", "Thin Gauge: High Taper (40%) required to prevent inner coil collapse.")
    elif 0.35 <= thickness < 0.8:
        taper_pct = 30
        taper_reason = tr("سماكة متوسطة: تخفيض قياسي (30%) لمنع انبعاج الحواف.", "Medium Gauge: Standard Taper (30%) required to prevent edge build-up.")
    else:
        taper_pct = 15
        taper_reason = tr("سماكة عالية: تتحمل الضغط العالي، تخفيض بسيط (15%) فقط.", "Heavy Gauge: Withstands pressure, low Taper (15%) required.")
        
    end_tension = recoiler_tension * (1 - (taper_pct / 100))
    return cls, recoiler_tension, back_tension, taper_pct, end_tension, taper_reason

# --- STREAMLIT UI ---
st.markdown("""
    <style>
    [data-testid="stImage"] { background-color: #0b0f19; padding: 15px; border-radius: 12px; border: 1px solid #333; width: fit-content; margin-bottom: 20px;}
    .metric-card { background-color: #f8f9fa; border-left: 5px solid #0056b3; padding: 15px; border-radius: 5px; margin-bottom: 10px; color: #000;}
    .stCheckbox { margin-top: 6px; } 
    </style>
""", unsafe_allow_html=True)

try:
    st.image("logo.png", width=250)
except:
    pass

st.title(tr("🏭 نظام أوربيت لإدارة التشريح والإنتاج", "🏭 Orbit Slitting & Production Management System"))
st.markdown("---")

# -----------------------------------------
# SIDEBAR: SETUP & LIVE INVENTORY
# -----------------------------------------
st.sidebar.header(tr("⚙️ المخزون المتاح حالياً", "⚙️ Current Available Inventory"))
rubber_origin = st.sidebar.radio(tr("اختر نوع الربر بناءً على السماكة:", "Select Rubber Type (by thickness):"), 
                                 [tr("ألماني (أقل من 0.7 mm)", "German (< 0.7 mm)"), tr("صيني (أعلى من 0.7 mm)", "Chinese (> 0.7 mm)")])
origin_key = "ألماني" if "ألماني" in rubber_origin or "German" in rubber_origin else "صيني"
st.sidebar.divider()

active_top, active_bottom, active_spacers = {}, {}, {}

def create_inventory_row(label, default_qty, key_prefix):
    col1, col2 = st.columns([3, 2])
    with col1:
        is_active = st.checkbox(label, value=True, key=f"chk_{key_prefix}")
    with col2:
        qty = st.number_input(tr("الكمية", "Qty"), min_value=0, value=default_qty, step=1, key=f"num_{key_prefix}", label_visibility="collapsed")
    return qty if is_active else 0

with st.sidebar.expander(tr("⚙️ السبسرات (Spacers)", "⚙️ Metal Spacers"), expanded=False):
    for s in METAL_SPACERS_LIST: 
        active_spacers[s] = create_inventory_row(f"{tr('سبسر', 'Spacer')} {s} mm", 100, f"sp_{s}")

with st.sidebar.expander(tr("🟡 ربر أصفر - علوي (ذكر)", "🟡 Yellow Rubber (Male)"), expanded=True):
    ref_dict_yellow = GERMAN_YELLOW if origin_key == "ألماني" else CHINESE_YELLOW
    for s, qty in ref_dict_yellow.items(): 
        active_top[s] = create_inventory_row(f"{tr('أصفر', 'Yellow')} {s} mm", qty, f"top_{s}")

with st.sidebar.expander(tr("🟢 ربر أخضر - سفلي (أنثى)", "🟢 Green Rubber (Female)"), expanded=True):
    ref_dict_green = GERMAN_GREEN if origin_key == "ألماني" else CHINESE_GREEN
    for s, qty in ref_dict_green.items(): 
        active_bottom[s] = create_inventory_row(f"{tr('أخضر', 'Green')} {s} mm", qty, f"bot_{s}")

calc = OrbitSlittingCalculator(top_inv=active_top, bottom_inv=active_bottom, spacer_inv=active_spacers)

# Create 5 Tabs
t1_name = tr("🔪 هندسة الشرحات (Slits)", "🔪 Slits Setup")
t2_name = tr("⚙️ إعدادات الرأس (Head B)", "⚙️ Head B Offset")
t3_name = tr("📐 حسابات الكويل (Coil Data)", "📐 Coil Calculations")
t4_name = tr("📦 تخطيط الدفعات (Batches)", "📦 Batches Planning")
t5_name = tr("🎛️ هندسة الشد (Tension)", "🎛️ Tension Specs")

tab1, tab2, tab3, tab4, tab5 = st.tabs([t1_name, t2_name, t3_name, t4_name, t5_name])

# -----------------------------------------
# TAB 1: MAIN SLIT CALCULATOR
# -----------------------------------------
with tab1:
    st.header(tr("هندسة وتخطيط الشرحات (مطابقة ذكية)", "Slit Arbor Engineering (Smart Symmetrical Focus)"))
    
    colA, colB = st.columns(2)
    with colA: coil_width = st.number_input(tr("عرض الكويل الإجمالي (mm):", "Total Mother Coil Width (mm):"), min_value=1.0, value=1000.0, step=1.0)
    with colB: num_slits = st.number_input(tr("عدد الشرحات المطلوبة:", "Number of Slits:"), min_value=1, max_value=20, value=3, step=1)
        
    st.divider()
    st.subheader(tr("أبعاد الشرحات", "Slit Widths Configuration"))
    
    slit_widths = []
    cols = st.columns(min(num_slits, 4))
    for i in range(int(num_slits)):
        with cols[i % len(cols)]:
            w = st.number_input(f"{tr('عرض الشرحة', 'Slit Width')} {i+1} (mm):", min_value=0.1, value=float(coil_width/num_slits), step=0.1, key=f"slit_{i}")
            slit_widths.append(w)
            
    total_slits_width = sum(slit_widths)
    if total_slits_width > coil_width:
        st.error(tr("⚠️ خطأ: المجموع يتجاوز عرض الكويل!", "⚠️ Error: Total slits width exceeds Mother Coil width!"))
    else:
        st.success(f"{tr('✅ العرض سليم. الفواقد (Scrap Trim):', '✅ Width OK. Scrap Trim:')} {coil_width - total_slits_width:.2f} mm")
        
        if st.button(tr("ابحث عن تشكيلات للعمودين", "🔍 Calculate Arbor Setups"), type="primary"):
            spacer_targets = [w - calc.knife_width for w in slit_widths]
            if any(t < 0 for t in spacer_targets):
                st.error(tr("أحد الشرحات أصغر من عرض السكينة!", "A slit width is smaller than the knife thickness!"))
            else:
                options = calc.get_multiple_arbor_options(spacer_targets, max_options=5)
                if options:
                    st.info(tr("✅ تم إيجاد خيارات ذكية.", "✅ Smart setup options generated."))
                    for i, arbor_setup in enumerate(options):
                        
                        # تحديد ما إذا كان الخيار يشتمل على تعويض طوارئ (غير متماثل)
                        has_asym = any(not c['is_sym'] for c in arbor_setup)
                        
                        if i == 0 and not has_asym:
                            st.markdown(f"""
                            <div style="background-color: #e3f2fd; padding: 12px; border-radius: 8px; margin-top: 30px; margin-bottom: 15px; border: 2px solid #2196f3;">
                                <h3 style="margin: 0; color: #0d47a1; text-align: center;">🚀 {tr('الخيار الأول: التجميع القياسي المتطابق (Symmetrical Setup)', 'Option 1: Standard Symmetrical Setup')}</h3>
                            </div>
                            """, unsafe_allow_html=True)
                        elif has_asym:
                            st.markdown(f"""
                            <div style="background-color: #f8d7da; padding: 12px; border-radius: 8px; margin-top: 30px; margin-bottom: 15px; border: 2px solid #dc3545;">
                                <h3 style="margin: 0; color: #721c24; text-align: center;">⚠️ {tr(f'خيار مساند رقم {i + 1} (استخدام تطابق غير متماثل بسبب نقص المخزون)', f'Fallback Option {i + 1} (Asymmetrical match due to inventory constraints)')}</h3>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style="background-color: #ffeb3b; padding: 12px; border-radius: 8px; margin-top: 30px; margin-bottom: 15px; border: 2px solid #fbc02d;">
                                <h3 style="margin: 0; color: #000; text-align: center;">🛠️ {tr(f'الخيار المرن رقم {i + 1} (تنويع متطابق)', f'Flexible Option {i + 1} (Symmetrical Diversity)')}</h3>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        total_y = Counter()
                        total_g = Counter()
                        for setup in arbor_setup:
                            total_y.update(setup['top']['yellow'])
                            total_y.update(setup['bottom']['yellow'])
                            total_g.update(setup['top']['green'])
                            total_g.update(setup['bottom']['green'])
                            
                        with st.expander(tr("📦 اضغط لمعرفة فاتورة المواد الإجمالية (BOM)", "📦 Click to view Bill of Materials (Total Rubber Required)"), expanded=False):
                            bom_c1, bom_c2 = st.columns(2)
                            with bom_c1:
                                st.info(tr("**إجمالي الربر الأصفر المطلوب (🟡)**", "**Total Yellow Rubber Required (🟡)**"))
                                st.write(f"- 🔪 {tr('سكينة', 'Knife')}: **{num_slits} {tr('حبة', 'pcs')}**")
                                for size, count in sorted(total_y.items(), reverse=True):
                                    st.write(f"- {tr('ربر أصفر مقاس', 'Yellow Rubber size')} {size} mm: **{count} {tr('حبة', 'pcs')}**")
                            with bom_c2:
                                st.success(tr("**إجمالي الربر الأخضر المطلوب (🟢)**", "**Total Green Rubber Required (🟢)**"))
                                st.write(f"- 🔪 {tr('سكينة', 'Knife')}: **{num_slits} {tr('حبة', 'pcs')}**")
                                for size, count in sorted(total_g.items(), reverse=True):
                                    st.write(f"- {tr('ربر أخضر مقاس', 'Green Rubber size')} {size} mm: **{count} {tr('حبة', 'pcs')}**")
                                
                        st.markdown(f"### 🔍 {tr('تفاصيل التركيب لكل شرحة:', 'Detailed Setup Per Slit:')}")
                        for slit_idx, setup in enumerate(arbor_setup):
                            is_sym = setup['is_sym']
                            sym_text = tr("✅ متطابق تماماً", "✅ Fully Symmetrical") if is_sym else tr("⚠️ غير متماثل القطع (مساند)", "⚠️ Asymmetrical Backup")
                            st.markdown(f"#### 🔹 {tr('الشرحة', 'Slit')} {slit_idx + 1} ({slit_widths[slit_idx]:.2f} mm) — *{sym_text}*")
                            c1, c2 = st.columns(2)
                            
                            with c1:
                                st.markdown(tr("🟡 **العمود العلوي (ذكر)**", "🟡 **Top Arbor (Male)**"))
                                st.markdown(f"- 🔪 {tr('سكينة', 'Knife')}: 8.0 mm (x1)")
                                if setup['top']['yellow']:
                                    for s, q in sorted(Counter(setup['top']['yellow']).items(), reverse=True): st.markdown(f"- 🟡 {tr('ربر أصفر', 'Yellow Rubber')}: {s} mm (x{q})")
                                if setup['top']['green']:
                                    for s, q in sorted(Counter(setup['top']['green']).items(), reverse=True): st.markdown(f"- 🟢 {tr('ربر أخضر', 'Green Rubber')}: {s} mm (x{q})")
                                if setup['top']['spacers']:
                                    for s, q in sorted(Counter(setup['top']['spacers']).items(), reverse=True): st.markdown(f"- ⚙️ {tr('سبسر', 'Spacer')}: {s} mm (x{q})")
                                    
                            with c2:
                                st.markdown(tr("🟢 **العمود السفلي (أنثى)**", "🟢 **Bottom Arbor (Female)**"))
                                st.markdown(f"- 🔪 {tr('سكينة', 'Knife')}: 8.0 mm (x1)")
                                if setup['bottom']['green']:
                                    for s, q in sorted(Counter(setup['bottom']['green']).items(), reverse=True): st.markdown(f"- 🟢 {tr('ربر أخضر', 'Green Rubber')}: {s} mm (x{q})")
                                if setup['bottom']['yellow']:
                                    for s, q in sorted(Counter(setup['bottom']['yellow']).items(), reverse=True): st.markdown(f"- 🟡 {tr('ربر أصفر', 'Yellow Rubber')}: {s} mm (x{q})")
                                if setup['bottom']['spacers']:
                                    for s, q in sorted(Counter(setup['bottom']['spacers']).items(), reverse=True): st.markdown(f"- ⚙️ {tr('سبسر', 'Spacer')}: {s} mm (x{q})")
                            st.markdown("---")
                else:
                    st.error(tr("❌ المخزون لا يكفي لإنشاء أعمدة بهذه الشرحات حتى مع استخدام البدائل.", "❌ Insufficient inventory to create arbors even with fallback options."))

# -----------------------------------------
# TAB 2: HEAD B OFFSET
# -----------------------------------------
with tab2:
    st.header(tr("إعدادات الرأس (Head B Offset)", "Head B Offset Calculator"))
    thickness_b = st.number_input(tr("سماكة الصاج (mm):", "Strip Thickness (mm):"), min_value=0.20, max_value=1.60, value=0.50, step=0.01)
    if st.button(tr("احسب أبعاد الرأس", "Calculate Offsets"), type="primary"):
        top_target, bottom_target = calc.get_offset_targets(thickness_b)
        if top_target:
            col1, col2 = st.columns(2)
            col1.metric(tr("الجانب العلوي (أصفر)", "Top Offset (Yellow)"), f"{top_target} mm")
            col2.metric(tr("الجانب السفلي (أخضر)", "Bottom Offset (Green)"), f"{bottom_target} mm")
            
            top_opt = calc._find_single_combo_legacy(top_target, calc.top_inv, calc.spacer_inv)
            if top_opt: st.info(f"**{tr('الترتيب العلوي:', 'Top Setup:')}** " + " + ".join([f"{s}mm(x{c})" for s, c in sorted(Counter(top_opt).items(), reverse=True)]))
            else: st.warning(tr("المخزون لا يغطي القياس العلوي.", "Inventory insufficient for Top offset."))
                
            bot_opt = calc._find_single_combo_legacy(bottom_target, calc.bottom_inv, calc.spacer_inv)
            if bot_opt: st.success(f"**{tr('الترتيب السفلي:', 'Bottom Setup:')}** " + " + ".join([f"{s}mm(x{c})" for s, c in sorted(Counter(bot_opt).items(), reverse=True)]))
            else: st.warning(tr("المخزون لا يغطي القياس السفلي.", "Inventory insufficient for Bottom offset."))

# -----------------------------------------
# TAB 3: COIL DATA
# -----------------------------------------
with tab3:
    st.header(tr("حسابات الكويل (الأوزان، الأطوال، والقطر الخارجي)", "Coil Data (Weight, Length, and OD)"))
    calc_mode = st.radio(tr("طريقة الحساب:", "Calculation Mode:"), 
                         [tr("حساب الطول من الوزن", "Calculate Length from Weight"), 
                          tr("حساب الوزن من الطول", "Calculate Weight from Length"), 
                          tr("حساب الطول والوزن من القطر الخارجي (OD)", "Calculate from Outer Diameter (OD)")], horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        material = st.selectbox(tr("المادة:", "Material:"), [tr("ألمنيوم (2.74)", "Aluminum (2.74)"), tr("حديد (7.85)", "Steel (7.85)")])
        density = 2.74 if "2.74" in material else 7.85
        width_m = st.number_input(tr("عرض الكويل (mm):", "Coil Width (mm):"), value=1230.0) / 1000.0
        thickness_coil = st.number_input(tr("السماكة (mm):", "Thickness (mm):"), min_value=0.01, value=0.27)
    with col2:
        line_speed = st.number_input(tr("السرعة (m/min):", "Line Speed (m/min):"), value=75.0)
        
        if "من الوزن" in calc_mode or "from Weight" in calc_mode:
            coil_weight = st.number_input(tr("الوزن الإجمالي للكويل (kg):", "Total Coil Weight (kg):"), value=4758.0)
        elif "من الطول" in calc_mode or "from Length" in calc_mode:
            coil_length_input = st.number_input(tr("الطول الإجمالي للكويل (متر):", "Total Coil Length (m):"), value=2060.0)
        else:
            outer_diameter = st.number_input(tr("القطر الخارجي OD (mm):", "Outer Diameter OD (mm):"), value=1433.0)
            inner_diameter = st.number_input(tr("القطر الداخلي ID (mm):", "Inner Diameter ID (mm):"), value=508.0)
            packing_factor = st.number_input(tr("معامل الرص (Packing Factor %):", "Packing Factor %:"), value=88.5) / 100.0
            
    if st.button(tr("احسب بيانات الكويل", "Calculate Coil Data"), type="primary"):
        weight_per_meter = thickness_coil * width_m * density
        if weight_per_meter > 0:
            
            if "من الوزن" in calc_mode or "from Weight" in calc_mode:
                coil_length = coil_weight / weight_per_meter
            elif "من الطول" in calc_mode or "from Length" in calc_mode:
                coil_length = coil_length_input
                coil_weight = coil_length * weight_per_meter
            else:
                area_mm2 = (math.pi / 4.0) * ((outer_diameter**2) - (inner_diameter**2)) * packing_factor
                coil_length = area_mm2 / (thickness_coil * 1000.0)
                coil_weight = coil_length * weight_per_meter
                
            st.divider()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(tr("الوزن لكل متر", "Weight Per Meter"), f"{weight_per_meter:.3f} kg/m")
            c2.metric(tr("الطول الإجمالي", "Total Length"), f"{coil_length:,.1f} {tr('متر', 'm')}")
            c3.metric(tr("الوزن الإجمالي", "Total Weight"), f"{coil_weight:,.1f} kg")
            c4.metric(tr("وقت التشغيل", "Processing Time"), f"{coil_length / line_speed:.1f} {tr('دقيقة', 'mins')}")

# -----------------------------------------
# TAB 4: BATCH PLANNING
# -----------------------------------------
with tab4:
    st.header(tr("تخطيط دفعات الإنتاج للكويل", "Batch Production Planning"))
    col_b1, col_b2 = st.columns(2)
    with col_b1: main_length = st.number_input(tr("الطول الإجمالي للكويل (متر):", "Total Coil Length (m):"), min_value=1.0, value=5000.0)
    with col_b2: num_batches = st.number_input(tr("عدد الدفعات المطلوبة (Batches):", "Number of Batches:"), min_value=1, value=2)
    
    st.divider()
    if num_batches > 0:
        batch_length = main_length / num_batches
        st.metric(label=tr("طول الدفعة الواحدة", "Length per Batch"), value=f"{batch_length:,.1f} {tr('متر', 'm')}")
        b_cols = st.columns(min(num_batches, 6))
        for i in range(int(num_batches)):
            with b_cols[i % len(b_cols)]: st.info(f"**{tr('الدفعة', 'Batch')} {i+1}**\n\n{batch_length:,.1f} {tr('م', 'm')}")

# -----------------------------------------
# TAB 5: TENSION CALIBRATION
# -----------------------------------------
with tab5:
    st.header(tr("🎛️ هندسة ومعايرة الشد (Tension Calibration)", "🎛️ Tension Engineering & Calibration"))
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        sel_alloy = st.selectbox(tr("نوع السبيكة (Alloy):", "Alloy Type:"), ["3105", "1050", "1100", "3003", "5005", "5052", "8011", tr("أخرى...", "Other...")])
        alloy_input = st.text_input(tr("إدخال يدوي:", "Manual Input:"), value="3105") if sel_alloy in ["أخرى...", "Other..."] else sel_alloy
    with col_t2: tension_thickness = st.number_input(tr("سماكة الصاج (mm) لحساب الشد:", "Thickness for Tension (mm):"), min_value=0.01, value=0.27)
    with col_t3: tension_width = st.number_input(tr("إجمالي عرض الشرحات (mm):", "Total Slits Width (mm):"), min_value=1.0, value=1230.0)
        
    if st.button(tr("⚙️ تحليل وحساب الشد", "⚙️ Analyze and Calculate Tension"), type="primary"):
        cls, rec_t, back_t, t_pct, end_t, t_reason = analyze_alloy(alloy_input, tension_thickness, tension_width)
        st.markdown(f"### 📊 {tr('تصنيف المادة:', 'Material Classification:')} **{cls}**")
        st.markdown(f"""
        <div class="metric-card"><h4 style="margin:0; color:#0056b3;">1. {tr('قوة لف الريكويلر (Recoiler)', 'Recoiler Tension')}</h4><h2 style="margin:0;">{rec_t:,.0f} Kg</h2></div>
        <div class="metric-card" style="border-left-color: #28a745;"><h4 style="margin:0; color:#28a745;">2. {tr('الشد العكسي (Back Tension)', 'Back Tension')}</h4><h2 style="margin:0;">{back_t:,.0f} Kg</h2></div>
        """, unsafe_allow_html=True)
        st.info(f"💡 **{tr('تحليل النظام للشد المتناقص:', 'System Analysis for Taper Tension:')}** {t_reason}")
        col_bar1, col_bar2 = st.columns([1, 3])
        with col_bar1: st.metric(label=tr("نسبة الانخفاض (Taper)", "Taper Percentage"), value=f"% {t_pct}")
        with col_bar2:
            st.markdown(f"**{tr('سينخفض من', 'Will taper down from')} `{rec_t:,.0f} Kg` {tr('إلى', 'to')} `{end_t:,.0f} Kg`**")
            st.progress(1.0 - (t_pct / 100.0))
